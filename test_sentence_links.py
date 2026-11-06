import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sentences,reader


def item(id,text,box,flow=None,offset=0):
    return dict(id=id,text=text,bbox=box,flow_bbox=flow or box,offset=offset)

class ReadingOrderTests(unittest.TestCase):
    def test_full_width_caption_precedes_both_columns_below(self):
        caption=[40,350,550,410]
        data=[item('left','Body text.',[40,430,290,480]),
              item('right','Right body.',[310,430,550,480]),
              item('caption2','Second caption sentence.',[40,370,290,380],caption,30),
              item('caption1','Figure 1 caption.',[40,350,450,360],caption,0)]
        result=sentences.reading_order(data,600,800)
        self.assertEqual([s['id'] for s in result],['caption1','caption2','left','right'])
    def test_spanning_section_between_columns_preserves_upper_and_lower_flow(self):
        data=[item('bl','lower left',[40,500,280,550]),item('ar','upper right',[310,100,550,300]),
              item('h','wide heading',[40,400,550,420]),item('al','upper left',[40,100,280,300]),
              item('br','lower right',[310,500,550,550])]
        self.assertEqual([s['id'] for s in sentences.reading_order(data,600,800)],['al','ar','h','bl','br'])
    def test_headers_do_not_shift_caption_match(self):
        en=[item('paper','Paper',[40,24,70,33]),item('journal','Journal',[400,24,550,33]),
            item('caption','Figure 1. A sample caption.',[40,350,550,380]),
            item('body','Water at 38 degrees.',[40,430,290,460])]
        ko=[item('kjournal','Journal',[400,21,550,34]),item('kpaper','논문',[40,23,60,37]),
            item('kcaption','그림 1. 시험 설명문입니다.',[40,350,550,380]),
            item('kbody','38도에서 물을 확인했다.',[40,430,290,460])]
        links=sentences.align(sentences.reading_order(en,600,800),sentences.reading_order(ko,600,800),[])
        actual={l['source']:l['targets'] for l in links}
        self.assertEqual(actual,{'paper':['kpaper'],'journal':['kjournal'],'caption':['kcaption'],'body':['kbody']})
    def test_ordering_preserves_existing_sentence_ids_and_text(self):
        data=[item('stable','A sentence.',[40,100,280,120])]
        self.assertEqual(sentences.reading_order(data,600,800)[0]['id'],'stable')
        self.assertEqual(data[0]['text'],'A sentence.')

class LinkWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'links.sqlite3'
        self.patch=patch.object(reader,'DB',self.db);self.patch.start()
        with reader.database() as db:db.execute('CREATE TABLE sentence_links(paper TEXT,page INTEGER,source TEXT,targets TEXT,PRIMARY KEY(paper,page,source))')
        self.data=patch.object(reader,'page_data',return_value={'sentences_en':[{'id':'e1'},{'id':'e2'}],'sentences_ko':[{'id':'k1'},{'id':'k2'}]});self.data.start()
    def tearDown(self):self.data.stop();self.patch.stop();self.tmp.cleanup()
    def rows(self):
        with reader.database() as db:return [dict(r) for r in db.execute('SELECT * FROM sentence_links ORDER BY source')]
    def test_multi_target_and_unlinked_choices_persist(self):
        reader.write_sentence_links('paper',3,[{'source':'e1','targets':['k1','k2']},{'source':'e2','targets':[]}])
        self.assertEqual(len(self.rows()),2);self.assertEqual(self.rows()[1]['targets'],'[]')
    def test_invalid_batch_commits_nothing(self):
        with self.assertRaises(ValueError):reader.write_sentence_links('paper',3,[{'source':'e1','targets':['k1']},{'source':'e2','targets':['unknown']}])
        self.assertEqual(self.rows(),[])
    def test_reset_removes_only_selected_override(self):
        reader.write_sentence_links('paper',3,[{'source':'e1','targets':['k1']},{'source':'e2','targets':['k2']}])
        reader.write_sentence_links('paper',3,[{'source':'e1','targets':[],'reset':True}])
        self.assertEqual([r['source'] for r in self.rows()],['e2'])
    def test_duplicate_source_and_target_rejected(self):
        for changes in [[{'source':'e1','targets':['k1','k1']}],[{'source':'e1','targets':[]},{'source':'e1','targets':[]}]]:
            with self.assertRaises(ValueError):reader.write_sentence_links('paper',3,changes)
        self.assertEqual(self.rows(),[])

if __name__=='__main__':unittest.main()
