"""Offline, auditable FY2025 Item 1A exploratory extraction and review support."""
import csv
import hashlib
import json
import re
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/exploratory_fy2025_item1a_review'
TEXT = ROOT / 'data/raw/documents/item1a_text'
AI = re.compile(r'\bAI\b|artificial intelligence|generative|machine.learning|large.language|\bLLMs?\b|algorithmic|neural network|automated.decision|deep.learning|chatbot', re.I)

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def blocks(path, *, exclude_hidden=False):
    root = html.fromstring(path.read_bytes(), parser=html.HTMLParser(encoding='utf-8'))
    result, buffer = [], []
    owner = None
    boundary = {'p','div','li','tr','td','h1','h2','h3','h4','h5','h6','br','hr'}
    absolute_fragments = path.name.startswith('CALM_')
    def flush():
        nonlocal buffer
        text = re.sub(r'\s+', ' ', ''.join(buffer)).strip()
        if text:
            result.append({'text':text, 'xpath':root.getroottree().getpath(owner), 'style':owner.get('style') or ''})
        buffer = []
    def walk(el):
        nonlocal owner
        if exclude_hidden and not isinstance(el.tag,str):
            return
        tag = str(el.tag).lower()
        style=(el.get('style') or '').replace(' ','').lower()
        if tag in {'script','style','ix:header','head'} or 'display:none' in style:
            return
        if exclude_hidden and (tag in {'ix:hidden','noscript','template'} or el.get('hidden') is not None or
                               (el.get('aria-hidden') or '').lower()=='true' or 'visibility:hidden' in style):
            return
        if exclude_hidden and (tag=='nav' or el.get('role')=='navigation'):
            return
        if exclude_hidden and tag=='a' and el.get('href') and re.fullmatch(
                r'(?:table\s+of\s+contents|back\s+to\s+(?:top|contents))',
                ' '.join(''.join(el.itertext()).split()),re.I):
            return
        is_boundary = tag in boundary and not (absolute_fragments and 'display:inline-block' in (el.get('style') or ''))
        if is_boundary:
            flush()
        owner = el
        if el.text: buffer.append(el.text)
        for ch in el:
            walk(ch)
            owner = el
            if ch.tail: buffer.append(ch.tail)
        if is_boundary: flush()
    walk(root)
    flush()
    for i,b in enumerate(result): b['block'] = i
    return result

def inspect(tickers):
    OUT.mkdir(parents=True, exist_ok=True)
    for ticker in tickers:
        b = blocks(ROOT / f'data/raw/documents/{ticker}_FY2025_10K.html')
        (OUT / f'{ticker}_blocks.json').write_text(json.dumps(b,ensure_ascii=False),encoding='utf-8')
        print('\n',ticker,len(b))
        for i,x in enumerate(b):
            if re.search(r'^item\s*1\s*[abc]\b',x['text'],re.I):
                print(i,repr(x['text'][:200]),'NEXT',repr(b[i+1]['text'][:100]))

def extract(tickers):
    OUT.mkdir(parents=True, exist_ok=True)
    TEXT.mkdir(parents=True, exist_ok=True)
    (OUT / 'item1a_text').mkdir(exist_ok=True)
    (OUT / 'audit').mkdir(exist_ok=True)
    manifests = {r['ticker']:r for r in read_csv(ROOT/'data/interim/documents/fy2025_10k_manifest.csv')}
    for t in tickers:
        m = manifests[t]
        path = ROOT/m['local_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == m['sha256'], t
        b = blocks(path)
        starts = [i for i,x in enumerate(b) if re.fullmatch(r'item\s*1\s*a[.\s:–—-]*(?:risk factors\.?)?',x['text'],re.I)]
        if not starts:
            # Some issuers label the body only RISK FACTORS; TOC and successor
            # must independently confirm this fallback before final approval.
            starts = [i for i,x in enumerate(b) if x['text'].upper()=='RISK FACTORS'][-1:]
        ends = [i for i,x in enumerate(b) if re.match(r'^item\s*1\s*[bc]\b|^item\s*2\b',x['text'],re.I) and len(x['text'])<150]
        pairs = [(s,next((e for e in ends if e>s),len(b))) for s in starts]
        pairs = [(s,e) for s,e in pairs if 'risk factors' in ' '.join(x['text'] for x in b[s:s+3]).lower()]
        if not pairs:
            print(t,'FAILED',starts,ends); continue
        s,e = max(pairs,key=lambda p:sum(len(x['text']) for x in b[p[0]:p[1]]))
        # Only literal printed numbers in styled footer blocks; validate consecutive series.
        nums = [(i,int(x['text'])) for i,x in enumerate(b) if re.fullmatch(r'\d{1,3}',x['text']) and ('text-align:center' in x['style'].replace(' ','') or 'text-align:right' in x['style'].replace(' ',''))]
        foot = [(i,n) for k,(i,n) in enumerate(nums) if (k>0 and nums[k-1][1]==n-1) or (k+1<len(nums) and nums[k+1][1]==n+1)]
        section = b[s:e]
        for x in section:
            nxt = next(((i,n) for i,n in foot if i>=x['block']),None)
            prev = next(((i,n) for i,n in reversed(foot) if i<x['block']),None)
            x['printed_page'] = nxt[1] if nxt and prev and nxt[1]==prev[1]+1 else None
        words = sum(len(x['text'].split()) for x in section)
        status = 'success' if words>1500 and e<len(b) else 'manual_review_required'
        audit = {'ticker':t,'source_file':m['local_path'],'sha256':m['sha256'],'start_block':s,'end_block_exclusive':e,'start_heading':b[s]['text'],'end_heading':b[e]['text'],'word_count':words,'extraction_status':status,'boundary_candidates':pairs,'footers':[(i,n) for i,n in foot if s-30<i<e+30], 'blocks':section}
        (OUT/'audit'/f'{t}.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        text='\n\n'.join(x['text'] for x in section)+'\n'
        name=f'{t}_FY2025_Item1A.txt'
        for folder in (TEXT,OUT/'item1a_text'):
            dest=folder/name
            if dest.exists() and dest.read_text(encoding='utf-8')!=text:
                # Derived extraction corrections only; source HTML is immutable.
                history=OUT/'audit'/'extraction_corrections.jsonl'
                with history.open('a',encoding='utf-8') as f:
                    f.write(json.dumps({'path':str(dest.relative_to(ROOT)),'old_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'reason':'boundary/layout QA correction'})+'\n')
            dest.write_text(text,encoding='utf-8')
        print(t,status,words,s,e,'candidates',sum(bool(AI.search(x['text'])) for x in section),'pages',audit['footers'])

if __name__ == '__main__':
    import sys
    if sys.argv[1]=='extract': extract(sys.argv[2:] or [r['ticker'] for r in read_csv(ROOT/'data/interim/samples/sample_55.csv')])
    else: inspect(sys.argv[1:])
