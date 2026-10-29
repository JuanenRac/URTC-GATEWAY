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
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Ehrlichkeitscheck - was heute tatsächlich läuft:** Dieses Repository enthält ein Gateway als Software: Die Liste der Kennungen wird aus der Protokollspezifikation erzeugt, die Nutzdaten jedes Frames werden dagegen geprüft, die Rate ist begrenzt, und eine Gegenstelle muss nachweisen, dass sie einen Schlüssel besitzt. Alles wird in der CI mit Attrappen und einem lokalen Socket getestet. Es war nie an einen echten CAN-Bus, einen Adapter oder eine Platine angeschlossen, und keine Installation nutzt es bisher. Heiz-, Laser- und Schweißköpfe brauchen weiterhin die Hardware-Maßnahmen des Bedrohungsmodells: eine Verriegelung, die kein Frame schließen kann, einen geschlossenen Bus und einen Stopp, der die Energie abschaltet.

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem, und es existiert noch keine bestückte URTC-Platine. Die Bootloader prüfen Firmware-Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur (geplant); die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`), sodass jeder ein vom Bootloader akzeptiertes Image erzeugen kann; an eine echte Platine wurde noch nichts gesendet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.0.2` |
| Reifegrad | Gerüst |
| Tests | 79 |
| Technik | Python / CAN / HMAC |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nur simuliert: gegen Emulatoren, Attrappen oder Simulatoren getestet; für diese Version ist kein Lauf auf echter Hardware vermerkt |

<!-- urtc-section:status_gateway -->
## 🚦 Projektstatus

🟢 fertig und überprüft · 🟡 funktioniert, mit bekannten Grenzen · 🟠 halb fertig oder nicht überprüft · 🔴 nicht gemacht oder funktioniert nicht. Nichts ist grün, wenn es nie auf echter Hardware lief.

| Teil | Status | Was das Repository belegen kann |
| --- | :---: | --- |
| Software | 🟡 | Läuft am PC und gegen den Simulator; nie an einer echten Platine ausgeführt. |
| Tests | 🟢 | Die Testsuite besteht bei jedem Push in der CI. |
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

## 📂 Repository-Struktur

```text
URTC-GATEWAY/
├── src/urtc_gateway/  das Gateway: Kennungslisten, Richtlinie, Ratenbegrenzung, Sitzungsschlüssel, Optionen, TCP- und serielle Enden, Kommandozeile
├── docs/              die Optionen (POLICY.md) und die erzeugte Kennungstabelle
├── tests/             Unit-Tests jedes Schutzes und ein Test über einen echten lokalen Socket
├── tools/             make_id_table.py und die gemeinsamen CI-Prüfungen des Ökosystems
├── images/            das Banner
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ BUILD & AUSFÜHRUNG

**Voraussetzungen:** Python 3.10 oder neuer; pyserial nur für einen echten SLCAN-Adapter

```bash
python tools/make_id_table.py --check                              # die Kennungstabelle ist aktuell
python -m pytest tests -q                                          # die Tests
python -m urtc_gateway.cli policy                                  # die wirksamen Optionen und eine Warnung für jeden abgeschalteten Schutz
python -m urtc_gateway.cli keygen keys.txt controller              # eine neue Schlüsseldatei (nur für den Besitzer, nie überschrieben)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # auf 127.0.0.1:8765 lauschen, ohne etwas am Bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# die virtuelle Platine von URTC-COMMON (oder eine beliebige pyserial-URL) statt eines Adapters
```

`build.sh` / `build.bat` erhöhen die Version um einen Schritt (der Kilometerzähler des Ökosystems), installieren das Paket und führen die Tests aus; `build-test.sh` / `build-test.bat` prüfen, ohne eine Version zu ändern; `run.sh` / `run.bat` starten die Kommandozeile (`policy`, `ids`, `keygen`, `run`).

## 🔗 Verwandte Projekte

URTC besteht aus unabhängigen Repositories mit jeweils eigener Version, eigenen Tests und eigenem README. Das ist die Familie, nach Gruppen:

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (dieses Repository), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Über URTC hinaus:**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - die Hauptplatine des Roboterarms, deren CAN-Relay als der Bus dokumentiert ist, an dem der Werkzeugkopf hängt
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - dieselbe Idee für das Ökosystem HYDRA-UMC
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - dieselbe Idee für das Sicherheits-Ökosystem A.R.M.O.R.
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - das Profil und das Status-Dashboard aller Ökosysteme

## 📚 Dokumentation & Community

Mehr zum Lesen:

* [Richtlinie: jede Option, ihr Standardwert und wie man sie abschaltet](docs/POLICY.md)
* [Kennungen: was das Gateway mit jeder tut](docs/ALLOWED_IDS.md)
* [Änderungsprotokoll dieses Repositorys](CHANGELOG.md)
* [Lizenz (GPL-3.0-or-later)](LICENSE)
* Fragen, Ideen und Meldungen: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

<!-- urtc-section:compatibility -->
## 🧩 Kompatibilität

Welche Versionen der URTC-Programme zusammenarbeiten und welche Protokollversion jede spricht, steht in der Kompatibilitätstabelle, die URTC-COMMON erzeugt: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
