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
  <img src="https://img.shields.io/badge/Version-0.0.1-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Honesty check - what actually runs today:** this repository holds a gateway written as software: the list of identifiers is made from the protocol specification, the payload of every frame is checked against it, the rate is limited, and a peer has to prove it holds a key. All of it is tested in CI with fakes and a local socket. It has never been connected to a real CAN bus, an adapter or a board, and no installation uses it yet. The heating, laser and welding heads still need the hardware measures of the threat model: an interlock that no frame can close, a closed bus and a stop that cuts power.

---

> **Safety and security status:** this ecosystem is not a certified safety system, and no populated URTC board exists yet. The bootloaders check firmware images with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature (planned); the published application images are signed with the public development key (`signing_key_kind: dev`), so anyone can produce an image the bootloader accepts; nothing has been transmitted to a real board. Read the [security baseline](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

## 📋 At a glance

| | |
|---|---|
| Version | `0.0.1` |
| Maturity | Scaffolding |
| Tests | 75 |
| Stack | Python / CAN / HMAC |
| Target | The PC of the person using it |
| On real hardware | Simulated only: tested against emulators, fakes or simulators; no run on real hardware is recorded for this version |

## 🎯 Overview

The CAN bus of the tool head has no sender authentication: any node on the wires is obeyed. When an installation cannot keep the bus closed, this gateway sits in front of it:

* **Identifier list, made from the specification:** only the identifiers a host sends cross towards the bus; the dangerous ones (bootloader, update of the expansion slave, erase of the saved state, every persistent setting) are refused unless the operator unlocks them. [The table of identifiers](docs/ALLOWED_IDS.md) is generated.
* **Payload check:** a frame must have the length and the values the specification allows (a setpoint inside its range, a direction that exists, the magic bytes where they are required).
* **Rate limit:** a token bucket per identifier and for the whole link, and a harder one for an unlocked dangerous identifier.
* **Session key:** a peer proves it holds a key with an HMAC over a nonce of the connection, a counter and the frame, so nothing recorded can be replayed.
* **Every protection can be switched off:** from the configuration file or the command line, and the program lists each protection that is off when it starts. It does not encrypt, and it does not replace the hardware measures of the threat model.

## 🧩 Role in URTC

The threat model of the URTC repository says that, if an installation cannot keep the bus closed or cannot avoid bridging it to a network, the protection belongs in a gateway in front of the bus and not in each tool head. This repository is that gateway: useful for a tunnel between the robot controller and the tool heads and for exposing the bus to a network. It uses the protocol specification of URTC-COMMON as its only source of identifiers and layouts.

## 📂 Repository Structure

```text
URTC-GATEWAY/
├── src/urtc_gateway/  the gateway: identifier lists, policy, rate limit, session keys, options, TCP and serial ends, command line
├── docs/              the options (POLICY.md) and the generated table of identifiers
├── tests/             unit tests of every protection and a test over a real local socket
├── tools/             make_id_table.py and the shared CI checks of the ecosystem
├── images/            the banner
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ BUILD & RUN

**Requirements:** Python 3.10 or newer; pyserial only to use a real SLCAN adapter

```bash
python tools/make_id_table.py --check                              # the table of identifiers is current
python -m pytest tests -q                                          # the tests
python -m urtc_gateway.cli policy                                  # the effective options and a warning for each protection that is off
python -m urtc_gateway.cli keygen keys.txt controller              # a new key file (owner-only, never overwritten)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # listen on 127.0.0.1:8765 with nothing on the bus
```

`build.sh` / `build.bat` raise the version by one step (the ecosystem's odometer), install the package and run the tests; `build-test.sh` / `build-test.bat` check without changing any version; `run.sh` / `run.bat` start the command line (`policy`, `ids`, `keygen`, `run`).

## 🔗 Related Projects

URTC is made of independent repositories, each with its own version, tests and README. This is the family, by group:

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (this repository), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Beyond URTC:**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - the robot-arm motherboard whose CAN relay is documented as the bus the tool head sits on
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - the same idea for the HYDRA-UMC ecosystem
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - the same idea for the A.R.M.O.R. security ecosystem
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - the profile and the status dashboard of all the ecosystems

## 📚 Documentation & Community

Where to read more:

* [Policy: every option, its default and how to switch it](docs/POLICY.md)
* [Identifiers: what the gateway does with each one](docs/ALLOWED_IDS.md)
* [Changelog of this repository](CHANGELOG.md)
* [License (GPL-3.0-or-later)](LICENSE)
* Questions, ideas and reports: electrohobby3d@gmail.com

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - see [LICENSE](LICENSE).
