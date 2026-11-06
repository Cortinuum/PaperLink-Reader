"""Allowlisted, relocatable browser-launch ZIP; never packages user data or Quick."""
from pathlib import Path
import hashlib,json,sqlite3,tempfile,zipfile
ROOT=Path(__file__).resolve().parent
VERSION='0.8.2'
APP_FILES=['reader.py','sentences.py','vocabulary.py','local_dictionary.py','paper_library.py','pdf_import.py','review_options.py','chatgpt_account.py','index.html','app.js','words.js','import.js','link_editor.js','style.css','theme.js','markdown.js','question_prompt.js','Start_PaperLink.cmd','Start_PaperLink.ps1','Stop_PaperLink.cmd','Stop_PaperLink.ps1','requirements.txt','README.md','LICENSE','THIRD_PARTY.md','DISTRIBUTION_REVIEW.md']
README='''PaperLink 0.8.2 — Windows x64 로컬 브라우저 실행판

1. ZIP 전체를 쓰기 가능한 폴더에 압축 해제하세요.
2. Start_PaperLink.cmd를 두 번 클릭하세요. 기본 브라우저에서 열립니다.
3. PDF 불러오기에서 영어 원문과 한국어 번역 PDF를 각각 선택하세요.
4. 종료는 Stop_PaperLink.cmd를 실행하세요. 브라우저 탭만 닫으면 서버는 남습니다.

Python과 필요한 패키지는 포함되어 있습니다. 별도 설치·첫 실행 다운로드가
필요하지 않고 시스템 Python이나 PATH를 바꾸지 않습니다. Windows 10/11 x64용입니다.
폴더를 다른 위치로 옮겨도 실행할 수 있습니다. 사용 중인 파일을 옮길 때는 먼저 종료하세요.
주소는 이 PC의 127.0.0.1에만 열립니다. 기본 포트가 사용 중이면 다른 포트를 선택합니다.

개인 논문·메모·대화·단어장·로그인 정보는 배포물에 포함하지 않았습니다.
새로 추가한 논문과 읽기 기록은 이 폴더의 data에 저장됩니다. 업데이트 전에 앱을
종료하고 data를 백업하세요. 새 버전에서도 data를 보존해야 기록이 유지됩니다.
ChatGPT 연결 정보는 해당 Windows 사용자 계정에 별도로 보호해 저장합니다.

기본 표시 사전은 커뮤니티 보충입니다. 첫 논문 11쪽 전체의 단어 조회 적중률은
커뮤니티 보충 87.13%, 공개 사전 75.61%였습니다. 번역 정확도를 뜻하는 수치는 아닙니다.
다른 사전·추가 결과를 펼치면 다른 뜻도 볼 수 있습니다. Quick 사전은 제외했습니다.
기본 사전 조회는 오프라인으로 처리합니다. 용례 검색을 눌렀을 때만 표제어를
외부 검색으로 전달합니다. GPT 질문에는 별도 로그인·전송 동의가 필요합니다.

사이트 호스팅이나 GitHub 업로드 없이 ZIP을 받아 이 PC에서 실행하는 배포물입니다.
사전 출처·이용 조건: dictionary/NOTICE.md, 각 sources의 고지 파일
사전 비교 상세: dictionary/comparison.json
실행환경 라이선스: .runtime/python 및 .venv/Lib/site-packages의 라이선스 파일
'''

def build():
    output=ROOT.parent/'PaperLink_Releases';output.mkdir(exist_ok=True)
    target=output/f'PaperLink-{VERSION}-Windows-x64.zip'
    runtime=ROOT/'.runtime/python/cpython-3.13.16-windows-x86_64-none'
    packages=ROOT/'.venv/Lib/site-packages'
    assert (runtime/'pythonw.exe').is_file()
    with tempfile.TemporaryDirectory(prefix='paperlink-release-') as temp:
        filtered=Path(temp)/'english_korean.sqlite3'
        source=sqlite3.connect((ROOT/'dictionary/english_korean.sqlite3').as_uri()+'?mode=ro',uri=True)
        db=sqlite3.connect(filtered);source.backup(db);source.close()
        db.execute("DELETE FROM lookup WHERE entry_id IN (SELECT id FROM entries WHERE source='Quick English-Korean')")
        db.execute("DELETE FROM entries WHERE source='Quick English-Korean'")
        count=db.execute('SELECT COUNT(DISTINCT lower(headword)) FROM entries').fetchone()[0]
        db.execute("INSERT OR REPLACE INTO metadata VALUES('unique_headwords',?)",(str(count),))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('license','CC BY-SA 4.0; authored supplements CC0; see NOTICE.md')")
        db.execute("DELETE FROM metadata WHERE key='quick'");db.commit();db.execute('VACUUM');db.close()
        manifest={}
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            def add(path,name):
                data=path.read_bytes();entry='PaperLink/'+name.replace('\\','/')
                z.writestr(entry,data);manifest[name]=hashlib.sha256(data).hexdigest()
            for name in APP_FILES:add(ROOT/name,name)
            for directory in ['vendor','.runtime/python/cpython-3.13.16-windows-x86_64-none','.venv/Lib/site-packages']:
                for p in sorted((ROOT/directory).rglob('*')):
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):add(p,p.relative_to(ROOT).as_posix())
            add(filtered,'dictionary/english_korean.sqlite3')
            for name in ['NOTICE.md','engineering_supplement.json','preference.json','comparison.json']:add(ROOT/'dictionary'/name,'dictionary/'+name)
            # Original public data + licences; deliberately omit local Quick archives/JSON.
            for name in ['ATTRIBUTION','LICENSE','README.txt','en-ko.ifo','CC-BY-SA-4.0.txt','en-ko-v1.3.0.zip']:
                add(ROOT/'dictionary/sources'/name,'dictionary/sources/'+name)
            for p in sorted((ROOT/'dictionary/sources/open-english-korean-dict').glob('*')):
                if p.is_file():add(p,'dictionary/sources/open-english-korean-dict/'+p.name)
            z.writestr('PaperLink/먼저_읽어주세요.txt',README.encode('utf-8-sig'))
            z.writestr('PaperLink/release-manifest.json',json.dumps(dict(version=VERSION,unique_headwords=count,preferred_source='Open English-Korean Dictionary',excluded_sources=['Quick English-Korean'],files=manifest),ensure_ascii=False,indent=2))
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None
            names=z.namelist()
            assert not any(n.startswith('PaperLink/data/') or n.endswith(('.pdf','.dpapi')) or 'Quick_' in n or 'quick-eng-kor-review' in n or 'instance-id' in n for n in names)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
        print(json.dumps(dict(zip=str(target),bytes=target.stat().st_size,files=len(names),unique_headwords=count,sha256=digest),ensure_ascii=False))
if __name__=='__main__':build()
