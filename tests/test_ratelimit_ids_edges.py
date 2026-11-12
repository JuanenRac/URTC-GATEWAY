# =============================================================================
# URTC-GATEWAY - tests/test_ratelimit_ids_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The token buckets at the ends of their ranges and over generated times (a fixed seed), and the sets of identifiers that cross the gateway: they come from the
specification, never overlap, and the table in the documents is the one the code makes."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from urtc_gateway import ids
from urtc_gateway.ratelimit import RateLimiter, TokenBucket

SEED = 20261112
ROOT = Path(__file__).resolve().parents[1]


# ---- the bucket --------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("rate, burst", [(0, 1), (-1, 1), (10, 0.99), (10, 0), (10, -5)])
def test_a_bucket_needs_a_positive_rate_and_a_burst_of_at_least_one(rate, burst):
    with pytest.raises(ValueError):
        TokenBucket(rate, burst)


def test_the_burst_goes_out_at_once_and_then_nothing_until_time_passes():
    bucket = TokenBucket(10, 3)
    assert [bucket.allow(0.0) for _ in range(5)] == [True, True, True, False, False]
    assert bucket.allow(0.05) is False        # half a token
    assert bucket.allow(0.10) is True         # a whole one
    assert bucket.allow(0.10) is False


def test_the_tokens_never_pass_the_burst_however_long_the_wait():
    bucket = TokenBucket(1000, 2)
    assert bucket.allow(0.0) and bucket.allow(0.0)
    assert bucket.allow(10_000.0) and bucket.allow(10_000.0) and not bucket.allow(10_000.0)


def test_a_clock_that_goes_back_gives_no_extra_token():
    bucket = TokenBucket(1, 1)
    assert bucket.allow(100.0) is True
    assert bucket.allow(50.0) is False
    assert bucket.allow(50.5) is False
    assert bucket.allow(51.5) is True       # one second after the (earlier) last reading


def test_over_a_long_time_the_bucket_lets_through_the_rate_and_no_more():
    rng = random.Random(SEED)
    rate, burst = 20.0, 5.0
    bucket = TokenBucket(rate, burst)
    now, allowed = 0.0, 0
    for _ in range(20_000):
        now += rng.random() * 0.01
        allowed += bucket.allow(now)
    assert allowed <= burst + rate * now + 1
    assert allowed >= rate * now * 0.9      # a flood is held to the rate, not to far less


def test_a_bucket_that_has_never_been_asked_has_all_its_tokens():
    bucket = TokenBucket(5, 4)
    assert bucket.tokens == 4.0 and bucket.last_s is None


# ---- the limiter -------------------------------------------------------------------------------------------------------------------------------

def test_a_flood_of_one_identifier_does_not_use_the_tokens_of_the_others():
    limiter = RateLimiter(global_hz=1000, global_burst=1000, per_id_hz=1, per_id_burst=2)
    first = [limiter.allow(0x100, 0.0) for _ in range(10)]
    assert first == [True, True] + [False] * 8
    assert limiter.allow(0x101, 0.0) is True


def test_the_global_bucket_limits_the_sum_of_all_identifiers():
    limiter = RateLimiter(global_hz=1, global_burst=3, per_id_hz=100, per_id_burst=100)
    results = [limiter.allow(0x100 + i, 0.0) for i in range(6)]
    assert results == [True, True, True, False, False, False]


def test_an_identifier_that_is_refused_by_its_own_bucket_does_not_spend_a_global_token():
    limiter = RateLimiter(global_hz=1, global_burst=2, per_id_hz=1, per_id_burst=1)
    assert limiter.allow(0x100, 0.0) is True
    assert limiter.allow(0x100, 0.0) is False      # refused by its own bucket: no global token spent
    assert limiter.allow(0x101, 0.0) is True       # the second global token is still there


def test_an_override_replaces_the_default_for_its_identifier_only():
    limiter = RateLimiter(100, 100, per_id_hz=1, per_id_burst=1, overrides={0x200: (1, 4)})
    assert sum(limiter.allow(0x200, 0.0) for _ in range(10)) == 4
    assert sum(limiter.allow(0x201, 0.0) for _ in range(10)) == 1


def test_the_overrides_are_copied_so_a_later_change_does_not_alter_the_limiter():
    overrides = {0x200: (1.0, 4.0)}
    limiter = RateLimiter(100, 100, 1, 1, overrides)
    overrides[0x200] = (1.0, 1.0)
    assert sum(limiter.allow(0x200, 0.0) for _ in range(10)) == 4


def test_a_limiter_with_a_bad_default_refuses_when_the_first_frame_of_an_identifier_arrives():
    limiter = RateLimiter(100, 100, per_id_hz=0, per_id_burst=1)
    with pytest.raises(ValueError):
        limiter.allow(0x100, 0.0)


# ---- the identifiers ---------------------------------------------------------------------------------------------------------------------------

def test_the_inbound_and_the_dangerous_identifiers_never_overlap_and_together_are_what_the_hosts_send():
    inbound, dangerous = ids.inbound_ids(), ids.dangerous_ids()
    assert inbound and dangerous and not inbound & dangerous
    assert inbound | dangerous == frozenset(ids._from_hosts())


def test_a_rack_order_never_goes_towards_the_bus_and_a_rack_reply_goes_towards_the_network():
    rack = ids.rack_ids()
    assert rack and not rack & ids.inbound_ids() and not rack & ids.dangerous_ids()
    replies = {i for i, direction in ids.RACK_DIRECTIONS.items() if direction == "rack_to_host"}
    assert replies and replies <= ids.outbound_ids()
    assert not {i for i, direction in ids.RACK_DIRECTIONS.items() if direction != "rack_to_host"} & ids.outbound_ids()


def test_every_dangerous_identifier_has_a_reason_and_no_other_has_one():
    for can_id in ids.dangerous_ids():
        assert isinstance(ids.dangerous_reason(can_id), str) and ids.dangerous_reason(can_id)
    for can_id in ids.inbound_ids():
        assert ids.dangerous_reason(can_id) is None
    assert ids.dangerous_reason(0x7FF) is None or 0x7FF in ids.MESSAGES


def test_a_question_is_never_dangerous_whatever_its_group():
    for can_id, info in ids.MESSAGES.items():
        if info["name"].startswith("QUERY_") and not info.get("gates", {}).get("needs_magic"):
            assert ids.dangerous_reason(can_id) is None


def test_a_message_that_needs_a_magic_payload_is_always_dangerous():
    magic = [i for i, info in ids.MESSAGES.items() if info.get("gates", {}).get("needs_magic")]
    assert magic
    for can_id in magic:
        assert ids.dangerous_reason(can_id) is not None


def test_names_are_the_specification_name_the_rack_name_or_the_hex_for_an_unknown_identifier():
    some = next(iter(ids.MESSAGES))
    assert ids.name_of(some) == ids.MESSAGES[some]["name"]
    for can_id, name in ids.RACK_NAMES.items():
        if can_id not in ids.MESSAGES:
            assert ids.name_of(can_id) == "RACK_" + name
    unknown = next(i for i in range(0x7FF, 0, -1) if i not in ids.MESSAGES and i not in ids.RACK_NAMES)
    assert ids.name_of(unknown) == f"0x{unknown:03X}"


def test_the_table_has_one_row_per_identifier_and_is_the_one_in_the_documents():
    table = ids.table_markdown()
    rows = [line for line in table.splitlines() if line.startswith("| 0x")]
    assert len(rows) == len(set(ids.MESSAGES) | ids.rack_ids())
    assert [row.split("|")[1].strip() for row in rows] == sorted((row.split("|")[1].strip() for row in rows), key=lambda text: int(text, 16))
    published = ROOT / "docs" / "ALLOWED_IDS.md"
    if published.exists():
        assert published.read_bytes().decode("utf-8").replace("\r\n", "\n") == table
