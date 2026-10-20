"""Pós-processamento final antes de publicar.

Compara cada string dos pacotes gerados em ``out/`` com a fonte original e:

* reverte para a fonte qualquer string alterada que continua em inglês
  (trocas de exemplo, glosas reescritas sem tradução, palavras soltas
  substituídas dentro de frases em inglês);
* recalcula as tags de status (``pt-reaproveitada``, ``pt-automatica``,
  ``pt-parcial``, ``pt-pendente``) a partir do que realmente foi traduzido;
* garante as declarações das tags no ``tag_bank`` e os URLs de atualização
  no ``index.json``;
* grava o resultado em ``public_out/`` e o índice solto ao lado do ZIP
  (``<Nome>.json``), que é o arquivo apontado por ``indexUrl``.

Uso: python scripts/finalizar_publicacao.py [--revision AAAA-MM-DD]
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "CosmionLabs/yomitan-ja-pt"
RELEASE_URL = f"https://github.com/{REPO}/releases/latest/download/"

STATUS = ["pt-reaproveitada", "pt-automatica", "pt-parcial", "pt-pendente"]
STATUS_DECLS = [
    ["pt-reaproveitada", "translation", 0, "Português reaproveitado de fonte aberta (JMdict-PT)", 0],
    ["pt-automatica", "translation", 0, "Tradução automática (DeepL), ainda não revisada", 0],
    ["pt-parcial", "translation", 0, "Parte das glosas ainda está em inglês", 0],
    ["pt-pendente", "translation", 0, "Glosas ainda em inglês, aguardando tradução", 0],
]

LATIN = re.compile(r"[A-Za-z]{3,}")
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿]")
PT_CHARS = re.compile(r"[áéíóúâêôãõçàÁÉÍÓÚÂÊÔÃÕÇÀ]")
PT_WORDS = re.compile(
    r"\b(?:de|da|do|das|dos|uma|um|não|para|com|pessoa|alguém|algo|ser|estar|que|em|ou|no|na|nos|nas|"
    r"pelo|pela|sem|seu|sua|isso|este|esta|muito|como|mais|também|quando|onde|ele|ela|eu|você|é)\b",
    re.I,
)
EN_WORDS = re.compile(
    r"\b(?:the|of|to|and|with|someone|something|one's|being|having|which|who|is|are|was|it|this|"
    r"that|you|your|from|by|at|on|an|as|not|be)\b",
    re.I,
)

PACKAGES = {
    "Jitendex-PT": ("jitendex-yomitan.zip", "Termos japonês → português brasileiro (base Jitendex/JMdict)."),
    "JMnedict-PT": ("JMnedict.zip", "Nomes próprios japonês → português brasileiro (base JMnedict)."),
    "KANJIDIC-PT-completo": ("KANJIDIC_portuguese (1).zip", "Kanji japonês → português brasileiro (base KANJIDIC2)."),
}


def still_english(s: str) -> bool:
    return bool(EN_WORDS.search(s)) and not PT_WORDS.search(s) and not PT_CHARS.search(s)


LOWER_WORD = re.compile(r"(?<![A-Za-z])[a-z]{3,}")


TOKEN = re.compile(r"[^\W\d_]{3,}")

# Léxico que versões antigas de build_dictionary.py aplicavam palavra a palavra
# dentro de frases inglesas; serve para reconhecer e desfazer essas trocas.
OLD_LEX = {
    "animal": "animal", "person": "pessoa", "people": "pessoas", "place": "lugar", "name": "nome",
    "Japanese": "japonês", "English": "inglês", "to eat": "comer", "to go": "ir", "to see": "ver",
    "to make": "fazer", "to use": "usar", "to have": "ter", "to be": "ser/estar", "school": "escola",
    "student": "estudante", "work": "trabalho", "water": "água", "fire": "fogo", "one": "um",
    "two": "dois", "three": "três", "good": "bom", "bad": "ruim", "large": "grande",
    "small": "pequeno", "food": "comida",
}


def old_lex(s: str) -> str:
    for a, b in sorted(OLD_LEX.items(), key=lambda z: -len(z[0])):
        s = re.sub(r"\b" + re.escape(a) + r"\b", b, s, flags=re.I)
    return s


def word_swapped(src: str, cur: str) -> bool:
    """Tradução palavra-a-palavra dentro da frase inglesa ("maiden nome")."""
    if src.strip().lower() not in {k.lower() for k in OLD_LEX} and cur == old_lex(src):
        return True
    s, c = TOKEN.findall(src), TOKEN.findall(cur)
    if len(s) < 3:
        return False
    kept = sum(1 for t in s if t in c)
    new = sum(1 for t in c if t not in s)
    return kept / len(s) >= 0.6 and new <= 2


def translatable(s: str) -> bool:
    # Nomes romanizados soltos ("Tanaka", "NASDAQ") não precisam de tradução.
    if JAPANESE.search(s) or not LATIN.search(s):
        return False
    return bool(EN_WORDS.search(s) or LOWER_WORD.search(s))


def merge(src, cur, glossary: bool, found: list, stats: Counter):
    """Devolve ``cur`` com a forma de ``src``; registra (glosa?, traduzida?) em ``found``."""
    if isinstance(src, str):
        if not isinstance(cur, str):
            cur = src
        if cur != src and translatable(src) and (still_english(cur) or word_swapped(src, cur)):
            stats["revertidas"] += 1
            cur = src
        if translatable(src):
            found.append((glossary, cur != src))
        return cur
    if isinstance(src, list):
        if not isinstance(cur, list) or len(cur) != len(src):
            stats["forma_restaurada"] += 1
            cur = [None] * len(src)
        return [merge(a, b, glossary, found, stats) for a, b in zip(src, cur)]
    if isinstance(src, dict):
        data = src.get("data")
        here = glossary or (isinstance(data, dict) and data.get("content") == "glossary")
        out = {}
        for key, value in src.items():
            if key in ("content", "text") and isinstance(cur, dict):
                out[key] = merge(value, cur.get(key), here, found, stats)
            elif key in ("content", "text"):
                out[key] = merge(value, None, here, found, stats)
            else:
                out[key] = copy.deepcopy(value)
        return out
    return copy.deepcopy(src)


def status_for(found: list, previous: set[str]) -> str | None:
    gloss = [t for g, t in found if g] or [t for _, t in found]
    if not gloss:
        return None
    done = sum(gloss)
    if done == len(gloss):
        return "pt-reaproveitada" if "pt-reaproveitada" in previous else "pt-automatica"
    if done:
        return "pt-parcial"
    return "pt-pendente"


def set_status(tags: str, status: str | None) -> str:
    items = [t for t in (tags or "").split(",") if t and t not in STATUS]
    if status:
        items.append(status)
    return ",".join(items)


def fix_index(raw: bytes, name: str, desc: str, revision: str) -> dict:
    idx = json.loads(raw)
    idx.update(
        title=name,
        author="CosmionLabs",
        revision=revision,
        sourceLanguage="ja",
        targetLanguage="pt",
        isUpdatable=True,
        indexUrl=RELEASE_URL + name + ".json",
        downloadUrl=RELEASE_URL + name + ".zip",
        description=desc + " Pré-lançamento: parte das definições ainda está em inglês (tag pt-pendente/pt-parcial).",
    )
    for k in ("description", "attribution"):
        if isinstance(idx.get(k), str):
            idx[k] = idx[k].replace("現代日葡辞典", "").strip()
    return idx


def process(name: str, source: Path, current: Path, target: Path, desc: str, revision: str) -> Counter:
    stats = Counter()
    with zipfile.ZipFile(source) as sz, zipfile.ZipFile(current) as cz, \
            zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as oz:
        names = set(cz.namelist())
        for info in sz.infolist():
            fn = info.filename
            raw = sz.read(fn)
            if fn == "index.json":
                idx = fix_index(cz.read(fn) if fn in names else raw, name, desc, revision)
                raw = json.dumps(idx, ensure_ascii=False, indent=2).encode("utf-8")
                target.with_suffix(".json").write_bytes(raw)
            elif fn.startswith("tag_bank") and fn.endswith(".json"):
                tags = json.loads(raw)
                have = {t[0] for t in tags}
                tags += [d for d in STATUS_DECLS if d[0] not in have]
                raw = json.dumps(tags, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                stats["tag_bank"] += 1
            elif fn.startswith("term_bank") and fn.endswith(".json") and fn in names:
                src_rows = json.loads(raw)
                cur_rows = json.loads(cz.read(fn))
                if len(src_rows) != len(cur_rows):
                    raise SystemExit(f"{name}/{fn}: número de entradas difere da fonte")
                out_rows = []
                for s, c in zip(src_rows, cur_rows):
                    if s[0] != c[0] or s[1] != c[1]:
                        raise SystemExit(f"{name}/{fn}: ordem de entradas difere da fonte ({s[0]})")
                    found: list = []
                    row = copy.deepcopy(s)
                    row[5] = merge(s[5], c[5], False, found, stats)
                    previous = set((c[2] or "").split(","))
                    status = status_for(found, previous)
                    row[2] = set_status(s[2], status)
                    stats[status or "sem-texto"] += 1
                    stats["entradas"] += 1
                    out_rows.append(row)
                raw = json.dumps(out_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            elif fn in names and fn.endswith(".json"):
                # kanji_bank e afins: mantém a versão gerada (a fonte já é PT).
                raw = cz.read(fn)
            oz.writestr(info, raw)
        if not any(n.startswith("tag_bank") for n in sz.namelist()):
            oz.writestr("tag_bank_1.json", json.dumps(STATUS_DECLS, ensure_ascii=False))
            stats["tag_bank"] += 1
    return stats


def validate(path: Path) -> None:
    with zipfile.ZipFile(path) as z:
        assert "index.json" in z.namelist(), path
        for n in z.namelist():
            if n.endswith(".json"):
                raw = z.read(n)
                json.loads(raw)
                for bad in (b"translation-source", "[EN→PT pendente]".encode()):
                    if bad in raw:
                        raise SystemExit(f"{path.name}/{n}: contém {bad!r}")
        # O JMnedict tem uma entrada para o título 現代日葡辞典 (nome de obra);
        # o que não pode aparecer é a obra como fonte nos metadados.
        if "現代日葡辞典".encode() in z.read("index.json"):
            raise SystemExit(f"{path.name}: index.json cita 現代日葡辞典")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", default="2026-10-20")
    ap.add_argument("--out", type=Path, default=ROOT / "out")
    ap.add_argument("--public", type=Path, default=ROOT / "public_out")
    args = ap.parse_args()
    args.public.mkdir(exist_ok=True)
    lines = ["| Dicionário | Entradas | reaproveitada | automática | parcial | pendente |", "|---|---:|---:|---:|---:|---:|"]
    for name, (src, desc) in PACKAGES.items():
        target = args.public / f"{name}.zip"
        st = process(name, ROOT / src, args.out / f"{name}.zip", target, desc, args.revision)
        validate(target)
        n = st["entradas"] or 1
        pct = lambda k: f"{st[k]:,} ({st[k] / n * 100:.1f}%)".replace(",", ".")
        lines.append(f"| {name} | {st['entradas']:,} | {pct('pt-reaproveitada')} | {pct('pt-automatica')} | {pct('pt-parcial')} | {pct('pt-pendente')} |".replace(",", "."))
        print(name, dict(st))
    bonus = args.public / "bonus"
    bonus.mkdir(exist_ok=True)
    for p in (args.out / "bonus").glob("*.zip"):
        shutil.copy2(p, bonus / p.name)
    (args.public / "status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
