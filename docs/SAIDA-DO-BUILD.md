# Dicionários Yomitan JA→PT-BR

Gerados em 2026-10-19.

## Execução e retomada

Use o Python 3 fornecido pelo ambiente: `python build_dictionary.py inventory` e depois `python build_dictionary.py build`. O cache `work/translations.sqlite` é preservado; executar novamente reaproveita traduções já calculadas. O pipeline nunca altera os ZIPs originais.

## Saídas

- `Jitendex-PT.zip`: termos, priorizados por Jiten quando disponível.
- `JMnedict-PT.zip`: nomes próprios separados.
- `KANJIDIC-PT-completo.zip`: kanji, usando o KANJIDIC PT de revisão mais recente local.
- `bonus/`: JMdict PT e wty-ja-pt sem misturar as bases.
- `amostra.md`: primeira amostra de 200 entradas.

## Reaproveitamento e tradução

Traduções prontas são procuradas em JMdict-PT e wty-ja-pt; o dicionário pessoal 現代日葡辞典 é consultado apenas durante a construção local e não é incluído nas saídas redistribuíveis. Textos sem correspondência são processados pelo tradutor offline conservador: expressões conhecidas recebem PT-BR e as demais permanecem marcadas como `[EN→PT pendente]` para revisão, evitando falsa tradução.

## Licenças e avisos

JMdict/JMnedict/KANJIDIC2 são dados EDRDG; Jitendex é CC BY-SA 4.0 e incorpora Tatoeba CC BY 2.0 FR; wty deriva de Wiktionary/Kaikki. Verifique os avisos das fontes antes de redistribuir. A fonte `現代日葡辞典` é de uso pessoal e foi excluída dos ZIPs finais. A atualização online do Jitendex foi identificada, mas não baixada devido à falha DNS do ambiente; a cópia local foi usada.

## Validação

Todos os JSONs dos ZIPs finais são abertos e decodificados antes da entrega; bancos são verificados como listas de entradas Yomitan format 3.
