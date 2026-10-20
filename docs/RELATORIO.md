# Relatório de publicação (revisão 2026-10-20)

Gerado por `scripts/finalizar_publicacao.py`, que compara cada string publicada com a string correspondente da fonte.

## Por dicionário

| Dicionário | Entradas | reaproveitada | automática | parcial | pendente | sem texto a traduzir |
|---|---:|---:|---:|---:|---:|---:|
| Jitendex-PT | 436.555 | 0 | 33.550 (7,7%) | 33.753 (7,7%) | 230.301 (52,8%) | 138.951 (31,8%) |
| JMnedict-PT | 668.008 | 26 | 4.713 (0,7%) | 96 | 13.422 (2,0%) | 649.751 (97,3%) |
| KANJIDIC-PT-completo | 1.944 kanji | a fonte já é em português | | | | |

"Sem texto a traduzir" reúne redirecionamentos entre grafias (Jitendex) e nomes romanizados sem glosa (JMnedict).

Considerando só as entradas do Jitendex-PT que têm glosa, 11,3% estão inteiramente em português, 11,3% estão parciais e 77,4% ainda estão em inglês.

## Correções desta revisão

- Ficaram zero ocorrências de `translation-source` e de `[EN→PT pendente]` nos JSONs. A marca vazava para o texto e para campos `data` usados pelo CSS do Jitendex.
- A forma de cada entrada é idêntica à da fonte, nas 436.555 entradas do Jitendex-PT.
- 2.081 strings do Jitendex-PT e 2.079 do JMnedict-PT foram revertidas ao original. Eram trocas palavra a palavra feitas por um léxico offline antigo ("japonês Society of escola Health", "maiden nome") ou reescritas que continuavam em inglês. Essas entradas agora aparecem como `pt-pendente` ou `pt-parcial`, em vez de passarem por traduzidas.
- As tags de status foram recalculadas. A revisão anterior marcava 68% do Jitendex como "DeepL" porque a tag era herdada da entrada, mesmo quando só um exemplo tinha sido traduzido.
- `index.json` traz `isUpdatable`, `indexUrl` e `downloadUrl` apontando para o release mais recente, e `tag_bank` declara as tags `pt-*`.
- `build_dictionary.py` não troca mais palavras dentro de frases e não grava marcas no texto.

## Pendências

- Cerca de 229 mil strings únicas (≈4,1 milhões de caracteres) ainda estão em inglês. A cota gratuita do DeepL (500 mil caracteres/mês) já foi usada. As opções são DeepL Pro, outra API de tradução ou continuar mês a mês com a cota gratuita, sempre pelo cache, sem pagar duas vezes.
- As traduções automáticas não foram revisadas por humanos.
