#!/usr/bin/env python3
# =============================================================================
# URTC-GATEWAY - tools/make_id_table.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Write docs/ALLOWED_IDS.md: every identifier of the specification and what the gateway does with it.

    python tools/make_id_table.py           write the file
    python tools/make_id_table.py --check   fail when the file differs from what the specification gives
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from urtc_gateway import ids  # noqa: E402

OUT = ROOT / "docs" / "ALLOWED_IDS.md"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = ids.table_markdown()
    if "--check" in args:
        if not OUT.is_file() or OUT.read_bytes().decode("utf-8").replace("\r\n", "\n") != text:
            print("ID_TABLE=FAIL docs/ALLOWED_IDS.md is out of date (run python tools/make_id_table.py)", file=sys.stderr)
            return 1
        print("ID_TABLE=PASS")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    print("wrote docs/ALLOWED_IDS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
