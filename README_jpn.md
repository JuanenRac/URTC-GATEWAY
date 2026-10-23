<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b> | <a href="README_por.md">🇵🇹 Português</a></p>

### CAN バスの手前に置くゲートウェイ：ホストが送れる識別子、レート制限、セッション鍵

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.1-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**正直な現状確認 - 実際に今動くもの：** このリポジトリにはソフトウェアとして書かれたゲートウェイがあります。識別子の一覧はプロトコル仕様から作られ、各フレームの内容はそれと照合され、送信レートは制限され、相手は鍵を持っていることを証明しなければなりません。すべて CI で模擬部品とローカルソケットを使って試験しています。実際の CAN バス、アダプター、基板につないだことは一度もなく、これを使っている設置もまだありません。加熱・レーザー・溶接のヘッドには、脅威モデルにあるハードウェア対策が引き続き必要です。どのフレームでも閉じられないインターロック、閉じたバス、電源を切る停止装置です。

---

> **安全性とセキュリティの現状:** このエコシステムは認証された安全システムではなく、実装済みの URTC 基板もまだ存在しません。ブートローダーはファームウェアイメージを CRC32 と共有鍵の HMAC-SHA256 で検査しており、非対称署名ではありません(予定)。公開されているアプリケーションイメージは公開の開発用鍵(`signing_key_kind: dev`)で署名されているため、誰でもブートローダーが受け入れるイメージを作れます。実際の基板には何も送信されていません。ここに書かれた内容を人の安全のために頼る前に、[セキュリティベースライン](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md)と[脅威モデル](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md)をお読みください。

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.0.1` |
| 成熟度 | 足場段階 |
| テスト | 74 |
| 技術 | Python / CAN / HMAC |
| 対象 | 利用者の PC |
| 実機での確認 | シミュレーションのみ：エミュレーター、模擬部品、シミュレーターで試験済み。このバージョンについて実機での動作記録はありません |

## 🎯 概要

ツールヘッドの CAN バスは送信者を認証しません。配線につながったどのノードにも従います。設置環境でバスを閉じておけない場合は、このゲートウェイをその手前に置きます。

* **仕様から作る識別子の一覧：** ホストが送る識別子だけがバスへ通ります。危険なもの（ブートローダー、拡張スレーブの更新、保存状態の消去、すべての永続設定）は、運用者が解除しない限り拒否されます。[識別子の表](docs/ALLOWED_IDS.md)は自動生成です。
* **内容の検査：** フレームは、仕様が許す長さと値でなければなりません（範囲内の設定値、存在する方向、必要な場所のマジックバイト）。
* **レート制限：** 識別子ごとと回線全体のトークンバケットがあり、解除した危険な識別子にはより厳しいものを使います。
* **セッション鍵：** 相手は、接続ごとのナンス、カウンター、フレームに対する HMAC で鍵を持っていることを証明します。そのため、録音したものは再生できません。
* **すべての保護はオフにできます：** 設定ファイルまたはコマンドラインで切り替え、起動時にオフの保護をすべて表示します。暗号化はせず、脅威モデルのハードウェア対策の代わりにもなりません。

## 🧩 URTC での役割

URTC リポジトリの脅威モデルは、設置環境でバスを閉じておけない、またはネットワークへの接続を避けられない場合、保護は各ツールヘッドではなくバスの手前のゲートウェイに置くべきだと述べています。このリポジトリがそのゲートウェイです。ロボットコントローラーとツールヘッドの間のトンネルや、バスをネットワークに公開する場合に役立ちます。識別子とレイアウトの唯一の情報源として、URTC-COMMON のプロトコル仕様を使います。

## 📂 リポジトリ構成

```text
URTC-GATEWAY/
├── src/urtc_gateway/  ゲートウェイ本体：識別子の一覧、ポリシー、レート制限、セッション鍵、オプション、TCP とシリアルの両端、コマンドライン
├── docs/              オプション（POLICY.md）と自動生成の識別子表
├── tests/             各保護の単体テストと、実際のローカルソケットを使うテスト
├── tools/             make_id_table.py とエコシステム共通の CI チェック
├── images/            バナー
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ ビルドと実行

**必要なもの：** Python 3.10 以降。実際の SLCAN アダプターを使うときだけ pyserial が必要

```bash
python tools/make_id_table.py --check                              # 識別子の表が最新であること
python -m pytest tests -q                                          # テスト
python -m urtc_gateway.cli policy                                  # 有効なオプションと、オフの保護ごとの警告
python -m urtc_gateway.cli keygen keys.txt controller              # 新しい鍵ファイル（所有者のみ、上書きしない）
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # バスに何もつながずに 127.0.0.1:8765 で待ち受ける
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# アダプターの代わりに URTC-COMMON の仮想ボード（または任意の pyserial URL）を使う
```

`build.sh` / `build.bat` はバージョンを 1 つ進め（エコシステムのオドメーター）、パッケージをインストールしてテストを実行します。`build-test.sh` / `build-test.bat` はバージョンを変えずに確認します。`run.sh` / `run.bat` はコマンドライン（`policy`、`ids`、`keygen`、`run`）を起動します。

## 🔗 関連プロジェクト

URTC は独立したリポジトリで構成され、それぞれに固有のバージョン、テスト、README があります。グループ別のファミリーは次のとおりです：

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (このリポジトリ), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**URTC の外：**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - ロボットアームのマザーボード。そのCANリレーが、ツールヘッドが接続されるバスとして文書化されています
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - HYDRA-UMC エコシステム向けの同じ考え方
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - A.R.M.O.R. セキュリティエコシステム向けの同じ考え方
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - すべてのエコシステムのプロフィールとステータスダッシュボード

## 📚 ドキュメントとコミュニティ

さらに読むには：

* [ポリシー：各オプション、既定値、オフにする方法](docs/POLICY.md)
* [識別子：ゲートウェイが各識別子をどう扱うか](docs/ALLOWED_IDS.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [ライセンス（GPL-3.0-or-later）](LICENSE)
* 質問、アイデア、報告：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

<!-- urtc-section:compatibility -->
## 🧩 互換性

どのバージョンの URTC プログラムが連携して動作し、それぞれがどのプロトコルバージョンを話すかは、URTC-COMMON が生成する互換性表に載っています：[docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md)。
<!-- /urtc-section:compatibility -->

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照してください。
