<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### CAN 总线前的网关：主机可以发送的标识符、速率限制和会话密钥

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**诚实性检查 - 今天真正能运行的部分：** 本仓库包含一个以软件形式编写的网关：标识符列表由协议规范生成，每一帧的数据都会与规范对照检查，速率受到限制，对端必须证明自己持有密钥。全部内容都在 CI 中用模拟对象和本地套接字测试。它从未连接过真实的 CAN 总线、适配器或电路板，目前也没有任何安装在使用它。加热、激光和焊接工具头仍然需要威胁模型中的硬件措施：任何帧都无法闭合的联锁、封闭的总线，以及切断电源的停止装置。

---

> **安全与安防现状:**本生态系统不是经认证的安全系统,目前也不存在已组装的 URTC 电路板。引导程序使用 CRC32 和共享密钥的 HMAC-SHA256 校验固件映像,而非非对称签名(计划中);已发布的应用映像使用公开的开发密钥签名(`signing_key_kind: dev`),因此任何人都可以生成引导程序接受的映像;尚未向任何真实电路板发送过任何内容。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md)。

## 📋 速览

| | |
|---|---|
| 版本 | `0.0.2` |
| 成熟度 | 雏形 |
| 测试 | 79 |
| 技术栈 | Python / CAN / HMAC |
| 目标 | 使用者的电脑 |
| 真实硬件 | 仅模拟：使用模拟器、替身或仿真测试；此版本没有在真实硬件上运行的记录 |

**跳转到：** [概述](#-概述) · [架构](#-架构) · [安全](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [结构](#-仓库结构) · [相关项目](#-相关项目)

<!-- urtc-section:status_gateway -->
## 🚦 项目状态

🟢 已完成并已验证 · 🟡 可用，但有已知限制 · 🟠 做了一半或未验证 · 🔴 未完成或不能用。从未在真实硬件上运行过的内容不会是绿色。

| 部分 | 状态 | 仓库能够证明的内容 |
| --- | :---: | --- |
| 软件 | 🟡 | 可在电脑上和模拟器上运行；从未在真实板子上运行过。 |
| 测试 | 🟢 | 每次推送时测试套件都会在 CI 中通过。 |
| 真实硬件 | 🟠 | 尚未在真实板子上运行：台架测试仍待进行。 |
| 安全 | 🟡 | 只放行列出的标识符并限制其频率；已在电脑上检查，从未面对真实总线。 |
| 文档 | 🟡 | 提供八种语言的 README 和参考文档；翻译未经母语者审阅。 |

<!-- /urtc-section:status_gateway -->

## 🎯 概述

工具头的 CAN 总线不对发送者进行认证：线路上的任何节点都会被服从。当安装环境无法保持总线封闭时，就把这个网关放在它前面：

* **标识符列表，由规范生成：** 只有主机会发送的标识符才能通往总线；危险的标识符（引导程序、扩展从机的更新、清除已保存状态、所有持久设置）会被拒绝，除非操作员解锁。[标识符表](docs/ALLOWED_IDS.md)是自动生成的。
* **数据检查：** 一帧必须具有规范允许的长度和取值（范围内的设定值、存在的方向、需要魔术字节的地方带有魔术字节）。
* **速率限制：** 每个标识符和整条链路各一个令牌桶，已解锁的危险标识符使用更严格的令牌桶。
* **会话密钥：** 对端通过对连接的随机数、计数器和帧计算 HMAC 来证明持有密钥，因此录下来的内容无法重放。
* **每项保护都可以关闭：** 通过配置文件或命令行，程序启动时会列出每一项已关闭的保护。它不加密，也不能代替威胁模型中的硬件措施。

## 🧩 在 URTC 中的角色

URTC 仓库的威胁模型指出：如果安装环境无法保持总线封闭，或无法避免把它桥接到网络，保护应放在总线前的网关中，而不是每个工具头里。本仓库就是这个网关：适用于机器人控制器与工具头之间的隧道，以及把总线暴露给网络。它以 URTC-COMMON 的协议规范作为标识符和格式的唯一来源。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="URTC-GATEWAY 的架构：谁在使用、包含什么、依赖什么" width="100%">
</p>

本仓库各部分如何协作：谁在使用它、它包含什么、它依赖什么。图片由 `docs/architecture.json` 绘制，并与代码核对。

## 🔒 安全与防护

| 威胁 | 防御 |
|---|---|
| 总线上的某个节点发送危险命令（引导程序、扩展从机的更新、擦除已保存的状态、持久设置） | 标识符列表会拒绝这些命令，直到操作员用 `--unlock-dangerous` 解锁 |
| 超出协议允许范围的值（超范围的设定值、不存在的方向、错误的魔术字节） | 载荷检查拒绝该帧 |
| 失控或恶意的发送方淹没总线 | 每个标识符和整条链路各有一个令牌桶，已解锁的危险标识符使用更严格的令牌桶 |
| 录制的消息被重新发送 | 会话密钥：对连接的随机数、必须递增的计数器和帧做 HMAC，因此录制内容之后或在别处都无用 |
| 网关在没有密钥的情况下可从网络访问 | 在没有会话密钥时监听非本地地址会被拒绝，除非给出 `--allow-open-network` |

它不加密：总线不是秘密。它不会阻止持有密钥却行为不当的对端；列表、载荷检查、速率限制以及工具头的看门狗就是为此而设。它不能取代 CAN 威胁模型中的硬件措施（任何帧都无法闭合的联锁、封闭的总线、切断电源的停止）。它从未在真实总线上使用过。

## 🔌 接口

命令行是 `urtc-gateway`（或 `python -m urtc_gateway.cli`）：

| 命令 | 作用 |
|---|---|
| `policy` | 显示生效的选项，并为每个关闭的保护给出警告 |
| `ids` | 列出每个标识符以及网关对它的处理 |
| `keygen FILE PEER [PEER ...]` | 为每个对端写入一个带新随机密钥的密钥文件（仅所有者可读，绝不覆盖已有文件，不显示密钥）；只把各自的那一行交给每个对端 |
| `run` | 监听 TCP 端口（`--host`，默认 `127.0.0.1`；`--port`，默认 `8765`）并转发到总线（`--bus loopback`、`socket://127.0.0.1:7777` 这样的 pyserial URL，或 SLCAN 适配器的串口；`--bitrate`，默认 500000） |

**行协议。** 连接时网关发送 `{"type": "hello", "nonce": "<hex>", "session": true}`。对端发送的每条消息是每行一个 JSON 对象：`{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 位十六进制>"}`。`mac` 是用该对端的密钥对 `urtc-gw/1|<nonce>|<计数器>|<三位十六进制的 id>|<十六进制数据>` 计算的 HMAC-SHA256 的前 16 个字节；计数器必须随连接中的每条消息递增，每次连接的随机数都是新的。被拒绝的消息会收到 `{"type": "refused", "code": "<原因>"}`，总线上的帧以 `{"type": "frame", "id": ..., "data": "<hex>"}` 返回。参见[策略](docs/POLICY.md)。

## ⚙️ 配置

每项保护默认开启，也都可以关闭：可在 JSON 配置文件中（`--config FILE`，`"schema": 1`；未知的章节或选项、错误的类型或负的速率都会报错并指出问题）或在命令行中设置，命令行优先于文件。已关闭或放宽的保护会在程序启动时作为警告列出。

| 保护 | 文件中的章节 | 关闭 / 开启 | 作用 |
|---|---|---|---|
| 标识符列表 | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | 只有主机会发送的标识符才能通往总线 |
| 危险标识符 | `whitelist.unlock_dangerous` | `--unlock-dangerous` | 引导程序、扩展从机的更新、擦除已保存状态和所有持久设置在解锁前一直被拒绝 |
| 添加 / 移除的标识符 | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | 手动添加一个标识符，或不管其余规则如何都移除一个 |
| 载荷检查 | `payload.enabled` | `--no-payload-check` / `--payload-check` | 长度和数值必须是规范允许的 |
| 速率限制 | `rate.*` | `--no-rate-limit` / `--rate-limit` | 每个标识符每秒 20 帧、突发 10 帧，整条链路突发 50 帧，已解锁的危险标识符突发 2 帧；`rate.overrides` 可给某个标识符单独的速率和突发 |
| 会话密钥 | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | 对端证明自己持有密钥 |
| 出站过滤 | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | 只有板子发出的内容才会流向网络，每秒最多 500 帧 |
| 开放网络 | `server.allow_open_network` | `--allow-open-network` | 没有会话密钥时监听非本地地址会被拒绝，除非明确要求 |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 快速开始

**要求：** Python 3.10 或更高版本；只有使用真实 SLCAN 适配器时才需要 pyserial

```bash
python tools/make_id_table.py --check                              # 标识符表是最新的
python -m pytest tests -q                                          # 测试
python -m urtc_gateway.cli policy                                  # 实际生效的选项，以及对每项已关闭保护的警告
python -m urtc_gateway.cli keygen keys.txt controller              # 新的密钥文件（仅所有者可读，绝不覆盖）
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # 在 127.0.0.1:8765 监听，总线上没有任何东西
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# 用 URTC-COMMON 的虚拟板（或任意 pyserial URL）代替适配器
```

<!-- urtc-section:compatibility -->
### 要求与兼容性

哪些版本的 URTC 程序可以配合使用、各自使用哪个协议版本，列在 URTC-COMMON 生成的兼容性表中：[docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md)。
<!-- /urtc-section:compatibility -->

## 🧪 测试

测试套件共有 79 个测试（`python -m pytest tests -q`）：标识符列表、载荷检查、速率限制、会话及其拒绝情形、选项和配置文件、命令行、通过真实本地套接字的测试，以及针对模拟端口的串口端。缺少可选依赖时有一个测试会被跳过。`python -m mypy` 检查软件包的类型，`ruff check .` 检查源码。

## 🏗️ 构建与发布

`build.sh` / `build.bat` 安装软件包并运行测试；`build-test.sh` / `build-test.bat` 只检查，不改变任何版本；`run.sh` / `run.bat` 启动命令行（`policy`、`ids`、`keygen`、`run`）。`python tools/make_id_table.py` 根据规范写出 [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) 的标识符表（`--check` 用于比对）。

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="URTC-GATEWAY 的仓库结构" width="100%">
</p>

<details>
<summary>目录树的文本版</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                网关：标识符列表、策略、速率限制、会话密钥、选项、TCP 和串口端以及命令行
├── docs/                                            选项 (POLICY.md) 和生成的标识符表
├── tests/                                           每项保护的单元测试，以及通过真实本地套接字的测试
├── tools/                                           make_id_table.py 以及共用的 CI 和图片工具
├── images/                                          横幅和本 README 的图片
├── .github/                                         CI 工作流以及 Issue 和 Pull Request 模板
├── build.sh build.bat                               构建脚本
├── build-test.sh build-test.bat                     构建并测试的脚本，不会修改仓库内容
├── test.sh test.bat                                 运行测试
├── run.sh run.bat                                   启动程序
├── urtc.project.json                                清单：版本、角色、成熟度和构建命令
├── CHANGELOG.md                                     每个版本的变更
├── SECURITY.md SUPPORT.md LICENSE                   安全政策、支持和许可证
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               如何参与贡献和行为准则
├── .gitattributes .gitignore                        Git 设置
├── bump_version.py bump_manifest_version.py         提升版本号的脚本
└── pyproject.toml requirements-dev.lock ruff.toml   软件包、锁定的工具和 lint 设置
```

</details>

## 🗺️ 路线图与已知限制

**目前已知的限制**

* 它从未连接过真实的 CAN 总线、适配器或板子，也没有任何安装在使用它；它在 CI 中用模拟对象和本地套接字测试。
* 加热、激光和焊接头仍然需要威胁模型中的硬件措施：任何帧都无法闭合的联锁、封闭的总线和切断电源的停止。
* 它不加密，也无法阻止持有密钥却行为不当的对端。

**下一步**

* 在试验台上用控制器和真实的工具头试一试，先从虚拟板后面开始。

## 🌍 语言

README 和文本提供英语、西班牙语、法语、意大利语、德语、汉语、日语和欧洲葡萄牙语版本。

## 🔗 相关项目

URTC 由相互独立的仓库组成，每个仓库都有自己的版本、测试和 README。以下是按组划分的家族：

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - 工具头电路板的固件(25 个工具配置、CAN 引导程序)以及 CAN 协议参考。
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - 只写一次的 CAN 协议数据(规范、生成的表格、一致性向量)以及各程序共享的代码。
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - 通过 CAN 或 SWD/JTAG 更新电路板固件的桌面工具。
  * **URTC-GATEWAY** (本仓库) - 位于 CAN 总线前的网关:只放行列表中的标识符,限制其速率,并要求会话密钥。
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - 用于带预热和生命周期跟踪的工具架的、与硬件无关的 C 逻辑和命令协议。
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - 桌面实时 CAN 总线测试器,显示电路板所报告工具配置的控件和遥测。
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - C 语言的传感器帧协议,以及用于检测工具头的 Python 热成像/RGB 配套程序。
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - 通过 Web Serial 和 SLCAN 烧录并测试电路板的浏览器应用,无需安装。
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - 生态系统的架构、接口、安全基线和生成的目录,以及比较所有仓库的工具。
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - 检测、安装并更新 URTC 家族仓库的桌面工具,每次只执行一个明确的操作。

**姊妹项目（相互独立，共用同一基础和工具）：**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - 姊妹项目：HYDRA-UMC 的文档中心，一个独立的生态，与本生态共用基础和工具
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 姊妹项目：A.R.M.O.R. 安全生态的文档中心，同样独立，建立在同一基础上
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - 所有生态的个人主页和状态面板

## 📚 文档

更多阅读：

* [策略：每个选项、默认值以及如何关闭](docs/POLICY.md)
* [标识符：网关对每个标识符的处理](docs/ALLOWED_IDS.md)
* [本仓库的更新日志](CHANGELOG.md)
* [许可证（GPL-3.0-or-later）](LICENSE)
* 问题、想法和报告：electrohobby3d@gmail.com

## 🤝 参与贡献与社区

* 提交 Pull Request 之前请运行 `URTC_CI=1 python tools/ci_validate.py`：必须通过。参见 [CONTRIBUTING.md](CONTRIBUTING.md) 和[行为准则](CODE_OF_CONDUCT.md)。
* README 有八种语言：修改文字时要同步修改全部八个文件，与其他仓库共用的章节由 URTC-COMMON 的 `tools/readme_sections.py` 写入。
* 对 CAN 协议的修改从 URTC-COMMON（`spec/can_protocol.json`）开始，并通过经过核对的副本进入本仓库。
* 不要把仅仅构建过的东西描述为已在板子上运行。
* 请私下报告漏洞：[SECURITY.md](SECURITY.md)。问题、想法和报告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - 参见 [LICENSE](LICENSE)。
