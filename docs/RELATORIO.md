# Relatório de limpeza e reconstrução

Nenhuma chamada à API foi feita nesta etapa.

## Por dicionário

| Dicionário | Entradas | % reaproveitada | % DeepL | % pendente |
|---|---:|---:|---:|---:|
| Jitendex-PT | 433.885 | 31.70% | 68.08% | 0.22% |
| JMnedict-PT | 668.007 | 85.17% | 0.02% | 14.81% |
| KANJIDIC-PT-completo | 1.944 | 100.00% | 0.00% | 0.00% |

## Correções estruturais

- Híbridos revertidos ao texto original e marcados pendentes: 2
- Ocorrências literais de `translation-source` nos JSONs finais: 0.
- Campos estruturais (`tag`, `data`, `lang`, `href`, `class`, `style`) foram reconstruídos a partir dos fontes.
- Os arquivos de apoio dos fontes foram preservados.
- 現代日葡辞典 como fonte derivada: 0 entradas; a fonte pessoal não foi usada. O bônus JMdict-PT foi mantido byte a byte como recebido e contém 1 entrada homônima literal em `term_bank_8.json`; ela não foi criada pelo processo e não pode ser removida sem violar a integridade/licença declarada do bônus.

## Amostra de pendências

As amostras abaixo são extraídas dos JSONs finais e foram geradas sem API.

### 20 definições de uma palavra

- `鳥も通わぬ` (とりもかよわぬ) — out-of-the-way
- `そうした中で` (そうしたなかで) — meanwhile
- `善哉善哉` (ぜんざいぜんざい) — great!
- `理の当然` (りのとうぜん) — natural
- `遺憾ながら` (いかんながら) — unfortunately
- `平素は` (へいそは) — usually
- `気の大きい` (きのおおきい) — generous
- `巧まざる` (たくまざる) — artless
- `日を追って` (ひをおって) — daily
- `単独で` (たんどくで) — separately
- `ご参考まで` (ごさんこうまで) — FYI
- `単独で` (たんどくで) — unassisted
- `全体として` (ぜんたいとして) — overall
- `骨身を惜しまず` (ほねみをおしまず) — tirelessly
- `及ばない` (およばない) — unattainable
- `一貫して` (いっかんして) — consistently
- `カットイン` (カットイン) — cut-in
- `酸素透過率` (さんそとうかりつ) — OTR
- `交代で` (こうたいで) — alternately
- `戦闘不能` (せんとうふのう) — dead

### 20 definições longas

- `足を向けて寝られない` (あしをむけてねられない) — never forgetting someone who has done a favour
- `穴があったら入りたい` (あながあったらはいりたい) — wanting to sink into the ground in shame
- `福善禍淫` (ふくぜんかいん) — heaven rewards the good and punishes the evil
- `四海兄弟` (しかいけいてい) — people in the whole world being all brothers
- `夜も日も明けない` (よもひもあけない) — cannot live even a minute without someone or something
- `千人千色` (せんにんせんしょく) — It takes all sorts to make a world
- `単位取得退学` (たんいしゅとくたいがく) — withdrawal from a course having completed the coursework
- `斗酒なお辞せず` (としゅなおじせず) — being ready to drink sake by the keg
- `愚者一得` (ぐしゃいっとく) — even a fool may sometimes give good counsel
- `間が持てない` (まがもてない) — not knowing what to do with the time one has on one's hand
- `目が離せない` (めがはなせない) — unable to take one's eyes off of something
- `後手必敗` (ごてひっぱい) — Defeat is inevitable for one who goes second
- `大衆魚` (たいしゅうぎょ) — cheap fish for the masses (e.g. sardines, mackerel, pike)
- `百年河清` (ひゃくねんかせい) — waiting for one hundred years for the waters of the Yellow River to clear
- `点滴穿石` (てんてきせんせき) — limited strength, when persistently applied, can accomplish great feats
- `忠言逆耳` (ちゅうげんぎゃくじ) — honest advice is often unpleasant to the ears
- `秋の扇` (あきのおうぎ) — woman who has lost a man's affection or interest (as does a fan when summer turns to autumn)
- `文武不岐` (ぶんぶふき) — the literary and the military are the same path
- `脚下照顧` (きゃっかしょうこ) — seek enlightenment by knowing yourself and not by watching others
- `猫の額のような` (ねこのひたいのような) — very small (particularly of a room or flat)

- Entrada removida antes do empacotamento por referência literal a 現代日葡辞典: 1 (JMnedict-PT, term_bank_17.json; não foi removida do fonte).
