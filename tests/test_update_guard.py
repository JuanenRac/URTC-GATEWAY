# =============================================================================
# URTC-GATEWAY - tests/test_update_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The header inside a firmware image, read from an update that passes through the gateway: what is cut, what crosses and what the switch decides."""
from __future__ import annotations

import json
import socket
import struct
import threading

import pytest

from urtc_gateway import cli, serve
from urtc_gateway import image_header as ih
from urtc_gateway import urtc_protocol as proto
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict, warnings
from urtc_gateway.gateway import Gateway
from urtc_gateway.policy import Policy
from urtc_gateway.serve import LoopbackBus
from urtc_gateway.update_guard import KINDS, UpdateGuard, default_state_file

MAIN, SLAVE = proto.HARDWARE_ID_MAIN, proto.HARDWARE_ID_SLAVE


def firmware(hardware: int = MAIN, length: int = 2048, sealed: bool = True) -> bytes:
    raw = bytearray((i * 31 + 7) & 0x7F for i in range(length))
    raw[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 32] = ih.embedded_slot(hardware, (0, 8, 1, 3))
    return ih.seal_embedded(bytes(raw)) if sealed else bytes(raw)


def plain(length: int = 2048) -> bytes:
    return bytes((i * 31 + 7) & 0x7F for i in range(length))


def frames(kind: str, image: bytes, hardware: int, announced: int | None = None):
    start, data_id, end = KINDS[kind]
    yield start, struct.pack(">II", len(image) if announced is None else announced, hardware)
    for i in range(0, len(image), 8):
        yield data_id, image[i:i + 8]
    yield end, b""


def run(guard: UpdateGuard, kind: str, image: bytes, hardware: int, announced: int | None = None):
    return [(can_id, guard.check(can_id, data)) for can_id, data in frames(kind, image, hardware, announced)]


def refused_at(result):
    return next((index for index, (_id, verdict) in enumerate(result) if verdict.refused), None)


@pytest.mark.parametrize("kind, hardware", [("main", MAIN), ("slave", SLAVE)])
def test_an_update_with_a_good_header_crosses_whole(kind, hardware):
    result = run(UpdateGuard(), kind, firmware(hardware), hardware)
    assert refused_at(result) is None and all(v.code == "ok" for _i, v in result)


def test_an_image_for_the_other_board_is_cut_as_soon_as_the_header_is_read():
    result = run(UpdateGuard(), "main", firmware(SLAVE), MAIN)
    cut = refused_at(result)
    assert cut is not None and cut > 1
    # the first bytes (up to the end of the header) crossed; the frame that completes the header, everything after it and the end frame are refused
    assert cut == (ih.EMBED_OFFSET + 32) // 8   # frame 0 is the start frame, so data frame number 68 is at index 68
    assert all(v.refused for _i, v in result[cut:]) and "0x0303CB01" in result[cut][1].detail
    assert result[-1][1].refused


def test_a_length_that_is_not_the_one_announced_is_cut():
    image = firmware()
    result = run(UpdateGuard(), "main", image, MAIN, announced=len(image) + 8)
    assert refused_at(result) is not None and "announced" in result[refused_at(result)][1].detail


def test_a_damaged_or_unsealed_header_is_cut_whatever_the_switch():
    broken = bytearray(firmware())
    broken[ih.EMBED_OFFSET + 9] ^= 1
    for policy in ih.POLICIES:
        assert refused_at(run(UpdateGuard(policy), "main", bytes(broken), MAIN)) is not None
        assert refused_at(run(UpdateGuard(policy), "main", firmware(sealed=False), MAIN)) is not None


def test_the_switch_decides_an_image_without_a_header():
    assert refused_at(run(UpdateGuard("accept"), "main", plain(), MAIN)) is None
    warned = run(UpdateGuard("warn"), "main", plain(), MAIN)
    assert refused_at(warned) is None and [v.code for _i, v in warned].count("ok_no_header") == 1
    required = run(UpdateGuard("require"), "main", plain(), MAIN)
    assert refused_at(required) is not None and "requires" in required[refused_at(required)][1].detail
    assert refused_at(run(UpdateGuard("sometimes"), "main", plain(), MAIN)) is not None   # an unknown word is the strictest


def test_an_image_too_short_to_hold_the_header_follows_the_switch():
    assert refused_at(run(UpdateGuard("require"), "main", plain(200), MAIN)) is not None
    assert [v.code for _i, v in run(UpdateGuard("warn"), "main", plain(200), MAIN)].count("ok_no_header") == 1


def test_frames_that_are_not_an_update_and_data_without_a_start_are_not_looked_at():
    guard = UpdateGuard("require")
    assert not guard.check(proto.CAN_ID_QUERY_VERSION, b"").refused
    assert not guard.check(proto.CAN_ID_DATA, b"12345678").refused
    assert not guard.check(proto.CAN_ID_START_UPDATE, b"\x00").refused and not guard.active("main")


def test_a_new_start_begins_again_and_the_two_boards_are_followed_apart():
    guard = UpdateGuard()
    assert refused_at(run(guard, "main", firmware(SLAVE), MAIN)) is not None
    assert refused_at(run(guard, "main", firmware(MAIN), MAIN)) is None   # the next update is judged on its own
    start_main = KINDS["main"][0]
    start_slave = KINDS["slave"][0]
    guard.check(start_main, struct.pack(">II", 2048, MAIN))
    guard.check(start_slave, struct.pack(">II", 2048, SLAVE))
    assert guard.active("main") and guard.active("slave")


def test_the_policy_and_the_gateway_use_it():
    config = config_from_dict({"whitelist": {"unlock_dangerous": True}, "rate": {"enabled": False}, "session": {"enabled": False}, "payload": {"enabled": False},
                               "update_image": {"header": "require"}})
    sent: list[tuple[int, bytes]] = []
    gateway = Gateway(config, None, lambda i, d: sent.append((i, d)), lambda m: None, lambda: 1000.0)
    outcome = [gateway.from_network({"id": i, "data": d.hex()}) for i, d in frames("main", plain(), MAIN)]
    assert not all(d.allowed for d in outcome) and gateway.stats.refused["bad_image_header"] > 0
    assert len(sent) < len(outcome)
    assert isinstance(Policy(config).guard, UpdateGuard)


def test_a_note_is_left_in_the_audit_for_an_image_without_header():
    config = config_from_dict({"whitelist": {"unlock_dangerous": True}, "rate": {"enabled": False}, "session": {"enabled": False}, "payload": {"enabled": False}})
    gateway = Gateway(config, None, lambda i, d: None, lambda m: None, lambda: 1000.0)
    for can_id, data in frames("main", plain(), MAIN):
        gateway.from_network({"id": can_id, "data": data.hex()})
    assert any("note ok_no_header" in line for line in gateway.audit) and not gateway.stats.refused


def test_the_option_is_validated_listed_and_warned_about():
    assert GatewayConfig().update_image.header == "warn"
    assert config_to_dict(config_from_dict({"update_image": {"header": "require"}}))["update_image"] == {"header": "require", "remember_refused": True, "state_file": ""}
    with pytest.raises(ConfigError, match="accept, warn or require"):
        config_from_dict({"update_image": {"header": "sometimes"}})
    with pytest.raises(ConfigError):
        config_from_dict({"update_image": {"header": 1}})
    assert not any("image header" in w for w in warnings(GatewayConfig()))
    assert any("image header" in w for w in warnings(config_from_dict({"update_image": {"header": "accept"}})))


@pytest.mark.parametrize("kind, hardware", [("main", MAIN), ("slave", SLAVE)])
def test_a_refused_update_stays_refused_when_the_end_frame_is_sent_again(kind, hardware):
    guard = UpdateGuard("require")
    start, data_id, end = KINDS[kind]
    assert refused_at(run(guard, kind, plain(), hardware)) is not None
    # the board never got an end frame, so it is still in the update: neither a second end frame nor more data may cross
    assert guard.check(end, b"").refused
    assert guard.check(data_id, b"12345678").refused
    assert guard.check(end, b"").refused
    # a start frame too short to be one does not clear it either
    assert not guard.check(start, b"\x00").refused
    assert guard.check(end, b"").refused
    # a whole new start does
    assert refused_at(run(guard, kind, firmware(hardware), hardware)) is None


def test_a_refused_update_stays_refused_for_the_next_connection():
    config = config_from_dict({"whitelist": {"unlock_dangerous": True}, "rate": {"enabled": False}, "session": {"enabled": False}, "payload": {"enabled": False},
                               "update_image": {"header": "require"}, "server": {"port": 0}})
    bus, stop, ready, bound = LoopbackBus(), threading.Event(), threading.Event(), []
    server = threading.Thread(target=serve.run, args=(config, None, bus, stop), kwargs={"log": lambda text: None, "ready": ready, "bound": bound}, daemon=True)
    server.start()
    try:
        assert ready.wait(5)
        image = list(frames("main", plain(), MAIN))
        assert "bad_image_header" in refusals(bound[0], image)
        assert refusals(bound[0], [image[-1]]) == ["bad_image_header", "bad_frame"]   # the end frame alone, from a new connection
        assert KINDS["main"][2] not in [can_id for can_id, _data in bus.sent]
    finally:
        stop.set()
        server.join(timeout=5)


def refusals(port: int, messages) -> list[str]:
    """Send the frames and then a line that is not one; the codes of the refusals up to the one that answers that last line."""
    with socket.create_connection(("127.0.0.1", port), timeout=10) as peer:
        reader = peer.makefile("rb")
        reader.readline()   # the greeting
        peer.sendall(b"".join(json.dumps({"id": can_id, "data": data.hex()}).encode() + b"\n" for can_id, data in messages) + b"[]\n")
        codes: list[str] = []
        while "bad_frame" not in codes:
            codes.append(json.loads(reader.readline())["code"])
        return codes


def refuse(state, kind: str = "main", hardware: int = MAIN) -> UpdateGuard:
    guard = UpdateGuard("require", state)
    assert refused_at(run(guard, kind, plain(), hardware)) is not None
    return guard


@pytest.mark.parametrize("kind, hardware", [("main", MAIN), ("slave", SLAVE)])
def test_a_refused_update_is_still_refused_after_a_restart(tmp_path, kind, hardware):
    state = tmp_path / "sub" / "refused.json"
    refuse(state, kind, hardware)
    start, data_id, end = KINDS[kind]
    again = UpdateGuard("require", state)
    assert again.refused_kinds() == [kind]
    assert again.check(end, b"").refused and again.check(data_id, b"12345678").refused
    assert not again.check(start, b"\x00").refused
    assert UpdateGuard("require", state).refused_kinds() == [kind]   # a start frame too short clears nothing
    assert refused_at(run(again, kind, firmware(hardware), hardware)) is None
    assert UpdateGuard("require", state).refused_kinds() == []       # a whole new start does, in the file too


def test_clearing_one_kind_keeps_the_other_in_the_file(tmp_path):
    state = tmp_path / "refused.json"
    guard = refuse(state)
    assert refused_at(run(guard, "slave", plain(), SLAVE)) is not None
    run(guard, "main", firmware(), MAIN)
    assert UpdateGuard("require", state).refused_kinds() == ["slave"]


def test_no_state_file_yet_refuses_nothing_and_a_good_update_leaves_nothing_to_remember(tmp_path):
    state = tmp_path / "refused.json"
    guard = UpdateGuard("require", state)
    assert guard.refused_kinds() == [] and refused_at(run(guard, "main", firmware(), MAIN)) is None
    assert json.loads(state.read_text(encoding="utf-8")) == {"schema": 1, "refused": {}, "pending": []}
    assert UpdateGuard("require", state).refused_kinds() == []


@pytest.mark.parametrize("kind, hardware", [("main", MAIN), ("slave", SLAVE)])
@pytest.mark.parametrize("sent", [0, 1, 60])   # data frames before the restart: none, the first, and still short of the header
def test_an_update_whose_header_was_not_read_is_cut_by_a_restart(tmp_path, kind, hardware, sent):
    state = tmp_path / "refused.json"
    image = list(frames(kind, firmware(hardware), hardware))
    guard = UpdateGuard("warn", state)
    assert not any(guard.check(can_id, data).refused for can_id, data in image[:1 + sent])
    said: list[str] = []
    again = UpdateGuard("warn", state, said.append)
    _start, data_id, end = KINDS[kind]
    assert again.refused_kinds() == [kind]
    assert again.check(data_id, b"12345678").refused and "restarted" in again.check(end, b"").detail
    assert UpdateGuard("warn", state).refused_kinds() == [kind]   # and after one more restart
    assert refused_at(run(again, kind, firmware(hardware), hardware)) is None   # a whole new update is followed as always
    assert UpdateGuard("warn", state).refused_kinds() == []


@pytest.mark.parametrize("policy, image", [("require", firmware()), ("warn", plain()), ("accept", plain())])
def test_an_update_whose_header_was_judged_goes_on_after_a_restart(tmp_path, policy, image):
    state = tmp_path / "refused.json"
    whole = list(frames("main", image, MAIN))
    judged = 1 + (ih.EMBED_OFFSET + ih.HEADER_SIZE) // 8
    guard = UpdateGuard(policy, state)
    assert not any(guard.check(can_id, data).refused for can_id, data in whole[:judged])
    again = UpdateGuard(policy, state)
    assert again.refused_kinds() == [] and not any(again.check(can_id, data).refused for can_id, data in whole[judged:])


def test_an_update_ended_or_dropped_before_its_header_leaves_nothing_to_remember(tmp_path):
    state = tmp_path / "refused.json"
    start, _data_id, end = KINDS["main"]
    for closing in ((end, b""), (start, b"\x00")):
        guard = UpdateGuard("require", state)
        guard.check(start, struct.pack(">II", 2048, MAIN))
        assert UpdateGuard("require", state).refused_kinds() == ["main"]
        guard.check(*closing)
        assert UpdateGuard("require", state).refused_kinds() == []


def test_a_record_of_an_earlier_version_is_still_read(tmp_path):
    state = tmp_path / "refused.json"
    state.write_bytes(b'{"schema": 1, "refused": {"slave": "refused then"}}')
    assert UpdateGuard("warn", state).refused_kinds() == ["slave"]


@pytest.mark.parametrize("content", [b"", b"{", b"[]", b'{"schema": 2, "refused": {}}', b'{"schema": 1, "refused": {"other": "x"}}',
                                     b'{"schema": 1, "refused": {"main": ""}}', b"\xff\xfe", b" " * 5000,
                                     b'{"schema": 1, "refused": {}, "pending": "main"}', b'{"schema": 1, "refused": {}, "pending": [["main"]]}'])
def test_a_state_file_that_cannot_be_read_refuses_until_a_new_start(tmp_path, content):
    state = tmp_path / "refused.json"
    state.write_bytes(content)
    said: list[str] = []
    guard = UpdateGuard("warn", state, said.append)
    assert guard.refused_kinds() == ["main", "slave"] and "could not be read" in said[0]
    assert guard.check(KINDS["main"][2], b"").refused
    run(guard, "main", firmware(), MAIN)
    assert UpdateGuard("warn", state).refused_kinds() == ["slave"]


def test_a_state_file_that_cannot_be_written_still_refuses_and_says_so(tmp_path):
    blocker = tmp_path / "a_file"
    blocker.write_text("x", encoding="utf-8")
    said: list[str] = []
    guard = UpdateGuard("require", blocker / "refused.json", said.append)
    said.clear()
    assert refused_at(run(guard, "main", plain(), MAIN)) is not None
    assert guard.check(KINDS["main"][2], b"").refused and any("could not be written" in line for line in said)


def test_the_gateway_remembers_across_a_restart_of_the_service(tmp_path):
    config = config_from_dict({"whitelist": {"unlock_dangerous": True}, "rate": {"enabled": False}, "session": {"enabled": False}, "payload": {"enabled": False},
                               "update_image": {"header": "require", "state_file": str(tmp_path / "refused.json")}, "server": {"port": 0}})
    image = list(frames("main", plain(), MAIN))
    said: list[str] = []

    def service(messages):
        bus, stop, ready, bound = LoopbackBus(), threading.Event(), threading.Event(), []
        server = threading.Thread(target=serve.run, args=(config, None, bus, stop), kwargs={"log": said.append, "ready": ready, "bound": bound}, daemon=True)
        server.start()
        try:
            assert ready.wait(5)
            return refusals(bound[0], messages), [can_id for can_id, _data in bus.sent]
        finally:
            stop.set()
            server.join(timeout=5)

    assert "bad_image_header" in service(image)[0]
    codes, sent = service([image[-1]])
    assert codes == ["bad_image_header", "bad_frame"] and KINDS["main"][2] not in sent
    assert any("still refused from before the restart" in line for line in said)
    config.update_image.remember_refused = False
    codes, sent = service([image[-1]])
    assert codes == ["bad_frame"] and KINDS["main"][2] in sent


def test_the_options_of_the_record_come_from_the_file_and_the_command_line():
    config = config_from_dict({"update_image": {"remember_refused": False, "state_file": "here.json"}})
    assert (config.update_image.remember_refused, config.update_image.state_file) == (False, "here.json")
    assert any("not remembered" in line for line in warnings(config)) and not any("not remembered" in line for line in warnings(GatewayConfig()))
    with pytest.raises(ConfigError):
        config_from_dict({"update_image": {"remember_refused": 1}})
    args = cli.build_parser().parse_args(["policy", "--no-remember-refused", "--update-state-file", "there.json"])
    given = cli.config_from_args(args)
    assert (given.update_image.remember_refused, given.update_image.state_file) == (False, "there.json")


def test_the_default_record_is_one_file_per_bus():
    one, other = default_state_file("/dev/ttyACM0"), default_state_file("/dev/ttyACM1")
    assert one != other and one.parent == other.parent and one.parent.name == ".urtc-gateway"
    assert default_state_file("socket://127.0.0.1:7777").name.startswith("refused-updates-socket_127_0_0_1_7777-")


@pytest.mark.parametrize("bus, flags, expected", [("loopback", [], ""), ("COM7", [], "default"), ("COM7", ["--no-remember-refused"], ""),
                                                  ("COM7", ["--update-state-file", "x.json"], "x.json")])
def test_run_chooses_the_record_for_a_real_bus(monkeypatch, bus, flags, expected):
    seen: list[str] = []

    class Port(LoopbackBus):
        def __init__(self, *args) -> None:
            super().__init__()

    monkeypatch.setattr(serve, "SerialSlcanBus", Port)
    monkeypatch.setattr(serve, "run", lambda config, *rest, **kw: seen.append(config.update_image.state_file))
    assert cli.cmd_run(cli.build_parser().parse_args(["run", "--bus", bus, "--no-session", *flags])) == 0
    assert seen == [str(default_state_file(bus)) if expected == "default" else expected]
