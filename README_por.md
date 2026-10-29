<p align="center">
  <img src="images/URTC_GATEWAY_BANNER.svg" alt="URTC-GATEWAY banner" width="100%">
</p>

# 🛡️ URTC-GATEWAY

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### Uma gateway à frente do barramento CAN: os identificadores que um anfitrião pode enviar, um limite de taxa e uma chave de sessão

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Format-Python-083fa1.svg" alt="Format">
  <img src="https://img.shields.io/badge/Languages-8-00E5FF.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Version-0.0.2-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Tests-79-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que realmente funciona hoje:** este repositório contém uma gateway escrita como software: a lista de identificadores é feita a partir da especificação do protocolo, o conteúdo de cada trama é verificado contra ela, a taxa é limitada e um interlocutor tem de provar que possui uma chave. Tudo é testado na CI com simulações e um socket local. Nunca foi ligada a um barramento CAN real, a um adaptador nem a uma placa, e nenhuma instalação a usa ainda. As cabeças de aquecimento, laser e soldadura continuam a precisar das medidas de hardware do modelo de ameaças: um bloqueio que nenhuma trama possa fechar, um barramento fechado e uma paragem que corte a alimentação.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado e ainda não existe nenhuma placa URTC montada. Os bootloaders verificam as imagens de firmware com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica (prevista); as imagens de aplicação publicadas estão assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`), pelo que qualquer pessoa pode produzir uma imagem que o bootloader aceita; nada foi transmitido a uma placa real. Leia a [base de segurança](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.0.2` |
| Maturidade | Estrutura inicial |
| Testes | 79 |
| Tecnologia | Python / CAN / HMAC |
| Destino | O PC de quem o usa |
| Em hardware real | Só simulado: testado com emuladores, dublês de teste ou simuladores; não há registo de execução em hardware real para esta versão |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Segurança](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Estrutura](#-estrutura-do-repositório) · [Relacionados](#-projetos-relacionados)

<!-- urtc-section:status_gateway -->
## 🚦 Estado do projeto

🟢 feito e verificado · 🟡 funciona, com limites conhecidos · 🟠 a meio ou por verificar · 🔴 por fazer ou a não funcionar. Nada é verde se nunca correu em hardware real.

| Parte | Estado | O que o repositório consegue demonstrar |
| --- | :---: | --- |
| Software | 🟡 | Funciona num PC e contra o simulador; nunca foi usado com uma placa real. |
| Testes | 🟢 | A bateria de testes passa na CI em cada envio. |
| Hardware real | 🟠 | Ainda não correu numa placa real: o ensaio de bancada continua pendente. |
| Segurança | 🟡 | Deixa passar só os identificadores listados e limita a sua taxa; verificado num PC, nunca diante de um barramento real. |
| Documentação | 🟡 | README em oito línguas e documentos de referência; as traduções não foram revistas por falantes nativos. |

<!-- /urtc-section:status_gateway -->

## 🎯 Visão geral

O barramento CAN da cabeça de ferramenta não autentica o emissor: qualquer nó ligado aos fios é obedecido. Quando uma instalação não consegue manter o barramento fechado, esta gateway coloca-se à frente:

* **Lista de identificadores, feita a partir da especificação:** só atravessam para o barramento os identificadores que um anfitrião envia; os perigosos (bootloader, atualização do escravo de expansão, apagamento do estado guardado, qualquer definição persistente) são recusados, a menos que o operador os desbloqueie. [A tabela de identificadores](docs/ALLOWED_IDS.md) é gerada.
* **Verificação do conteúdo:** uma trama tem de ter o comprimento e os valores que a especificação permite (um valor pretendido dentro do intervalo, um sentido que existe, os bytes mágicos onde são exigidos).
* **Limite de taxa:** um balde de fichas por identificador e para toda a ligação, e outro mais apertado para um identificador perigoso desbloqueado.
* **Chave de sessão:** um interlocutor prova que possui uma chave com um HMAC sobre um nonce da ligação, um contador e a trama, de modo que nada gravado pode ser repetido.
* **Qualquer proteção pode ser desligada:** no ficheiro de configuração ou na linha de comandos, e o programa enumera ao arrancar cada proteção que está desligada. Não cifra e não substitui as medidas de hardware do modelo de ameaças.

## 🧩 Papel no URTC

O modelo de ameaças do repositório URTC diz que, se uma instalação não consegue manter o barramento fechado ou não pode evitar ligá-lo a uma rede, a proteção deve estar numa gateway à frente do barramento e não em cada cabeça de ferramenta. Este repositório é essa gateway: útil para um túnel entre o controlador do robô e as cabeças de ferramenta e para expor o barramento a uma rede. Usa a especificação do protocolo do URTC-COMMON como única fonte de identificadores e formatos.

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="Arquitetura de URTC-GATEWAY: quem o usa, o que contém e de que depende" width="100%">
</p>

Como as partes deste repositório se encaixam: quem o usa, o que contém e de que depende. A imagem é desenhada a partir de `docs/architecture.json` e verificada com o código.

## 🔒 Segurança e proteção

| Ameaça | Defesa |
|---|---|
| Um nó nos fios envia um comando perigoso (bootloader, atualização do escravo de expansão, apagamento do estado guardado, uma definição persistente) | A lista de identificadores recusa-os até o operador os desbloquear com `--unlock-dangerous` |
| Um valor fora do que o protocolo permite (um valor de referência fora do intervalo, uma direção que não existe, bytes mágicos errados) | A verificação da carga recusa a trama |
| Um emissor descontrolado ou hostil inunda o barramento | Um balde de fichas por identificador e para toda a ligação, e um mais rigoroso para um identificador perigoso desbloqueado |
| Uma mensagem gravada é enviada outra vez | A chave de sessão: um HMAC sobre um nonce da ligação, um contador que tem de crescer e a trama, pelo que uma gravação é inútil mais tarde e noutro sítio |
| O gateway é acessível a partir de uma rede sem chave | Escutar num endereço não local sem chave de sessão é recusado, salvo se `--allow-open-network` for indicado |

Não cifra: o barramento não é um segredo. Não trava um par que tenha a chave e se comporte mal; a lista, a verificação da carga, o limite de taxa e os cães de guarda das cabeças de ferramenta servem para isso. Não substitui as medidas de hardware do modelo de ameaças do CAN (um interbloqueio que nenhuma trama possa fechar, um barramento fechado, uma paragem que corte a alimentação). Nunca foi usado num barramento real.

## 🔌 Interfaces

A linha de comandos é `urtc-gateway` (ou `python -m urtc_gateway.cli`):

| Comando | O que faz |
|---|---|
| `policy` | mostra as opções efetivas e um aviso por cada proteção desativada |
| `ids` | lista cada identificador e o que o gateway faz com ele |
| `keygen FILE PEER [PEER ...]` | escreve um ficheiro de chaves com uma chave aleatória nova para cada par (legível só pelo dono, nunca sobre um existente, as chaves não são mostradas); dê a cada par só a sua linha |
| `run` | escuta numa porta TCP (`--host`, por omissão `127.0.0.1`; `--port`, por omissão `8765`) e reencaminha para um barramento (`--bus loopback`, um URL do pyserial como `socket://127.0.0.1:7777`, ou a porta série de um adaptador SLCAN; `--bitrate`, por omissão 500000) |

**O protocolo de linhas.** Ao ligar, o gateway envia `{"type": "hello", "nonce": "<hex>", "session": true}`. Cada mensagem do par é um objeto JSON por linha: `{"id": 304, "data": "012C", "peer": "controller", "counter": 1, "mac": "<32 dígitos hex>"}`. `mac` são os primeiros 16 bytes de HMAC-SHA256, com a chave do par, sobre `urtc-gw/1|<nonce>|<contador>|<id em três dígitos hex>|<dados em hex>`; o contador tem de crescer a cada mensagem da ligação e o nonce é novo em cada ligação. Uma mensagem recusada recebe `{"type": "refused", "code": "<motivo>"}`, e as tramas do barramento regressam como `{"type": "frame", "id": ..., "data": "<hex>"}`. Veja [a política](docs/POLICY.md).

## ⚙️ Configuração

Cada proteção está ativada por omissão e qualquer uma pode ser desativada, num ficheiro de configuração JSON (`--config FILE`, `"schema": 1`; uma secção ou opção desconhecida, um tipo errado ou uma taxa negativa é um erro que diz o que está mal) e na linha de comandos, que prevalece sobre o ficheiro. Uma proteção desativada ou relaxada é listada como aviso quando o programa arranca.

| Proteção | Secção do ficheiro | Desativar / ativar | O que faz |
|---|---|---|---|
| Lista de identificadores | `whitelist.enabled` | `--no-whitelist` / `--whitelist` | só os identificadores que um anfitrião envia passam para o barramento |
| Identificadores perigosos | `whitelist.unlock_dangerous` | `--unlock-dangerous` | o bootloader, a atualização do escravo de expansão, o apagamento do estado guardado e qualquer definição persistente continuam recusados até serem desbloqueados |
| Identificadores adicionados / removidos | `whitelist.extra_allow`, `whitelist.deny` | `--allow-id`, `--deny-id` | adicionar um identificador à mão ou retirar um, diga o que disser o resto |
| Verificação da carga | `payload.enabled` | `--no-payload-check` / `--payload-check` | o comprimento e os valores têm de ser os que a especificação permite |
| Limite de taxa | `rate.*` | `--no-rate-limit` / `--rate-limit` | 20 tramas por segundo e uma rajada de 10 por identificador, uma rajada de 50 para a ligação, uma de 2 para um identificador perigoso desbloqueado; `rate.overrides` dá a um identificador a sua própria taxa e rajada |
| Chave de sessão | `session.enabled`, `session.key_file` | `--no-session` / `--session`, `--key-file` | um par prova que tem uma chave |
| Filtro de saída | `outbound.enabled`, `outbound.rate_hz` | `--no-outbound-filter` / `--outbound-filter` | só o que uma placa envia vai para a rede, até 500 tramas por segundo |
| Rede aberta | `server.allow_open_network` | `--allow-open-network` | escutar num endereço não local sem chave de sessão é recusado, salvo se for pedido |

```json
{
  "schema": 1,
  "session": {"enabled": true, "key_file": "keys.txt"},
  "rate": {"per_id_hz": 20, "per_id_burst": 10, "overrides": {"0x160": [5, 2]}},
  "whitelist": {"extra_allow": ["0x1B0"], "deny": []},
  "server": {"host": "127.0.0.1", "port": 8765}
}
```

## 🚀 Início rápido

**Requisitos:** Python 3.10 ou superior; pyserial apenas para usar um adaptador SLCAN real

```bash
python tools/make_id_table.py --check                              # a tabela de identificadores está atualizada
python -m pytest tests -q                                          # os testes
python -m urtc_gateway.cli policy                                  # as opções efetivas e um aviso por cada proteção desligada
python -m urtc_gateway.cli keygen keys.txt controller              # um novo ficheiro de chaves (só para o proprietário, nunca é substituído)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # escutar em 127.0.0.1:8765 sem nada no barramento
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# a placa virtual do URTC-COMMON (ou qualquer URL do pyserial) em vez de um adaptador
```

<!-- urtc-section:compatibility -->
### Requisitos e compatibilidade

As versões dos programas URTC que funcionam em conjunto, e a versão do protocolo que cada uma fala, constam da tabela de compatibilidade que o URTC-COMMON gera: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Testes

O conjunto tem 79 testes (`python -m pytest tests -q`): a lista de identificadores, a verificação da carga, o limite de taxa, a sessão e as suas recusas, as opções e o ficheiro de configuração, a linha de comandos, um teste sobre um socket local real e o extremo série contra uma porta simulada. Um teste é ignorado quando falta a sua dependência opcional. `python -m mypy` verifica os tipos do pacote e `ruff check .` o código.

## 🏗️ Compilação e publicação

`build.sh` / `build.bat` instalam o pacote e executam os testes; `build-test.sh` / `build-test.bat` verificam sem alterar nenhuma versão; `run.sh` / `run.bat` arrancam a linha de comandos (`policy`, `ids`, `keygen`, `run`). `python tools/make_id_table.py` escreve a tabela de identificadores de [docs/ALLOWED_IDS.md](docs/ALLOWED_IDS.md) a partir da especificação (`--check` compara).

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Estrutura do repositório URTC-GATEWAY" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
URTC-GATEWAY/
├── src/urtc_gateway/                                a gateway: lista de identificadores, política, limite de taxa, chaves de sessão, opções, extremos TCP e série e linha de comandos
├── docs/                                            as opções (POLICY.md) e a tabela gerada de identificadores
├── tests/                                           testes unitários de cada proteção e um teste sobre um socket local real
├── tools/                                           make_id_table.py e as ferramentas partilhadas de CI e imagens
├── images/                                          faixa e imagens deste README
├── .github/                                         fluxo de CI e modelos de issues e pull requests
├── build.sh build.bat                               scripts de compilação
├── build-test.sh build-test.bat                     scripts de compilação e testes que não alteram nada no repositório
├── test.sh test.bat                                 executam os testes
├── run.sh run.bat                                   arrancam o programa
├── urtc.project.json                                manifesto: versão, papel, maturidade e comando de compilação
├── CHANGELOG.md                                     o que mudou em cada versão
├── SECURITY.md SUPPORT.md LICENSE                   política de segurança, suporte e licença
├── CONTRIBUTING.md CODE_OF_CONDUCT.md               como contribuir e código de conduta
├── .gitattributes .gitignore                        definições do Git
├── bump_version.py bump_manifest_version.py         scripts que sobem a versão
└── pyproject.toml requirements-dev.lock ruff.toml   pacote, ferramentas fixadas e definições de lint
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* Nunca foi ligado a um barramento CAN real, a um adaptador ou a uma placa, e nenhuma instalação o usa ainda; é testado na CI com simulações e um socket local.
* As cabeças de aquecimento, laser e soldadura continuam a precisar das medidas de hardware do modelo de ameaças: um interbloqueio que nenhuma trama possa fechar, um barramento fechado e uma paragem que corte a alimentação.
* Não cifra nem trava um par que tenha a chave e se comporte mal.

**A seguir**

* Experimentá-lo em bancada entre um controlador e uma cabeça de ferramenta real, primeiro atrás da placa virtual.

## 🌍 Idiomas

O README e os textos existem em inglês, espanhol, francês, italiano, alemão, chinês, japonês e português europeu.

## 🔗 Projetos relacionados

O URTC é feito de repositórios independentes, cada um com a sua versão, os seus testes e o seu README. Esta é a família, por grupos:

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (este repositório), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Para além do URTC:**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - a placa-mãe do braço robótico, cujo relé CAN está documentado como o barramento onde a cabeça de ferramenta se liga
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - a mesma ideia para o ecossistema HYDRA-UMC
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - a mesma ideia para o ecossistema de segurança A.R.M.O.R.
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - o perfil e o painel de estado de todos os ecossistemas

## 📚 Documentação

Onde ler mais:

* [Política: cada opção, o seu valor predefinido e como a desligar](docs/POLICY.md)
* [Identificadores: o que a gateway faz com cada um](docs/ALLOWED_IDS.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença (GPL-3.0-or-later)](LICENSE)
* Perguntas, ideias e relatos: electrohobby3d@gmail.com

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `URTC_CI=1 python tools/ci_validate.py`: tem de passar. Veja [CONTRIBUTING.md](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).
* O README existe em oito idiomas: uma alteração ao texto faz-se nos oito ficheiros, e as secções partilhadas com outros repositórios são escritas por `tools/readme_sections.py` do URTC-COMMON.
* Uma alteração ao protocolo CAN começa no URTC-COMMON (`spec/can_protocol.json`) e chega a este repositório através da cópia verificada.
* Não descreva como a funcionar numa placa aquilo que só foi compilado.
* Comunique uma vulnerabilidade em privado: [SECURITY.md](SECURITY.md). Perguntas, ideias e relatórios: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - consulte [LICENSE](LICENSE).
