<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### Une passerelle devant le bus CAN : les identifiants qu'un hôte peut envoyer, une limite de débit et une clé de session

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** ce dépôt contient une passerelle écrite comme un logiciel : la liste des identifiants est produite à partir de la spécification du protocole, la charge utile de chaque trame est contrôlée par rapport à elle, le débit est limité et un pair doit prouver qu'il détient une clé. Le tout est testé en CI avec des simulations et un socket local. Il n'a jamais été relié à un vrai bus CAN, à un adaptateur ou à une carte, et aucune installation ne l'utilise encore. Les têtes de chauffage, de laser et de soudure ont toujours besoin des mesures matérielles du modèle de menaces : un verrouillage qu'aucune trame ne peut fermer, un bus fermé et un arrêt qui coupe l'alimentation.

---

> **État de la sûreté et de la cybersécurité :** cet écosystème n'est pas un système de sécurité certifié et aucune carte URTC assemblée n'existe encore. Les bootloaders contrôlent les images de firmware par CRC32 et un HMAC-SHA256 à clé partagée, pas par une signature asymétrique (prévue) ; les images d'application publiées sont signées avec la clé publique de développement (`signing_key_kind: dev`), si bien que n'importe qui peut produire une image acceptée par le bootloader ; rien n'a été transmis à une carte réelle. Lisez la [base de sécurité](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) et le [modèle de menaces](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) avant de vous fier à une affirmation d'ici pour la sécurité d'une personne.

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.0.2` |
| Maturité | Ébauche |
| Tests | 79 |
| Technologie | Python / CAN / HMAC |
| Cible | Le PC de la personne qui l'utilise |
| Sur matériel réel | Simulé seulement : testé avec des émulateurs, des doubles de test ou des simulateurs ; aucune exécution sur du matériel réel n'est consignée pour cette version |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Structure](#-structure-du-dépôt) · [Liés](#-projets-liés)

<!-- urtc-section:status_gateway -->
## 🚦 État du projet

🟢 fait et vérifié · 🟡 fonctionne, avec des limites connues · 🟠 à moitié fait ou non vérifié · 🔴 non fait ou non fonctionnel. Rien n'est vert si cela n'a jamais tourné sur du vrai matériel.

| Partie | État | Ce que le dépôt peut démontrer |
| --- | :---: | --- |
| Logiciel | 🟡 | Fonctionne sur un PC et face au simulateur ; jamais utilisé avec une vraie carte. |
| Tests | 🟢 | La suite de tests passe dans la CI à chaque push. |
| Matériel réel | 🟠 | Pas encore d'essai sur une vraie carte : l'essai au banc reste à faire. |
| Sécurité | 🟡 | Ne laisse passer que les identifiants listés et limite leur débit ; vérifié sur PC, jamais devant un vrai bus. |
| Documentation | 🟡 | README en huit langues et documents de référence ; les traductions n'ont pas été relues par des locuteurs natifs. |

<!-- /urtc-section:status_gateway -->

## 🎯 Présentation

Le bus CAN de la tête d'outil n'authentifie pas l'émetteur : tout nœud raccordé aux fils est obéi. Quand une installation ne peut pas garder le bus fermé, cette passerelle se place devant :

* **Liste d'identifiants, produite à partir de la spécification :** seuls les identifiants qu'un hôte envoie traversent vers le bus ; les dangereux (bootloader, mise à jour de l'esclave d'extension, effacement de l'état enregistré, tout réglage persistant) sont refusés sauf si l'opérateur les débloque. [Le tableau des identifiants](docs/ALLOWED_IDS.md) est généré.
* **Contrôle de la charge utile :** une trame doit avoir la longueur et les valeurs que la spécification permet (une consigne dans sa plage, un sens qui existe, les octets magiques là où ils sont exigés).
* **Limite de débit :** un seau de jetons par identifiant et pour toute la liaison, et un seau plus strict pour un identifiant dangereux débloqué.
* **Clé de session :** un pair prouve qu'il détient une clé avec un HMAC sur un nonce de la connexion, un compteur et la trame, de sorte que rien d'enregistré ne peut être rejoué.
* **Toute protection peut être désactivée :** depuis le fichier de configuration ou la ligne de commande, et le programme énumère au démarrage chaque protection désactivée. Il ne chiffre pas et ne remplace pas les mesures matérielles du modèle de menaces.

## 🧩 Rôle dans URTC

Le modèle de menaces du dépôt URTC dit que, si une installation ne peut pas garder le bus fermé ou éviter de le relier à un réseau, la protection doit se trouver dans une passerelle devant le bus et non dans chaque tête d'outil. Ce dépôt est cette passerelle : utile pour un tunnel entre le contrôleur du robot et les têtes d'outil et pour exposer le bus à un réseau. Elle utilise la spécification du protocole d'URTC-COMMON comme seule source d'identifiants et de formats.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="Architecture de URTC-GATEWAY : qui l'utilise, ce qu'il contient et de quoi il dépend" width="100%">
</p>

Comment les parties de ce dépôt s'articulent : qui l'utilise, ce qu'il contient et de quoi il dépend. L'image est dessinée à partir de `docs/architecture.json` et vérifiée par rapport au code.

## 🔒 Sécurité et protection

| Menace | Défense |
|---|---|
| Un nœud sur les fils envoie une commande dangereuse (chargeur d'amorçage, mise à jour de l'esclave d'extension, effacement de l'état sauvegardé, un réglage persistant) | La liste d'identifiants les refuse tant que l'opérateur ne les déverrouille pas avec `--unlock-dangerous` |
| Une valeur hors de ce que le protocole permet (une consigne hors plage, un sens qui n'existe pas, de mauvais octets magiques) | Le contrôle de la charge refuse la trame |
| Un émetteur emballé ou hostile inonde le bus | Un seau à jetons par identifiant et pour toute la liaison, et un plus strict pour un identifiant dangereux déverrouillé |
| Un message enregistré est renvoyé | La clé de session : un HMAC sur un nonce de la connexion, un compteur qui doit croître et la trame, de sorte qu'un enregistrement est inutile plus tard et ailleurs |
| La passerelle est joignable depuis un réseau sans clé | Écouter sur une adresse non locale sans clé de session est refusé sauf si `--allow-open-network` est donné |

Elle ne chiffre pas : le bus n'est pas un secret. Elle n'arrête pas un pair qui détient la clé et se comporte mal ; la liste, le contrôle de la charge et la limite de débit sont là pour cela, ainsi que les chiens de garde des têtes d'outil. Elle ne remplace pas les mesures matérielles du modèle de menaces du CAN (un verrouillage qu'aucune trame ne peut fermer, un bus fermé, un arrêt qui coupe l'alimentation). Elle n'a jamais été utilisée sur un vrai bus.

## 🔌 Interfaces

La ligne de commande est `urtc-gateway` (ou `python -m urtc_gateway.cli`) :

| Commande | Ce qu'elle fait |
|---|---|
| `policy` | affiche les options effectives et un avertissement pour chaque protection désactivée |
| `ids` | liste chaque identifiant et ce que la passerelle en fait |
| `keygen FILE PEER [PEER ...]` | écrit un fichier de clés avec une nouvelle clé aléatoire pour chaque pair (lisible par son propriétaire seul, jamais sur un fichier existant, les clés ne sont pas affichées) ; ne donnez à chaque pair que sa propre ligne |
| `run` | écoute sur un port TCP (`--host`, `127.0.0.1` par défaut ; `--port`, `8765` par défaut) et transmet à un bus (`--bus loopback`, une URL pyserial comme `socket://127.0.0.1:7777`, ou le port série d'un adaptateur SLCAN ; `--bitrate`, 500000 par défaut) |

**Le protocole de lignes.** À la connexion, la passerelle envoie `{"type": "hello", "nonce": "<hex>", "session": true}`. Chaque message du pair est un objet JSON par ligne : `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 chiffres hex>"}`. `mac` est constitué des 16 premiers octets de HMAC-SHA256, avec la clé du pair, sur `urtc-gw/1|<nonce>|<compteur>|<id en trois chiffres hex>|<données en hex>` ; le compteur doit croître à chaque message de la connexion et le nonce est nouveau à chaque connexion. Un message refusé reçoit `{"type": "refused", "code": "<motif>"}`, et les trames du bus reviennent sous la forme `{"type": "frame", "id": ..., "data": "<hex>"}`. Voir [la politique](docs/POLICY.md).

## ⚙️ Configuration

Chaque protection est activée par défaut et chacune peut être désactivée, dans un fichier de configuration JSON (`--config FILE`, `"schema": 1` ; une section ou option inconnue, un mauvais type ou un débit négatif est une erreur qui dit ce qui ne va pas) et sur la ligne de commande, qui l'emporte sur le fichier. Une protection désactivée ou assouplie est listée comme avertissement au démarrage du programme.

| Protection | Section du fichier | Désactiver / activer | Ce qu'elle fait |
|---|---|---|---|
| Liste d'identifiants | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | seuls les identifiants qu'envoie un hôte passent vers le bus |
| Identifiants dangereux | `whitelist.unlock_dangerous` | `--unlock-dangerous` | le chargeur d'amorçage, la mise à jour de l'esclave d'extension, l'effacement de l'état sauvegardé et tout réglage persistant restent refusés jusqu'au déverrouillage |
| Identifiants ajoutés / retirés | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | ajouter un identifiant à la main ou en retirer un quoi que dise le reste |
| Contrôle de la charge | `payload.enabled` | `--no-payload-check` / `--payload-check` | la longueur et les valeurs doivent être celles que la spécification permet |
| Limite de débit | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 trames par seconde et une rafale de 10 par identifiant, une rafale de 50 pour la liaison, une de 2 pour un identifiant dangereux déverrouillé ; `rate.overrides` donne à un identifiant son propre débit et sa propre rafale |
| Clé de session | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | un pair prouve qu'il détient une clé |
| Filtre sortant | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | seul ce qu'envoie une carte va vers le réseau, jusqu'à 500 trames par seconde |
| Réseau ouvert | `server.allow_open_network` | `--allow-open-network` | écouter sur une adresse non locale sans clé de session est refusé sauf demande explicite |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Démarrage rapide

**Prérequis :** Python 3.10 ou plus récent ; pyserial seulement pour utiliser un vrai adaptateur SLCAN

```bash
python tools/make_id_table.py --check                              # le tableau des identifiants est à jour
python -m pytest tests -q                                          # les tests
python -m urtc_gateway.cli policy                                  # les options effectives et un avertissement pour chaque protection désactivée
python -m urtc_gateway.cli keygen keys.txt controller              # un nouveau fichier de clés (réservé au propriétaire, jamais écrasé)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # écouter sur 127.0.0.1:8765 sans rien sur le bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# la carte virtuelle d'URTC-COMMON (ou n'importe quelle URL pyserial) à la place d'un adaptateur
```

<!-- urtc-section:compatibility -->
### Prérequis et compatibilité

Les versions des programmes URTC qui fonctionnent ensemble, et la version du protocole que parle chacune, figurent dans le tableau de compatibilité que génère URTC-COMMON : [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Tests

La suite compte 79 tests (`python -m pytest tests -q`) : la liste d'identifiants, le contrôle de la charge, la limite de débit, la session et ses refus, les options et le fichier de configuration, la ligne de commande, un test sur une vraie socket locale et l'extrémité série face à un faux port. Un test est ignoré quand sa dépendance optionnelle manque. `python -m mypy` vérifie les types du paquet et `ruff check .` le code.

## 🏗️ Compilation et publication

`build.sh` / `build.bat` installent le paquet et lancent les tests ; `build-test.sh` / `build-test.bat` vérifient sans changer aucune version ; `run.sh` / `run.bat` lancent la ligne de commande (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` écrit le tableau des identifiants de [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) à partir de la spécification (`--check` compare).

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Structure du dépôt URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                la passerelle : liste d'identifiants, politique, limite de débit, clés de session, options, extrémités TCP et série, ligne de commande
├── docs/                                            les options (POLICY.md) et le tableau généré des identifiants
├── tests/                                           tests unitaires de chaque protection et un test sur une vraie socket locale
├── tools/                                           make_id_table.py et les outils partagés de CI et d'images
├── images/                                          bannière et images de ce README
├── .github/                                         workflow de CI et modèles d'issues et de pull requests
├── build.sh build.bat                               scripts de compilation
├── build-test.sh build-test.bat                     scripts de compilation et de test qui ne changent rien dans le dépôt
├── test.sh test.bat                                 lancent les tests
├── run.sh run.bat                                   lancent le programme
├── urtc.project.json                                manifeste : version, rôle, maturité et commande de compilation
├── CHANGELOG.md                                     ce qui a changé à chaque version
├── SECURITY.md SUPPORT.md LICENSE                   politique de sécurité, assistance et licence
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               comment contribuer et code de conduite
├── .gitattributes .gitignore                        réglages Git
├── bump_version.py bump_manifest_version.py         scripts qui augmentent la version
└── pyproject.toml requirements-dev.lock ruff.toml   paquet, outils figés et réglages de lint
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

* Elle n'a jamais été connectée à un vrai bus CAN, un adaptateur ou une carte, et aucune installation ne l'utilise encore ; elle est testée en CI avec des faux et une socket locale.
* Les têtes chauffantes, laser et de soudure exigent toujours les mesures matérielles du modèle de menaces : un verrouillage qu'aucune trame ne peut fermer, un bus fermé et un arrêt qui coupe l'alimentation.
* Elle ne chiffre pas et n'arrête pas un pair qui détient la clé et se comporte mal.

**Ensuite**

* L'essayer sur banc entre un contrôleur et une vraie tête d'outil, d'abord derrière la carte virtuelle.

## 🌍 Langues

Le README et les textes existent en anglais, espagnol, français, italien, allemand, chinois, japonais et portugais européen.

## 🔗 Projets liés

URTC est fait de dépôts indépendants, chacun avec sa version, ses tests et son README. Voici la famille, par groupes :

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware de la carte de la tête d'outil (25 profils d'outil, bootloader CAN) et référence du protocole CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - le protocole CAN écrit une seule fois comme données (spécification, tables générées, vecteurs de conformité) et le code que les programmes partagent.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - outil de bureau qui met à jour le firmware de la carte par CAN ou par SWD/JTAG.
  * **URTC-GATEWAY** (ce dépôt) - passerelle devant le bus CAN : ne laisse passer que les identifiants d'une liste, limite leur cadence et demande une clé de session.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - logique C indépendante du matériel et protocole de commandes pour un support d'outils avec préchauffage et suivi du cycle de vie.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - testeur de bureau du bus CAN en direct qui affiche les commandes et la télémétrie du profil d'outil signalé par une carte.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocole de trames de capteur en C et compagnon Python thermique/RVB pour une tête d'outil d'inspection.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - application de navigateur qui flashe et teste la carte via Web Serial et SLCAN, sans rien installer.
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - architecture, interfaces, base de sécurité et catalogue généré de l'écosystème, plus les outils qui comparent tous les dépôts.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - outil de bureau qui détecte, installe et met à jour les dépôts de la famille URTC, une action explicite à la fois.

**Projets frères (indépendants, avec la même base et les mêmes outils) :**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - projet frère : le centre de documentation de HYDRA-UMC, un écosystème indépendant qui partage la base et les outils de celui-ci
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - projet frère : le centre de documentation d'A.R.M.O.R., l'écosystème de sécurité, lui aussi indépendant et construit sur la même base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - le profil et le tableau d'état de tous les écosystèmes

## 📚 Documentation

Pour en savoir plus :

* [Politique : chaque option, sa valeur par défaut et comment la désactiver](docs/POLICY.md)
* [Identifiants : ce que la passerelle fait de chacun](docs/ALLOWED_IDS.md)
* [Journal des modifications de ce dépôt](CHANGELOG.md)
* [Licence (GPL-3.0-or-later)](LICENSE)
* Questions, idées et signalements : electrohobby3d@gmail.com

## 🤝 Contribuer et communauté

* Avant une pull request, lancez `URTC_CI=1 python tools/ci_validate.py` : il doit réussir. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).
* Le README existe en huit langues : une modification du texte se fait dans les huit fichiers, et les sections partagées avec d'autres dépôts sont écrites par `tools/readme_sections.py` d'URTC-COMMON.
* Un changement du protocole CAN commence dans URTC-COMMON (`spec/can_protocol.json`) et arrive dans ce dépôt par la copie vérifiée.
* Ne décrivez pas comme fonctionnant sur une carte ce qui a seulement été compilé.
* Signalez une vulnérabilité en privé : [SECURITY.md](SECURITY.md). Questions, idées et rapports : electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
