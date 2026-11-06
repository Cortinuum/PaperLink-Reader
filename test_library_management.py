import sys,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reader
from paper_library import PaperLibrary,digest
from pdf_import import decode_upload
from test_pdf_import import pdf,multipart

class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=pdf(self.root/'original.pdf');self.translation=pdf(self.root/'translated.pdf',text='Translation A')
        self.prepared=pdf(self.root/'prepared.pdf',text='Prepared text')
        self.library=PaperLibrary(self.root/'data')
        self.old=self.library.register(self.source,self.translation,'Original title',text_source=self.prepared)['paper']
    def tearDown(self):self.tmp.cleanup()
    def revision(self,name='revision.pdf',text='Translation B',pages=2):return pdf(self.root/name,text=text,pages=pages)
    def test_trash_restore_survive_restart_and_keep_files(self):
        before=digest(self.old['source']);self.library.trash(self.old['id'])
        again=PaperLibrary(self.library.root)
        self.assertEqual(again.listing(),[]);self.assertEqual(len(again.listing(deleted=True)),1)
        with self.assertRaises(ValueError):again.get(self.old['id'])
        again.restore(self.old['id']);self.assertEqual(again.listing()[0]['id'],self.old['id'])
        self.assertEqual(digest(self.old['source']),before)
    def test_change_translation_keeps_source_and_prepared_layer(self):
        revision=self.revision();before=[digest(self.source),digest(self.translation),digest(self.prepared)]
        result=self.library.replace_upload(self.old['id'],{'translation':('revision.pdf',revision.read_bytes())})
        new=result['paper'];self.assertTrue(result['changed']);self.assertNotEqual(new['id'],self.old['id'])
        self.assertEqual(new['source_hash'],self.old['source_hash']);self.assertEqual(digest(new['text_source']),digest(self.prepared))
        self.assertEqual(self.library.listing(deleted=True)[0]['replaced_by'],new['id'])
        self.assertEqual(before,[digest(self.source),digest(self.translation),digest(self.prepared)])
        self.assertEqual(digest(self.old['korean']),before[1])
    def test_change_original_does_not_reuse_old_text_layer(self):
        new_source=self.revision('new_source.pdf','New English original')
        result=self.library.replace_upload(self.old['id'],{'source':('new-source.pdf',new_source.read_bytes())})
        new=result['paper'];self.assertEqual(new['text_source'],new['source'])
        self.assertNotEqual(new['source_hash'],self.old['source_hash']);self.assertEqual(new['translation_hash'],self.old['translation_hash'])
    def test_invalid_change_leaves_old_pair_active(self):
        bad=self.revision('bad_count.pdf',pages=1)
        with self.assertRaises(ValueError):self.library.replace_upload(self.old['id'],{'translation':('bad.pdf',bad.read_bytes())})
        self.assertEqual([p['id'] for p in self.library.listing()],[self.old['id']]);self.assertEqual(self.library.listing(deleted=True),[])
    def test_title_only_and_same_content_keep_version(self):
        result=self.library.replace_upload(self.old['id'],{},'Updated title')
        self.assertFalse(result['changed']);self.assertTrue(result['title_updated']);self.assertEqual(result['paper']['id'],self.old['id'])
        same=self.library.replace_upload(self.old['id'],{'source':('same.pdf',self.source.read_bytes())})
        self.assertFalse(same['changed']);self.assertEqual(self.library.listing(deleted=True),[])
        self.assertEqual(digest(same['paper']['text_source']),digest(self.prepared))
    def test_existing_pair_is_reused_and_previous_can_be_restored(self):
        revision=self.revision();other=self.library.register(self.source,revision,'Other version')['paper']
        result=self.library.replace_upload(self.old['id'],{'translation':('revision.pdf',revision.read_bytes())})
        self.assertEqual(result['paper']['id'],other['id']);self.assertTrue(result['duplicate'])
        self.assertEqual(len(self.library.listing()),1)
        self.library.restore(self.old['id']);self.assertEqual(len(self.library.listing()),2)
    def test_importing_trashed_pair_restores_it(self):
        self.library.trash(self.old['id']);result=self.library.register(self.source,self.translation)
        self.assertTrue(result['restored']);self.assertTrue(result['duplicate']);self.assertEqual(result['paper']['id'],self.old['id'])
    def test_browser_empty_file_parts_are_allowed_only_for_changes(self):
        ctype,body=multipart(b'',self.translation.read_bytes())
        body=body.replace(b'filename="source.pdf"',b'filename=""')
        files,_=decode_upload(ctype,body,required_pair=False);self.assertEqual(set(files),{'translation'})
        with self.assertRaises(ValueError):decode_upload(ctype,body)
    def test_http_change_trash_restore_and_authentication(self):
        old_catalog=reader.CATALOG.copy();old_pages=reader.PAGES.copy()
        server=reader.ThreadingHTTPServer(('127.0.0.1',0),reader.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
        def post(path,data=None,body=None,ctype='application/json',token=True):
            headers={'Content-Type':ctype}
            if token:headers['X-Reader-Token']=reader.TOKEN
            req=Request(base+path,data=body if body is not None else json.dumps(data).encode(),headers=headers)
            with urlopen(req) as response:return json.load(response)
        try:
            with patch.object(reader,'LIBRARY',self.library),patch.object(reader.AUTH,'infer',side_effect=AssertionError('No GPT call')):
                with self.assertRaises(HTTPError) as denied:post('/api/library/trash',{'paper':self.old['id']},token=False)
                self.assertEqual(denied.exception.code,403)
                post('/api/library/trash',{'paper':self.old['id']});self.assertEqual(reader.discover(),[])
                post('/api/library/restore',{'paper':self.old['id']});self.assertEqual(len(reader.discover()),1)
                revision=self.revision();ctype,body=multipart(b'',revision.read_bytes(),'Changed title');body=body.replace(b'filename="source.pdf"',b'filename=""')
                result=post('/api/replace?paper='+self.old['id'],body=body,ctype=ctype)
                self.assertTrue(result['changed']);self.assertNotIn(self.old['id'],reader.CATALOG)
                post('/api/library/restore',{'paper':self.old['id']});self.assertEqual(len(reader.discover()),2)
        finally:
            server.shutdown();server.server_close();reader.CATALOG.clear();reader.CATALOG.update(old_catalog);reader.PAGES.clear();reader.PAGES.update(old_pages)

if __name__=='__main__':unittest.main(verbosity=2)
