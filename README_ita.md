<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### Un gateway davanti al bus CAN: gli identificatori che un host può inviare, un limite di frequenza e una chiave di sessione

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Verifica di onestà - cosa funziona davvero oggi:** questo repository contiene un gateway scritto come software: l'elenco degli identificatori è ricavato dalla specifica del protocollo, il contenuto di ogni frame è controllato rispetto ad essa, la frequenza è limitata e un interlocutore deve dimostrare di possedere una chiave. Tutto è testato in CI con simulazioni e un socket locale. Non è mai stato collegato a un vero bus CAN, a un adattatore o a una scheda, e nessuna installazione lo usa ancora. Le teste di riscaldamento, laser e saldatura richiedono ancora le misure hardware del modello di minaccia: un interblocco che nessun frame possa chiudere, un bus chiuso e un arresto che tolga l'alimentazione.

---

> **Stato di sicurezza (safety e security):** questo ecosistema non è un sistema di sicurezza certificato e non esiste ancora alcuna scheda URTC assemblata. I bootloader controllano le immagini firmware con CRC32 e un HMAC-SHA256 a chiave condivisa, non con una firma asimmetrica (prevista); le immagini applicative pubblicate sono firmate con la chiave pubblica di sviluppo (`signing_key_kind: dev`), quindi chiunque può produrre un'immagine accettata dal bootloader; nulla è stato trasmesso a una scheda reale. Leggi la [base di sicurezza](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e il [modello delle minacce](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) prima di fidarti di qualsiasi affermazione qui per la sicurezza di una persona.

## 📋 In breve

| | |
|---|---|
| Versione | `0.0.3` |
| Maturità | Impalcatura |
| Test | 79 |
| Tecnologia | Python / CAN / HMAC |
| Destinazione | Il PC di chi lo usa |
| Su hardware reale | Solo simulato: provato con emulatori, test double o simulatori; per questa versione non risulta alcuna esecuzione su hardware reale |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza](#-sicurezza-e-protezione) · [Interfacce](#-interfacce) · [Configurazione](#-configurazione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Struttura](#-struttura-del-repository) · [Correlati](#-progetti-correlati)

<!-- urtc-section:status_gateway -->
## 🚦 Stato del progetto

🟢 fatto e verificato · 🟡 funziona, con limiti noti · 🟠 a metà o non verificato · 🔴 non fatto o non funzionante. Nulla è verde se non ha mai girato su hardware reale.

| Parte | Stato | Ciò che il repository può dimostrare |
| --- | :---: | --- |
| Software | 🟡 | Funziona su un PC e contro il simulatore; mai usato con una scheda reale. |
| Test | 🟢 | La suite di test passa nella CI a ogni push. |
| Hardware reale | 🟠 | Nessuna esecuzione su una scheda reale: la prova al banco è ancora da fare. |
| Sicurezza | 🟡 | Lascia passare solo gli identificatori elencati e ne limita la frequenza; verificato su PC, mai davanti a un bus reale. |
| Documentazione | 🟡 | README in otto lingue e documenti di riferimento; le traduzioni non sono state riviste da madrelingua. |

<!-- /urtc-section:status_gateway -->

## 🎯 Panoramica

Il bus CAN della testa utensile non autentica il mittente: qualsiasi nodo collegato ai fili viene obbedito. Quando un'installazione non può tenere il bus chiuso, questo gateway si colloca davanti:

* **Elenco di identificatori, ricavato dalla specifica:** verso il bus passano solo gli identificatori che un host invia; quelli pericolosi (bootloader, aggiornamento dello slave di espansione, cancellazione dello stato salvato, ogni impostazione persistente) sono rifiutati a meno che l'operatore li sblocchi. [La tabella degli identificatori](docs/ALLOWED_IDS.md) è generata.
* **Controllo del contenuto:** un frame deve avere la lunghezza e i valori che la specifica consente (un setpoint nel suo intervallo, una direzione esistente, i byte magici dove sono richiesti).
* **Limite di frequenza:** un secchio di gettoni per identificatore e per l'intero collegamento, e uno più rigido per un identificatore pericoloso sbloccato.
* **Chiave di sessione:** un interlocutore dimostra di possedere una chiave con un HMAC su un nonce della connessione, un contatore e il frame, così nulla di registrato può essere riproposto.
* **Ogni protezione si può disattivare:** dal file di configurazione o dalla riga di comando, e il programma elenca all'avvio ogni protezione spenta. Non cifra e non sostituisce le misure hardware del modello di minaccia.

## 🧩 Ruolo in URTC

Il modello di minaccia del repository URTC dice che, se un'installazione non può tenere il bus chiuso o non può evitare di collegarlo a una rete, la protezione va in un gateway davanti al bus e non in ogni testa utensile. Questo repository è quel gateway: utile per un tunnel tra il controllore del robot e le teste utensile e per esporre il bus a una rete. Usa la specifica del protocollo di URTC-COMMON come unica fonte di identificatori e formati.

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="Architettura di URTC-GATEWAY: chi lo usa, che cosa contiene e da che cosa dipende" width="100%">
</p>

Come si incastrano le parti di questo repository: chi lo usa, che cosa contiene e da che cosa dipende. L'immagine è disegnata da `docs/architecture.json` e verificata rispetto al codice.

## 🔒 Sicurezza e protezione

| Minaccia | Difesa |
|---|---|
| Un nodo sui fili invia un comando pericoloso (bootloader, aggiornamento dello slave di espansione, cancellazione dello stato salvato, un'impostazione persistente) | L'elenco degli identificatori li rifiuta finché l'operatore non li sblocca con `--unlock-dangerous` |
| Un valore fuori da ciò che il protocollo consente (un setpoint fuori intervallo, una direzione inesistente, byte magici errati) | Il controllo del payload rifiuta il frame |
| Un mittente fuori controllo o ostile inonda il bus | Un token bucket per identificatore e per l'intero collegamento, e uno più severo per un identificatore pericoloso sbloccato |
| Un messaggio registrato viene inviato di nuovo | La chiave di sessione: un HMAC su un nonce della connessione, un contatore che deve crescere e il frame, così una registrazione è inutile dopo e altrove |
| Il gateway è raggiungibile da una rete senza chiave | L'ascolto su un indirizzo non locale senza chiave di sessione viene rifiutato salvo `--allow-open-network` |

Non cifra: il bus non è un segreto. Non ferma un peer che possiede la chiave e si comporta male; per questo ci sono l'elenco, il controllo del payload, il limite di frequenza e i watchdog delle teste utensile. Non sostituisce le misure hardware del modello di minacce del CAN (un interblocco che nessun frame può chiudere, un bus chiuso, un arresto che taglia l'alimentazione). Non è mai stato usato su un bus reale.

## 🔌 Interfacce

La riga di comando è `urtc-gateway` (o `python -m urtc_gateway.cli`):

| Comando | Che cosa fa |
|---|---|
| `policy` | mostra le opzioni effettive e un avviso per ogni protezione disattivata |
| `ids` | elenca ogni identificatore e che cosa ne fa il gateway |
| `keygen FILE PEER [PEER ...]` | scrive un file di chiavi con una nuova chiave casuale per ogni peer (leggibile solo dal proprietario, mai su un file esistente, le chiavi non vengono mostrate); dai a ogni peer solo la sua riga |
| `run` | ascolta su una porta TCP (`--host`, predefinito `127.0.0.1`; `--port`, predefinita `8765`) e inoltra a un bus (`--bus loopback`, un URL pyserial come `socket://127.0.0.1:7777` o la porta seriale di un adattatore SLCAN; `--bitrate`, predefinito 500000) |

**Il protocollo a righe.** Alla connessione il gateway invia `{"type": "hello", "nonce": "<hex>", "session": true}`. Ogni messaggio del peer è un oggetto JSON per riga: `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 cifre hex>"}`. `mac` sono i primi 16 byte di HMAC-SHA256, con la chiave del peer, su `urtc-gw/1|<nonce>|<contatore>|<id in tre cifre hex>|<dati in hex>`; il contatore deve crescere a ogni messaggio della connessione e il nonce è nuovo a ogni connessione. A un messaggio rifiutato si risponde con `{"type": "refused", "code": "<motivo>"}` e i frame del bus tornano come `{"type": "frame", "id": ..., "data": "<hex>"}`. Vedi [la politica](docs/POLICY.md).

## ⚙️ Configurazione

Ogni protezione è attiva per impostazione predefinita e ognuna può essere disattivata, in un file di configurazione JSON (`--config FILE`, `"schema": 1`; una sezione o opzione sconosciuta, un tipo errato o una frequenza negativa è un errore che dice che cosa non va) e dalla riga di comando, che prevale sul file. Una protezione disattivata o allentata viene elencata come avviso all'avvio del programma.

| Protezione | Sezione del file | Disattiva / attiva | Che cosa fa |
|---|---|---|---|
| Elenco degli identificatori | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | verso il bus passano solo gli identificatori che invia un host |
| Identificatori pericolosi | `whitelist.unlock_dangerous` | `--unlock-dangerous` | il bootloader, l'aggiornamento dello slave di espansione, la cancellazione dello stato salvato e ogni impostazione persistente restano rifiutati finché non vengono sbloccati |
| Identificatori aggiunti / tolti | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | aggiungere un identificatore a mano o toglierne uno qualunque cosa dica il resto |
| Controllo del payload | `payload.enabled` | `--no-payload-check` / `--payload-check` | lunghezza e valori devono essere quelli che la specifica consente |
| Limite di frequenza | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 frame al secondo e una raffica di 10 per identificatore, una raffica di 50 per il collegamento, una di 2 per un identificatore pericoloso sbloccato; `rate.overrides` dà a un identificatore la propria frequenza e raffica |
| Chiave di sessione | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | un peer dimostra di possedere una chiave |
| Filtro in uscita | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | verso la rete va solo ciò che invia una scheda, fino a 500 frame al secondo |
| Rete aperta | `server.allow_open_network` | `--allow-open-network` | l'ascolto su un indirizzo non locale senza chiave di sessione viene rifiutato salvo richiesta esplicita |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Avvio rapido

**Requisiti:** Python 3.10 o superiore; pyserial solo per usare un vero adattatore SLCAN

```bash
python tools/make_id_table.py --check                              # la tabella degli identificatori è aggiornata
python -m pytest tests -q                                          # i test
python -m urtc_gateway.cli policy                                  # le opzioni effettive e un avviso per ogni protezione disattivata
python -m urtc_gateway.cli keygen keys.txt controller              # un nuovo file di chiavi (solo per il proprietario, mai sovrascritto)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # restare in ascolto su 127.0.0.1:8765 senza nulla sul bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# la scheda virtuale di URTC-COMMON (o qualsiasi URL pyserial) al posto di un adattatore
```

<!-- urtc-section:compatibility -->
### Requisiti e compatibilità

Quali versioni dei programmi URTC funzionano insieme, e quale versione del protocollo parla ciascuna, è elencato nella tabella di compatibilità generata da URTC-COMMON: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Test

La suite ha 79 test (`python -m pytest tests -q`): l'elenco degli identificatori, il controllo del payload, il limite di frequenza, la sessione e i suoi rifiuti, le opzioni e il file di configurazione, la riga di comando, un test su un vero socket locale e l'estremità seriale contro una porta finta. Un test viene saltato se manca la sua dipendenza opzionale. `python -m mypy` controlla i tipi del pacchetto e `ruff check .` il codice.

## 🏗️ Compilazione e rilascio

`build.sh` / `build.bat` installano il pacchetto ed eseguono i test; `build-test.sh` / `build-test.bat` controllano senza cambiare alcuna versione; `run.sh` / `run.bat` avviano la riga di comando (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` scrive la tabella degli identificatori di [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) dalla specifica (`--check` confronta).

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Struttura del repository URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                il gateway: elenco degli identificatori, politica, limite di frequenza, chiavi di sessione, opzioni, estremità TCP e seriale, riga di comando
├── docs/                                            le opzioni (POLICY.md) e la tabella generata degli identificatori
├── tests/                                           test unitari di ogni protezione e un test su un vero socket locale
├── tools/                                           make_id_table.py e gli strumenti condivisi di CI e immagini
├── images/                                          banner e immagini di questo README
├── .github/                                         workflow di CI e modelli per issue e pull request
├── build.sh build.bat                               script di compilazione
├── build-test.sh build-test.bat                     script di compilazione e test che non cambiano nulla nel repository
├── test.sh test.bat                                 eseguono i test
├── run.sh run.bat                                   avviano il programma
├── urtc.project.json                                manifesto: versione, ruolo, maturità e comando di compilazione
├── CHANGELOG.md                                     che cosa è cambiato in ogni versione
├── SECURITY.md SUPPORT.md LICENSE                   politica di sicurezza, supporto e licenza
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               come contribuire e codice di condotta
├── .gitattributes .gitignore                        impostazioni di Git
├── bump_version.py bump_manifest_version.py         script che alzano la versione
└── pyproject.toml requirements-dev.lock ruff.toml   pacchetto, strumenti bloccati e impostazioni di lint
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

* Non è mai stato collegato a un vero bus CAN, a un adattatore o a una scheda, e nessuna installazione lo usa ancora; è testato in CI con finti e un socket locale.
* Le teste di riscaldamento, laser e saldatura richiedono ancora le misure hardware del modello di minacce: un interblocco che nessun frame può chiudere, un bus chiuso e un arresto che taglia l'alimentazione.
* Non cifra e non ferma un peer che possiede la chiave e si comporta male.

**Prossimi passi**

* Provarlo su banco tra un controllore e una vera testa utensile, prima dietro la scheda virtuale.

## 🌍 Lingue

Il README e i testi esistono in inglese, spagnolo, francese, italiano, tedesco, cinese, giapponese e portoghese europeo.

## 🔗 Progetti correlati

URTC è fatto di repository indipendenti, ciascuno con la propria versione, i propri test e il proprio README. Ecco la famiglia, per gruppi:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware della scheda della testa utensile (25 profili utensile, bootloader CAN) e riferimento del protocollo CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - il protocollo CAN scritto una sola volta come dati (specifica, tabelle generate, vettori di conformità) e il codice condiviso dai programmi.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - strumento desktop che aggiorna il firmware della scheda via CAN o via SWD/JTAG.
  * **URTC-GATEWAY** (questo repository) - gateway davanti al bus CAN: lascia passare solo gli identificatori di un elenco, ne limita la frequenza e chiede una chiave di sessione.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - logica C indipendente dall'hardware e protocollo di comandi per un portautensili con preriscaldamento e tracciamento del ciclo di vita.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - tester desktop del bus CAN in tempo reale che mostra i comandi e la telemetria del profilo utensile segnalato da una scheda.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocollo di frame del sensore in C e un companion Python termico/RGB per una testa utensile di ispezione.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - app per browser che programma e collauda la scheda via Web Serial e SLCAN, senza installare nulla.
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - architettura, interfacce, base di sicurezza e catalogo generato dell'ecosistema, più gli strumenti che confrontano tutti i repository.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - strumento desktop che rileva, installa e aggiorna i repository della famiglia URTC, un'azione esplicita alla volta.

**Progetti fratelli (indipendenti, con la stessa base e gli stessi strumenti):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - progetto fratello: il centro di documentazione di HYDRA-UMC, un ecosistema indipendente che condivide base e strumenti con questo
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - progetto fratello: il centro di documentazione di A.R.M.O.R., l'ecosistema di sicurezza, anch'esso indipendente e sulla stessa base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - il profilo e il pannello di stato di tutti gli ecosistemi

## 📚 Documentazione

Dove leggere di più:

* [Politica: ogni opzione, il suo valore predefinito e come disattivarla](docs/POLICY.md)
* [Identificatori: cosa fa il gateway con ciascuno](docs/ALLOWED_IDS.md)
* [Registro delle modifiche di questo repository](CHANGELOG.md)
* [Licenza (GPL-3.0-or-later)](LICENSE)
* Domande, idee e segnalazioni: electrohobby3d@gmail.com

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `URTC_CI=1 python tools/ci_validate.py`: deve passare. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) e il [codice di condotta](CODE_OF_CONDUCT.md).
* Il README esiste in otto lingue: una modifica del testo si fa in tutti e otto i file, e le sezioni condivise con altri repository le scrive `tools/readme_sections.py` di URTC-COMMON.
* Una modifica al protocollo CAN parte da URTC-COMMON (`spec/can_protocol.json`) e arriva in questo repository tramite la copia verificata.
* Non descrivere come funzionante su una scheda ciò che è stato solo compilato.
* Segnala una vulnerabilità in privato: [SECURITY.md](SECURITY.md). Domande, idee e segnalazioni: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
