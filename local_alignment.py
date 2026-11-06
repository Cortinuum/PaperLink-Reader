"""Conservative local alignment: document regions, anchors and path ambiguity.

Scores express agreement between rules, never a probability of semantic accuracy.
No network access, ML models, PDF edits or paper-specific IDs are used here.
"""
import math,re,statistics,unicodedata
from collections import defaultdict,Counter
from functools import lru_cache

REGION_LABELS={'content':'본문','figure-caption':'그림 설명','table-caption':'표 설명',
               'heading':'제목','footnote':'각주','header':'머리말','footer':'꼬리말','margin':'여백 정보'}
CAPTION=re.compile(r'^(?:Fig(?:ure)?s?\.?|Table|그림|표)\s*(S?\d+)',re.I)
REF=re.compile(r'(Fig(?:ure)?s?\.?|Table|Eq(?:uation)?s?\.?|그림|표|수식|식)\s*\(?\s*(S?\d+(?:[a-z])?)',re.I)
MEASURE=re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(wt\s*%|MPa|GPa|kPa|mPa|mm|μm|µm|um|nm|cm|mg|kg|mL|ml|°\s*C|℃|%|Hz|kHz|MHz|eV|mV|V|K)(?![A-Za-z])|(?<![\w.])(\d+(?:\.\d+)?)\s*(%)')

def clean(text):return unicodedata.normalize('NFKC',text).replace('µ','μ')
@lru_cache(maxsize=8192)
def features(text):
    text=clean(text)
    refs=set()
    for kind,num in REF.findall(text):
        kind=kind.lower();family='fig' if kind.startswith('fig') or kind=='그림' else 'table' if kind in ('table','표') else 'eq'
        refs.add(family+':'+num.lower())
    measures=set()
    for number,unit,percent,punit in MEASURE.findall(text):
        number=number or percent;unit=unit or punit
        measures.add((str(float(number)),re.sub(r'\s','',unit).replace('um','μm')))
    numbers=set(re.findall(r'\d+(?:\.\d+)?',text))
    return dict(refs=refs,measures=measures,numbers=numbers)

def classify(items,size):
    width,height=size
    samples=[s.get('font_size',0) for s in items if s.get('layout_role','content')=='content' and len(s['text'])>80 and s.get('font_size',0)>0]
    baseline=statistics.median(samples) if samples else 0
    flows=defaultdict(list)
    for s in items:flows[tuple(s.get('flow_bbox',s['bbox']))].append(s)
    for box,group in flows.items():
        first=min(group,key=lambda s:s.get('offset',0));text=clean(first['text']).strip()
        role=first.get('layout_role','content');key=role
        font=first.get('font_size',baseline)
        if role=='content':
            cap=CAPTION.match(text)
            wide=box[2]-box[0]>width*.68
            # A body paragraph beginning "Fig. 2 shows ..." is not a caption
            # merely because it cites a figure. Require typography or spanning flow.
            if cap and (wide or (baseline and font<baseline*.96)):
                role='table-caption' if re.match(r'^(?:Table|표)',text,re.I) else 'figure-caption'
                key=role+':'+cap.group(1).lower()
            elif baseline and font<baseline*.86 and box[1]>height*.65 and re.match(r'^[†‡*\d]',text):role=key='footnote'
            elif baseline and font>baseline*1.12 and len(' '.join(s['text'] for s in group))<150 and not re.search(r'[.!?。！？]$',text):role=key='heading'
        for s in group:
            s['region_type']=role;s['region_key']=key;s['region_label']=REGION_LABELS[role]


def anchor_keys(s):
    f=features(s['text']);keys={('ref',x) for x in f['refs']}|{('measure',x) for x in f['measures']}
    if len(f['numbers'])>=2:keys.add(('numbers',tuple(sorted(f['numbers']))))
    return keys

def anchors(source,target):
    left=defaultdict(list);right=defaultdict(list)
    for i,s in enumerate(source):
        for key in anchor_keys(s):left[key].append(i)
    for j,s in enumerate(target):
        for key in anchor_keys(s):right[key].append(j)
    choices=defaultdict(set)
    for key,indices in left.items():
        if len(indices)==1 and len(right.get(key,[]))==1:choices[indices[0]].add(right[key][0])
    pairs=sorted((i,next(iter(js))) for i,js in choices.items() if len(js)==1)
    # Discard mutually contradictory anchors, then find an increasing chain.
    counts=Counter(j for i,j in pairs);pairs=[(i,j) for i,j in pairs if counts[j]==1]
    if not pairs:return []
    paths=[]
    for i,pair in enumerate(pairs):
        previous=max((paths[k] for k in range(i) if pairs[k][1]<pair[1]),key=len,default=[])
        paths.append(previous+[pair])
    return max(paths,key=len)


def match_cost(source,target,ratio,size):
    en=' '.join(s['text'] for s in source);ko=' '.join(s['text'] for s in target)
    x,y=features(en),features(ko)
    korean=sum('가'<=c<='힣' for c in ko)>=5
    scale=ratio if korean else 1
    length=abs(math.log((len(en)+8)/(scale*len(ko)+8)))
    a,b=x['numbers'],y['numbers'];numeric=1-len(a&b)/len(a|b) if a or b else 0
    lexical=0
    if not korean:
        a=set(re.findall(r'[a-z]{2,}',clean(en).lower()));b=set(re.findall(r'[a-z]{2,}',clean(ko).lower()))
        lexical=1-len(a&b)/max(1,len(a|b))
    width,height=size
    a=source[0]['bbox'];b=target[0]['bbox']
    distance=(abs((a[0]+a[2]-b[0]-b[2])/2)/width+abs((a[1]+a[3]-b[1]-b[3])/2)/height)
    reasons=[]
    if length>1.25:reasons.append('문장 길이 비율 차이가 큼')
    if x['refs'] and y['refs'] and not x['refs']&y['refs']:reasons.append('그림·표·수식 번호가 충돌함')
    units={unit for n,unit in x['measures']}&{unit for n,unit in y['measures']}
    if any({n for n,u in x['measures'] if u==unit}.isdisjoint({n for n,u in y['measures'] if u==unit}) for unit in units):reasons.append('동일 단위의 수치가 충돌함')
    if distance>.36:reasons.append('문서 안의 위치 차이가 큼')
    if len(target)>1 and len({re.sub(r'\W','',clean(s['text'])) for s in target})<len(target):reasons.append('동일한 번역문이 반복되어 후보 구분이 어려움')
    return length+numeric*.8+lexical*1.4+distance*.8+(len(source)+len(target)-2)*.4,reasons


def interval(source,target,size,ratio):
    """Forward/backward costs expose the best competing path for each sentence."""
    n,m=len(source),len(target);edges=defaultdict(list);forward={(0,0):0};previous={}
    for i in range(n+1):
        for j in range(m+1):
            if (i,j) not in forward:continue
            for a,b in ((1,1),(1,2),(2,1),(1,3),(3,1),(1,0),(0,1)):
                if i+a>n or j+b>m:continue
                cost,reasons=(2.2,[]) if not a or not b else match_cost(source[i:i+a],target[j:j+b],ratio,size)
                edge=((i+a,j+b),cost,reasons,a,b);edges[i,j].append(edge)
                value=forward[i,j]+cost
                if value<forward.get((i+a,j+b),math.inf):forward[i+a,j+b]=value;previous[i+a,j+b]=((i,j),edge)
    backward={(n,m):0}
    for i in range(n,-1,-1):
        for j in range(m,-1,-1):
            for dest,cost,*_ in edges[i,j]:backward[i,j]=min(backward.get((i,j),math.inf),cost+backward.get(dest,math.inf))
    candidates=defaultdict(dict)
    for (i,j),choices in edges.items():
        for dest,cost,reasons,a,b in choices:
            if not a:continue
            ids=tuple(s['id'] for s in target[j:j+b]);total=forward[i,j]+cost+backward.get(dest,math.inf)
            for index in range(i,i+a):
                old=candidates[index].get(ids)
                if old is None or total<old[0]:candidates[index][ids]=(total,reasons)
    out={};cursor=(n,m)
    while cursor!=(0,0):
        (i,j),edge=previous[cursor];dest,cost,reasons,a,b=edge
        ids=[s['id'] for s in target[j:j+b]]
        for index in range(i,i+a):
            alternatives=sorted(candidates[index].items(),key=lambda pair:pair[1][0])
            competing=min((v[0] for keys,v in alternatives if list(keys)!=ids),default=math.inf)
            margin=competing-forward[n,m]
            why=list(reasons)
            if margin<.22:why.append('다른 후보와 규칙 일치도가 비슷함')
            if not ids:why.append('대응 번역문을 찾지 못함')
            severe=any('충돌' in r or '길이' in r for r in why) or any('반복' in r for r in why) or (margin<.10 and bool(ids))
            proposed=[list(keys) for keys,v in alternatives if keys][:3]
            out[source[index]['id']]=dict(targets=[] if severe else ids,candidates=proposed,
                review_reasons=why,evidence=[],status='unlinked' if severe or not ids else 'needs-review' if why else 'candidate')
        cursor=(i,j)
    return out


def group_align(source,target,size,manual):
    out={};si={s['id']:i for i,s in enumerate(source)};ti={s['id']:i for i,s in enumerate(target)}
    ratio=max(.7,min(3.5,sum(len(s['text']) for s in source)/max(1,sum(len(s['text']) for s in target))))
    # Manual links form hard fences. Crossed or overlapping fences reserve a
    # rectangle; unresolved automatic sentences inside it are left for review.
    blocks=[]
    for id,ids in manual.items():
        if id in si and ids and all(t in ti for t in ids):blocks.append([si[id],si[id],min(ti[t] for t in ids),max(ti[t] for t in ids)])
    merged=[]
    for block in sorted(blocks):
        merged.append(block)
        while len(merged)>1 and merged[-1][2]<=merged[-2][3]:
            b=merged.pop();a=merged.pop()
            merged.append([a[0],b[1],min(a[2],b[2]),max(a[3],b[3])])
    used={t for ids in manual.values() for t in ids}
    def run(a,b,c,d):
        en=[s for s in source[a:b] if s['id'] not in manual];ko=[s for s in target[c:d] if s['id'] not in used]
        points=anchors(en,ko);i=j=0
        for x,y in points+[(len(en),len(ko))]:
            out.update(interval(en[i:x],ko[j:y],size,ratio))
            if x<len(en):
                cost,reasons=match_cost([en[x]],[ko[y]],ratio,size)
                if reasons:
                    out.update(interval([en[x]],[ko[y]],size,ratio))
                else:out[en[x]['id']]=dict(targets=[ko[y]['id']],candidates=[[ko[y]['id']]],review_reasons=[],evidence=['구간 내 고유 번호·수치 기준점'],status='candidate')
            i=x+1;j=y+1
    a=c=0
    for lo,hi,left,right in merged:
        run(a,lo,c,left)
        for s in source[lo:hi+1]:
            if s['id'] not in manual:out[s['id']]=dict(targets=[],candidates=[],review_reasons=['수동 연결 범위가 겹치거나 순서가 교차함'],evidence=[],status='unlinked')
        a=hi+1;c=right+1
    run(a,len(source),c,len(target))
    return out


def align(source,target,size,manual=None):
    manual=manual or {};classify(source,size);classify(target,size)
    source_ids={s['id'] for s in source};target_ids={s['id'] for s in target}
    manual={s:[t for t in ids if t in target_ids] for s,ids in manual.items() if s in source_ids}
    out={}
    for key in dict.fromkeys(s['region_key'] for s in source):
        en=[s for s in source if s['region_key']==key];ko=[s for s in target if s['region_key']==key]
        if en[0]['region_type'] in ('header','footer','margin','heading'):
            available=[s for s in ko if s['id'] not in {t for ids in manual.values() for t in ids}]
            for s in en:
                if s['id'] in manual:continue
                if not available:continue
                a=s['bbox'];t=min(available,key=lambda t:sum(abs(a[i]+a[i+2]-t['bbox'][i]-t['bbox'][i+2]) for i in (0,1))+40*abs(s.get('font_size',0)-t.get('font_size',0)))
                distance=(abs(a[0]+a[2]-t['bbox'][0]-t['bbox'][2])/size[0]+abs(a[1]+a[3]-t['bbox'][1]-t['bbox'][3])/size[1])/2
                if distance>.30:
                    out[s['id']]=dict(targets=[],candidates=[[t['id']]],review_reasons=['같은 영역의 후보 위치가 너무 멂'],evidence=[],status='unlinked');continue
                available.remove(t);out[s['id']]=dict(targets=[t['id']],candidates=[[t['id']]],review_reasons=[],evidence=['같은 영역의 위치·글자 크기'],status='candidate')
        else:out.update(group_align(en,ko,size,manual))
    result=[]
    for s in source:
        record=dict(source=s['id'],method='local-rules',review=True,region_type=s['region_type'],region_label=s['region_label'])
        record.update(out.get(s['id'],dict(targets=[],candidates=[],review_reasons=['같은 문서 영역의 대응 후보가 없음'],evidence=[],status='unlinked')))
        if s['id'] in manual:record.update(targets=manual[s['id']],candidates=[],review_reasons=[],evidence=['사용자가 직접 지정한 고정 연결'],status='manual',method='manual',review=False)
        result.append(record)
    return result
