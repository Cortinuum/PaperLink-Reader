"""Convert the pinned, unmodified StarDict data archive into a local search index.

No upstream code is executed. Original archive and notices remain in dictionary/sources.
"""
from pathlib import Path
from html.parser import HTMLParser
import gzip,hashlib,json,re,sqlite3,struct,zipfile

ROOT=Path(__file__).resolve().parent/'dictionary'
ARCHIVE=ROOT/'sources/en-ko-v1.3.0.zip'

class Senses(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.bold=False;self.italic=False
        self.buffer=[];self.pos='';self.entries=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('b','i'):self.buffer=[];self.bold=tag=='b';self.italic=tag=='i'
    def handle_data(self,data):
        if self.bold or self.italic:self.buffer.append(data)
    def handle_endtag(self,tag):
        text=''.join(self.buffer).strip()
        if tag=='i' and self.italic:
            if text in ('n.','v.','adj.','adv.','prep.','pron.','conj.','interj.','num.','det.','phr.'):
                self.pos=text
            self.italic=False
        if tag=='b' and self.bold:
            if re.search('[가-힣]',text):self.entries.append(dict(pos=self.pos,meaning=text))
            self.bold=False

def build():
    ROOT.mkdir(exist_ok=True)
    dbpath=ROOT/'english_korean.sqlite3'
    temp=ROOT/'english_korean.build.tmp'
    if temp.exists():temp.unlink()
    db=sqlite3.connect(temp)
    db.executescript('CREATE TABLE entries(id INTEGER PRIMARY KEY,headword TEXT,senses TEXT,source TEXT);'
        'CREATE TABLE lookup(term TEXT,entry_id INTEGER,kind TEXT,UNIQUE(term,entry_id));'
        'CREATE INDEX lookup_term ON lookup(term);CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);')
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in ('LICENSE','ATTRIBUTION','README.txt','en-ko.ifo'):
            (ROOT/'sources'/name).write_bytes(archive.read('en-ko/'+name))
        idx=archive.read('en-ko/en-ko.idx');body=gzip.decompress(archive.read('en-ko/en-ko.dict.dz'))
        entries=[];cursor=0;loaded=0
        while cursor<len(idx):
            end=idx.index(b'\0',cursor);word=idx[cursor:end].decode('utf8')
            offset,size=struct.unpack('>II',idx[end+1:end+9]);cursor=end+9
            parser=Senses();parser.feed(body[offset:offset+size].decode('utf8'))
            if parser.entries:
                ident=db.execute('INSERT INTO entries(headword,senses,source) VALUES(?,?,?)',
                    (word,json.dumps(parser.entries,ensure_ascii=False),'Wiktionary / koreader-dicts')).lastrowid
                db.execute('INSERT OR IGNORE INTO lookup VALUES(?,?,?)',(word.casefold(),ident,'exact'))
                loaded+=1
            else:ident=None
            entries.append(ident)
        syn=archive.read('en-ko/en-ko.syn');cursor=0
        while cursor<len(syn):
            end=syn.index(b'\0',cursor);word=syn[cursor:end].decode('utf8')
            entry_index=struct.unpack('>I',syn[end+1:end+5])[0];cursor=end+5
            if entries[entry_index]:db.execute('INSERT OR IGNORE INTO lookup VALUES(?,?,?)',(word.casefold(),entries[entry_index],'form'))
    # Clearly separate authored technical supplements from the open general dictionary.
    supplements=json.loads((ROOT/'engineering_supplement.json').read_text('utf8'))
    for word,spec in supplements.items():
        ident=db.execute('INSERT INTO entries(headword,senses,source) VALUES(?,?,?)',
            (word,json.dumps([dict(pos=spec['pos'],meaning=spec['meaning'])],ensure_ascii=False),'PaperLink 공학 보충')).lastrowid
        for alias in [word]+spec.get('forms',[]):db.execute('INSERT OR IGNORE INTO lookup VALUES(?,?,?)',(alias.casefold(),ident,'exact' if alias==word else 'form'))
    # Optional pinned second dictionary, displayed with its own source label.
    community_path=ROOT/'sources/open-english-korean-dict/words.json'
    community_count=0
    if community_path.exists():
        community=json.loads(community_path.read_text('utf8'))
        pos_names={'noun':'n.','verb':'v.','adjective':'adj.','adverb':'adv.','preposition':'prep.'}
        for word,spec in community.items():
            meaning=str(spec.get('meaning_ko','')).strip()
            if not re.search('[가-힣]',meaning) or not word.strip():continue
            ident=db.execute('INSERT INTO entries(headword,senses,source) VALUES(?,?,?)',
                (word,json.dumps([dict(pos=pos_names.get(spec.get('pos'),''),meaning=meaning)],ensure_ascii=False),'Open English-Korean Dictionary')).lastrowid
            db.execute('INSERT OR IGNORE INTO lookup VALUES(?,?,?)',(word.casefold(),ident,'exact'))
            community_count+=1
    metadata=dict(source_url='https://github.com/DanielGregorini/koreader-dicts',version='v1.3.0',
        license='CC BY-SA 4.0; authored supplements CC0; see NOTICE.md',archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        general_headwords=loaded,community_entries=community_count,unique_headwords=db.execute('SELECT COUNT(DISTINCT lower(headword)) FROM entries').fetchone()[0],technical_supplements=len(supplements),lookup_keys=db.execute('SELECT COUNT(DISTINCT term) FROM lookup').fetchone()[0])
    db.executemany('INSERT INTO metadata VALUES(?,?)',[(k,str(v)) for k,v in metadata.items()]);db.commit();db.close()
    temp.replace(dbpath)
    (ROOT/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(metadata,ensure_ascii=False))

if __name__=='__main__':build()
