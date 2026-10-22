# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/config.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The options of the gateway. Every protection can be switched on and off, from the file and from the command line.

All protections are ON by default. Switching one off is allowed (an installation may have its own reasons), and every protection
that is off, or loosened, is listed by :func:`warnings` so that the program says it at start and in the ``policy`` command.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

SCHEMA = 1


class ConfigError(ValueError):
    """The configuration file is not valid."""


@dataclass
class WhitelistOptions:
    enabled: bool = True                      # only the identifiers of the specification a host sends cross to the bus
    unlock_dangerous: bool = False            # also let the dangerous ones (bootloader, persistent settings) cross
    extra_allow: list[int] = field(default_factory=list)   # identifiers added to the list
    deny: list[int] = field(default_factory=list)          # identifiers removed from the list, whatever the rest says


@dataclass
class PayloadOptions:
    enabled: bool = True                      # the length and the values of a frame must be those the specification allows


@dataclass
class RateOptions:
    enabled: bool = True
    per_id_hz: float = 20.0                   # a command with a watchdog is repeated about every 150 ms: 20 per second is plenty
    per_id_burst: float = 10.0
    global_hz: float = 200.0
    global_burst: float = 50.0
    dangerous_hz: float = 1.0                 # the limit of an unlocked dangerous identifier
    dangerous_burst: float = 2.0
    overrides: dict[str, list[float]] = field(default_factory=dict)   # "0x160": [rate, burst]


@dataclass
class SessionOptions:
    enabled: bool = True                      # a peer must prove it holds a key
    key_file: str = ""


@dataclass
class OutboundOptions:
    enabled: bool = True                      # only what a board sends goes towards the network
    rate_hz: float = 500.0                    # frames per second towards the network (0 = no limit)


@dataclass
class ServerOptions:
    host: str = "127.0.0.1"
    port: int = 8765
    allow_open_network: bool = False          # listen on a non-local address even without a session key


@dataclass
class GatewayConfig:
    whitelist: WhitelistOptions = field(default_factory=WhitelistOptions)
    payload: PayloadOptions = field(default_factory=PayloadOptions)
    rate: RateOptions = field(default_factory=RateOptions)
    session: SessionOptions = field(default_factory=SessionOptions)
    outbound: OutboundOptions = field(default_factory=OutboundOptions)
    server: ServerOptions = field(default_factory=ServerOptions)


_SECTIONS = {f.name: f.type for f in fields(GatewayConfig)}
_CLASSES = {"whitelist": WhitelistOptions, "payload": PayloadOptions, "rate": RateOptions, "session": SessionOptions, "outbound": OutboundOptions, "server": ServerOptions}


def _id(value: Any, where: str) -> int:
    if isinstance(value, str):
        try:
            value = int(value, 0)
        except ValueError:
            raise ConfigError(f"{where}: {value!r} is not an identifier") from None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0x7FF:
        raise ConfigError(f"{where}: an identifier is a number from 0 to 0x7FF")
    return value


def config_from_dict(data: Any) -> GatewayConfig:
    if not isinstance(data, dict):
        raise ConfigError("the configuration must be a JSON object")
    unknown = set(data) - set(_CLASSES) - {"schema"}
    if unknown:
        raise ConfigError(f"unknown section(s): {', '.join(sorted(unknown))}")
    if "schema" in data and data["schema"] != SCHEMA:
        raise ConfigError(f"schema must be {SCHEMA}")
    config = GatewayConfig()
    for name, cls in _CLASSES.items():
        raw = data.get(name)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            raise ConfigError(f"{name} must be an object")
        known = {f.name: f for f in fields(cls)}
        extra = set(raw) - set(known)
        if extra:
            raise ConfigError(f"{name}: unknown option(s): {', '.join(sorted(extra))}")
        section = getattr(config, name)
        for key, value in raw.items():
            default = getattr(section, key)
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    raise ConfigError(f"{name}.{key} must be true or false")
            elif isinstance(default, (int, float)):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ConfigError(f"{name}.{key} must be a number")
                if key.endswith(("_hz", "_burst")) and value < 0:
                    raise ConfigError(f"{name}.{key} must not be negative")
                if key == "port" and not 0 <= value <= 65535:
                    raise ConfigError("server.port must be 0 (the system chooses) to 65535")
            elif isinstance(default, str):
                if not isinstance(value, str):
                    raise ConfigError(f"{name}.{key} must be text")
            elif key in ("extra_allow", "deny"):
                if not isinstance(value, list):
                    raise ConfigError(f"{name}.{key} must be a list of identifiers")
                value = [_id(v, f"{name}.{key}") for v in value]
            elif key == "overrides":
                if not isinstance(value, dict):
                    raise ConfigError("rate.overrides must be an object")
                cleaned = {}
                for k, v in value.items():
                    ident = _id(k, "rate.overrides")
                    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0 for x in v)):
                        raise ConfigError(f"rate.overrides[{k}] must be [rate, burst], both positive")
                    cleaned[f"0x{ident:03X}"] = [float(v[0]), float(v[1])]
                value = cleaned
            setattr(section, key, value)
    return config


def load_config(path: str | Path) -> GatewayConfig:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read the configuration: {error}") from error
    except ValueError as error:
        raise ConfigError(f"the configuration is not valid JSON: {error}") from error
    return config_from_dict(data)


def config_to_dict(config: GatewayConfig) -> dict[str, Any]:
    out: dict[str, Any] = {"schema": SCHEMA}
    for name in _CLASSES:
        section = getattr(config, name)
        out[name] = {f.name: getattr(section, f.name) for f in fields(section)}
    return out


def warnings(config: GatewayConfig) -> list[str]:
    """One sentence for every protection that is off or loosened."""
    out: list[str] = []
    if not config.session.enabled:
        out.append("session authentication is OFF: any peer that reaches the port can send frames to the bus")
    if not config.whitelist.enabled:
        out.append("the identifier list is OFF: every identifier from the network crosses to the bus, bootloader included")
    elif config.whitelist.unlock_dangerous:
        out.append("dangerous identifiers are UNLOCKED: the bootloader, the slave update and the persistent settings can be reached from the network")
    if config.whitelist.extra_allow:
        out.append("identifiers added to the list by hand: " + ", ".join(f"0x{i:03X}" for i in config.whitelist.extra_allow))
    if not config.payload.enabled:
        out.append("the payload check is OFF: frames with a length or a value the specification refuses are forwarded")
    if not config.rate.enabled:
        out.append("the rate limit is OFF: a peer can flood the bus")
    if not config.outbound.enabled:
        out.append("the outbound filter is OFF: every frame of the bus goes to the network")
    if config.server.host not in ("127.0.0.1", "::1", "localhost") and not config.session.enabled:
        out.append(f"listening on {config.server.host} without session authentication")
    return out
