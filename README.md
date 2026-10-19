# Yomitan JA → PT-BR

Dicionários japonês → português brasileiro para [Yomitan](https://github.com/yomidevs/yomitan): termos, nomes próprios e kanji.

## Instalação

Baixe os ZIPs na página de [Releases](https://github.com/Astronyz/yomitan-ja-pt/releases) e importe-os em **Yomitan → Dictionaries → Configure → Import**. Os índices apontam para o release mais recente para permitir atualização automática.

## Conteúdo e licenças

Os dados derivam de JMdict/JMnedict/KANJIDIC2, Jitendex e fontes portuguesas públicas. Consulte [ATRIBUICOES.md](ATRIBUICOES.md) e [FONTES.md](FONTES.md). O dicionário pessoal 現代日葡辞典 e qualquer conteúdo derivado dele são deliberadamente excluídos.

Parte das definições ainda contém a marca `[EN→PT pendente]`; correções manuais devem ser adicionadas em `data/overrides/`.

## Build e contribuição

Use Python 3 e as fontes públicas listadas em `fontes.json`. O build público é `python scripts/build.py --public`; ele valida JSON, bloqueia fontes pessoais e gera os artefatos para o Release. Veja [CONTRIBUTING.md](CONTRIBUTING.md) e [docs/BUILD.md](docs/BUILD.md).

English: Japanese → Brazilian Portuguese Yomitan dictionaries. See the same build and licensing documents; contributions and corrections are welcome.
