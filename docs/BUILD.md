# Build

O pipeline roda localmente com Python 3.10+ e sem dependências externas. As fontes originais ficam na raiz do projeto local (fora do Git) e os intermediários em `work/` e `out/`, que o `.gitignore` exclui.

## Etapas

1. `python scripts/download_latest_sources.py`: baixa as versões mais recentes das fontes públicas listadas em `fontes.json`.
2. `python scripts/build_dictionary.py`: gera `out/` a partir das fontes, reaproveitando o português do JMdict-PT e o glossário de etiquetas em `data/overrides/`.
3. `python scripts/translate_pending.py` / `python scripts/translate_remaining.py`: traduz as glosas pendentes com DeepL, usando a chave em `DEEPL_API_KEY` e o cache `work/translations.sqlite`. Cada string é paga só uma vez.
   Alternativa: `python scripts/translate_gemini.py`, com a chave em `GEMINI_API_KEY`. Ele lê `public_out/`, envia só as glosas que continuam em inglês e grava no mesmo cache (`engine = gemini:<modelo>`). Rode antes com `--dry-run`, que conta as strings e estima o custo, e depois `--max-requests 2` para conferir a qualidade. O script é retomável e para sozinho quando a cota diária acaba. Depois volte à etapa 5.
4. `python scripts/rebuild_clean.py`: reconstrói os pacotes de `out/` sobre a estrutura exata das fontes, preservando os campos estruturais (`tag`, `data`, `lang`, `href`, `style`) e os arquivos de apoio.
5. `python scripts/finalizar_publicacao.py`: compara cada string com a fonte, desfaz trocas que continuaram em inglês (incluindo híbridos como "maiden nome"), aplica as traduções do cache às strings que ainda estão iguais à fonte, recalcula as tags `pt-*`, ajusta `index.json`/`tag_bank` e grava `public_out/`.
6. Copie `public_out/*.zip` e `public_out/*.json` para `dictionaries/` e rode `python scripts/build.py --public`.

## Release

Um push de tag `vX.Y.Z` dispara `.github/workflows/release.yml`. Ele valida `dictionaries/` com `scripts/build.py` e publica os ZIPs e os índices soltos (`Jitendex-PT.json`, etc.) como assets do Release. Os índices são o alvo de `indexUrl`, que o Yomitan consulta para verificar atualizações. O release sai sempre como "latest", e não como prerelease, porque `releases/latest/download/` ignora pré-lançamentos e quebraria as atualizações. O aviso de que a v0.x é um pré-lançamento fica em `docs/RELEASE.md`.

## Regras

- `現代日葡辞典` nunca é fonte. O build e o CI rejeitam metadados que o citem.
- Nada de `work/`, `out/`, caches de tradução ou chaves de API no Git.
- Os bônus (`JMdict-PT-bonus.zip`, `wty-ja-pt.zip`) são cópias byte a byte das fontes.
