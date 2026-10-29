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

## 🎯 Vue d'ensemble

Le bus CAN de la tête d'outil n'authentifie pas l'émetteur : tout nœud raccordé aux fils est obéi. Quand une installation ne peut pas garder le bus fermé, cette passerelle se place devant :

* **Liste d'identifiants, produite à partir de la spécification :** seuls les identifiants qu'un hôte envoie traversent vers le bus ; les dangereux (bootloader, mise à jour de l'esclave d'extension, effacement de l'état enregistré, tout réglage persistant) sont refusés sauf si l'opérateur les débloque. [Le tableau des identifiants](docs/ALLOWED_IDS.md) est généré.
* **Contrôle de la charge utile :** une trame doit avoir la longueur et les valeurs que la spécification permet (une consigne dans sa plage, un sens qui existe, les octets magiques là où ils sont exigés).
* **Limite de débit :** un seau de jetons par identifiant et pour toute la liaison, et un seau plus strict pour un identifiant dangereux débloqué.
* **Clé de session :** un pair prouve qu'il détient une clé avec un HMAC sur un nonce de la connexion, un compteur et la trame, de sorte que rien d'enregistré ne peut être rejoué.
* **Toute protection peut être désactivée :** depuis le fichier de configuration ou la ligne de commande, et le programme énumère au démarrage chaque protection désactivée. Il ne chiffre pas et ne remplace pas les mesures matérielles du modèle de menaces.

## 🧩 Rôle dans URTC

Le modèle de menaces du dépôt URTC dit que, si une installation ne peut pas garder le bus fermé ou éviter de le relier à un réseau, la protection doit se trouver dans une passerelle devant le bus et non dans chaque tête d'outil. Ce dépôt est cette passerelle : utile pour un tunnel entre le contrôleur du robot et les têtes d'outil et pour exposer le bus à un réseau. Elle utilise la spécification du protocole d'URTC-COMMON comme seule source d'identifiants et de formats.

## 📂 Structure du dépôt

```text
URTC-GATEWAY/
├── src/urtc_gateway/  la passerelle : listes d'identifiants, politique, limite de débit, clés de session, options, extrémités TCP et série, ligne de commande
├── docs/              les options (POLICY.md) et le tableau généré des identifiants
├── tests/             tests unitaires de chaque protection et un test sur un vrai socket local
├── tools/             make_id_table.py et les contrôles de CI partagés de l'écosystème
├── images/            la bannière
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ COMPILATION ET EXÉCUTION

**Prérequis :** Python 3.10 ou plus récent ; pyserial seulement pour utiliser un vrai adaptateur SLCAN

```bash
python tools/make_id_table.py --check                              # le tableau des identifiants est à jour
python -m pytest tests -q                                          # les tests
python -m urtc_gateway.cli policy                                  # les options effectives et un avertissement pour chaque protection désactivée
python -m urtc_gateway.cli keygen keys.txt controller              # un nouveau fichier de clés (réservé au propriétaire, jamais écrasé)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # écouter sur 127.0.0.1:8765 sans rien sur le bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# la carte virtuelle d'URTC-COMMON (ou n'importe quelle URL pyserial) à la place d'un adaptateur
```

`build.sh` / `build.bat` montent la version d'un cran (le compteur kilométrique de l'écosystème), installent le paquet et lancent les tests ; `build-test.sh` / `build-test.bat` contrôlent sans changer aucune version ; `run.sh` / `run.bat` lancent la ligne de commande (`policy`, `ids`, `keygen`, `run`).

## 🔗 Projets liés

URTC est fait de dépôts indépendants, chacun avec sa version, ses tests et son README. Voici la famille, par groupes :

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (ce dépôt), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Au-delà de URTC :**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - la carte mère du bras robotique, dont le relais CAN est documenté comme le bus sur lequel se branche la tête d'outil
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - la même idée pour l'écosystème HYDRA-UMC
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - la même idée pour l'écosystème de sécurité A.R.M.O.R.
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - le profil et le tableau d'état de tous les écosystèmes

## 📚 Documentation et communauté

Pour en savoir plus :

* [Politique : chaque option, sa valeur par défaut et comment la désactiver](docs/POLICY.md)
* [Identifiants : ce que la passerelle fait de chacun](docs/ALLOWED_IDS.md)
* [Journal des modifications de ce dépôt](CHANGELOG.md)
* [Licence (GPL-3.0-or-later)](LICENSE)
* Questions, idées et signalements : electrohobby3d@gmail.com

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

<!-- urtc-section:compatibility -->
## 🧩 Compatibilité

Les versions des programmes URTC qui fonctionnent ensemble, et la version du protocole que parle chacune, figurent dans le tableau de compatibilité que génère URTC-COMMON : [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
