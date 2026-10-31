<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### Ein Gateway vor dem CAN-Bus: die Kennungen, die ein Host senden darf, eine Ratenbegrenzung und ein Sitzungsschlüssel

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Ehrlichkeitscheck - was heute tatsächlich läuft:** Dieses Repository enthält ein Gateway als Software: Die Liste der Kennungen wird aus der Protokollspezifikation erzeugt, die Nutzdaten jedes Frames werden dagegen geprüft, die Rate ist begrenzt, und eine Gegenstelle muss nachweisen, dass sie einen Schlüssel besitzt. Alles wird in der CI mit Attrappen und einem lokalen Socket getestet. Es war nie an einen echten CAN-Bus, einen Adapter oder eine Platine angeschlossen, und keine Installation nutzt es bisher. Heiz-, Laser- und Schweißköpfe brauchen weiterhin die Hardware-Maßnahmen des Bedrohungsmodells: eine Verriegelung, die kein Frame schließen kann, einen geschlossenen Bus und einen Stopp, der die Energie abschaltet.

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem, und es existiert noch keine bestückte URTC-Platine. Die Bootloader prüfen Firmware-Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur (geplant); die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`), sodass jeder ein vom Bootloader akzeptiertes Image erzeugen kann; an eine echte Platine wurde noch nichts gesendet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.0.3` |
| Reifegrad | Gerüst |
| Tests | 79 |
| Technik | Python / CAN / HMAC |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nur simuliert: gegen Emulatoren, Attrappen oder Simulatoren getestet; für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Sicherheit](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Struktur](#-struktur-des-repositorys) · [Verwandte](#-verwandte-projekte)

<!-- urtc-section:status_gateway -->
## 🚦 Projektstatus

🟢 fertig und überprüft · 🟡 funktioniert, mit bekannten Grenzen · 🟠 halb fertig oder nicht überprüft · 🔴 nicht gemacht oder funktioniert nicht. Nichts ist grün, wenn es nie auf echter Hardware lief.

| Teil | Status | Was das Repository belegen kann |
| --- | :---: | --- |
| Software | 🟡 | Läuft am PC und gegen den Simulator; nie an einer echten Platine ausgeführt. |
| Tests | 🟡 | Die Testsuite besteht bei jedem Push in der CI. |
| Echte Hardware | 🟠 | Noch kein Lauf an einer echten Platine: der Bankversuch steht noch aus. |
| Sicherheit | 🟡 | Lässt nur gelistete Kennungen durch und begrenzt ihre Rate; am PC geprüft, nie vor einem echten Bus. |
| Dokumentation | 🟡 | README in acht Sprachen und Referenzdokumente; die Übersetzungen wurden nicht von Muttersprachlern geprüft. |

<!-- /urtc-section:status_gateway -->

## 🎯 Überblick

Der CAN-Bus des Werkzeugkopfs authentifiziert den Absender nicht: Jedem Knoten an den Leitungen wird gehorcht. Wenn eine Installation den Bus nicht geschlossen halten kann, sitzt dieses Gateway davor:

* **Kennungsliste, aus der Spezifikation erzeugt:** Nur die Kennungen, die ein Host sendet, gehen zum Bus; die gefährlichen (Bootloader, Update des Erweiterungs-Slaves, Löschen des gespeicherten Zustands, jede dauerhafte Einstellung) werden abgelehnt, solange der Betreiber sie nicht freigibt. [Die Kennungstabelle](docs/ALLOWED_IDS.md) wird erzeugt.
* **Prüfung der Nutzdaten:** Ein Frame muss die Länge und die Werte haben, die die Spezifikation erlaubt (ein Sollwert in seinem Bereich, eine existierende Richtung, die Magic-Bytes dort, wo sie verlangt werden).
* **Ratenbegrenzung:** ein Token-Bucket je Kennung und für die ganze Verbindung, und ein strengerer für eine freigegebene gefährliche Kennung.
* **Sitzungsschlüssel:** Eine Gegenstelle weist den Besitz eines Schlüssels mit einem HMAC über eine Nonce der Verbindung, einen Zähler und den Frame nach, sodass nichts Aufgezeichnetes wiedereingespielt werden kann.
* **Jeder Schutz lässt sich abschalten:** in der Konfigurationsdatei oder auf der Kommandozeile, und das Programm listet beim Start jeden abgeschalteten Schutz auf. Es verschlüsselt nicht und ersetzt nicht die Hardware-Maßnahmen des Bedrohungsmodells.

## 🧩 Rolle in URTC

Das Bedrohungsmodell des URTC-Repositorys sagt: Kann eine Installation den Bus nicht geschlossen halten oder die Verbindung zu einem Netz nicht vermeiden, gehört der Schutz in ein Gateway vor dem Bus und nicht in jeden Werkzeugkopf. Dieses Repository ist dieses Gateway: nützlich für einen Tunnel zwischen der Robotersteuerung und den Werkzeugköpfen und um den Bus einem Netz zugänglich zu machen. Es nutzt die Protokollspezifikation von URTC-COMMON als einzige Quelle für Kennungen und Formate.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="Architektur von URTC-GATEWAY: wer es nutzt, was es enthält und wovon es abhängt" width="100%">
</p>

Wie die Teile dieses Repositorys zusammenpassen: wer es nutzt, was es enthält und wovon es abhängt. Das Bild wird aus `docs/architecture.json` gezeichnet und gegen den Code geprüft.

## 🔒 Sicherheit und Schutz

| Bedrohung | Abwehr |
|---|---|
| Ein Knoten an den Leitungen sendet einen gefährlichen Befehl (Bootloader, Aktualisierung des Erweiterungs-Slaves, Löschen des gespeicherten Zustands, eine dauerhafte Einstellung) | Die Bezeichnerliste lehnt sie ab, bis der Betreiber sie mit `--unlock-dangerous` freigibt |
| Ein Wert außerhalb dessen, was das Protokoll erlaubt (ein Sollwert außerhalb des Bereichs, eine nicht existierende Richtung, falsche Magic Bytes) | Die Nutzdatenprüfung lehnt den Frame ab |
| Ein außer Kontrolle geratener oder feindlicher Sender überflutet den Bus | Ein Token-Bucket je Bezeichner und für die ganze Verbindung sowie ein strengerer für einen freigegebenen gefährlichen Bezeichner |
| Eine aufgezeichnete Nachricht wird erneut gesendet | Der Sitzungsschlüssel: ein HMAC über einen Nonce der Verbindung, einen wachsenden Zähler und den Frame, sodass eine Aufzeichnung später und anderswo nutzlos ist |
| Das Gateway ist ohne Schlüssel aus einem Netz erreichbar | Das Lauschen auf einer nicht lokalen Adresse ohne Sitzungsschlüssel wird abgelehnt, außer `--allow-open-network` wird angegeben |

Es verschlüsselt nicht: Der Bus ist kein Geheimnis. Es hält keinen Teilnehmer auf, der den Schlüssel besitzt und sich schlecht benimmt; dafür sind die Liste, die Nutzdatenprüfung, die Ratenbegrenzung und die Watchdogs der Werkzeugköpfe da. Es ersetzt nicht die Hardware-Maßnahmen des CAN-Bedrohungsmodells (eine Verriegelung, die kein Frame schließen kann, ein geschlossener Bus, ein Stopp, der die Stromversorgung trennt). Es wurde nie an einem echten Bus verwendet.

## 🔌 Schnittstellen

Die Befehlszeile heißt `urtc-gateway` (oder `python -m urtc_gateway.cli`):

| Befehl | Was er tut |
|---|---|
| `policy` | zeigt die wirksamen Optionen und eine Warnung für jede abgeschaltete Schutzfunktion |
| `ids` | listet jeden Bezeichner und was das Gateway mit ihm tut |
| `keygen FILE PEER [PEER ...]` | schreibt eine Schlüsseldatei mit einem neuen Zufallsschlüssel je Teilnehmer (nur für den Besitzer lesbar, nie über eine vorhandene, Schlüssel werden nicht angezeigt); jedem Teilnehmer nur seine eigene Zeile geben |
| `run` | lauscht auf einem TCP-Port (`--host`, Standard `127.0.0.1`; `--port`, Standard `8765`) und leitet an einen Bus weiter (`--bus loopback`, eine pyserial-URL wie `socket://127.0.0.1:7777` oder der serielle Port eines SLCAN-Adapters; `--bitrate`, Standard 500000) |

**Das Zeilenprotokoll.** Beim Verbinden sendet das Gateway `{"type": "hello", "nonce": "<hex>", "session": true}`. Jede Nachricht des Teilnehmers ist ein JSON-Objekt pro Zeile: `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 Hex-Ziffern>"}`. `mac` sind die ersten 16 Bytes von HMAC-SHA256 mit dem Schlüssel des Teilnehmers über `urtc-gw/1|<nonce>|<counter>|<id als drei Hex-Ziffern>|<Daten als Hex>`; der Zähler muss mit jeder Nachricht der Verbindung wachsen, und der Nonce ist bei jeder Verbindung neu. Eine abgelehnte Nachricht wird mit `{"type": "refused", "code": "<Grund>"}` beantwortet, die Frames des Busses kommen als `{"type": "frame", "id": ..., "data": "<hex>"}` zurück. Siehe [die Richtlinie](docs/POLICY.md).

## ⚙️ Konfiguration

Jede Schutzfunktion ist standardmäßig aktiv und jede lässt sich abschalten, in einer JSON-Konfigurationsdatei (`--config FILE`, `"schema": 1`; ein unbekannter Abschnitt oder eine unbekannte Option, ein falscher Typ oder eine negative Rate ist ein Fehler, der sagt, was falsch ist) und in der Befehlszeile, die die Datei überschreibt. Eine abgeschaltete oder gelockerte Schutzfunktion wird beim Start des Programms als Warnung aufgelistet.

| Schutzfunktion | Abschnitt der Datei | Aus / an | Was sie tut |
|---|---|---|---|
| Bezeichnerliste | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | nur die Bezeichner, die ein Host sendet, gelangen zum Bus |
| Gefährliche Bezeichner | `whitelist.unlock_dangerous` | `--unlock-dangerous` | Bootloader, Aktualisierung des Erweiterungs-Slaves, Löschen des gespeicherten Zustands und jede dauerhafte Einstellung bleiben abgelehnt, bis sie freigegeben werden |
| Hinzugefügte / entfernte Bezeichner | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | einen Bezeichner von Hand hinzufügen oder einen entfernen, was auch immer der Rest sagt |
| Nutzdatenprüfung | `payload.enabled` | `--no-payload-check` / `--payload-check` | Länge und Werte müssen die sein, die die Spezifikation erlaubt |
| Ratenbegrenzung | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 Frames pro Sekunde und ein Burst von 10 je Bezeichner, ein Burst von 50 für die Verbindung, ein Burst von 2 für einen freigegebenen gefährlichen Bezeichner; `rate.overrides` gibt einem Bezeichner eine eigene Rate und einen eigenen Burst |
| Sitzungsschlüssel | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | ein Teilnehmer beweist, dass er einen Schlüssel besitzt |
| Ausgangsfilter | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | nur was eine Platine sendet, geht Richtung Netz, mit bis zu 500 Frames pro Sekunde |
| Offenes Netz | `server.allow_open_network` | `--allow-open-network` | das Lauschen auf einer nicht lokalen Adresse ohne Sitzungsschlüssel wird abgelehnt, außer es wird verlangt |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Schnellstart

**Voraussetzungen:** Python 3.10 oder neuer; pyserial nur für einen echten SLCAN-Adapter

```bash
python tools/make_id_table.py --check                              # die Kennungstabelle ist aktuell
python -m pytest tests -q                                          # die Tests
python -m urtc_gateway.cli policy                                  # die wirksamen Optionen und eine Warnung für jeden abgeschalteten Schutz
python -m urtc_gateway.cli keygen keys.txt controller              # eine neue Schlüsseldatei (nur für den Besitzer, nie überschrieben)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # auf 127.0.0.1:8765 lauschen, ohne etwas am Bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# die virtuelle Platine von URTC-COMMON (oder eine beliebige pyserial-URL) statt eines Adapters
```

<!-- urtc-section:compatibility -->
### Voraussetzungen und Kompatibilität

Welche Versionen der URTC-Programme zusammenarbeiten und welche Protokollversion jede spricht, steht in der Kompatibilitätstabelle, die URTC-COMMON erzeugt: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md). Die Notizen einer Version der Repositories, die `tools/changelog_section.py` mitführen (die Firmware, der Flasher, der Tester und der Updater), sind der Abschnitt des CHANGELOG dieser Version, gefolgt von dieser Tabelle: `python tools/changelog_section.py VERSION --compat`.
<!-- /urtc-section:compatibility -->

## 🧪 Tests

Die Suite hat 79 Tests (`python -m pytest tests -q`): die Bezeichnerliste, die Nutzdatenprüfung, die Ratenbegrenzung, die Sitzung und ihre Ablehnungen, die Optionen und die Konfigurationsdatei, die Befehlszeile, ein Test über einen echten lokalen Socket und das serielle Ende gegen einen Schein-Port. Ein Test wird übersprungen, wenn seine optionale Abhängigkeit fehlt. `python -m mypy` prüft die Typen des Pakets und `ruff check .` den Quelltext.

## 🏗️ Build und Veröffentlichung

`build.sh` / `build.bat` installieren das Paket und führen die Tests aus; `build-test.sh` / `build-test.bat` prüfen, ohne eine Version zu ändern; `run.sh` / `run.bat` starten die Befehlszeile (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` schreibt die Bezeichnertabelle von [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) aus der Spezifikation (`--check` vergleicht).

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Struktur des Repositorys URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                das Gateway: Bezeichnerliste, Richtlinie, Ratenbegrenzung, Sitzungsschlüssel, Optionen, TCP- und serielle Enden, Befehlszeile
├── docs/                                            die Optionen (POLICY.md) und die erzeugte Bezeichnertabelle
├── tests/                                           Unit-Tests jeder Schutzfunktion und ein Test über einen echten lokalen Socket
├── tools/                                           make_id_table.py und die gemeinsamen CI- und Bild-Werkzeuge
├── images/                                          Banner und Bilder dieses READMEs
├── .github/                                         CI-Workflow sowie Vorlagen für Issues und Pull Requests
├── build.sh build.bat                               Build-Skripte
├── build-test.sh build-test.bat                     Build- und Testskripte, die im Repository nichts ändern
├── test.sh test.bat                                 führen die Tests aus
├── run.sh run.bat                                   starten das Programm
├── urtc.project.json                                Manifest: Version, Rolle, Reifegrad und Build-Befehl
├── CHANGELOG.md                                     was sich in jeder Version geändert hat
├── SECURITY.md SUPPORT.md LICENSE                   Sicherheitsrichtlinie, Support und Lizenz
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               wie man mitwirkt, und der Verhaltenskodex
├── .gitattributes .gitignore                        Git-Einstellungen
├── bump_version.py bump_manifest_version.py         Skripte, die die Version erhöhen
└── pyproject.toml requirements-dev.lock ruff.toml   Paket, festgelegte Werkzeuge und Lint-Einstellungen
```

</details>

## 🗺️ Roadmap und bekannte Grenzen

**Bekannte Grenzen heute**

* Es wurde nie an einen echten CAN-Bus, einen Adapter oder eine Platine angeschlossen, und keine Installation nutzt es bisher; es wird in der CI mit Attrappen und einem lokalen Socket getestet.
* Die Heiz-, Laser- und Schweißköpfe brauchen weiterhin die Hardware-Maßnahmen des Bedrohungsmodells: eine Verriegelung, die kein Frame schließen kann, einen geschlossenen Bus und einen Stopp, der die Stromversorgung trennt.
* Es verschlüsselt nicht und hält keinen Teilnehmer auf, der den Schlüssel besitzt und sich schlecht benimmt.

**Als Nächstes**

* Es auf einem Prüfstand zwischen einer Steuerung und einem echten Werkzeugkopf ausprobieren, zuerst hinter der virtuellen Platine.

## 🌍 Sprachen

README und Texte gibt es auf Englisch, Spanisch, Französisch, Italienisch, Deutsch, Chinesisch, Japanisch und europäischem Portugiesisch.

## 🔗 Verwandte Projekte

URTC besteht aus unabhängigen Repositories mit jeweils eigener Version, eigenen Tests und eigenem README. Das ist die Familie, nach Gruppen:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - Firmware der Werkzeugkopf-Platine (25 Werkzeugprofile, CAN-Bootloader) und die Referenz des CAN-Protokolls.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - das CAN-Protokoll einmal als Daten geschrieben (Spezifikation, erzeugte Tabellen, Konformitätsvektoren) und der Code, den die Programme teilen.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - Desktop-Werkzeug, das die Platinen-Firmware über CAN oder über SWD/JTAG aktualisiert.
  * **URTC-GATEWAY** (dieses Repository) - Gateway vor dem CAN-Bus: lässt nur gelistete Kennungen durch, begrenzt ihre Rate und verlangt einen Sitzungsschlüssel.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardwareunabhängige C-Logik und Befehlsprotokoll für eine Werkzeugablage mit Vorheizen und Lebenszyklusverfolgung.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - Desktop-Live-Tester für den CAN-Bus, der die Bedienelemente und die Telemetrie des von einer Platine gemeldeten Werkzeugprofils zeigt.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - Sensorrahmen-Protokoll in C und ein Python-Thermo-/RGB-Begleiter für einen Inspektions-Werkzeugkopf.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - Browser-App, die die Platine über Web Serial und SLCAN flasht und testet, ohne Installation.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - die gemeinsamen Repository-Werkzeuge der Familie als versionierter Satz, mit einer Sperrdatei, die eine bearbeitete von einer veralteten Kopie unterscheidet.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - Architektur, Schnittstellen, Sicherheitsbasis und erzeugter Katalog des Ökosystems sowie die Werkzeuge, die alle Repositories vergleichen.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - Desktop-Werkzeug, das die Repositories der URTC-Familie erkennt, installiert und aktualisiert, jeweils eine ausdrückliche Aktion.

**Schwesterprojekte (unabhängig, mit derselben Basis und denselben Werkzeugen):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von HYDRA-UMC, einem unabhängigen Ökosystem, das Basis und Werkzeuge mit diesem teilt
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von A.R.M.O.R., dem Sicherheits-Ökosystem, ebenfalls unabhängig und auf derselben Basis
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - das Profil und das Status-Dashboard aller Ökosysteme

## 📚 Dokumentation

Mehr zum Lesen:

* [Richtlinie: jede Option, ihr Standardwert und wie man sie abschaltet](docs/POLICY.md)
* [Kennungen: was das Gateway mit jeder tut](docs/ALLOWED_IDS.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz (GPL-3.0-or-later)](LICENSE)
* Fragen, Ideen und Meldungen: electrohobby3d@gmail.com

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `URTC_CI=1 python tools/ci_validate.py` aus: es muss bestehen. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) und den [Verhaltenskodex](CODE_OF_CONDUCT.md).
* Das README gibt es in acht Sprachen: Eine Textänderung wird in allen acht Dateien vorgenommen, und die mit anderen Repositorys geteilten Abschnitte schreibt `tools/readme_sections.py` von URTC-COMMON.
* Eine Änderung am CAN-Protokoll beginnt in URTC-COMMON (`spec/can_protocol.json`) und gelangt über die geprüfte Kopie in dieses Repository.
* Beschreibe nichts als auf einer Platine funktionierend, was nur gebaut wurde.
* Melde eine Schwachstelle privat: [SECURITY.md](SECURITY.md). Fragen, Ideen und Meldungen: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
