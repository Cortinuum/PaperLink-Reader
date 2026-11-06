"""Offline dictionary lookup. Standard library only; no network or AI calls."""
import json,re,sqlite3,unicodedata
from pathlib import Path

def lemma_candidates(key):
    """Conservative spelling candidates; never label a guessed stem as confirmed."""
    out=[]
    def add(value):
        if len(value)>=3 and value!=key and value not in out:out.append(value)
    if key.endswith('ies'):add(key[:-3]+'y')
    if key.endswith('ves'):
        add(key[:-3]+'f');add(key[:-3]+'fe')
    if key.endswith('s') and not key.endswith(('ss','us','is')):
        add(key[:-1])
        if key.endswith(('ches','shes','xes','zes','ses')):add(key[:-2])
    for suffix in ('ing','ed','er','est'):
        if key.endswith(suffix) and len(key)>len(suffix)+3:
            stem=key[:-len(suffix)];add(stem);add(stem+'e')
            if len(stem)>2 and stem[-1]==stem[-2]:add(stem[:-1])
            if suffix in ('ed','er','est') and stem.endswith('i'):add(stem[:-1]+'y')
    if key.endswith('ly'):
        add(key[:-2])
        if key.endswith('ily'):add(key[:-3]+'y')
        if key.endswith('ally'):add(key[:-4])
    return out

class LocalDictionary:
    def __init__(self,path):
        self.path=Path(path)
        self.preferred_source='Open English-Korean Dictionary'
    def lookup(self,term,side='en'):
        term=unicodedata.normalize('NFKC',str(term)).strip()
        if len(term)>200:raise ValueError('표제어는 200자 이내로 입력하세요.')
        result=dict(term=term,entries=[],offline=True,available=self.path.is_file(),preferred_source=self.preferred_source)
        if not result['available']:
            result['message']='로컬 사전 파일을 찾지 못했습니다.';return result
        if side!='en':
            result['message']='영한사전입니다. 영어 원문의 단어를 선택하세요.';return result
        if not term:return result
        key=term.casefold().replace('’',"'").replace('ﬁ','fi').replace('ﬂ','fl')
        key=re.sub(r'(?<=[a-z])[.,]\d+(?:[,–-]\d+)*$','',key)
        key=key.strip('.,;:!?()[]{}<>"“”‘†‡*')
        key=re.sub(r'(?<=[a-z])-\s*\n\s*(?=[a-z])','',key)
        # Possessive normalization only; other forms come from the source index.
        keys=[key]
        if key.endswith("'s"):keys.append(key[:-2])
        elif key.endswith("s'"):keys.append(key[:-1])
        db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            for candidate in keys:
                rows=db.execute("SELECT e.*,l.kind FROM lookup l JOIN entries e ON e.id=l.entry_id WHERE l.term=? AND e.source!='Quick English-Korean' ORDER BY CASE WHEN source=? THEN 0 WHEN source LIKE 'Wiktionary%' THEN 1 ELSE 2 END,e.headword LIMIT 30",(candidate,'PaperLink 공학 보충')).fetchall()
                # An exact headword wins over broader synonym-index connections.
                primary=[r for r in rows if r['source'] not in ('Open English-Korean Dictionary','Quick English-Korean')]
                exact=[r for r in primary if r['kind']=='exact']
                if exact:
                    heads={r['headword'].casefold() for r in exact}
                    rows=exact+[r for r in rows if r['source'] in ('Open English-Korean Dictionary','Quick English-Korean') and r['headword'].casefold() in heads]
                elif not primary:
                    exact=[r for r in rows if r['kind']=='exact']
                    if exact:rows=exact
                if rows:
                    result['entries']=[dict(headword=r['headword'],senses=json.loads(r['senses']),source=r['source'],matched_form=r['headword'].casefold()!=key) for r in rows];break
            if not result['entries']:
                # Candidates must exist as actual headwords, not synonym-index links.
                for candidate in lemma_candidates(keys[-1]):
                    rows=db.execute("SELECT DISTINCT e.* FROM lookup l JOIN entries e ON e.id=l.entry_id WHERE l.term=? AND l.kind='exact' AND e.source!='Quick English-Korean' ORDER BY CASE WHEN source='PaperLink 공학 보충' THEN 0 WHEN source LIKE 'Wiktionary%' THEN 1 ELSE 2 END LIMIT 8",(candidate,)).fetchall()
                    if rows:
                        result['entries']=[dict(headword=r['headword'],senses=json.loads(r['senses']),source=r['source'],matched_form=True,match_method='lemma') for r in rows]
                        break
            if not result['entries'] and '-' in key:
                # Show components explicitly; do not invent a translation of a compound.
                components=[]
                for component in dict.fromkeys(key.split('-')):
                    if len(component)<3 or not component.isalpha():components=[];break
                    rows=db.execute("SELECT DISTINCT e.* FROM lookup l JOIN entries e ON e.id=l.entry_id WHERE l.term=? AND l.kind='exact' AND e.source!='Quick English-Korean' LIMIT 3",(component,)).fetchall()
                    if not rows:components=[];break
                    components.extend(dict(headword=r['headword'],senses=json.loads(r['senses']),source=r['source'],matched_form=True,match_method='component') for r in rows)
                result['entries']=components
        finally:db.close()
        if not result['entries']:result['message']='로컬 사전에 없는 단어입니다. 전문 용어·고유명사는 직접 뜻을 등록할 수 있습니다.'
        return result
