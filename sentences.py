"""Local sentence segmentation and character-level PDF anchors; no API calls."""
import re, hashlib, math
from collections import defaultdict
import pymupdf as fitz

def spans(text):
    """Keep decimals, common scientific abbreviations and trailing citations intact."""
    start=0
    for m in re.finditer(r'[.!?。！？]',text):
        i=m.start(); mark=m.group()
        if mark=='.':
            if i and i+1<len(text) and text[i-1].isdigit() and text[i+1].isdigit(): continue
            before=text[:i+1]
            if re.search(r'\b(?:Fig|Figs|Eq|Eqs|Ref|Refs|Dr|Mr|Mrs|Prof|vs|al|e\.g|i\.e)\.$',before,re.I): continue
            if re.search(r'\b[A-Z]\.$',before): continue
            if i+1<len(text) and text[i+1].isalpha() and text[i+1].isascii(): continue
        end=i+1
        citation=re.match(r'\d+(?:[,–−-]\d+)*',text[end:])
        if citation: end+=len(citation.group())
        rest=text[end:]
        if rest and not re.match(r'\s|[가-힣]',rest): continue
        a=start
        while a<end and text[a].isspace(): a+=1
        if a<end: yield a,end
        start=end
    while start<len(text) and text[start].isspace(): start+=1
    if start<len(text): yield start,len(text)

def normalize(chars):
    raw=''.join(c[0] for c in chars)
    removed=set()
    for m in re.finditer(r'(?<=[A-Za-z])-\s*\n\s*(?=[a-z])',raw): removed.update(range(m.start(),m.end()))
    kept=[c for i,c in enumerate(chars) if i not in removed]
    result=[];pending=None
    for c in kept:
        if c[0].isspace():
            if result: pending=(' ',None,None)
        else:
            if pending:result.append(pending);pending=None
            result.append(c)
    return result

def extract(path,page,side,parents):
    with fitz.open(path) as doc:
        raw=doc[page-1].get_text('rawdict')
        items=[]
        pieces=[]
        page_width=doc[page-1].rect.width
        for block in raw['blocks']:
            if block['type']!=0:continue
            run=[];previous=None
            for line in block['lines']:
                if not line['spans']:continue
                box=line['bbox'];size=line['spans'][0]['size']
                center=(box[0]+box[2])/2
                column=0 if box[2]-box[0]>page_width*.7 else 1 if center<page_width/2 else 2
                if previous and column!=previous[0] and abs(box[0]-previous[2])>page_width*.18:
                    pieces.append((run,block['bbox']));run=[]
                run.append(line);previous=(column,size,box[0])
            if run:pieces.append((run,block['bbox']))
        for lines,parent_bbox in pieces:
            bounds=[l['bbox'] for l in lines]
            b=dict(type=0,lines=lines,bbox=[min(r[0] for r in bounds),min(r[1] for r in bounds),max(r[2] for r in bounds),max(r[3] for r in bounds)])
            if b['type']!=0:continue
            lines=[l for l in b['lines'] if l['spans']]
            if not lines:continue
            parent=min(parents,key=lambda p:sum(abs(a-z) for a,z in zip(p['bbox'],parent_bbox)))['id']
            chars=[];sizes=[]
            for li,line in enumerate(lines):
                if chars:chars.append(('\n',None,None))
                for span in line['spans']:
                    sizes.append(span['size'])
                    for c in span['chars']:chars.append((c['c'],list(c['bbox']),(parent,li)))
            items.append(dict(chars=chars,bbox=list(b['bbox']),parents=[parent],
                              lines=len(lines),size=sum(sizes)/max(1,len(sizes))))
        # Rejoin fragmented text lines in the same column before sentence splitting.
        items.sort(key=lambda b:(round(b['bbox'][0]/8),b['bbox'][1]))
        groups=[]
        for item in items:
            previous=groups[-1] if groups else None
            join=False
            if previous:
                a,z=previous['last'],item
                gap=z['bbox'][1]-a['bbox'][3]
                previous_text=''.join(c[0] for c in a['chars']).rstrip()
                join=(abs(a['bbox'][0]-z['bbox'][0])<5 and -2<=gap<max(5,a['size']*.85)
                    and abs(a['size']-z['size'])<1 and (a['lines']==1 or z['lines']==1 or
                        not re.search(r'[.!?。！？](?:\d+(?:[,–-]\d+)*)?$',previous_text))
                    and a['bbox'][2]-a['bbox'][0]>50)
            if join:
                previous['chars']+=[('\n',None,None)]+item['chars']
                previous['parents']+=item['parents'];previous['last']=item
            else:groups.append(dict(chars=item['chars'][:],parents=item['parents'][:],last=item))
        result=[]
        for group in groups:
            mapped=normalize(group['chars']);text=''.join(c[0] for c in mapped)
            all_boxes=[c[1] for c in mapped if c[1] is not None]
            flow_box=[min(r[0] for r in all_boxes),min(r[1] for r in all_boxes),max(r[2] for r in all_boxes),max(r[3] for r in all_boxes)] if all_boxes else [0,0,0,0]
            for a,z in spans(text):
                snippet=text[a:z];rects={};pids=[]
                for _,bbox,line in mapped[a:z]:
                    if bbox is None:continue
                    if line[0] not in pids:pids.append(line[0])
                    if line not in rects:rects[line]=bbox[:]
                    else:
                        r=rects[line];r[:]=[min(r[0],bbox[0]),min(r[1],bbox[1]),max(r[2],bbox[2]),max(r[3],bbox[3])]
                boxes=[[round(v,3) for v in r] for r in rects.values()]
                if not boxes:continue
                ident=side+'s'+hashlib.sha256((str(page)+str(boxes)+snippet).encode()).hexdigest()[:12]
                result.append(dict(id=ident,text=snippet,rects=boxes,parents=pids,flow_parents=list(dict.fromkeys(group['parents'])),
                    flow_bbox=flow_box,offset=a,
                    bbox=[min(r[0] for r in boxes),min(r[1] for r in boxes),max(r[2] for r in boxes),max(r[3] for r in boxes)]))
        w=doc[page-1].rect.width
        h=doc[page-1].rect.height
        return reading_order(result,w,h)


def reading_order(items,width,height):
    """Read columns between full-width text bands, including figure captions.

    Use the containing text flow rather than individual sentence width: a short
    caption sentence still belongs to the same spanning caption as its neighbours.
    IDs/character anchors are unchanged so saved links and notes remain valid.
    """
    for s in items:
        b=s['flow_bbox']
        s['layout_role']=('margin' if b[2]<width*.05 or b[0]>width*.96 else
                          'header' if b[1]<height*.045 else
                          'footer' if b[1]>height*.94 else 'content')
    bands=[]
    boxes=sorted({tuple(s['flow_bbox']) for s in items
                  if s['flow_bbox'][2]-s['flow_bbox'][0]>width*.68
                  and s['flow_bbox'][0]<width*.4 and s['flow_bbox'][2]>width*.6})
    for box in sorted(boxes,key=lambda b:b[1]):
        if bands and box[1]<=bands[-1][1]+2:
            bands[-1][1]=max(bands[-1][1],box[3])
        else:bands.append([box[1],box[3]])
    def order(s):
        b=s['flow_bbox'];x=(b[0]+b[2])/2
        # Sideways publishing notices and page furniture must not interrupt prose.
        if b[2]<width*.05 or b[0]>width*.96:return (-1,b[1],b[0],s['offset'])
        if b[1]<height*.045:return (-2,b[1],b[0],s['offset'])
        if b[1]>height*.94:return (2*len(bands)+2,b[0],b[1],s['offset'])
        spanning=b[2]-b[0]>width*.68 and b[0]<width*.4 and b[2]>width*.6
        if spanning:
            index=next(i for i,(top,bottom) in enumerate(bands) if top-2<=b[1]<=bottom)
            return (2*index+1,0,b[1],s['offset'])
        segment=sum(bottom<=b[1]+2 for top,bottom in bands)
        return (2*segment,0 if x<width/2 else 1,b[1],s['offset'])
    return sorted(items,key=order)

def monotonic(source,target):
    """Ordered 1:1 / 1:many candidates using lengths and numeric anchors, not semantics."""
    n,m=len(source),len(target)
    if not n or not m:return {}
    ratio=sum(len(s['text']) for s in source)/max(1,sum(len(s['text']) for s in target))
    dp={(0,0):(0,None)}
    for i in range(n+1):
        for j in range(m+1):
            if (i,j) not in dp:continue
            for a,b in ((1,1),(1,2),(2,1),(1,3),(3,1),(1,0),(0,1)):
                if i+a>n or j+b>m:continue
                if not a or not b:cost=2.5
                else:
                    en=' '.join(s['text'] for s in source[i:i+a]);ko=' '.join(s['text'] for s in target[j:j+b])
                    x=set(re.findall(r'\d+(?:\.\d+)?',en));y=set(re.findall(r'\d+(?:\.\d+)?',ko))
                    num=1-len(x&y)/max(1,len(x|y)) if x or y else 0
                    if sum('가'<=c<='힣' for c in ko)<5:
                        xwords=set(re.findall(r'[a-z]{2,}',en.lower()));ywords=set(re.findall(r'[a-z]{2,}',ko.lower()))
                        lexical=1-len(xwords&ywords)/max(1,len(xwords|ywords))
                        cost=abs(math.log((len(en)+8)/(len(ko)+8)))+lexical*1.5+num*.9+(a+b-2)*.4
                    else:cost=abs(math.log((len(en)+8)/(ratio*len(ko)+8)))+num*.9+(a+b-2)*.4
                value=dp[i,j][0]+cost;dest=(i+a,j+b)
                if dest not in dp or value<dp[dest][0]:dp[dest]=(value,(i,j))
    mapped=defaultdict(list);cursor=(n,m)
    while cursor!=(0,0):
        prev=dp[cursor][1];i,j=prev;a,b=cursor[0]-i,cursor[1]-j
        for s in source[i:i+a]:mapped[s['id']]+=[t['id'] for t in target[j:j+b]]
        cursor=prev
    return dict(mapped)

def align(en,ko,paragraph_links):
    # PDF text blocks may accidentally combine a right-column paragraph and a left
    # footnote. Align the reconstructed page reading order, not those merged boxes.
    # Running headers/footers and rotated margin notices can be emitted in a
    # different order by the two PDFs. Do not let them shift the body alignment.
    mapped=monotonic([s for s in en if s.get('layout_role','content')=='content'],
                     [s for s in ko if s.get('layout_role','content')=='content'])
    for role in ('header','footer','margin'):
        available=[s for s in ko if s.get('layout_role')==role]
        for s in (s for s in en if s.get('layout_role')==role):
            if not available:mapped[s['id']]=[];continue
            a=s['bbox']
            target=min(available,key=lambda t:sum(abs(a[i]+a[i+2]-t['bbox'][i]-t['bbox'][i+2]) for i in (0,1)))
            mapped[s['id']]=[target['id']];available.remove(target)
    return [dict(source=s['id'],targets=mapped.get(s['id'],[]),method='sentence-order',review=True) for s in en]
