<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### A gateway in front of the CAN bus: the identifiers a host may send, a rate limit and a session key

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Honesty check - what actually runs today:** this repository holds a gateway written as software: the list of identifiers is made from the protocol specification, the payload of every frame is checked against it, the rate is limited, and a peer has to prove it holds a key. All of it is tested in CI with fakes and a local socket. It has never been connected to a real CAN bus, an adapter or a board, and no installation uses it yet. The heating, laser and welding heads still need the hardware measures of the threat model: an interlock that no frame can close, a closed bus and a stop that cuts power.

---

> **Safety and security status:** this ecosystem is not a certified safety system, and no populated URTC board exists yet. The bootloaders check firmware images with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature (planned); the published application images are signed with the public development key (`signing_key_kind: dev`), so anyone can produce an image the bootloader accepts; nothing has been transmitted to a real board. Read the [security baseline](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

## 📋 At a glance

| | |
|---|---|
| Version | `0.0.3` |
| Maturity | Scaffolding |
| Tests | 79 |
| Stack | Python / CAN / HMAC |
| Target | The PC of the person using it |
| On real hardware | Simulated only: tested against emulators, fakes or simulators; no run on real hardware is recorded for this version |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Structure](#-repository-structure) · [Related](#-related-projects)

<!-- urtc-section:status_gateway -->
## 🚦 Project status

🟢 done and verified · 🟡 works, with known limits · 🟠 half done or not verified · 🔴 not done or not working. Nothing is green if it never ran on real hardware.

| Part | Status | What the repository can show |
| --- | :---: | --- |
| Software | 🟡 | Works on a PC and against the simulator; never run against a real board. |
| Tests | 🟡 | The test suite passes in the CI on every push. |
| Real hardware | 🟠 | No run on a real board yet: the bench test is still pending. |
| Security | 🟡 | Lets only listed identifiers through and limits their rate; checked on a PC, never in front of a real bus. |
| Documentation | 🟡 | README in eight languages and reference documents; the translations were not reviewed by native speakers. |

<!-- /urtc-section:status_gateway -->

## 🎯 Overview

The CAN bus of the tool head has no sender authentication: any node on the wires is obeyed. When an installation cannot keep the bus closed, this gateway sits in front of it:

* **Identifier list, made from the specification:** only the identifiers a host sends cross towards the bus; the dangerous ones (bootloader, update of the expansion slave, erase of the saved state, every persistent setting) are refused unless the operator unlocks them. [The table of identifiers](docs/ALLOWED_IDS.md) is generated.
* **Payload check:** a frame must have the length and the values the specification allows (a setpoint inside its range, a direction that exists, the magic bytes where they are required).
* **Rate limit:** a token bucket per identifier and for the whole link, and a harder one for an unlocked dangerous identifier.
* **Session key:** a peer proves it holds a key with an HMAC over a nonce of the connection, a counter and the frame, so nothing recorded can be replayed.
* **Every protection can be switched off:** from the configuration file or the command line, and the program lists each protection that is off when it starts. It does not encrypt, and it does not replace the hardware measures of the threat model.

## 🧩 Role in URTC

The threat model of the URTC repository says that, if an installation cannot keep the bus closed or cannot avoid bridging it to a network, the protection belongs in a gateway in front of the bus and not in each tool head. This repository is that gateway: useful for a tunnel between the robot controller and the tool heads and for exposing the bus to a network. It uses the protocol specification of URTC-COMMON as its only source of identifiers and layouts.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="URTC-GATEWAY architecture: who uses it, what it holds and what it depends on" width="100%">
</p>

How the parts of this repository fit together: who uses it, what it holds and what it depends on. The picture is drawn from `docs/architecture.json` and checked against the code.

## 🔒 Security & Safety

| Threat | Defence |
|---|---|
| A node on the wires sends a dangerous command (bootloader, update of the expansion slave, erase of the saved state, a persistent setting) | The identifier list refuses them until the operator unlocks them with `--unlock-dangerous` |
| A value outside what the protocol allows (a setpoint out of range, a direction that does not exist, wrong magic bytes) | The payload check refuses the frame |
| A runaway or hostile sender floods the bus | A token bucket per identifier and for the whole link, and a harder one for an unlocked dangerous identifier |
| A recorded message is sent again | The session key: an HMAC over a nonce of the connection, a counter that must grow and the frame, so a recording is useless later and elsewhere |
| The gateway is reachable from a network without a key | Listening on a non-local address without a session key is refused unless `--allow-open-network` is given |

It does not encrypt: the bus is not a secret. It does not stop a peer that holds the key and misbehaves; the list, the payload check and the rate limit are there for that, and the watchdogs of the tool heads. It does not replace the hardware measures of the CAN threat model (an interlock that no frame can close, a closed bus, a stop that cuts power). It has never been used on a real bus.

## 🔌 Interfaces

The command line is `urtc-gateway` (or `python -m urtc_gateway.cli`):

| Command | What it does |
|---|---|
| `policy` | shows the effective options and a warning for each protection that is off |
| `ids` | lists every identifier and what the gateway does with it |
| `keygen FILE PEER [PEER ...]` | writes a key file with a new random key for each peer (owner-only, never over an existing file, keys are not shown); give each peer only its own line |
| `run` | listens on a TCP port (`--host`, default `127.0.0.1`; `--port`, default `8765`) and forwards to a bus (`--bus loopback`, a pyserial URL such as `socket://127.0.0.1:7777`, or the serial port of an SLCAN adapter; `--bitrate`, default 500000) |

**The line protocol.** On connection the gateway sends `{"type": "hello", "nonce": "<hex>", "session": true}`. Every message the peer sends is one JSON object per line: `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 hex digits>"}`. `mac` is the first 16 bytes of HMAC-SHA256, with the key of the peer, over `urtc-gw/1|<nonce>|<counter>|<id as three hex digits>|<data as hex>`; the counter has to grow with every message of the connection and the nonce is new for every connection. A refused message is answered with `{"type": "refused", "code": "<reason>"}`, and the frames of the bus come back as `{"type": "frame", "id": ..., "data": "<hex>"}`. See [the policy](docs/POLICY.md).

## ⚙️ Configuration

Every protection is on by default and every one can be switched off, in a JSON configuration file (`--config FILE`, `"schema": 1`; an unknown section or option, a wrong type or a negative rate is an error that says what is wrong) and on the command line, which overrides the file. A protection that is off, or loosened, is listed as a warning when the program starts.

| Protection | File section | Off / on | What it does |
|---|---|---|---|
| Identifier list | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | only the identifiers a host sends cross towards the bus |
| Dangerous identifiers | `whitelist.unlock_dangerous` | `--unlock-dangerous` | the bootloader, the expansion-slave update, the erase of the saved state and every persistent setting stay refused until unlocked |
| Added / removed identifiers | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | add an identifier by hand, or take one out whatever the rest says |
| Payload check | `payload.enabled` | `--no-payload-check` / `--payload-check` | length and values must be those the specification allows |
| Rate limit | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 frames per second and a burst of 10 per identifier, a burst of 50 for the link, a burst of 2 for an unlocked dangerous identifier; `rate.overrides` gives an identifier its own rate and burst |
| Session key | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | a peer proves it holds a key |
| Outbound filter | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | only what a board sends goes towards the network, at up to 500 frames per second |
| Open network | `server.allow_open_network` | `--allow-open-network` | listening on a non-local address without a session key is refused unless asked for |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Quick start

**Requirements:** Python 3.10 or newer; pyserial only to use a real SLCAN adapter

```bash
python tools/make_id_table.py --check                              # the table of identifiers is current
python -m pytest tests -q                                          # the tests
python -m urtc_gateway.cli policy                                  # the effective options and a warning for each protection that is off
python -m urtc_gateway.cli keygen keys.txt controller              # a new key file (owner-only, never overwritten)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # listen on 127.0.0.1:8765 with nothing on the bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# the virtual board of URTC-COMMON (or any pyserial URL) in place of an adapter
```

<!-- urtc-section:compatibility -->
### Requirements & compatibility

Which versions of the URTC programs work together, and which protocol version each one speaks, is listed in the compatibility table that URTC-COMMON generates: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Testing

The suite has 79 tests (`python -m pytest tests -q`): the identifier list, the payload check, the rate limit, the session and its refusals, the options and the configuration file, the command line, a test over a real local socket and the serial end against a fake port. One test skips where its optional dependency is missing. `python -m mypy` type-checks the package and `ruff check .` the sources.

## 🏗️ Build & Release

`build.sh` / `build.bat` install the package and run the tests; `build-test.sh` / `build-test.bat` check without changing any version; `run.sh` / `run.bat` start the command line (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` writes the table of identifiers of [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) from the specification (`--check` compares).

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                the gateway: identifier list, policy, rate limit, session keys, options, TCP and serial ends, command line
├── docs/                                            the options (POLICY.md) and the generated table of identifiers
├── tests/                                           unit tests, one on a real socket
├── tools/                                           make_id_table.py and shared tools
├── images/                                          banner and the pictures of this README
├── .github/                                         CI workflow, issue and pull-request templates
├── build.sh build.bat                               build scripts
├── build-test.sh build-test.bat                     build and test scripts that change nothing in the repository
├── test.sh test.bat                                 run the tests
├── run.sh run.bat                                   start the program
├── urtc.project.json                                manifest: version, role, maturity and build command
├── CHANGELOG.md                                     what changed in each version
├── SECURITY.md SUPPORT.md LICENSE                   security policy, support and license
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               how to contribute and the code of conduct
├── .gitattributes .gitignore                        Git settings
├── bump_version.py bump_manifest_version.py         scripts that raise the version
└── pyproject.toml requirements-dev.lock ruff.toml   package, locked tools and lint settings
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

* It has never been connected to a real CAN bus, an adapter or a board, and no installation uses it yet; it is tested in CI with fakes and a local socket.
* The heating, laser and welding heads still need the hardware measures of the threat model: an interlock that no frame can close, a closed bus and a stop that cuts power.
* It does not encrypt and does not stop a peer that holds the key and misbehaves.

**Next**

* Try it between a controller and a real tool head on a bench, behind the virtual board first.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

URTC is made of independent repositories, each with its own version, tests and README. This is the family, by group:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware of the tool-head board (25 tool profiles, CAN bootloader) and the CAN protocol reference.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - the CAN protocol written once as data (specification, generated tables, conformance vectors) and the code the programs share.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - desktop tool that updates the board firmware over CAN or over SWD/JTAG.
  * **URTC-GATEWAY** (this repository) - gateway in front of the CAN bus: lets only listed identifiers through, limits their rate and asks for a session key.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardware-independent C logic and command protocol for a tool rack with pre-heating and lifecycle tracking.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - desktop live CAN-bus tester that shows the controls and telemetry of the tool profile a board reports.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - sensor-frame protocol in C and a Python thermal/RGB companion for an inspection tool head.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - browser app that flashes and tests the board over Web Serial and SLCAN, with nothing to install.
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - architecture, interfaces, security baseline and generated catalogue of the ecosystem, plus the tools that compare all repositories.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - desktop tool that detects, installs and updates the repositories of the URTC family, one explicit action at a time.

**Sister projects (independent, with the same base and tools):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - sister project: the documentation hub of HYDRA-UMC, an independent ecosystem that shares this one's base and tools
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - sister project: the documentation hub of A.R.M.O.R., the security ecosystem, also independent and on the same base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - the profile and the status dashboard of all the ecosystems

## 📚 Documentation

Where to read more:

* [Policy: every option, its default and how to switch it](docs/POLICY.md)
* [Identifiers: what the gateway does with each one](docs/ALLOWED_IDS.md)
* [Changelog of this repository](CHANGELOG.md)
* [License (GPL-3.0-or-later)](LICENSE)
* Questions, ideas and reports: electrohobby3d@gmail.com

## 🤝 Contributing & Community

* Before a pull request run `URTC_CI=1 python tools/ci_validate.py`: it must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages: a change to the text is made in all eight files, and the sections shared with other repositories are written by `tools/readme_sections.py` of URTC-COMMON.
* A change to the CAN protocol starts in URTC-COMMON (`spec/can_protocol.json`) and reaches this repository through the checked copy.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
