# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- **The lights of Project status follow the evidence of the manifest:** the manifest says how far the repository has been shown to work (`evidence`: `host-test`, `simulator`, `bench` or `field`) and the validator fails when a light is above what that evidence and the maturity allow (`tools/status_lights.py`), so a green that never ran on real hardware cannot come back.

## [0.0.3] - The nightly CI and the universal README

- **Related Projects lists the URTC family:** the section names the repositories of URTC by group, each with one short line about what it is for, and, in one short line each, the sister projects (independent ecosystems of the same author that share the base and the tools), in the eight languages. It no longer says that URTC is part of another ecosystem.
- **The README follows the universal layout in the eight languages** and now carries what was only in `docs/POLICY.md`: the command line (`policy`, `ids`, `keygen`, `run`), the line protocol of a session, a table of every protection with how to switch it, and the threats the gateway answers. The Architecture and the Repository Structure are drawn from `docs/architecture.json` and `docs/structure.json`.
- **The layout of the README is checked in the CI:** the validator runs `tools/universal_readme_check.py` and lists, as a warning, what differs from the universal layout of the README.
- **Project status is the second section of the README,** right after At a glance, in the eight languages.
- **The full CI runs every night:** a scheduled workflow runs the complete baseline again on the default branch and opens (or updates) one issue when it fails, so a change in a runner image, a toolchain or a pinned dependency is found the next day instead of with the next unrelated change.

## [0.0.3]

- Build version synchronized with `urtc.project.json` and the repository-native version source.

## [0.0.2] - The copy of the shared protocol is current and the dev dependencies are closed with hashes and the types are checked

- The test count of the At a glance table is current.
- **The copy of the shared protocol is current:** it now knows `0x222` (the patch companion of the slave version, sent by the board and refused towards it, with an optional third byte), and `docs/ALLOWED_IDS.md` lists it.
- **The dev dependencies are closed with hashes and the types are checked:** `requirements-dev.lock` pins every package the tests need, with the hash of every file (the CI and the build scripts install it with `--require-hashes`, then the project itself without dependencies), and `mypy` runs on `src` in the CI (the shared protocol table is typed where it is read, ten findings fixed, no behaviour changed).
- **The README files carry sections written once in URTC-COMMON:** "Compatibility", in the eight languages, between marker comments before the license heading (`tools/readme_sections.py` of URTC-COMMON writes and checks them; the rest of each README is hand-written as before).
- **A static check on every push:** `ruff.toml` (unused names, exception chaining and syntax errors, the rules the flasher and the tester already ran) and a step of the CI that runs `ruff check .` with a pinned ruff; nothing to fix.
- **The serial bus opens pyserial URLs:** a `--bus` value with `://` (for example `socket://127.0.0.1:7777`, the virtual board of URTC-COMMON or a serial server) is opened with `serial_for_url`; a plain port name opens as before. 4 new tests, one against the virtual board when URTC-COMMON is checked out beside this repository.
- The CI holds the tests to a coverage floor of 66 percent (measured 74; `pytest-cov` and `pyserial` are in the `dev` extra).

## [0.0.1] - A gateway in front of the CAN bus

- First version of the gateway: a program in front of the URTC CAN bus for an installation that cannot keep the bus closed.
- **Identifier list made from the protocol specification**: only the identifiers a host sends cross towards the bus. The dangerous ones (bootloader, update of the expansion slave, erase of the saved state, every persistent setting) are refused unless the operator unlocks them; questions are always allowed. `docs/ALLOWED_IDS.md` is generated and the CI fails when it is out of date.
- **Payload check**: the length and the values of a frame have to be those the specification allows (range, defined values, magic bytes).
- **Rate limit**: a token bucket per identifier and for the whole link, and a harder one for an unlocked dangerous identifier; a limit on the way out too.
- **Session key**: a peer proves it holds a key with an HMAC over a nonce of the connection, a counter and the frame; a recorded frame cannot be replayed in the same connection or in another. A key file is made with `keygen` (owner-only, never overwritten) and a key is never printed.
- **Every protection can be switched off**, from the configuration file or the command line, and the program lists each protection that is off when it starts. Listening on a non-local address without session authentication is refused unless asked for.
- A TCP end (one JSON object per line) and a bus end (an SLCAN serial adapter, or a loopback with nothing on it); the command line has `policy`, `ids`, `keygen` and `run`.
- Tested on the host with fakes and a real local socket; it has not been connected to a CAN bus, an adapter or a board.
