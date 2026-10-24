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
  <img src="https://img.shields.io/badge/Version-0.0.1-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-FFB020.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que realmente funciona hoje:** este repositório contém uma gateway escrita como software: a lista de identificadores é feita a partir da especificação do protocolo, o conteúdo de cada trama é verificado contra ela, a taxa é limitada e um interlocutor tem de provar que possui uma chave. Tudo é testado na CI com simulações e um socket local. Nunca foi ligada a um barramento CAN real, a um adaptador nem a uma placa, e nenhuma instalação a usa ainda. As cabeças de aquecimento, laser e soldadura continuam a precisar das medidas de hardware do modelo de ameaças: um bloqueio que nenhuma trama possa fechar, um barramento fechado e uma paragem que corte a alimentação.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado e ainda não existe nenhuma placa URTC montada. Os bootloaders verificam as imagens de firmware com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica (prevista); as imagens de aplicação publicadas estão assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`), pelo que qualquer pessoa pode produzir uma imagem que o bootloader aceita; nada foi transmitido a uma placa real. Leia a [base de segurança](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.0.1` |
| Maturidade | Estrutura inicial |
| Testes | 79 |
| Tecnologia | Python / CAN / HMAC |
| Destino | O PC de quem o usa |
| Em hardware real | Só simulado: testado com emuladores, dublês de teste ou simuladores; não há registo de execução em hardware real para esta versão |

## 🎯 Visão geral

O barramento CAN da cabeça de ferramenta não autentica o emissor: qualquer nó ligado aos fios é obedecido. Quando uma instalação não consegue manter o barramento fechado, esta gateway coloca-se à frente:

* **Lista de identificadores, feita a partir da especificação:** só atravessam para o barramento os identificadores que um anfitrião envia; os perigosos (bootloader, atualização do escravo de expansão, apagamento do estado guardado, qualquer definição persistente) são recusados, a menos que o operador os desbloqueie. [A tabela de identificadores](docs/ALLOWED_IDS.md) é gerada.
* **Verificação do conteúdo:** uma trama tem de ter o comprimento e os valores que a especificação permite (um valor pretendido dentro do intervalo, um sentido que existe, os bytes mágicos onde são exigidos).
* **Limite de taxa:** um balde de fichas por identificador e para toda a ligação, e outro mais apertado para um identificador perigoso desbloqueado.
* **Chave de sessão:** um interlocutor prova que possui uma chave com um HMAC sobre um nonce da ligação, um contador e a trama, de modo que nada gravado pode ser repetido.
* **Qualquer proteção pode ser desligada:** no ficheiro de configuração ou na linha de comandos, e o programa enumera ao arrancar cada proteção que está desligada. Não cifra e não substitui as medidas de hardware do modelo de ameaças.

## 🧩 Papel no URTC

O modelo de ameaças do repositório URTC diz que, se uma instalação não consegue manter o barramento fechado ou não pode evitar ligá-lo a uma rede, a proteção deve estar numa gateway à frente do barramento e não em cada cabeça de ferramenta. Este repositório é essa gateway: útil para um túnel entre o controlador do robô e as cabeças de ferramenta e para expor o barramento a uma rede. Usa a especificação do protocolo do URTC-COMMON como única fonte de identificadores e formatos.

## 📂 Estrutura do repositório

```text
URTC-GATEWAY/
├── src/urtc_gateway/  a gateway: listas de identificadores, política, limite de taxa, chaves de sessão, opções, extremos TCP e série, linha de comandos
├── docs/              as opções (POLICY.md) e a tabela gerada de identificadores
├── tests/             testes unitários de cada proteção e um teste com um socket local real
├── tools/             make_id_table.py e as verificações de CI partilhadas do ecossistema
├── images/            o banner
├── build.sh / build.bat, build-test.sh / build-test.bat, run.sh / run.bat
└── urtc.project.json, pyproject.toml, CHANGELOG.md, LICENSE
```

## 🛠️ COMPILAÇÃO E EXECUÇÃO

**Requisitos:** Python 3.10 ou superior; pyserial apenas para usar um adaptador SLCAN real

```bash
python tools/make_id_table.py --check                              # a tabela de identificadores está atualizada
python -m pytest tests -q                                          # os testes
python -m urtc_gateway.cli policy                                  # as opções efetivas e um aviso por cada proteção desligada
python -m urtc_gateway.cli keygen keys.txt controller              # um novo ficheiro de chaves (só para o proprietário, nunca é substituído)
python -m urtc_gateway.cli run --key-file keys.txt --bus loopback  # escutar em 127.0.0.1:8765 sem nada no barramento
python -m urtc_gateway.cli run --key-file keys.txt --bus socket://127.0.0.1:7777# a placa virtual do URTC-COMMON (ou qualquer URL do pyserial) em vez de um adaptador
```

`build.sh` / `build.bat` sobem a versão um passo (o conta-quilómetros do ecossistema), instalam o pacote e executam os testes; `build-test.sh` / `build-test.bat` verificam sem alterar nenhuma versão; `run.sh` / `run.bat` iniciam a linha de comandos (`policy`, `ids`, `keygen`, `run`).

## 🔗 Projetos relacionados

O URTC é feito de repositórios independentes, cada um com a sua versão, os seus testes e o seu README. Esta é a família, por grupos:

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER), **URTC-GATEWAY** (este repositório), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Para além do URTC:**

* **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - a placa-mãe do braço robótico, cujo relé CAN está documentado como o barramento onde a cabeça de ferramenta se liga
* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - a mesma ideia para o ecossistema HYDRA-UMC
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - a mesma ideia para o ecossistema de segurança A.R.M.O.R.
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - o perfil e o painel de estado de todos os ecossistemas

## 📚 Documentação e comunidade

Onde ler mais:

* [Política: cada opção, o seu valor predefinido e como a desligar](docs/POLICY.md)
* [Identificadores: o que a gateway faz com cada um](docs/ALLOWED_IDS.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença (GPL-3.0-or-later)](LICENSE)
* Perguntas, ideias e relatos: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

<!-- urtc-section:compatibility -->
## 🧩 Compatibilidade

As versões dos programas URTC que funcionam em conjunto, e a versão do protocolo que cada uma fala, constam da tabela de compatibilidade que o URTC-COMMON gera: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 📜 LICENÇA

GPL-3.0-or-later - consulte [LICENSE](LICENSE).
