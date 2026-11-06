"""Compare dictionaries on one full paper without network/model calls."""
import json,re,sqlite3,tempfile
from collections import Counter
from pathlib import Path
import pymupdf
from local_dictionary import LocalDictionary
from vocabulary import extract_words
ROOT=Path(__file__).resolve().parent
SOURCES=['Wiktionary / koreader-dicts','Open English-Korean Dictionary']

def compare():
    paper=ROOT.parent/'1_Highly robust nanostructured carbon films.pdf'
    counts=Counter()
    with pymupdf.open(paper) as pdf:
        pages=len(pdf)
        for number in range(1,pages+1):
            for word in extract_words(paper,number,'en',[]):
                term=word['term'].lower()
                if re.fullmatch(r'[a-z]+(?:-[a-z]+)*',term) and len(term)>=3:counts[term]+=1
    rows=[]
    with tempfile.TemporaryDirectory() as folder:
        original=sqlite3.connect(ROOT/'dictionary/english_korean.sqlite3')
        for index,source in enumerate(SOURCES):
            path=Path(folder)/f'{index}.sqlite3';db=sqlite3.connect(path)
            db.executescript('CREATE TABLE entries(id INTEGER PRIMARY KEY,headword TEXT,senses TEXT,source TEXT);CREATE TABLE lookup(term TEXT,entry_id INTEGER,kind TEXT);CREATE INDEX terms ON lookup(term);')
            selected=original.execute('SELECT * FROM entries WHERE source=?',(source,)).fetchall()
            db.executemany('INSERT INTO entries VALUES(?,?,?,?)',selected)
            keys=original.execute('SELECT l.* FROM lookup l JOIN entries e ON e.id=l.entry_id WHERE e.source=?',(source,)).fetchall();db.executemany('INSERT INTO lookup VALUES(?,?,?)',keys);db.commit();db.close()
            dictionary=LocalDictionary(path)
            exact={term for term in counts if any(k[0]==term and k[2]=='exact' for k in keys)}
            hits={term for term in counts if dictionary.lookup(term)['entries']}
            rows.append(dict(source=source,headwords=len(selected),exact_unique_hits=len(exact),unique_hits=len(hits),unique_total=len(counts),unique_hit_rate=round(len(hits)/len(counts)*100,2),token_hits=sum(counts[t] for t in hits),token_total=sum(counts.values()),token_hit_rate=round(sum(counts[t] for t in hits)/sum(counts.values())*100,2),missing_common=[dict(term=t,count=n) for t,n in counts.most_common() if t not in hits][:20]))
        original.close()
    winner=max(rows,key=lambda r:(r['token_hits'],r['unique_hits']))['source']
    report=dict(paper=paper.name,pages=pages,method='All pages including captions and bibliography; PDF word extraction with line-break hyphen joining; lowercase English words/hyphenated compounds of at least 3 characters; same lookup normalization for both; primary metric is occurrence-weighted hit rate; no Quick or technical supplement; coverage is not semantic accuracy.',results=rows,preferred_source=winner)
    (ROOT/'dictionary/comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (ROOT/'dictionary/preference.json').write_text(json.dumps(dict(preferred_source=winner,excluded_sources=['Quick English-Korean'],basis=paper.name),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':compare()
