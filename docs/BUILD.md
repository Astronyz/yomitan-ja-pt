# Build público

O workflow usa Python 3, baixa somente fontes públicas listadas em `fontes.json`, aplica `data/overrides/`, valida JSON/Yomitan format 3 e rejeita `現代日葡辞典`, `work/`, `out/`, segredos e arquivos acima de 25 MB. Os ZIPs finais são destinados a Releases, nunca ao histórico Git.
