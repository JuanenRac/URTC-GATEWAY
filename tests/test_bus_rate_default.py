# =============================================================================
# URTC-GATEWAY - tests/test_bus_rate_default.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bus of the tool heads runs at 1 Mbit/s: the gateway opens an SLCAN adapter at that speed unless it is told another one (500 kbit/s for early boards)."""
from __future__ import annotations

import inspect

from urtc_gateway import cli
from urtc_gateway.serve import SerialSlcanBus
from urtc_gateway.urtc_protocol import BITRATE, BITRATE_LEGACY


def test_the_default_speed_is_one_megabit_and_the_legacy_one_is_half():
    assert BITRATE == 1_000_000 and BITRATE_LEGACY == 500_000


def test_the_command_line_default_is_the_speed_of_the_bus_of_the_tool_heads():
    args = cli.build_parser().parse_args(["run"])
    assert args.bitrate == BITRATE
    assert cli.build_parser().parse_args(["run", "--bitrate", "500000"]).bitrate == BITRATE_LEGACY


def test_an_adapter_is_opened_at_one_megabit_by_default(monkeypatch):
    assert inspect.signature(SerialSlcanBus.__init__).parameters["bitrate"].default == BITRATE
    assert SerialSlcanBus.BITRATE_CODES[BITRATE] == "S8" and SerialSlcanBus.BITRATE_CODES[BITRATE_LEGACY] == "S6"
