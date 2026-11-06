import sys,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pymupdf as fitz
import reader
from paper_library import PaperLibrary,digest
from pdf_import import decode_upload

def pdf(path,pages=2,width=612,text='Sample paper'):
    with fitz.open() as doc:
        for _ in range(pages):
            page=doc.new_page(width=width,height=792)
            if text:page.insert_text((50,60),text)
        doc.save(path)
    return path

def multipart(source,translation,title='새 논문'):
    boundary='PaperLinkTestBoundary';body=b''
    for name,filename,content in [('title',None,title.encode()),('source','source.pdf',source),('translation','translation.pdf',translation)]:
        body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+name+'"'+('' if filename is None else '; filename="'+filename+'"')+'\r\n\r\n').encode()+content+b'\r\n'
    return 'multipart/form-data; boundary='+boundary,body+('--'+boundary+'--\r\n').encode()

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=pdf(self.root/'original.pdf');self.translation=pdf(self.root/'translated.pdf',text='Translated sample')
        self.library=PaperLibrary(self.root/'owned-data')
    def tearDown(self):self.tmp.cleanup()
    def test_owned_copies_and_persistence_preserve_inputs(self):
        before=[digest(p) for p in (self.source,self.translation)]
        record=self.library.register(self.source,self.translation)['paper']
        self.assertEqual(before,[digest(p) for p in (self.source,self.translation)])
        self.assertNotEqual(record['source'],str(self.source))
        self.assertTrue(Path(record['source']).is_relative_to(self.library.files))
        self.assertEqual(PaperLibrary(self.library.root).listing()[0]['id'],record['id'])
        self.assertEqual(digest(record['source']),before[0])
    def test_duplicate_pair_is_not_copied_or_overwritten(self):
        first=self.library.register(self.source,self.translation)['paper']
        again=self.library.register(self.source,self.translation,'different title')
        self.assertTrue(again['duplicate']);self.assertEqual(again['paper']['title'],first['title'])
        self.assertEqual(len(self.library.listing()),1)
    def test_page_count_and_dimensions_rejected(self):
        other=pdf(self.root/'count.pdf',pages=1)
        with self.assertRaisesRegex(ValueError,'페이지 수'):self.library.register(self.source,other)
        other=pdf(self.root/'size.pdf',width=500)
        with self.assertRaisesRegex(ValueError,'크기'):self.library.register(self.source,other)
        self.assertEqual(self.library.listing(),[])
    def test_invalid_and_password_protected_pdf_rejected(self):
        bad=self.root/'bad.pdf';bad.write_bytes(b'not a PDF')
        with self.assertRaises(ValueError):self.library.register(bad,self.translation)
        locked=self.root/'locked.pdf'
        with fitz.open(self.source) as doc:doc.save(locked,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='test-owner',user_pw='test-user')
        with self.assertRaisesRegex(ValueError,'암호'):self.library.register(locked,self.translation)
    def test_no_text_pdf_is_viewable_with_warning(self):
        blank=pdf(self.root/'blank.pdf',text='')
        result=self.library.register(blank,self.translation)
        self.assertTrue(result['warnings']);self.assertEqual(result['paper']['pages'],2)
    def test_multipart_filenames_cannot_select_storage_paths(self):
        ctype,body=multipart(self.source.read_bytes(),self.translation.read_bytes())
        body=body.replace(b'filename="source.pdf"',b'filename="../../source.pdf"')
        files,title=decode_upload(ctype,body);self.assertEqual(files['source'][0],'source.pdf')
        result=self.library.import_upload(files,title)
        self.assertEqual(result['paper']['title'],'새 논문');self.assertTrue(Path(result['paper']['source']).is_relative_to(self.library.files))
    def test_malformed_missing_or_non_pdf_form_rejected(self):
        with self.assertRaises(ValueError):decode_upload('application/json',b'{}')
        ctype,body=multipart(self.source.read_bytes(),self.translation.read_bytes())
        with self.assertRaises(ValueError):decode_upload(ctype,body.replace(b'name="translation"',b'name="unknown"'))
        with self.assertRaises(ValueError):decode_upload(ctype,body.replace(b'filename="source.pdf"',b'filename="source.exe"'))
    def test_local_http_import_authentication_and_reading(self):
        old_catalog=reader.CATALOG.copy();old_pages=reader.PAGES.copy()
        server=reader.ThreadingHTTPServer(('127.0.0.1',0),reader.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
        ctype,body=multipart(self.source.read_bytes(),self.translation.read_bytes())
        def request(token=True):
            headers={'Content-Type':ctype}
            if token:headers['X-Reader-Token']=reader.TOKEN
            with urlopen(Request(base+'/api/import',data=body if token else b'',headers=headers)) as response:return json.load(response)
        try:
            with patch.object(reader,'LIBRARY',self.library),patch.object(reader.AUTH,'infer',side_effect=AssertionError('No model request')):
                with self.assertRaises(HTTPError) as blocked:request(False)
                self.assertEqual(blocked.exception.code,403)
                result=request();self.assertFalse(result['duplicate'])
                with urlopen(base+'/api/page?paper='+result['paper']['id']+'&page=1') as response:data=json.load(response)
                self.assertTrue(data['sentences_en']);self.assertTrue(request()['duplicate'])
        finally:
            server.shutdown();server.server_close();reader.CATALOG.clear();reader.CATALOG.update(old_catalog);reader.PAGES.clear();reader.PAGES.update(old_pages)

if __name__=='__main__':unittest.main(verbosity=2)
