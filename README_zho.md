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

## 🎯 简介

工具头的 CAN 总线不对发送者进行认证：线路上的任何节点都会被服从。当安装环境无法保持总线封闭时，就把这个网关放在它前面：

* **标识符列表，由规范生成：** 只有主机会发送的标识符才能通往总线；危险的标识符（引导程序、扩展从机的更新、清除已保存状态、所有持久设置）会被拒绝，除非操作员解锁。[标识符表](docs/ALLOWED_IDS.md)是自动生成的。
* **数据检查：** 一帧必须具有规范允许的长度和取值（范围内的设定值、存在的方向、需要魔术字节的地方带有魔术字节）。
* **速率限制：** 每个标识符和整条链路各一个令牌桶，已解锁的危险标识符使用更严格的令牌桶。
* **会话密钥：** 对端通过对连接的随机数、计数器和帧计算 HMAC 来证明持有密钥，因此录下来的内容无法重放。
* **每项保护都可以关闭：** 通过配置文件或命令行，程序启动时会列出每一项已关闭的保护。它不加密，也不能代替威胁模型中的硬件措施。

## 🧩 在 URTC 中的角色

URTC 仓库的威胁模型指出：如果安装环境无法保持总线封闭，或无法避免把它桥接到网络，保护应放在总线前的网关中，而不是每个工具头里。本仓库就是这个网关：适用于机器人控制器与工具头之间的隧道，以及把总线暴露给网络。它以 URTC-COMMON 的协议规范作为标识符和格式的唯一来源。

## 📂 仓库结构

```text
URTC-GATEWAY/
├── src/urtc_gateway/  网关：标识符列表、策略、速率限制、会话密钥、选项、TCP 和串口两端、命令行
├── docs/              选项（POLICY.md）和自动生成的标识符表
├── tests/             每项保护的单元测试，以及一个通过真实本地套接字的测试
├── tools/             make_id_table.py 和生态系统共享的 CI 检查
├── images/            横幅图
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ 构建与运行

**要求：** Python 3.10 或更高版本；只有使用真实 SLCAN 适配器时才需要 pyserial

```bash
python tools/make_id_table.py --check                              # 标识符表是最新的
python -m pytest tests -q                                          # 测试
python -m urtc_gateway.cli policy                                  # 实际生效的选项，以及对每项已关闭保护的警告
python -m urtc_gateway.cli keygen keys.txt controller              # 新的密钥文件（仅所有者可读，绝不覆盖）
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # 在 127.0.0.1:8765 监听，总线上没有任何东西
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# 用 URTC-COMMON 的虚拟板（或任意 pyserial URL）代替适配器
```

`build.sh` / `build.bat` 将版本号前进一步（生态系统的里程表）、安装软件包并运行测试；`build-test.sh` / `build-test.bat` 在不改变任何版本的情况下检查；`run.sh` / `run.bat` 启动命令行（`policy`、`ids`、`keygen`、`run`）。

## 🔗 相关项目

URTC 由相互独立的仓库组成，每个仓库都有自己的版本、测试和 README。以下是按组划分的家族：

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (本仓库), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**URTC 之外：**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - 机械臂主板，其 CAN 中继在文档中被记载为工具头所接入的总线
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - 同样的思路，用于 HYDRA-UMC 生态
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 同样的思路，用于 A.R.M.O.R. 安防生态
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - 所有生态的个人主页和状态面板

## 📚 文档与社区

更多阅读：

* [策略：每个选项、默认值以及如何关闭](docs/POLICY.md)
* [标识符：网关对每个标识符的处理](docs/ALLOWED_IDS.md)
* [本仓库的更新日志](CHANGELOG.md)
* [许可证（GPL-3.0-or-later）](LICENSE)
* 问题、想法和报告：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

<!-- urtc-section:compatibility -->
## 🧩 兼容性

哪些版本的 URTC 程序可以配合使用、各自使用哪个协议版本，列在 URTC-COMMON 生成的兼容性表中：[docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md)。
<!-- /urtc-section:compatibility -->

## 📜 许可证

GPL-3.0-or-later - 参见 [LICENSE](LICENSE)。
