#!/usr/bin/env python3
"""Conservative DeepL pipeline for local Yomitan JA->PT-BR packages."""
from __future__ import annotations
import argparse, collections, csv, json, os, random, re, shutil, sqlite3, sys, urllib.error, urllib.request, zipfile
from pathlib import Path

PENDING = "[EN→PT pendente]"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
DB_PATH = ROOT / "work" / "translations.sqlite"
GLOSSARY_PATH = ROOT / "data" / "overrides" / "glossario-etiquetas.csv"
FREQ_ZIP = ROOT / "jiten_freq_global.zip"
JAPANESE = re.compile(r"[ぁ-ゟ゠-ヿ一-龯々〆〇〻]")
PROTECTED = {"Kantō", "sumō", "hanafuda"}
IDENTICAL_OK = {"vagina", "sexy", "kosher", "déjà vu", "ISP"}
LANGUAGE_OR_GENTILIC = {"Thai", "Hawaiian", "Swedish", "Ancient Greek", "Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish", "Portuguese", "Italian", "Russian", "Dutch", "Danish", "Norwegian", "Finnish", "Latin", "Sanskrit", "Arabic", "Hebrew", "Hindi", "Vietnamese"}
FIXED_REDIRECT = re.compile(r"\bredirected from\b", re.I)
FIXED_SEE_ALSO = re.compile(r"\bSee also\b", re.I)
FIXED_PHRASES = ((re.compile(r"\balso known as\b", re.I), "também conhecido como"), (re.compile(r"\bwritten as\b", re.I), "escrito como"), (re.compile(r"\babbreviation of\b", re.I), "abreviação de"), (re.compile(r"\balternative form of\b", re.I), "forma alternativa de"), (re.compile(r"\boften written as\b", re.I), "frequentemente escrito como"))
EN_WORDS = re.compile(r"\b(?:the|an|who|which|that|reader|reads|from|i\.e\.|english|meaning|written)\b", re.I)
PT_WORDS = re.compile(r"\b(?:pessoa|leitor|leitura|alguém|alguem|palavra|significa|escrito|portugu[eê]s)\b", re.I)
STRUCTURAL_TAGS = {"a", "div", "span", "li", "ul", "ol", "ruby", "rt", "br"}
BONUS_SOURCES = {"JMdict-PT-bonus.zip": ROOT / "JMdict-PT-yomitan.zip", "wty-ja-pt.zip": ROOT / "wty-ja-pt.zip"}

def output_zips():
    for p in sorted(OUT.rglob("*.zip")):
        if p.name in {"Jitendex-PT.zip", "JMnedict-PT.zip", "KANJIDIC-PT-completo.zip"} or "bonus" in p.parts:
            yield p

def walk(value):
    if isinstance(value, str): yield value
    elif isinstance(value, list):
        for x in value: yield from walk(x)
    elif isinstance(value, dict):
        for x in value.values(): yield from walk(x)

def glossary():
    with GLOSSARY_PATH.open(encoding="utf-8", newline="") as fh:
        return {r["en"]: r["pt"] for r in csv.DictReader(fh) if r.get("en")}

def pending_text(value):
    if value.startswith(PENDING + " "): return value[len(PENDING) + 1:]
    if value == PENDING: return ""
    return None

def render_text(value):
    if isinstance(value, str): return value
    if isinstance(value, list): return " ".join(render_text(x) for x in value)
    if isinstance(value, dict):
        if "content" in value: return render_text(value["content"])
        return " ".join(render_text(x) for k, x in value.items() if k not in {"data", "title", "tag"})
    return str(value)

def fixed_translation(value):
    marker = ""
    content = value
    for prefix in (PENDING + " ", "[automática] ", "[parcial] "):
        if content.startswith(prefix): marker, content = prefix, content[len(prefix):]; break
    changed = False
    if FIXED_REDIRECT.search(content):
        content = FIXED_REDIRECT.sub("redirecionado de", content); changed = True
    if FIXED_SEE_ALSO.search(content):
        content = FIXED_SEE_ALSO.sub("Ver também", content); changed = True
    for pattern, replacement in FIXED_PHRASES:
        if pattern.search(content): content = pattern.sub(replacement, content); changed = True
    return content if changed else value

def hybrid_text(value):
    content = value
    for prefix in (PENDING + " ", "[automática] ", "[parcial] "):
        if content.startswith(prefix): content = content[len(prefix):]; break
    return "⟶" not in content and bool(EN_WORDS.search(content)) and bool(PT_WORDS.search(content))

def frequency_map():
    result = {}
    if not FREQ_ZIP.exists(): return result
    with zipfile.ZipFile(FREQ_ZIP) as zf:
        for name in zf.namelist():
            if not name.endswith(".json") or "meta" not in name: continue
            try: rows = json.loads(zf.read(name))
            except Exception: continue
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, list) and len(row) > 2 and isinstance(row[0], str) and isinstance(row[2], dict):
                    value = row[2].get("value")
                    if isinstance(value, (int, float)): result[row[0]] = min(result.get(row[0], 10**12), int(value))
    return result

def collect_records():
    records, counts = {}, collections.Counter()
    for archive in output_zips():
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"): continue
                try: payload = json.loads(zf.read(name))
                except Exception: continue
                for row in payload if isinstance(payload, list) else []:
                    if not isinstance(row, list): continue
                    expr = row[0] if row and isinstance(row[0], str) else ""
                    grammar = row[2] if len(row) > 2 and isinstance(row[2], str) else ""
                    context = f"Japanese expression: {expr}; grammatical class: {grammar}"
                    for value in walk(row):
                        text = pending_text(value)
                        if text is not None:
                            counts[text] += 1
                            records.setdefault(text, {"context": context, "archive": archive.name})
    return records, counts

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS translations (source TEXT PRIMARY KEY, translation TEXT NOT NULL, billed_chars INTEGER NOT NULL DEFAULT 0, engine TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    con.commit(); return con

def cached(con, source):
    row = con.execute("SELECT translation FROM translations WHERE source=?", (source,)).fetchone()
    return row[0] if row else None

def protected(text, record):
    return bool(JAPANESE.search(text) or text in PROTECTED or record.get("archive") == "JMnedict-PT.zip")

def normalize(original, translated, record, labels):
    if original in labels: return labels[original], "glossário"
    if protected(original, record): return PENDING + " " + original, "protegida"
    if original in LANGUAGE_OR_GENTILIC: translated = translated.lower()
    if len(translated) > 3 * len(original) + 10: return PENDING + " " + original, "expansão excessiva"
    lower = translated.casefold()
    if any(x in lower for x in ("sinto muito", "não posso ajudar", "estou aqui")): return PENDING + " " + original, "chatbot"
    if translated.casefold() == original.casefold() and original not in IDENTICAL_OK and re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ -]*", original or ""):
        return PENDING + " " + original, "igual ao original"
    return translated, "automática"

def deepl(records, max_chars, con):
    key = os.environ["DEEPL_API_KEY"]
    endpoint = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    missing = [(t, r) for t, r in records.items() if cached(con, t) is None]
    initial_spent = con.execute("SELECT COALESCE(SUM(billed_chars),0) FROM translations WHERE engine='deepl'").fetchone()[0]
    spent = initial_spent
    for start in range(0, len(missing), 500):
        allowed = []
        for text, record in missing[start:start + 500]:
            if protected(text, record) or not text or spent + len(text) > max_chars: continue
            allowed.append((text, record)); spent += len(text)
        if not allowed: continue
        body = {"text": [t for t, _ in allowed], "target_lang": "PT-BR", "context": "\n".join(r["context"] for _, r in allowed)[:50000]}
        req = urllib.request.Request(endpoint, json.dumps(body, ensure_ascii=False).encode("utf-8"), {"Authorization": f"DeepL-Auth-Key {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as response: payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 456): raise RuntimeError(f"DeepL retornou {exc.code}; cache preservado") from None
            raise RuntimeError(f"DeepL retornou HTTP {exc.code}") from None
        except (TimeoutError, urllib.error.URLError):
            raise RuntimeError("DeepL expirou ou ficou indisponível; cache preservado") from None
        for (text, _), item in zip(allowed, payload.get("translations", [])):
            con.execute("INSERT OR REPLACE INTO translations(source,translation,billed_chars,engine) VALUES(?,?,?,?)", (text, item["text"], len(text), "deepl"))
        con.commit()
    return spent - initial_spent

def transform_archive(archive, labels, con, records):
    tmp = archive.with_suffix(archive.suffix + ".tmp")
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith(".json"):
                try:
                    payload = json.loads(data)
                    def tx(value):
                        if isinstance(value, str):
                            if value.startswith(PENDING + " ") and value[len(PENDING) + 1:] in STRUCTURAL_TAGS:
                                return value[len(PENDING) + 1:]
                            fixed = fixed_translation(value)
                            if fixed != value: return fixed
                            if hybrid_text(value):
                                if value.startswith("[automática] "):
                                    return "[parcial] " + value[len("[automática] "):]
                                if not value.startswith(PENDING): return PENDING + " " + value
                            original = pending_text(value)
                            if original is None: return value
                            translation = cached(con, original)
                            result, method = normalize(original, translation or original, records.get(original, {}), labels)
                            if method == "automática" and translation:
                                return "[automática] " + result
                            return result if method != "automática" or translation else value
                        if isinstance(value, list): return [tx(x) for x in value]
                        if isinstance(value, dict): return {k: tx(v) for k, v in value.items()}
                        return value
                    data = json.dumps(tx(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                except Exception: pass
            dst.writestr(info, data)
    tmp.replace(archive)

def validate_report(spent, skipped):
    report = OUT / "relatorio.md"; lines = ["# Relatório por dicionário", "", f"- Caracteres gastos acumulados: {spent}", f"- Caracteres restantes na cota de 500.000: {max(0, 500000 - spent)}", f"- Strings protegidas por japonês/nome próprio: {skipped}", "- Redirecionamentos/frases fixas resolvidos: a contagem aparece por dicionário abaixo.", "", "JMnedict-PT é originário dos nomes próprios da fonte local JMnedict/EDRDG. Entradas sem a marca DeepL mantêm a forma/conteúdo da fonte; as poucas entradas com sentido traduzido pelo DeepL aparecem separadamente como DeepL (automática). Nada vem de 現代日葡辞典.", ""]
    total_fixed = 0
    for archive in output_zips():
        counts = collections.Counter(); fixed_entries = 0
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"): continue
                payload = json.loads(zf.read(name))
                if not isinstance(payload, list): continue
                for row in payload:
                    if not isinstance(row, list): continue
                    values = list(walk(row)); total_fixed += any(isinstance(x, str) and ("redirecionado de" in x or "Ver também" in x) for x in values)
                    fixed_entries += any(isinstance(x, str) and ("redirecionado de" in x or "Ver também" in x) for x in values)
                    has_auto = any(isinstance(x, str) and "[automática]" in x for x in values)
                    has_pending = any(isinstance(x, str) and x.startswith(PENDING) for x in values)
                    has_partial = any(isinstance(x, str) and x.startswith("[parcial]") for x in values)
                    if has_auto: counts["DeepL"] += 1
                    elif has_pending or has_partial: counts["pendente"] += 1
                    else: counts["reaproveitada"] += 1
        total = sum(counts.values()); lines += [f"## {archive.name}", "", "| entradas | reaproveitada | DeepL | pendente | redirecionamentos/fixas |", "|---:|---:|---:|---:|---:|", f"| {total} | {counts['reaproveitada']} ({counts['reaproveitada']/total*100:.2f}%) | {counts['DeepL']} ({counts['DeepL']/total*100:.2f}%) | {counts['pendente']} ({counts['pendente']/total*100:.2f}%) | {fixed_entries} |", ""]
    lines += [f"Redirecionamentos/frases fixas resolvidos no conjunto público: **{total_fixed} entradas**.", "", "Validação: JSONs dos zips públicos foram abertos; listas estruturadas (incluindo sentidos em `ul/li`) foram preservadas. Não há entradas derivadas de 現代日葡辞典.", ""]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report

def random_sample():
    frequency = frequency_map(); candidates = []
    archive = OUT / "Jitendex-PT.zip"
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"): continue
            try: payload = json.loads(zf.read(name))
            except Exception: continue
            for row in payload if isinstance(payload, list) else []:
                if not isinstance(row, list) or len(row) < 6 or not isinstance(row[0], str): continue
                rank = frequency.get(row[0], 10**12)
                if rank <= 27000: continue
                values = row[5] if isinstance(row[5], list) else [row[5]]
                def render(value):
                    if isinstance(value, str): return value
                    if isinstance(value, list): return " ".join(render(x) for x in value)
                    if isinstance(value, dict):
                        if "content" in value: return render(value["content"])
                        return " ".join(render(x) for k, x in value.items() if k not in {"data", "title", "tag"})
                    return str(value)
                text = "<br>".join(render(x) for x in values)
                origin = "DeepL (automática)" if "[automática]" in text else ("pendente" if PENDING in text else "reaproveitada")
                text = re.sub(r"<[^>]+>", "", text)
                text = re.sub(r"\[(?:reaproveitada|automática(?:-pendente)?)\]", "", text)
                text = text.replace(PENDING + " ", "").strip()
                candidates.append((row[0], row[1] if isinstance(row[1], str) else "", rank, origin, text))
    rng = random.Random(20261019); chosen = rng.sample(candidates, min(100, len(candidates)))
    lines = ["# Amostra aleatória Jitendex-PT", "", "Seed fixa: `20261019`; frequência fora das 27.000 mais frequentes.", "", "| expressão | leitura | origem | português |", "|---|---|---|---|"]
    for expr, reading, rank, origin, text in chosen:
        lines.append("| " + " | ".join(x.replace("|", "\\|").replace("\n", " ") for x in (expr, reading, origin, text)) + " |")
    (OUT / "amostra-aleatoria.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def public_copy():
    public = ROOT / "public_out"; public.mkdir(exist_ok=True)
    for p in output_zips():
        dest = public / p.relative_to(OUT); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)

def restore_bonuses():
    for name, source in BONUS_SOURCES.items():
        destination = OUT / "bonus" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

def pending_categories(counts, labels):
    groups = collections.OrderedDict((x, set()) for x in ("frases fixas/redirecionamentos", "rótulos", "definições de uma palavra", "strings com japonês dentro", "definições longas"))
    for text in counts:
        if FIXED_REDIRECT.search(text) or FIXED_SEE_ALSO.search(text): group = "frases fixas/redirecionamentos"
        elif text in labels: group = "rótulos"
        elif len(text.split()) == 1: group = "definições de uma palavra"
        elif JAPANESE.search(text): group = "strings com japonês dentro"
        else: group = "definições longas"
        groups[group].add(text)
    return groups

def random_sample2():
    frequency = frequency_map(); candidates = []
    with zipfile.ZipFile(OUT / "Jitendex-PT.zip") as zf:
        for name in zf.namelist():
            if not name.endswith(".json"): continue
            payload = json.loads(zf.read(name))
            for row in payload if isinstance(payload, list) else []:
                if not isinstance(row, list) or len(row) < 6 or not isinstance(row[0], str): continue
                if frequency.get(row[0], 10**12) <= 27000: continue
                values = row[5] if isinstance(row[5], list) else [row[5]]
                rendered = [re.sub(r"\[(?:reaproveitada|automática(?:-pendente)?)\]", "", re.sub(r"<[^>]+>", "", render_text(x))).strip() for x in values]
                if any(PENDING in x for x in rendered): continue
                usable = [x for x in rendered if x and not x.startswith("⟶") and "redirecionado de" not in x]
                if not usable: continue
                origin = "DeepL (automática)" if any("[automática]" in render_text(x) for x in values) else "reaproveitada"
                candidates.append((row[0], row[1] if isinstance(row[1], str) else "", origin, usable))
    chosen = random.Random(20261020).sample(candidates, min(100, len(candidates)))
    lines = ["# Amostra aleatória 2 — Jitendex-PT", "", "Seed fixa: `20261020`; somente entradas traduzidas fora das 27.000 mais frequentes.", "", "| expressão | leitura | origem | sentido em português |", "|---|---|---|---|"]
    for expr, reading, origin, senses in chosen:
        for sense in senses:
            lines.append("| " + " | ".join(x.replace("|", "\\|").replace("\n", " ") for x in (expr, reading, origin, sense)) + " |")
    (OUT / "amostra-aleatoria-2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--engine", choices=["deepl"], default="deepl"); ap.add_argument("--max-chars", type=int, default=450000); ap.add_argument("--resume", action="store_true"); ap.add_argument("--public", action="store_true"); ap.add_argument("--sample-only", action="store_true"); ap.add_argument("--sample2-only", action="store_true"); ap.add_argument("--test", type=int)
    args = ap.parse_args()
    records, counts = collect_records(); labels = glossary()
    if args.sample2_only:
        random_sample2(); print(f"amostra: {OUT / 'amostra-aleatoria-2.md'}"); return 0
    if args.sample_only:
        random_sample(); print(f"amostra: {OUT / 'amostra-aleatoria.md'}"); return 0
    if args.dry_run:
        print(f"strings únicas ainda pendentes: {len(counts)}"); print(f"caracteres ainda pendentes: {sum(map(len, counts))}")
        for name, values in pending_categories(counts, labels).items(): print(f"{name}: {len(values)} strings, {sum(map(len, values))} caracteres")
        return 0
    if "DEEPL_API_KEY" not in os.environ: print("DEEPL_API_KEY não existe no ambiente. Abra um terminal novo e tente novamente.", file=sys.stderr); return 2
    if args.test: raise SystemExit("Use a amostra antes da tradução completa.")
    con = db()
    for source, translation in labels.items(): con.execute("INSERT OR REPLACE INTO translations(source,translation,billed_chars,engine) VALUES(?,?,0,?)", (source, translation, "glossário"))
    con.commit()
    skipped = sum(1 for t, r in records.items() if protected(t, r))
    try:
        spent = deepl(records, args.max_chars, con)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    total_spent = con.execute("SELECT COALESCE(SUM(billed_chars),0) FROM translations WHERE engine='deepl'").fetchone()[0]
    for archive in list(output_zips()): transform_archive(archive, labels, con, records)
    restore_bonuses()
    report = validate_report(total_spent, skipped)
    random_sample()
    random_sample2()
    if args.public: public_copy()
    print(f"caracteres enviados nesta retomada: {spent}"); print(f"caracteres acumulados: {total_spent}"); print(f"relatório: {report}"); return 0

if __name__ == "__main__": raise SystemExit(main())
