# =============================================================================
# URTC-GATEWAY - tests/test_update_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The header inside a firmware image, read from an update that passes through the gateway: what is cut, what crosses and what the switch decides."""
from __future__ import annotations

import struct

import pytest

from urtc_gateway import image_header as ih
from urtc_gateway import urtc_protocol as proto
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict, warnings
from urtc_gateway.gateway import Gateway
from urtc_gateway.policy import Policy
from urtc_gateway.update_guard import KINDS, UpdateGuard

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
    assert config_to_dict(config_from_dict({"update_image": {"header": "require"}}))["update_image"] == {"header": "require"}
    with pytest.raises(ConfigError, match="accept, warn or require"):
        config_from_dict({"update_image": {"header": "sometimes"}})
    with pytest.raises(ConfigError):
        config_from_dict({"update_image": {"header": 1}})
    assert not any("image header" in w for w in warnings(GatewayConfig()))
    assert any("image header" in w for w in warnings(config_from_dict({"update_image": {"header": "accept"}})))
