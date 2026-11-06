"""App-owned PDF pairs. Input files are copied, never changed or moved."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,shutil,sqlite3,tempfile,threading
import pymupdf as fitz

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

class PaperLibrary:
    def __init__(self,data):
        self.root=Path(data).resolve();self.files=self.root/'papers';self.files.mkdir(parents=True,exist_ok=True)
        self.db=self.root/'library.sqlite3';self.lock=threading.RLock()
        with self.connect() as db:db.execute('''CREATE TABLE IF NOT EXISTS papers(
            id TEXT PRIMARY KEY,title TEXT NOT NULL,pages INTEGER NOT NULL,
            source TEXT NOT NULL,text_source TEXT NOT NULL,korean TEXT NOT NULL,
            source_hash TEXT NOT NULL,translation_hash TEXT NOT NULL,
            original_name TEXT NOT NULL,translation_name TEXT NOT NULL,
            created TEXT DEFAULT CURRENT_TIMESTAMP)''')
        with self.connect() as db:
            columns={row['name'] for row in db.execute('PRAGMA table_info(papers)')}
            for name in ('deleted_at','replaced_by'):
                if name not in columns:db.execute('ALTER TABLE papers ADD COLUMN '+name+' TEXT')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.db,timeout=20);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
    def listing(self,deleted=False):
        with self.connect() as db:rows=db.execute('SELECT * FROM papers WHERE deleted_at IS '+('NOT NULL' if deleted else 'NULL')+' ORDER BY title COLLATE NOCASE,id').fetchall()
        return [self.record(row) for row in rows if all((self.files/row[k]).is_file() for k in ('source','text_source','korean'))]
    def get(self,pid,include_deleted=False):
        with self.connect() as db:row=db.execute('SELECT * FROM papers WHERE id=?'+('' if include_deleted else ' AND deleted_at IS NULL'),(pid,)).fetchone()
        if not row:raise ValueError('보관함에서 논문쌍을 찾지 못했습니다.')
        return self.record(row)
    def trash(self,pid):
        with self.lock,self.connect() as db:
            if not db.execute('SELECT 1 FROM papers WHERE id=? AND deleted_at IS NULL',(pid,)).fetchone():raise ValueError('보관함에서 논문쌍을 찾지 못했습니다.')
            db.execute('UPDATE papers SET deleted_at=CURRENT_TIMESTAMP,replaced_by=NULL WHERE id=?',(pid,))
    def restore(self,pid):
        with self.lock:
            paper=self.get(pid,include_deleted=True)
            if not all(Path(paper[key]).is_file() for key in ('source','text_source','korean')):raise ValueError('복원할 PDF 사본을 찾지 못했습니다.')
            with self.connect() as db:db.execute('UPDATE papers SET deleted_at=NULL,replaced_by=NULL WHERE id=?',(pid,))
            return self.get(pid)
    def record(self,row):
        result=dict(row)
        for key in ('source','text_source','korean'):result[key]=str(self.files/row[key])
        return result
    @staticmethod
    def validate(source,translation,text_source=None):
        warnings=[]
        try:
            with fitz.open(source) as en,fitz.open(translation) as ko:
                if not en.is_pdf or not ko.is_pdf:raise ValueError('PDF 파일을 선택하세요.')
                if en.needs_pass or ko.needs_pass:raise ValueError('암호가 해제된 PDF를 선택하세요.')
                if not len(en) or len(en)!=len(ko):raise ValueError('원문과 번역문의 페이지 수가 같아야 합니다. 번역문만 들어 있는 PDF를 선택하세요.')
                has_text=False
                for index in range(len(en)):
                    a,b=en[index].rect,ko[index].rect
                    if abs(a.width-b.width)>2 or abs(a.height-b.height)>2:raise ValueError(f'{index+1}쪽의 원문·번역문 크기가 다릅니다. 같은 배치의 번역 PDF를 선택하세요.')
                    if not has_text and en[index].get_text().strip():has_text=True
                if not has_text:warnings.append('선택 가능한 원문 텍스트가 없습니다. PDF 보기는 가능하며 단어·문장 선택에는 OCR 처리가 필요합니다.')
                pages=len(en)
            if text_source:
                with fitz.open(text_source) as prepared:
                    if not prepared.is_pdf or prepared.needs_pass or len(prepared)!=pages:raise ValueError('텍스트 추출용 PDF의 페이지 수를 확인하세요.')
        except (fitz.FileDataError,fitz.EmptyFileError,RuntimeError) as exc:
            raise ValueError('PDF를 열 수 없습니다. 손상되지 않은 PDF 파일을 선택하세요.') from exc
        return pages,warnings
    def register(self,source,translation,title='',text_source=None,original_name=None,translation_name=None):
        source,translation=Path(source),Path(translation)
        pages,warnings=self.validate(source,translation,text_source)
        sh,th=digest(source),digest(translation);pid=sh[:12]+'-'+th[:10]
        title=(title.strip() or source.stem)[:200]
        with self.lock:
            with self.connect() as db:
                existing=db.execute('SELECT * FROM papers WHERE id=?',(pid,)).fetchone()
                if existing and all((self.files/existing[k]).is_file() for k in ('source','text_source','korean')):
                    restored=existing['deleted_at'] is not None
                    if restored:
                        db.execute('UPDATE papers SET deleted_at=NULL,replaced_by=NULL WHERE id=?',(pid,))
                        existing=db.execute('SELECT * FROM papers WHERE id=?',(pid,)).fetchone()
                    return dict(paper=self.record(existing),duplicate=True,restored=restored,warnings=warnings)
            target=(self.files/pid).resolve()
            if not target.is_relative_to(self.files):raise ValueError('잘못된 보관 위치입니다.')
            if target.exists():raise ValueError('기존 보관 파일을 확인해야 합니다. 파일을 덮어쓰지 않았습니다.')
            with tempfile.TemporaryDirectory(prefix='import-',dir=self.files) as temp:
                staging=Path(temp)/'pair';staging.mkdir()
                shutil.copyfile(source,staging/'original.pdf');shutil.copyfile(translation,staging/'translation.pdf')
                text_file='text_source.pdf' if text_source else 'original.pdf'
                if text_source:shutil.copyfile(text_source,staging/text_file)
                staging.rename(target)
            values=dict(id=pid,title=title,pages=pages,source=pid+'/original.pdf',korean=pid+'/translation.pdf',
                text_source=pid+'/'+text_file,source_hash=sh,translation_hash=th,
                original_name=original_name or source.name,translation_name=translation_name or translation.name)
            with self.connect() as db:
                columns=list(values)
                db.execute('INSERT INTO papers('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[values[k] for k in columns])
                row=db.execute('SELECT * FROM papers WHERE id=?',(pid,)).fetchone()
            return dict(paper=self.record(row),duplicate=False,warnings=warnings)
    def import_upload(self,files,title=''):
        with tempfile.TemporaryDirectory(prefix='upload-',dir=self.files) as temp:
            paths={}
            for key in ('source','translation'):
                if key not in files:raise ValueError('원문 PDF와 번역 PDF를 모두 선택하세요.')
                name,content=files[key];paths[key]=Path(temp)/(key+'.pdf');paths[key].write_bytes(content)
            return self.register(paths['source'],paths['translation'],title or Path(files['source'][0]).stem,
                original_name=files['source'][0],translation_name=files['translation'][0])
    def replace_upload(self,pid,files,title=''):
        with self.lock:
            old=self.get(pid)
            with tempfile.TemporaryDirectory(prefix='replace-',dir=self.files) as temp:
                paths={}
                for key,column in (('source','source'),('translation','korean')):
                    if key in files:
                        paths[key]=Path(temp)/(key+'.pdf');paths[key].write_bytes(files[key][1])
                    else:paths[key]=Path(old[column])
                # Keep a prepared text layer when the original PDF content is unchanged.
                prepared=old['text_source'] if digest(paths['source'])==old['source_hash'] else None
                result=self.register(paths['source'],paths['translation'],title.strip() or old['title'],text_source=prepared,
                    original_name=files['source'][0] if 'source' in files else old['original_name'],
                    translation_name=files['translation'][0] if 'translation' in files else old['translation_name'])
            new_id=result['paper']['id']
            with self.connect() as db:
                if new_id==pid:
                    new_title=title.strip() or old['title']
                    db.execute('UPDATE papers SET title=? WHERE id=?',(new_title[:200],pid))
                else:
                    db.execute('UPDATE papers SET deleted_at=CURRENT_TIMESTAMP,replaced_by=? WHERE id=?',(new_id,pid))
            result.update(paper=self.get(new_id),changed=new_id!=pid,previous_id=pid,title_updated=(new_id==pid and (title.strip() or old['title'])!=old['title']))
            return result

def migrate_legacy(folder,library):
    """Explicit one-time migration; the running reader never scans PDF2zh folders."""
    results=[]
    for status in sorted(Path(folder).glob('OpenAI_full_*/status.json')):
        try:
            job=json.loads(status.read_text(encoding='utf-8-sig'));source=Path(job['source'])
            translated=list(status.parent.glob('*.mono.pdf'));prepared=list(status.parent.glob('*_prepared.pdf'))
            if not source.is_file() or len(translated)!=1:continue
            result=library.register(source,translated[0],source.stem,text_source=prepared[0] if prepared else None)
            results.append(dict(id=result['paper']['id'],title=result['paper']['title'],duplicate=result['duplicate']))
        except (OSError,ValueError,KeyError,RuntimeError) as exc:results.append(dict(title=status.parent.name,error=str(exc)))
    return results
