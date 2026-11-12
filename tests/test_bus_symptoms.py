# =============================================================================
# URTC-GATEWAY - tests/test_bus_symptoms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The gateway reads every frame of the bus, so it keeps the health frames (0x1B8) of the heads that are heard and recognises a bus that mixes speeds by its symptoms.
The thresholds and the heads known to be built for 500 kbit/s come from the ``bus_health`` section of its configuration. No change of the protocol."""
from __future__ import annotations

import pytest

from urtc_gateway import bus_health
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict
from urtc_gateway.gateway import Gateway

HEALTH = bus_health.CAN_ID_HEALTH_PROFILE


def health(tec=0, rec=0, bus_off=0) -> bytes:
    return bytes([tec, rec, bus_off, 16, 7, 65, 0x0C, 0xE4])


def make(config: GatewayConfig | None = None) -> tuple[Gateway, list]:
    sent: list = []
    cfg = config or config_from_dict({"session": {"enabled": False}})
    return Gateway(cfg, None, lambda i, d: None, sent.append, lambda: 0.0), sent


def test_the_default_section_has_the_thresholds_of_the_shared_module_and_is_written_with_the_rest():
    options = GatewayConfig().bus_health
    assert (options.tec_warn, options.rec_warn, options.bus_off_warn, options.legacy_heads) == (96, 96, 1, [])
    assert config_to_dict(GatewayConfig())["bus_health"] == {"tec_warn": 96, "rec_warn": 96, "bus_off_warn": 1, "legacy_heads": []}


def test_the_thresholds_and_the_legacy_heads_come_from_the_configuration_file():
    config = config_from_dict({"bus_health": {"tec_warn": 40, "rec_warn": 50, "bus_off_warn": 3, "legacy_heads": ["A", 7]}})
    assert (config.bus_health.tec_warn, config.bus_health.rec_warn, config.bus_health.bus_off_warn, config.bus_health.legacy_heads) == (40, 50, 3, ["A", "7"])


@pytest.mark.parametrize("section", [{"tec_warn": 0}, {"tec_warn": 256}, {"rec_warn": 1.5}, {"bus_off_warn": True}, {"legacy_heads": "A"}, {"legacy_heads": [None]},
                                     {"unknown": 1}])
def test_a_bad_value_is_refused_like_every_other_option_of_the_gateway(section):
    with pytest.raises(ConfigError):
        config_from_dict({"bus_health": section})


def test_a_quiet_bus_has_no_warning_and_the_summary_says_so():
    gateway, _ = make()
    gateway.from_bus(HEALTH, health())
    assert gateway.summary()["bus_warnings"] == []


def test_error_counters_or_a_bus_off_of_the_heads_that_are_heard_are_a_warning_and_are_handed_over():
    gateway, _ = make()
    gateway.from_bus(HEALTH, health(tec=100))
    assert gateway.bus_warnings() == [bus_health.BUS_ERRORS]
    assert gateway.bus_warnings() == []                     # the frames were handed over: nothing is said twice
    gateway.from_bus(HEALTH, health(bus_off=2))
    assert gateway.bus_warnings() == [bus_health.BUS_ERRORS]


def test_a_known_legacy_head_with_errors_is_a_mixed_bus():
    gateway, _ = make(config_from_dict({"session": {"enabled": False}, "bus_health": {"legacy_heads": ["HEAD-OLD"]}}))
    gateway.from_bus(HEALTH, health(rec=120))
    assert gateway.bus_warnings(("HEAD-OLD",)) == [bus_health.MIXED_BUS_SUSPECTED, bus_health.BUS_ERRORS, bus_health.LEGACY_HEAD_KNOWN]


def test_a_lower_threshold_in_the_file_warns_earlier():
    gateway, _ = make(config_from_dict({"session": {"enabled": False}, "bus_health": {"tec_warn": 50}}))
    gateway.from_bus(HEALTH, health(tec=60))
    assert gateway.bus_warnings() == [bus_health.BUS_ERRORS]


def test_a_health_frame_is_kept_even_when_the_policy_does_not_forward_it():
    gateway, sent = make(config_from_dict({"session": {"enabled": False}, "outbound": {"enabled": True, "rate_hz": 0.001}}))
    for _ in range(5):
        gateway.from_bus(HEALTH, health(tec=100))
    assert len(sent) <= 5 and gateway.bus_warnings() == [bus_health.BUS_ERRORS]


def test_only_the_last_frames_are_kept():
    gateway, _ = make()
    for _ in range(200):
        gateway.from_bus(HEALTH, health(tec=100))
    assert len(gateway.health_frames) == 64
