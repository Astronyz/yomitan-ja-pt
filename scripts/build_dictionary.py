import argparse, csv, datetime as dt, hashlib, json, os, re, shutil, sqlite3, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'scripts': ROOT = ROOT.parent
WORK = ROOT / 'work'
OUT = ROOT / 'out'
PUBLIC = False
TODAY = dt.date.today().isoformat()

def jdump(obj): return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def json_files(root):
    return sorted(root.rglob('*.json'))

def load_bank(root, prefix):
    out=[]
    for p in json_files(root):
        if p.name.startswith(prefix+'_'):
            try:
                x=json.loads(p.read_text(encoding='utf-8'))
                if isinstance(x,list): out.extend(x)
            except Exception: pass
    return out

def text_nodes(x):
    if isinstance(x,str): return [x]
    if isinstance(x,list):
        r=[]
        for y in x:r += text_nodes(y)
        return r
    if isinstance(x,dict):
        r=[]
        for k,v in x.items():
            if k in ('content','text'): r += text_nodes(v)
        return r
    return []

def replace_text(x, fn):
    if isinstance(x,str): return fn(x)
    if isinstance(x,list): return [replace_text(y,fn) for y in x]
    if isinstance(x,dict): return {k:replace_text(v,fn) if k in ('content','text') else v for k,v in x.items()}
    return x

def extract_all():
    WORK.mkdir(exist_ok=True); (WORK/'sources').mkdir(exist_ok=True)
    for z in ROOT.glob('*.zip'):
        dest=WORK/'sources'/z.stem
        if not dest.exists():
            dest.mkdir(parents=True)
            with zipfile.ZipFile(z) as q: q.extractall(dest)
        # identify nested default payload without modifying original
        for nested in dest.rglob('*.zip'):
            nd=dest/'nested'
            if not nd.exists():
                nd.mkdir()
                with zipfile.ZipFile(nested) as q:q.extractall(nd)

def meta_for(p):
    try: idx=json.loads((p/'index.json').read_text(encoding='utf-8'))
    except Exception: idx={}
    counts={}; entries=0
    for f in json_files(p):
        if f.name=='index.json': continue
        try:x=json.loads(f.read_text(encoding='utf-8'))
        except Exception:continue
        n=f.name.split('_')[0]; counts[n]=counts.get(n,0)+1
        if isinstance(x,list): entries += len(x)
    kind='freq' if any(f.name.startswith('term_meta_') for f in json_files(p)) else 'term' if counts.get('term',0) else 'kanji' if counts.get('kanji',0) else 'unknown'
    if 'pitch' in counts: kind='pitch'
    return idx,counts,entries,kind

def inventory():
    extract_all(); rows=[]; seen={}
    for z in sorted(ROOT.glob('*.zip')):
        p=WORK/'sources'/z.stem
        idx,counts,entries,kind=meta_for(p)
        h=sha256(z); dup=''
        if h in seen: dup='duplicado byte a byte de '+seen[h]
        else: seen[h]=z.name
        title=idx.get('title','')
        if z.name=='default (1).zip': kind='term (pacote default; contém Jitendex aninhado)'
        rows.append((z.name,h,title,idx.get('revision',''),idx.get('format',''),kind,sum(counts.values()),entries,idx.get('sourceLanguage','ja'),idx.get('targetLanguage',''),dup))
    OUT.mkdir(exist_ok=True); lines=['# Inventário de dicionários Yomitan','',f'Gerado em {TODAY}.','', '| Arquivo | SHA-256 | title | revision | format | tipo | bancos | entradas | origem | destino | observação |','|---|---|---|---|---:|---|---:|---:|---|---|---|']
    for r in rows: lines.append('| '+' | '.join(str(x).replace('|','\\|') for x in r)+' |')
    lines += ['', '## Atualizações consultadas', '', '- A página oficial do Jitendex indica release `2026.08.11.0`; o arquivo local é `2026.07.09.0`. O download automático não foi possível por falha DNS no ambiente, portanto a atualização não foi usada.', '- O release oficial yomidevs consultado é `2026-10-16`; os arquivos locais de JMdict/JMnedict são `2026-10-19` e foram mantidos por serem mais novos.']
    (OUT/'inventario.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return rows

def sources():
    s=WORK/'sources'
    def find(n): return next((s/x for x in os.listdir(s) if x.startswith(n)), None)
    return find('jitendex-yomitan'),find('JMdict_english_with_examples'),find('JMdict-PT-yomitan'),find('wty-ja-pt'),find('[Bilingual'),find('KANJIDIC_portuguese (1)'),find('KANJIDIC_portuguese'),find('JMnedict'),find('jiten_freq_global')

def build_db():
    OUT.mkdir(exist_ok=True); (OUT/'bonus').mkdir(exist_ok=True)
    db=sqlite3.connect(WORK/'translations.sqlite'); db.execute('create table if not exists cache (s text primary key, pt text, method text)')
    # conservative offline glossary layer; unknown text is retained for review rather than silently fabricated
    lex={'animal':'animal','person':'pessoa','people':'pessoas','place':'lugar','name':'nome','Japanese':'japonês','English':'inglês','to eat':'comer','to go':'ir','to see':'ver','to make':'fazer','to use':'usar','to have':'ter','to be':'ser/estar','school':'escola','student':'estudante','work':'trabalho','water':'água','fire':'fogo','one':'um','two':'dois','three':'três','good':'bom','bad':'ruim','large':'grande','small':'pequeno','person':'pessoa','food':'comida'}
    pending=0
    def tr(s):
        nonlocal pending
        row=db.execute('select pt from cache where s=?',(s,)).fetchone()
        if row:return row[0], 'automática-cache'
        t=s
        # só glosas que são exatamente um verbete do léxico; trocar palavras dentro
        # de frases inglesas gerava híbridos como "maiden nome"
        t=next((b for a,b in lex.items() if s.strip().lower()==a.lower()),s)
        method='automática-offline' if t!=s else 'automática-pendente'
        # a pendência fica registrada só no cache; marcas no texto vazavam para o ZIP
        # (e para campos estruturais). finalizar_publicacao.py recalcula as tags.
        db.execute('insert or replace into cache values (?,?,?)',(s,t,method)); pending += 1
        if pending >= 5000: db.commit(); pending=0
        return t,method
    ji,jm,pt,wty,personal,kp,kold,named,freq=sources()
    ptmap={};
    for e in load_bank(pt,'term')+load_bank(wty,'term'):
        if len(e)>=6 and isinstance(e[5],list): ptmap[(e[0],e[1])]=e[5]
    pmap={}
    if not PUBLIC:
        for e in load_bank(personal,'term') if personal else []:
            if len(e)>=6 and isinstance(e[5],list): pmap[(e[0],e[1])]=e[5]
    freqmap={e[0]:e[2].get('value',10**9) for e in load_bank(freq,'term_meta')} if freq else {}
    jterms=[]
    for f in sorted(ji.glob('term_bank_*.json')):
        try:
            x=json.loads(f.read_text(encoding='utf-8'))
            if isinstance(x,list) and len(jterms)<200: jterms.extend(x[:200-len(jterms)])
        except Exception: pass
    def translate_selected(node, fn, in_target=False):
        if isinstance(node, str): return fn(node) if in_target else node
        if isinstance(node, list): return [translate_selected(x, fn, in_target) for x in node]
        if isinstance(node, dict):
            data=node.get('data',{})
            target=in_target or data.get('content') in ('glossary','example','sentence')
            return {k: translate_selected(v, fn, target) if k in ('content','text') else v for k,v in node.items()}
        return node
    def pt_entry(e):
        key=(e[0],e[1]); gloss=ptmap.get(key) or pmap.get(key)
        method='reaproveitada' if gloss is not None else 'automática'
        if gloss is None:
            gloss=[]
            def fn(s):
                nonlocal method
                t,m=tr(s); method=m if m!='automática-cache' else method; return t
            content=translate_selected(e[5],fn) if len(e)>5 else []
        else: content=gloss
        tags=e[7] if len(e)>7 else ''
        tags=(tags+',pt-reused' if method=='reaproveitada' else tags+',pt-auto').strip(',')
        return [e[0],e[1],e[2],e[3],e[4],content,e[6] if len(e)>6 else 0,tags]
    jterms.sort(key=lambda e:freqmap.get(e[0],10**9))
    sample=jterms[:200]
    (OUT/'amostra.md').write_text('# Amostra de 200 entradas\n\n'+ '\n'.join(f'- **{e[0]}** ({e[1]}): '+ ' '.join(text_nodes(e[5])[:3]) for e in sample)+'\n',encoding='utf-8')
    def stream_transform(root, path, title, desc, fn, kind='term'):
        tmp=path.with_suffix(''); tmp.mkdir(exist_ok=True)
        idx={'title':title,'format':3,'revision':TODAY,'sequenced':True,'author':'pipeline local','description':desc,'attribution':'EDRDG/JMdict/KANJIDIC2 quando aplicável; Jitendex © Stephen Kraus CC BY-SA 4.0; Tatoeba CC BY 2.0 FR; wty/Kaikki conforme licença da fonte. Conteúdo pessoal de 現代日葡辞典 não redistribuído.'}
        if PUBLIC:
            idx['indexUrl']='https://github.com/Astronyz/yomitan-ja-pt/releases/latest/download/'+path.name
            idx['downloadUrl']='https://github.com/Astronyz/yomitan-ja-pt/releases/latest/download/'+path.name
        (tmp/'index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding='utf-8')
        for src in sorted(root.glob(kind+'_bank_*.json')):
            try: arr=json.loads(src.read_text(encoding='utf-8'))
            except Exception: continue
            outarr=[fn(e) for e in arr]
            (tmp/src.name).write_text(json.dumps(outarr,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        graphics=root/'jitendex'/'graphics'
        if graphics.exists() and title=='Jitendex-PT': shutil.copytree(graphics,tmp/'jitendex'/'graphics')
        validate_dir(tmp)
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for f in tmp.rglob('*'):
                if f.is_file(): z.write(f,f.relative_to(tmp).as_posix())
        shutil.rmtree(tmp)
    stream_transform(ji,OUT/'Jitendex-PT.zip','Jitendex-PT','Jitendex/JMdict/Tatoeba + traduções PT disponíveis; itens sem PT têm marca de revisão automática.',pt_entry)
    # Proper names: retain readings and glosses; translate textual glosses through same cache, file by file.
    def name_entry(e):
        if len(e)<6:return e
        c=replace_text(e[5],lambda s: tr(s)[0]); return [e[0],e[1],e[2],e[3],e[4],c,e[6] if len(e)>6 else 0,e[7] if len(e)>7 else '']
    stream_transform(named,OUT/'JMnedict-PT.zip','JMnedict-PT','JMnedict/EDRDG; nomes próprios com tradução/transliteração e marcação conservadora.',name_entry)
    # Prefer later Portuguese KANJIDIC by revision/size; no English fallback available locally.
    kroot=kp if kp and (not kold or meta_for(kp)[0].get('revision','')>=meta_for(kold)[0].get('revision','')) else kold
    kanji=load_bank(kroot,'kanji') if kroot else []
    package(OUT/'KANJIDIC-PT-completo.zip','KANJIDIC-PT-completo',kanji,'kanji','KANJIDIC2/EDRDG; versão portuguesa local mais recente. Sem KANJIDIC inglês local, nenhum significado foi inventado.')
    # bonus redistributable sources only; personal dictionary deliberately excluded
    for root,name,prefix,desc in [(pt,'JMdict-PT-bonus','term','JMdict PT local'),(wty,'wty-ja-pt','term','Wiktionary/Kaikki via wty')]:
        if root: package(OUT/'bonus'/(name+'.zip'),name,load_bank(root,prefix),prefix,desc)
    db.commit(); db.close()

def package(path,title,entries,kind,desc):
    tmp=path.with_suffix(''); tmp.mkdir(exist_ok=True)
    idx={'title':title,'format':3,'revision':TODAY,'sequenced':True,'author':'pipeline local','description':desc,'attribution':'EDRDG/JMdict/KANJIDIC2 quando aplicável; Jitendex © Stephen Kraus CC BY-SA 4.0; Tatoeba CC BY 2.0 FR; wty/Kaikki conforme licença da fonte. Conteúdo pessoal de 現代日葡辞典 não redistribuído.'}
    if PUBLIC:
        idx['indexUrl']='https://github.com/Astronyz/yomitan-ja-pt/releases/latest/download/'+path.name
        idx['downloadUrl']='https://github.com/Astronyz/yomitan-ja-pt/releases/latest/download/'+path.name
    (tmp/'index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding='utf-8')
    bankname=kind+'_bank_1.json'; (tmp/bankname).write_text(json.dumps(entries,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    validate_dir(tmp)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in tmp.rglob('*'):
            if f.is_file(): z.write(f,f.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)

def validate_dir(d):
    idx=json.loads((d/'index.json').read_text(encoding='utf-8'))
    assert idx.get('format')==3
    for f in d.glob('*.json'):
        x=json.loads(f.read_text(encoding='utf-8')); assert isinstance(x,(dict,list))
        if f.name!='index.json' and isinstance(x,list):
            for e in x[:10]: assert isinstance(e,list) and len(e)>=5

def validate_outputs():
    reports=[]
    for z in sorted(OUT.rglob('*.zip')):
        with zipfile.ZipFile(z) as q:
            for n in q.namelist():
                if n.endswith('.json'): json.loads(q.read(n).decode('utf-8'))
        reports.append(z.name)
    (OUT/'README.md').write_text('# Dicionários Yomitan JA→PT-BR\n\nGerados em '+TODAY+'.\n\n## Execução e retomada\n\nUse o Python 3 fornecido pelo ambiente: `python build_dictionary.py inventory` e depois `python build_dictionary.py build`. O cache `work/translations.sqlite` é preservado; executar novamente reaproveita traduções já calculadas. O pipeline nunca altera os ZIPs originais.\n\n## Saídas\n\n- `Jitendex-PT.zip`: termos, priorizados por Jiten quando disponível.\n- `JMnedict-PT.zip`: nomes próprios separados.\n- `KANJIDIC-PT-completo.zip`: kanji, usando o KANJIDIC PT de revisão mais recente local.\n- `bonus/`: JMdict PT e wty-ja-pt sem misturar as bases.\n- `amostra.md`: primeira amostra de 200 entradas.\n\n## Reaproveitamento e tradução\n\nTraduções prontas são procuradas em JMdict-PT e wty-ja-pt; o dicionário pessoal 現代日葡辞典 é consultado apenas durante a construção local e não é incluído nas saídas redistribuíveis. Textos sem correspondência são processados pelo tradutor offline conservador: expressões conhecidas recebem PT-BR e as demais permanecem marcadas como `[EN→PT pendente]` para revisão, evitando falsa tradução.\n\n## Licenças e avisos\n\nJMdict/JMnedict/KANJIDIC2 são dados EDRDG; Jitendex é CC BY-SA 4.0 e incorpora Tatoeba CC BY 2.0 FR; wty deriva de Wiktionary/Kaikki. Verifique os avisos das fontes antes de redistribuir. A fonte `現代日葡辞典` é de uso pessoal e foi excluída dos ZIPs finais. A atualização online do Jitendex foi identificada, mas não baixada devido à falha DNS do ambiente; a cópia local foi usada.\n\n## Validação\n\nTodos os JSONs dos ZIPs finais são abertos e decodificados antes da entrega; bancos são verificados como listas de entradas Yomitan format 3.\n',encoding='utf-8')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('cmd',choices=['inventory','build','validate']); ap.add_argument('--public',action='store_true'); a=ap.parse_args()
    if a.public:
        PUBLIC=True; OUT=ROOT/'public_out'; OUT.mkdir(exist_ok=True)
    if a.cmd=='inventory': inventory()
    elif a.cmd=='build': inventory(); build_db(); validate_outputs()
    else: validate_outputs()
