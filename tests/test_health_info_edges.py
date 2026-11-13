# =============================================================================
# URTC-GATEWAY - tests/test_health_info_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The identity frame of a head (0x1BB) over generated frames with a fixed seed, and the text of a rate: what is encoded is read back, a frame of the wrong length or of an
older version never declares a rate, and an unknown code is never taken for one."""
from __future__ import annotations

import random

import pytest

from urtc_gateway import health_info as hi

SEED = 20261113
RATES = [1_000_000, 500_000, 250_000, 125_000]


def test_a_frame_of_version_two_gives_back_what_was_encoded():
    rng = random.Random(SEED)
    for _ in range(300):
        version = rng.randrange(2, 6)
        fields = (rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.randrange(0, 70_000))
        rate = rng.choice(RATES + [None, 3, 750_000])
        info = hi.parse(hi.encode(version, *fields, rate))
        assert info is not None and info.protocol_version == version
        assert (info.reset_cause, info.fw_minor, info.fw_patch, info.fw_build) == fields[:4]
        assert info.uptime_s == min(fields[4], hi.UPTIME_V2_MAX)
        assert info.rate_bps == (rate if rate in RATES else None)
        assert info.rate_code == (hi.CODE_OF_RATE[rate] if rate in RATES else hi.CODE_UNKNOWN)


def test_a_frame_of_version_one_has_a_long_uptime_and_never_a_rate():
    rng = random.Random(SEED)
    for _ in range(100):
        uptime = rng.randrange(0, 0x1000000)
        info = hi.parse(hi.encode(1, 1, 2, 3, 4, uptime, rng.choice(RATES)))
        assert info is not None and info.rate_code is None and info.rate_bps is None and info.uptime_s == uptime
    assert hi.parse(hi.encode(0, 0, 0, 0, 0, 5, 1_000_000)).rate_bps is None


@pytest.mark.parametrize("length", [0, 1, 7, 9, 64])
def test_a_payload_that_is_not_eight_bytes_is_not_a_frame(length):
    assert hi.parse(bytes(length)) is None


def test_a_code_that_this_reader_does_not_know_is_no_rate():
    for code in (0, 5, 9, 0x7F, 0xFF):
        frame = bytes([2, 0, 0, 0, 0, code, 0, 1])
        info = hi.parse(frame)
        assert info is not None and info.rate_code == code and info.rate_bps is None


def test_the_uptime_is_clamped_to_what_each_version_can_hold():
    assert hi.parse(hi.encode(2, 0, 0, 0, 0, 10**9)).uptime_s == hi.UPTIME_V2_MAX
    assert hi.parse(hi.encode(2, 0, 0, 0, 0, -5)).uptime_s == 0
    assert hi.parse(hi.encode(1, 0, 0, 0, 0, 10**9)).uptime_s == 0xFFFFFF


def test_the_rates_that_the_frames_declare_come_in_order_and_skip_the_ones_that_declare_nothing():
    frames = [hi.encode(2, 0, 0, 0, 0, 1, 1_000_000), hi.encode(1, 0, 0, 0, 0, 1, 500_000), bytes(3), hi.encode(2, 0, 0, 0, 0, 1), hi.encode(2, 0, 0, 0, 0, 1, 500_000)]
    assert hi.declared_rates(frames) == [1_000_000, 500_000]
    assert hi.declared_rates([]) == []
    assert hi.declared_rates(bytearray(frame) for frame in frames) == [1_000_000, 500_000]


def test_the_rate_of_each_head_is_its_last_declaration_or_none():
    heads = {"A": hi.encode(2, 0, 0, 0, 0, 1, 250_000), 7: hi.encode(1, 0, 0, 0, 0, 1, 250_000), "C": b"short", "D": hi.encode(2, 0, 0, 0, 0, 1)}
    assert hi.rates_by_head(heads) == {"A": 250_000, "7": None, "C": None, "D": None}
    assert hi.rates_by_head({}) == {}


@pytest.mark.parametrize("rate, text", [(None, ""), (0, ""), (1_000_000, "1 Mbit/s"), (2_000_000, "2 Mbit/s"), (500_000, "500 kbit/s"), (125_000, "125 kbit/s"), (1_500_000, "1500 kbit/s")])
def test_the_rate_is_written_in_numbers_only(rate, text):
    assert hi.rate_text(rate) == text
