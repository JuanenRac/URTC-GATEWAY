# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Command line: show the policy, make a key file, list the identifiers and run the gateway.

    urtc-gateway policy [--config FILE] [protection flags]   the effective options and a warning for each protection that is off
    urtc-gateway ids [--config FILE]                          every identifier and what the gateway does with it
    urtc-gateway keygen FILE PEER [PEER ...]                  a new key file (never overwritten, owner-only)
    urtc-gateway run [--config FILE] [--bus loopback|COMx] ...  listen and forward

Every protection is on by default and has a flag to switch it off (and a flag to switch it back on, so a file can be overridden):
--no-session / --session, --no-whitelist / --whitelist, --unlock-dangerous, --no-payload-check / --payload-check,
--no-rate-limit / --rate-limit, --no-outbound-filter / --outbound-filter, --allow-id, --deny-id.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading

from . import __version__, ids, session
from .config import ConfigError, GatewayConfig, config_to_dict, load_config, warnings
from .policy import Policy


def _id(text: str) -> int:
    try:
        value = int(text, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an identifier") from None
    if not 0 <= value <= 0x7FF:
        raise argparse.ArgumentTypeError("an identifier is 0 to 0x7FF")
    return value


def add_protection_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", metavar="FILE", help="a JSON file with the options (see docs/POLICY.md)")
    for name, dest in (("session", "session"), ("whitelist", "whitelist"), ("payload-check", "payload"), ("rate-limit", "rate"), ("outbound-filter", "outbound")):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(f"--no-{name}", dest=f"off_{dest}", action="store_true", help=f"switch the {name.replace('-', ' ')} off")
        group.add_argument(f"--{name}", dest=f"on_{dest}", action="store_true", help=f"switch the {name.replace('-', ' ')} on (overrides the file)")
    parser.add_argument("--unlock-dangerous", action="store_true", help="let the bootloader and persistent-setting identifiers through")
    parser.add_argument("--allow-id", type=_id, action="append", default=[], metavar="ID", help="add an identifier to the list (repeatable)")
    parser.add_argument("--deny-id", type=_id, action="append", default=[], metavar="ID", help="remove an identifier from the list (repeatable)")
    parser.add_argument("--key-file", metavar="FILE", help="the session key file")


def config_from_args(args: argparse.Namespace) -> GatewayConfig:
    config = load_config(args.config) if getattr(args, "config", None) else GatewayConfig()
    for dest in ("session", "whitelist", "payload", "rate", "outbound"):
        if getattr(args, f"off_{dest}", False):
            getattr(config, dest).enabled = False
        if getattr(args, f"on_{dest}", False):
            getattr(config, dest).enabled = True
    if getattr(args, "unlock_dangerous", False):
        config.whitelist.unlock_dangerous = True
    config.whitelist.extra_allow = sorted(set(config.whitelist.extra_allow) | set(getattr(args, "allow_id", [])))
    config.whitelist.deny = sorted(set(config.whitelist.deny) | set(getattr(args, "deny_id", [])))
    if getattr(args, "key_file", None):
        config.session.key_file = args.key_file
    for attr in ("host", "port"):
        value = getattr(args, attr, None)
        if value is not None:
            setattr(config.server, attr, value)
    if getattr(args, "allow_open_network", False):
        config.server.allow_open_network = True
    return config


def cmd_policy(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    print(json.dumps(config_to_dict(config), indent=2))
    policy = Policy(config)
    print(f"identifiers a peer may send to the bus: {len(policy.inbound)}; dangerous, refused: {len(policy.dangerous - policy.inbound)}")
    notes = warnings(config)
    for note in notes:
        print(f"WARNING: {note}", file=sys.stderr)
    return 0


def cmd_ids(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    policy = Policy(config)
    for can_id in sorted(set(ids.proto.MESSAGES)):
        to_bus = "forward" if can_id in policy.inbound else ("refuse (dangerous)" if can_id in policy.dangerous else "refuse")
        to_net = "forward" if can_id in policy.outbound or not config.outbound.enabled else "refuse"
        print(f"0x{can_id:03X} {ids.name_of(can_id):<28} to bus: {to_bus:<19} to network: {to_net}")
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    try:
        session.write_new_key_file(args.file, args.peers)
    except (session.KeyError_, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {args.file} with {len(args.peers)} key(s); the keys are not shown. Give each peer only its own line.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from . import serve  # noqa: PLC0415
    try:
        config = config_from_args(args)
        keys = None
        if config.session.enabled:
            if not config.session.key_file:
                print("error: session authentication is on and no key file was given (--key-file, or switch it off with --no-session)", file=sys.stderr)
                return 2
            keys = session.load_keys(config.session.key_file)
            if not session.key_file_is_private(config.session.key_file):
                print("WARNING: the key file can be read by other users", file=sys.stderr)
    except (ConfigError, session.KeyError_, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    local = config.server.host in ("127.0.0.1", "::1", "localhost")
    if not local and not config.session.enabled and not config.server.allow_open_network:
        print("error: refusing to listen on a non-local address without session authentication (use --allow-open-network if you mean it)", file=sys.stderr)
        return 2
    for note in warnings(config):
        print(f"WARNING: {note}", file=sys.stderr)
    try:
        bus = serve.LoopbackBus() if args.bus == "loopback" else serve.SerialSlcanBus(args.bus, args.bitrate)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    stop = threading.Event()
    try:
        serve.run(config, keys, bus, stop)
    except KeyboardInterrupt:
        stop.set()
    finally:
        bus.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="urtc-gateway", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"urtc-gateway {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("policy", help="show the effective options and the warnings")
    add_protection_flags(p)
    p.set_defaults(func=cmd_policy)
    p = sub.add_parser("ids", help="list every identifier and what the gateway does with it")
    add_protection_flags(p)
    p.set_defaults(func=cmd_ids)
    p = sub.add_parser("keygen", help="write a new session key file")
    p.add_argument("file")
    p.add_argument("peers", nargs="+", metavar="PEER")
    p.set_defaults(func=cmd_keygen)
    p = sub.add_parser("run", help="listen on a TCP port and forward to a bus")
    add_protection_flags(p)
    p.add_argument("--host", default=None, help="address to listen on (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=None, help="port to listen on (default 8765)")
    p.add_argument("--bus", default="loopback", help="'loopback' (nothing on it) or the serial port of an SLCAN adapter")
    p.add_argument("--bitrate", type=int, default=500000)
    p.add_argument("--allow-open-network", action="store_true", help="listen on a non-local address even without session authentication")
    p.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

