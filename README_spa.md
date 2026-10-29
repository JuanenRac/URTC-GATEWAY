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
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - lo que realmente funciona hoy:** este repositorio contiene una pasarela escrita como software: la lista de identificadores se hace a partir de la especificación del protocolo, la carga de cada trama se comprueba contra ella, la tasa está limitada y un interlocutor tiene que demostrar que posee una clave. Todo se prueba en CI con simulaciones y un socket local. Nunca se ha conectado a un bus CAN real, a un adaptador ni a una placa, y ninguna instalación la usa todavía. Los cabezales de calefacción, láser y soldadura siguen necesitando las medidas de hardware del modelo de amenazas: un enclavamiento que ninguna trama pueda cerrar, un bus cerrado y una parada que corte la alimentación.

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado y todavía no existe ninguna placa URTC poblada. Los bootloaders comprueban las imágenes de firmware con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica (prevista); las imágenes de aplicación publicadas están firmadas con la clave pública de desarrollo (`signing_key_kind: dev`), así que cualquiera puede producir una imagen que el bootloader acepte; no se ha transmitido nada a una placa real. Lee la [línea base de seguridad](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.0.3` |
| Madurez | Andamiaje |
| Tests | 79 |
| Tecnología | Python / CAN / HMAC |
| Destino | El PC de quien lo usa |
| En hardware real | Solo simulado: probado con emuladores, dobles de prueba o simuladores; no consta ninguna ejecución en hardware real para esta versión |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

<!-- urtc-section:status_gateway -->
## 🚦 Estado del proyecto

🟢 hecho y verificado · 🟡 funciona, con límites conocidos · 🟠 a medias o sin verificar · 🔴 sin hacer o sin funcionar. Nada es verde si nunca corrió en hardware real.

| Parte | Estado | Lo que el repositorio puede demostrar |
| --- | :---: | --- |
| Software | 🟡 | Funciona en un PC y contra el simulador; nunca se ha usado con una placa real. |
| Pruebas | 🟢 | La batería de pruebas pasa en la CI en cada subida. |
| Hardware real | 🟠 | Aún no se ha ejecutado con una placa real: la prueba de banco sigue pendiente. |
| Seguridad | 🟡 | Solo deja pasar los identificadores listados y limita su frecuencia; comprobado en un PC, nunca ante un bus real. |
| Documentación | 🟡 | README en ocho idiomas y documentos de referencia; las traducciones no las ha revisado ningún hablante nativo. |

<!-- /urtc-section:status_gateway -->

## 🎯 Resumen

El bus CAN del cabezal de herramienta no autentica al emisor: se obedece a cualquier nodo conectado a los cables. Cuando una instalación no puede mantener el bus cerrado, esta pasarela se coloca delante:

* **Lista de identificadores, hecha a partir de la especificación:** solo cruzan hacia el bus los identificadores que envía un host; los peligrosos (bootloader, actualización del esclavo de expansión, borrado del estado guardado, cualquier ajuste persistente) se rechazan salvo que el operador los desbloquee. [La tabla de identificadores](docs/ALLOWED_IDS.md) se genera.
* **Comprobación de la carga:** una trama debe tener la longitud y los valores que permite la especificación (una consigna dentro de su rango, una dirección que existe, los bytes mágicos donde se exigen).
* **Límite de tasa:** un cubo de fichas por identificador y para todo el enlace, y uno más estricto para un identificador peligroso desbloqueado.
* **Clave de sesión:** un interlocutor demuestra que posee una clave con un HMAC sobre un nonce de la conexión, un contador y la trama, de modo que nada grabado puede repetirse.
* **Toda protección se puede desactivar:** desde el fichero de configuración o la línea de comandos, y el programa enumera al arrancar cada protección que está apagada. No cifra, y no sustituye las medidas de hardware del modelo de amenazas.

## 🧩 Papel en URTC

El modelo de amenazas del repositorio URTC dice que, si una instalación no puede mantener el bus cerrado o no puede evitar conectarlo a una red, la protección va en una pasarela delante del bus y no en cada cabezal. Este repositorio es esa pasarela: útil para un túnel entre el controlador del robot y los cabezales y para exponer el bus a una red. Usa la especificación del protocolo de URTC-COMMON como única fuente de identificadores y formatos.

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="Arquitectura de URTC-GATEWAY: quién lo usa, qué contiene y de qué depende" width="100%">
</p>

Cómo encajan las partes de este repositorio: quién lo usa, qué contiene y de qué depende. La imagen se dibuja desde `docs/architecture.json` y se comprueba contra el código.

## 🔒 Seguridad y protección

| Amenaza | Defensa |
|---|---|
| Un nodo en los cables envía una orden peligrosa (cargador de arranque, actualización del esclavo de expansión, borrado del estado guardado, un ajuste persistente) | La lista de identificadores las rechaza hasta que el operador las desbloquea con `--unlock-dangerous` |
| Un valor fuera de lo que permite el protocolo (una consigna fuera de rango, una dirección que no existe, bytes mágicos incorrectos) | La comprobación de la carga rechaza la trama |
| Un emisor descontrolado u hostil inunda el bus | Un cubo de fichas por identificador y para todo el enlace, y uno más estricto para un identificador peligroso desbloqueado |
| Se vuelve a enviar un mensaje grabado | La clave de sesión: un HMAC sobre un nonce de la conexión, un contador que debe crecer y la trama, de modo que una grabación no sirve después ni en otro sitio |
| La pasarela es accesible desde una red sin clave | Escuchar en una dirección no local sin clave de sesión se rechaza salvo que se indique `--allow-open-network` |

No cifra: el bus no es un secreto. No detiene a un par que tenga la clave y se porte mal; para eso están la lista, la comprobación de la carga y el límite de tasa, y los perros guardianes de los cabezales. No sustituye las medidas de hardware del modelo de amenazas del CAN (un interbloqueo que ninguna trama pueda cerrar, un bus cerrado, una parada que corte la alimentación). Nunca se ha usado en un bus real.

## 🔌 Interfaces

La línea de comandos es `urtc-gateway` (o `python -m urtc_gateway.cli`):

| Comando | Qué hace |
|---|---|
| `policy` | muestra las opciones efectivas y un aviso por cada protección desactivada |
| `ids` | lista cada identificador y lo que hace la pasarela con él |
| `keygen FILE PEER [PEER ...]` | escribe un archivo de claves con una clave aleatoria nueva para cada par (solo legible por su dueño, nunca sobre uno existente, las claves no se muestran); da a cada par solo su línea |
| `run` | escucha en un puerto TCP (`--host`, por defecto `127.0.0.1`; `--port`, por defecto `8765`) y reenvía a un bus (`--bus loopback`, una URL de pyserial como `socket://127.0.0.1:7777` o el puerto serie de un adaptador SLCAN; `--bitrate`, por defecto 500000) |

**El protocolo de líneas.** Al conectar, la pasarela envía `{"type": "hello", "nonce": "<hex>", "session": true}`. Cada mensaje del par es un objeto JSON por línea: `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 dígitos hex>"}`. `mac` son los 16 primeros bytes de HMAC-SHA256, con la clave del par, sobre `urtc-gw/1|<nonce>|<contador>|<id en tres dígitos hex>|<datos en hex>`; el contador debe crecer con cada mensaje de la conexión y el nonce es nuevo en cada conexión. Un mensaje rechazado se responde con `{"type": "refused", "code": "<motivo>"}`, y las tramas del bus vuelven como `{"type": "frame", "id": ..., "data": "<hex>"}`. Consulta [la política](docs/POLICY.md).

## ⚙️ Configuración

Cada protección está activada por defecto y cualquiera puede desactivarse, en un archivo de configuración JSON (`--config FILE`, `"schema": 1`; una sección u opción desconocida, un tipo erróneo o una tasa negativa es un error que dice qué falla) y en la línea de comandos, que prevalece sobre el archivo. Una protección desactivada o relajada se lista como aviso al arrancar el programa.

| Protección | Sección del archivo | Desactivar / activar | Qué hace |
|---|---|---|---|
| Lista de identificadores | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | solo cruzan hacia el bus los identificadores que envía un host |
| Identificadores peligrosos | `whitelist.unlock_dangerous` | `--unlock-dangerous` | el cargador de arranque, la actualización del esclavo de expansión, el borrado del estado guardado y todo ajuste persistente siguen rechazados hasta desbloquearlos |
| Identificadores añadidos / quitados | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | añadir un identificador a mano o quitar uno diga lo que diga el resto |
| Comprobación de la carga | `payload.enabled` | `--no-payload-check` / `--payload-check` | la longitud y los valores deben ser los que permite la especificación |
| Límite de tasa | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 tramas por segundo y una ráfaga de 10 por identificador, una ráfaga de 50 para el enlace, una de 2 para un identificador peligroso desbloqueado; `rate.overrides` da a un identificador su propia tasa y ráfaga |
| Clave de sesión | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | un par demuestra que tiene una clave |
| Filtro de salida | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | solo lo que envía una placa va hacia la red, hasta 500 tramas por segundo |
| Red abierta | `server.allow_open_network` | `--allow-open-network` | escuchar en una dirección no local sin clave de sesión se rechaza salvo que se pida |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Inicio rápido

**Requisitos:** Python 3.10 o superior; pyserial solo para usar un adaptador SLCAN real

```bash
python tools/make_id_table.py --check                              # la tabla de identificadores está al día
python -m pytest tests -q                                          # las pruebas
python -m urtc_gateway.cli policy                                  # las opciones efectivas y un aviso por cada protección apagada
python -m urtc_gateway.cli keygen keys.txt controller              # un fichero de claves nuevo (solo para el propietario, nunca se sobrescribe)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # escuchar en 127.0.0.1:8765 sin nada en el bus
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# la placa virtual de URTC-COMMON (o cualquier URL de pyserial) en lugar de un adaptador
```

<!-- urtc-section:compatibility -->
### Requisitos y compatibilidad

Qué versiones de los programas de URTC funcionan juntas, y qué versión del protocolo habla cada una, figura en la tabla de compatibilidad que genera URTC-COMMON: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Pruebas

La suite tiene 79 pruebas (`python -m pytest tests -q`): la lista de identificadores, la comprobación de la carga, el límite de tasa, la sesión y sus rechazos, las opciones y el archivo de configuración, la línea de comandos, una prueba sobre un socket local real y el extremo serie contra un puerto simulado. Una prueba se omite si falta su dependencia opcional. `python -m mypy` revisa los tipos del paquete y `ruff check .` el código.

## 🏗️ Compilación y publicación

`build.sh` / `build.bat` instalan el paquete y ejecutan las pruebas; `build-test.sh` / `build-test.bat` comprueban sin cambiar ninguna versión; `run.sh` / `run.bat` arrancan la línea de comandos (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` escribe la tabla de identificadores de [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) a partir de la especificación (`--check` compara).

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Estructura del repositorio URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                la pasarela: lista de identificadores, política, límite de tasa, claves de sesión, opciones, extremos TCP y serie y línea de comandos
├── docs/                                            las opciones (POLICY.md) y la tabla generada de identificadores
├── tests/                                           pruebas unitarias de cada protección y una prueba sobre un socket local real
├── tools/                                           make_id_table.py y las herramientas compartidas de CI e imágenes
├── images/                                          banner e imágenes de este README
├── .github/                                         flujo de CI y plantillas de issues y pull requests
├── build.sh build.bat                               scripts de compilación
├── build-test.sh build-test.bat                     scripts de compilación y pruebas que no cambian nada en el repositorio
├── test.sh test.bat                                 ejecutan las pruebas
├── run.sh run.bat                                   arrancan el programa
├── urtc.project.json                                manifiesto: versión, papel, madurez y comando de compilación
├── CHANGELOG.md                                     qué cambió en cada versión
├── SECURITY.md SUPPORT.md LICENSE                   política de seguridad, soporte y licencia
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               cómo contribuir y código de conducta
├── .gitattributes .gitignore                        ajustes de Git
├── bump_version.py bump_manifest_version.py         scripts que suben la versión
└── pyproject.toml requirements-dev.lock ruff.toml   paquete, herramientas fijadas y ajustes de lint
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

**Límites conocidos hoy**

* Nunca se ha conectado a un bus CAN real, un adaptador o una placa, y ninguna instalación lo usa todavía; se prueba en CI con simulados y un socket local.
* Los cabezales de calor, láser y soldadura siguen necesitando las medidas de hardware del modelo de amenazas: un interbloqueo que ninguna trama pueda cerrar, un bus cerrado y una parada que corte la alimentación.
* No cifra ni detiene a un par que tenga la clave y se porte mal.

**Siguiente**

* Probarlo entre un controlador y un cabezal real en banco, primero detrás de la placa virtual.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

URTC se compone de repositorios independientes, cada uno con su versión, sus pruebas y su README. Esta es la familia, por grupos:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware de la placa del cabezal de herramienta (25 perfiles de herramienta, bootloader CAN) y la referencia del protocolo CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - el protocolo CAN escrito una sola vez como datos (especificación, tablas generadas, vectores de conformidad) y el código que comparten los programas.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - herramienta de escritorio que actualiza el firmware de la placa por CAN o por SWD/JTAG.
  * **URTC-GATEWAY** (este repositorio) - pasarela delante del bus CAN: solo deja pasar los identificadores de una lista, limita su frecuencia y pide una clave de sesión.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - lógica en C independiente del hardware y protocolo de órdenes para un soporte de herramientas con precalentamiento y seguimiento del ciclo de vida.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - probador de escritorio del bus CAN en vivo que muestra los controles y la telemetría del perfil de herramienta que informa una placa.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocolo de tramas de sensor en C y un acompañante en Python térmico/RGB para un cabezal de inspección.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - aplicación de navegador que graba y prueba la placa por Web Serial y SLCAN, sin instalar nada.
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - arquitectura, interfaces, línea base de seguridad y catálogo generado del ecosistema, más las herramientas que comparan todos los repositorios.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - herramienta de escritorio que detecta, instala y actualiza los repositorios de la familia URTC, una acción explícita cada vez.

**Proyectos hermanos (independientes, con la misma base y herramientas):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - proyecto hermano: el centro de documentación de HYDRA-UMC, un ecosistema independiente que comparte base y herramientas con este
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - proyecto hermano: el centro de documentación de A.R.M.O.R., el ecosistema de seguridad, también independiente y sobre la misma base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - el perfil y el panel de estado de todos los ecosistemas

## 📚 Documentación

Dónde leer más:

* [Política: cada opción, su valor por defecto y cómo desactivarla](docs/POLICY.md)
* [Identificadores: qué hace la pasarela con cada uno](docs/ALLOWED_IDS.md)
* [Registro de cambios de este repositorio](CHANGELOG.md)
* [Licencia (GPL-3.0-or-later)](LICENSE)
* Preguntas, ideas e informes: electrohobby3d@gmail.com

## 🤝 Contribuir y comunidad

* Antes de una pull request ejecuta `URTC_CI=1 python tools/ci_validate.py`: debe pasar. Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas: un cambio en el texto se hace en los ocho archivos, y las secciones compartidas con otros repositorios las escribe `tools/readme_sections.py` de URTC-COMMON.
* Un cambio en el protocolo CAN empieza en URTC-COMMON (`spec/can_protocol.json`) y llega a este repositorio mediante la copia comprobada.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
