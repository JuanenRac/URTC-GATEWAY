<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### Una pasarela delante del bus CAN: los identificadores que un host puede enviar, un límite de tasa y una clave de sesión

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.1-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - lo que realmente funciona hoy:** este repositorio contiene una pasarela escrita como software: la lista de identificadores se hace a partir de la especificación del protocolo, la carga de cada trama se comprueba contra ella, la tasa está limitada y un interlocutor tiene que demostrar que posee una clave. Todo se prueba en CI con simulaciones y un socket local. Nunca se ha conectado a un bus CAN real, a un adaptador ni a una placa, y ninguna instalación la usa todavía. Los cabezales de calefacción, láser y soldadura siguen necesitando las medidas de hardware del modelo de amenazas: un enclavamiento que ninguna trama pueda cerrar, un bus cerrado y una parada que corte la alimentación.

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado y todavía no existe ninguna placa URTC poblada. Los bootloaders comprueban las imágenes de firmware con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica (prevista); las imágenes de aplicación publicadas están firmadas con la clave pública de desarrollo (`signing_key_kind: dev`), así que cualquiera puede producir una imagen que el bootloader acepte; no se ha transmitido nada a una placa real. Lee la [línea base de seguridad](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.0.1` |
| Madurez | Andamiaje |
| Tests | 75 |
| Tecnología | Python / CAN / HMAC |
| Destino | El PC de quien lo usa |
| En hardware real | Solo simulado: probado con emuladores, dobles de prueba o simuladores; no consta ninguna ejecución en hardware real para esta versión |

## 🎯 Descripción general

El bus CAN del cabezal de herramienta no autentica al emisor: se obedece a cualquier nodo conectado a los cables. Cuando una instalación no puede mantener el bus cerrado, esta pasarela se coloca delante:

* **Lista de identificadores, hecha a partir de la especificación:** solo cruzan hacia el bus los identificadores que envía un host; los peligrosos (bootloader, actualización del esclavo de expansión, borrado del estado guardado, cualquier ajuste persistente) se rechazan salvo que el operador los desbloquee. [La tabla de identificadores](docs/ALLOWED_IDS.md) se genera.
* **Comprobación de la carga:** una trama debe tener la longitud y los valores que permite la especificación (una consigna dentro de su rango, una dirección que existe, los bytes mágicos donde se exigen).
* **Límite de tasa:** un cubo de fichas por identificador y para todo el enlace, y uno más estricto para un identificador peligroso desbloqueado.
* **Clave de sesión:** un interlocutor demuestra que posee una clave con un HMAC sobre un nonce de la conexión, un contador y la trama, de modo que nada grabado puede repetirse.
* **Toda protección se puede desactivar:** desde el fichero de configuración o la línea de comandos, y el programa enumera al arrancar cada protección que está apagada. No cifra, y no sustituye las medidas de hardware del modelo de amenazas.

## 🧩 Papel en URTC

El modelo de amenazas del repositorio URTC dice que, si una instalación no puede mantener el bus cerrado o no puede evitar conectarlo a una red, la protección va en una pasarela delante del bus y no en cada cabezal. Este repositorio es esa pasarela: útil para un túnel entre el controlador del robot y los cabezales y para exponer el bus a una red. Usa la especificación del protocolo de URTC-COMMON como única fuente de identificadores y formatos.

## 📂 Estructura del repositorio

```text
URTC-GATEWAY/
├── src/urtc_gateway/  la pasarela: listas de identificadores, política, límite de tasa, claves de sesión, opciones, extremos TCP y serie, línea de comandos
├── docs/              las opciones (POLICY.md) y la tabla generada de identificadores
├── tests/             pruebas unitarias de cada protección y una prueba con un socket local real
├── tools/             make_id_table.py y las comprobaciones de CI compartidas del ecosistema
├── images/            el banner
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ COMPILACIÓN Y EJECUCIÓN

**Requisitos:** Python 3.10 o superior; pyserial solo para usar un adaptador SLCAN real

```bash
python tools/make_id_table.py --check                              # la tabla de identificadores está al día
python -m pytest tests -q                                          # las pruebas
python -m urtc_gateway.cli policy                                  # las opciones efectivas y un aviso por cada protección apagada
python -m urtc_gateway.cli keygen keys.txt controller              # un fichero de claves nuevo (solo para el propietario, nunca se sobrescribe)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # escuchar en 127.0.0.1:8765 sin nada en el bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# la placa virtual de URTC-COMMON (o cualquier URL de pyserial) en lugar de un adaptador
```

`build.sh` / `build.bat` suben la versión un paso (el cuentakilómetros del ecosistema), instalan el paquete y ejecutan las pruebas; `build-test.sh` / `build-test.bat` comprueban sin cambiar ninguna versión; `run.sh` / `run.bat` inician la línea de comandos (`policy`, `ids`, `keygen`, `run`).

## 🔗 Proyectos relacionados

URTC se compone de repositorios independientes, cada uno con su versión, sus pruebas y su README. Esta es la familia, por grupos:

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (este repositorio), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Más allá de URTC:**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - la placa base del brazo robótico, cuyo relé CAN está documentado como el bus en el que se conecta la cabeza de herramienta
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - la misma idea para el ecosistema HYDRA-UMC
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - la misma idea para el ecosistema de seguridad A.R.M.O.R.
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - el perfil y el panel de estado de todos los ecosistemas

## 📚 Documentación y comunidad

Dónde leer más:

* [Política: cada opción, su valor por defecto y cómo desactivarla](docs/POLICY.md)
* [Identificadores: qué hace la pasarela con cada uno](docs/ALLOWED_IDS.md)
* [Registro de cambios de este repositorio](CHANGELOG.md)
* [Licencia (GPL-3.0-or-later)](LICENSE)
* Preguntas, ideas e informes: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
