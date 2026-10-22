# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A gateway in front of the URTC CAN bus: a list of allowed identifiers, a limit on the rate, and a session key.

The bus has no sender authentication (see the CAN threat model of the URTC repository). When it cannot be kept closed, the place
to add protection is a gateway that only lets a known set of frames through, slows them down, and only listens to a peer that
proves it holds a key. This package is that gateway as software; it has not been run against a real bus.
"""
from __future__ import annotations

__version__ = "0.0.1"
