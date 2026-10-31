"""Structural page mapping: literal printed labels within actual HTML pages."""
import json
import re
from collections import defaultdict
from lxml import html
from .item1a_review import ROOT, OUT, blocks, read_csv


def page_map(path, b):
    root = html.fromstring(path.read_bytes(), parser=html.HTMLParser(encoding='utf-8'))
    tree = root.getroottree()
    keys, key, serial = {}, 'flow:0', 0
    elements = {tree.getpath(el):el for el in root.iter()}
    for el in root.iter():
        style = (el.get('style') or '').replace(' ','').lower()
        if ('page-break-before:always' in style or ('page-break-after:always' in style and not el.text_content().strip())):
            serial += 1
            key = f'flow:{serial}'
        container = next((a for a in [el]+list(el.iterancestors()) if re.fullmatch(r'Page\d+',a.get('id') or '') or ('height:792pt' in (a.get('style') or '') and 'overflow:hidden' in (a.get('style') or ''))),None)
        keys[tree.getpath(el)] = tree.getpath(container) if container is not None else key
    groups = defaultdict(list)
    for x in b: groups[keys[x['xpath']]].append(x)
    labels = {}
    for k,group in groups.items():
        candidates=[]
        for x in group:
            txt=x['text']
            patterns=[r'^(\d{1,3})$',r'^Page\s+(\d{1,3})$',r'^.*(?:Form 10-K|FORM 10-K)\s*\|\s*(\d{1,3})$',r'^(\d{1,3})\s*\|\s*(?:20\d{2} Annual Report|CLF 20\d{2} FORM 10-K)$']
            match=next((m for pat in patterns if (m:=re.fullmatch(pat,txt))),None)
            if not match: continue
            el=elements[x['xpath']]
            ancestors=[el]+list(el.iterancestors())
            styles=';'.join(a.get('style') or '' for a in ancestors).replace(' ','').lower()
            footer=('bottom:0' in styles or 'top:729pt' in styles or 'top:1023px' in styles)
            explicit=not txt.isdigit()
            # Only a literal page label with page layout evidence is accepted.
            if footer or explicit or ('text-align:center' in styles or 'padding-left:216pt' in styles):
                candidates.append({'printed_page':int(match.group(1)),'label':txt,'label_xpath':x['xpath'],'block':x['block'],'layout_evidence':'footer_container' if footer else 'explicit_label' if explicit else 'positioned_number'})
        strong=[c for c in candidates if c['layout_evidence'] in ('footer_container','explicit_label')]
        selected=strong or candidates
        if len(selected)==1: labels[k]=selected[0]
    mapped={}
    for x in b:
        k=keys[x['xpath']]
        label=labels.get(k)
        mapped[x['block']]={'page_container':k,'printed_page':label['printed_page'] if label else None,'page_label_xpath':label['label_xpath'] if label else None,'label':label['label'] if label else None,'layout_evidence':label['layout_evidence'] if label else None}
    return root,mapped


def audit_all(tickers=None):
    (OUT/'page_maps').mkdir(exist_ok=True)
    rows=[]
    for row in read_csv(ROOT/'data/interim/samples/sample_55.csv'):
        t=row['ticker']
        if tickers and t not in tickers: continue
        audit=json.loads((OUT/'audit'/f'{t}.json').read_text(encoding='utf-8'))
        b=blocks(ROOT/audit['source_file'])
        root,mapped=page_map(ROOT/audit['source_file'],b)
        start=audit['start_block']; end=audit['end_block_exclusive']
        selected={str(i):mapped[i] for i in range(start,end)}
        # Independent TOC anchor validation near the actual body heading.
        anchors=[]
        for link in root.xpath('//a[starts-with(@href,"#")]'):
            txt=' '.join(link.text_content().split())
            if re.search(r'risk\s*factors',txt,re.I):
                target=link.get('href')[1:]
                found=root.xpath('//*[@id=$target or @name=$target]',target=target)
                if found:
                    anchors.append({'toc_text':txt,'target':target,'target_xpath':root.getroottree().getpath(found[0])})
        data={'ticker':t,'page_number_type':'printed','mapping_method':'literal printed label in the same explicit HTML page segment/container; no interpolation','start':mapped[start],'last':mapped[end-1],'toc_targets':anchors,'blocks':selected}
        (OUT/'page_maps'/f'{t}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        missing=sum(v['printed_page'] is None for v in selected.values())
        rows.append({'ticker':t,'start_block':start,'end_block_exclusive':end,'start_heading':audit['start_heading'],'end_heading':audit['end_heading'],'word_count':audit['word_count'],'mapped_blocks':len(selected)-missing,'total_blocks':len(selected),'start_page':mapped[start]['printed_page'],'last_page':mapped[end-1]['printed_page'],'toc_targets':len(anchors)})
        print(t,audit['word_count'],'pages',mapped[start]['printed_page'],mapped[end-1]['printed_page'],'mapped',len(selected)-missing,'/',len(selected),'toc',len(anchors))
    dest=OUT/'audit'/'structural_validation.json'
    if tickers and dest.exists():
        previous=json.loads(dest.read_text(encoding='utf-8'))
        updates={r['ticker']:r for r in rows}
        rows=[updates.get(r['ticker'],r) for r in previous]
    dest.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    import sys
    audit_all(sys.argv[1:])
