"""Independent local vocabulary store and word anchors. No translation API calls."""
import json,re,sqlite3,hashlib,csv,io
from pathlib import Path
from contextlib import contextmanager
import pymupdf as fitz

CATEGORIES=('미분류','일반 단어','전문 용어','고유명사','약어')
LIGATURES=str.maketrans({'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'})

def lookup_term(raw):
    term=raw.translate(LIGATURES).strip('.,;:!?()[]{}<>"“”‘’†‡*')
    term=re.sub(r'(?<=[A-Za-z])[.,]\d+(?:[,–-]\d+)*$','',term)
    term=re.sub(r'(?<=[A-Za-z])\d+(?:[,–-]\d+)+$','',term)
    return term.strip()

def extract_words(path,page,side,sentences):
    result=[]
    with fitz.open(path) as doc:
        raw_words=doc[page-1].get_text('words');index=0
        while index<len(raw_words):
            raw=raw_words[index];index+=1
            raw_text=raw[4];rects=[[round(float(v),3) for v in raw[:4]]]
            term=lookup_term(raw_text)
            if index<len(raw_words):
                following=raw_words[index]
                if re.search(r'[A-Za-z]-$',raw_text) and re.match(r'[a-z]',following[4]) and raw[5]==following[5] and raw[6]!=following[6]:
                    term=lookup_term(raw_text[:-1]+following[4])
                    raw_text+='\n'+following[4];rects.append([round(float(v),3) for v in following[:4]]);index+=1
            if not term or not re.search(r'[A-Za-z가-힣Α-Ωα-ω]',term):continue
            bbox=[min(r[0] for r in rects),min(r[1] for r in rects),max(r[2] for r in rects),max(r[3] for r in rects)]
            first=rects[0];cx,cy=(first[0]+first[2])/2,(first[1]+first[3])/2
            candidates=[s for s in sentences if any(r[0]-.5<=cx<=r[2]+.5 and r[1]-.5<=cy<=r[3]+.5 for r in s['rects'])]
            sentence=next((s for s in candidates if term in s['text'].translate(LIGATURES)),candidates[0] if candidates else None)
            ident=side+'w'+hashlib.sha256((str(page)+str(bbox)+raw_text).encode()).hexdigest()[:12]
            result.append(dict(id=ident,term=term,raw=raw_text,bbox=bbox,rects=rects,
                sentence_id=sentence['id'] if sentence else '',source_text=sentence['text'] if sentence else raw_text))
    return result

class Vocabulary:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY,term TEXT NOT NULL,term_key TEXT NOT NULL,
                general_meaning TEXT NOT NULL DEFAULT '',paper_meaning TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '미분류',notes TEXT NOT NULL DEFAULT '',
                paper_id TEXT NOT NULL,paper_title TEXT NOT NULL,source_page INTEGER NOT NULL,
                side TEXT NOT NULL,word_id TEXT NOT NULL,sentence_id TEXT NOT NULL,
                source_word TEXT NOT NULL,source_text TEXT NOT NULL,source_sha256 TEXT NOT NULL,
                search_text TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,deleted_at TEXT);
                CREATE INDEX IF NOT EXISTS vocabulary_term ON entries(term_key);
                CREATE INDEX IF NOT EXISTS vocabulary_paper ON entries(paper_id);''')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def editable(self,data):
        out={key:str(data.get(key,'')).strip() for key in ('term','general_meaning','paper_meaning','category','notes')}
        if not out['term'] or len(out['term'])>200:raise ValueError('표제어는 1~200자로 입력하세요.')
        if not out['general_meaning'] and not out['paper_meaning']:raise ValueError('일반 뜻 또는 이 논문에서의 뜻을 입력하세요.')
        if any(len(out[k])>6000 for k in ('general_meaning','paper_meaning','notes')):raise ValueError('뜻과 메모는 각각 6,000자 이내로 입력하세요.')
        if out['category'] not in CATEGORIES:raise ValueError('단어 분류를 선택하세요.')
        out['term_key']=out['term'].casefold()
        return out

    @staticmethod
    def search_text(record):
        return '\n'.join(str(record.get(k,'')) for k in ('term','general_meaning','paper_meaning','category','notes','paper_title','source_text')).casefold()

    def add(self,data,source):
        row=dict(source,**self.editable(data));row['search_text']=self.search_text(row)
        fields=('term','term_key','general_meaning','paper_meaning','category','notes','paper_id','paper_title',
                'source_page','side','word_id','sentence_id','source_word','source_text','source_sha256','search_text')
        with self.connect() as db:
            cur=db.execute('INSERT INTO entries('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',[row[k] for k in fields])
            return self._get(db,cur.lastrowid)

    def _get(self,db,ident,include_deleted=False):
        row=db.execute('SELECT * FROM entries WHERE id=?'+('' if include_deleted else ' AND deleted_at IS NULL'),(int(ident),)).fetchone()
        if row is None:raise ValueError('단어장 항목을 찾지 못했습니다.')
        return dict(row)

    def get(self,ident):
        with self.connect() as db:return self._get(db,ident)

    def update(self,ident,data):
        with self.connect() as db:
            row=dict(self._get(db,ident),**self.editable(data));row['search_text']=self.search_text(row)
            fields=('term','term_key','general_meaning','paper_meaning','category','notes','search_text')
            db.execute('UPDATE entries SET '+','.join(k+'=?' for k in fields)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',[row[k] for k in fields]+[int(ident)])
            return self._get(db,ident)

    def trash(self,ident):
        with self.connect() as db:
            self._get(db,ident)
            db.execute('UPDATE entries SET deleted_at=CURRENT_TIMESTAMP WHERE id=?',(int(ident),))

    def restore(self,ident):
        with self.connect() as db:
            self._get(db,ident,True)
            db.execute('UPDATE entries SET deleted_at=NULL WHERE id=?',(int(ident),))
            return self._get(db,ident)

    def matches(self,term,paper_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM entries WHERE deleted_at IS NULL AND term_key=? ORDER BY (paper_id=?) DESC,updated_at DESC,id DESC LIMIT 5',(term.casefold(),paper_id))]

    def listing(self,query='',paper_id='',category='',limit=500,deleted=False):
        conditions=['deleted_at IS NOT NULL' if deleted else 'deleted_at IS NULL'];params=[]
        if query:
            escaped=query.casefold().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            conditions.append("search_text LIKE ? ESCAPE '\\'");params.append('%'+escaped+'%')
        if paper_id:conditions.append('paper_id=?');params.append(paper_id)
        if category:conditions.append('category=?');params.append(category)
        where=' AND '.join(conditions)
        with self.connect() as db:
            total=db.execute('SELECT COUNT(*) FROM entries WHERE '+where,params).fetchone()[0]
            sql='SELECT * FROM entries WHERE '+where+' ORDER BY updated_at DESC,id DESC'
            rows=[dict(r) for r in db.execute(sql+(' LIMIT ?' if limit else ''),params+([limit] if limit else []))]
        return dict(entries=rows,total=total)

    def export(self,format='json'):
        records=self.listing(limit=None)['entries']
        if format=='json':return json.dumps(dict(version=1,entries=records),ensure_ascii=False,indent=2).encode('utf-8')
        if format!='csv':raise ValueError('CSV 또는 JSON을 선택하세요.')
        output=io.StringIO(newline='');writer=csv.writer(output)
        fields=('term','general_meaning','paper_meaning','category','paper_title','source_page','source_text','notes')
        writer.writerow(('단어','일반 뜻','논문에서의 뜻','분류','출처 논문','쪽','출처 문장','메모'))
        # Prevent spreadsheet formulas from user-entered values in exported CSV.
        for row in records:
            values=[str(row[k]) for k in fields]
            writer.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@')) else v for v in values])
        return output.getvalue().encode('utf-8-sig')
