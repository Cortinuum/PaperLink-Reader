import unittest
import local_alignment as rules
from test_sentence_links import item


def sentence(id,text,y=100,x=40,font=10):
    s=item(id,text,[x,y,x+240,y+15]);s['font_size']=font;return s

def mapping(en,ko,manual=None):return {l['source']:l for l in rules.align(en,ko,(600,800),manual)}

class RegionTests(unittest.TestCase):
    def test_caption_never_falls_back_to_body(self):
        en=[item('caption','Fig. 4 Sample caption.',[40,350,550,380])]
        ko=[sentence('body','일반 본문이 설명문과 같은 길이여도 연결하지 않습니다.',350)]
        l=mapping(en,ko)['caption'];self.assertEqual(l['targets'],[]);self.assertEqual(l['candidates'],[])
    def test_different_figure_numbers_stay_separate(self):
        en=[item('caption','Fig. 4 Caption.',[40,350,550,380])]
        ko=[item('other','그림 5 설명입니다.',[40,350,550,380])]
        self.assertEqual(mapping(en,ko)['caption']['targets'],[])
    def test_headings_use_positions_when_columns_change_extraction_order(self):
        en=[sentence('intro','Introduction',430,font=14),sentence('title','A title',130,x=300,font=16)]
        ko=[sentence('ktitle','논문 제목입니다',130,x=300,font=16),sentence('kintro','서론',430,font=14)]
        # Supply normal body typography so classification has a baseline.
        for rows,prefix in [(en,'e'),(ko,'k')]:rows.append(sentence(prefix+'body','This sufficiently long paragraph establishes the normal body size and gives some useful context for the typography.',500,font=10))
        l=mapping(en,ko);self.assertEqual(l['intro']['targets'],['kintro']);self.assertEqual(l['title']['targets'],['ktitle'])
    def test_typography_distinguishes_heading_footnote_and_body_reference(self):
        en=[sentence('body','Fig. 2 shows the results of this experiment and the changes observed in many repeated measurements.',100),
            sentence('body2','This longer paragraph is used to establish the normal body font and does not belong to the captions.',200),
            sentence('heading','Experimental procedure',70,font=13),sentence('note','† Additional data available.',700,font=8)]
        rules.classify(en,(600,800));self.assertEqual([s['region_type'] for s in en],['content','content','heading','footnote'])

class AnchorTests(unittest.TestCase):
    def test_only_unique_reference_or_measurement_can_be_an_anchor(self):
        en=[sentence('a','The length is 15 mm.'),sentence('b','Other text.',150)]
        ko=[sentence('x','길이는 15 mm이다.'),sentence('y','다른 문장입니다.',150)]
        self.assertEqual(rules.anchors(en,ko),[(0,0)])
        en.append(sentence('c','Again 15 mm.',200));self.assertEqual(rules.anchors(en,ko),[])
    def test_crossing_numeric_anchors_do_not_create_crossing_automatic_links(self):
        en=[sentence('a','Fig. 2a results.'),sentence('b','Fig. 3b results.',150)]
        ko=[sentence('x','그림 3b 결과입니다.'),sentence('y','그림 2a 결과입니다.',150)]
        pairs=rules.anchors(en,ko);self.assertEqual(len(pairs),1)
    def test_measurement_and_percent_features(self):
        f=rules.features('3 mm, 12%, 20 wt%, 335.0 MPa, 6 μm')
        self.assertTrue({('3.0','mm'),('12.0','%'),('20.0','wt%'),('335.0','MPa'),('6.0','μm')}<=f['measures'])
    def test_unique_anchor_splits_intervals(self):
        en=[sentence('a','The first sentence has a simple explanation.'),sentence('anchor','The gauge is 15 mm long.',200),sentence('b','The last sentence describes the observation.',300)]
        ko=[sentence('x','첫 문장은 단순한 설명을 담고 있다.'),sentence('fixed','게이지 길이는 15 mm이다.',200),sentence('y','마지막 문장은 관찰 결과를 설명한다.',300)]
        l=mapping(en,ko);self.assertEqual(l['anchor']['targets'],['fixed']);self.assertTrue(l['anchor']['evidence']);self.assertNotIn('y',l['a']['targets']);self.assertNotIn('x',l['b']['targets'])

class ConservativeTests(unittest.TestCase):
    def test_conflicting_measurement_is_withheld_with_candidate(self):
        l=mapping([sentence('e','The length is 10 mm.')],[sentence('k','길이는 20 mm이다.')])['e']
        self.assertEqual(l['targets'],[]);self.assertEqual(l['status'],'unlinked');self.assertIn(['k'],l['candidates']);self.assertTrue(any('충돌' in r for r in l['review_reasons']))
    def test_duplicate_translations_are_not_merged_as_if_certain(self):
        l=mapping([sentence('e','This is a test sentence.')],[sentence('k1','이것은 시험 문장입니다.'),sentence('k2','이것은 시험 문장입니다.')])['e']
        self.assertEqual(l['targets'],[]);self.assertTrue(l['candidates'])
    def test_missing_target_is_explicit(self):
        l=mapping([sentence('e','A sentence.')],[])['e'];self.assertEqual(l['status'],'unlinked');self.assertEqual(l['targets'],[])

class ManualFenceTests(unittest.TestCase):
    def setUp(self):
        self.en=[sentence('e'+str(i),'This sentence describes a step in the process.',100+i*60) for i in range(4)]
        self.ko=[sentence('k'+str(i),'이 문장은 과정의 한 단계를 설명합니다.',100+i*60) for i in range(5)]
    def test_manual_link_is_fixed_and_neighbours_cannot_cross_it(self):
        l=mapping(self.en,self.ko,{'e1':['k2']})
        self.assertEqual(l['e1']['targets'],['k2']);self.assertEqual(l['e1']['status'],'manual')
        self.assertTrue(set(l['e0']['targets'])<= {'k0','k1'})
        for id in ('e2','e3'):self.assertTrue(set(l[id]['targets'])<= {'k3','k4'})
    def test_crossed_manual_links_are_preserved_and_interior_is_not_guessed(self):
        l=mapping(self.en,self.ko,{'e0':['k3'],'e2':['k1']})
        self.assertEqual(l['e0']['targets'],['k3']);self.assertEqual(l['e2']['targets'],['k1'])
        self.assertEqual(l['e1']['targets'],[]);self.assertTrue(any('교차' in r for r in l['e1']['review_reasons']))
    def test_three_crossed_fences_merge_transitively(self):
        l=mapping(self.en,self.ko,{'e0':['k2'],'e1':['k4'],'e3':['k0']})
        self.assertEqual(l['e2']['targets'],[])
        self.assertTrue(any('교차' in r for r in l['e2']['review_reasons']))
        for id,target in [('e0','k2'),('e1','k4'),('e3','k0')]:self.assertEqual(l[id]['targets'],[target])
    def test_manual_unlink_survives_recalculation(self):
        l=mapping(self.en,self.ko,{'e1':[]});self.assertEqual(l['e1']['targets'],[]);self.assertEqual(l['e1']['method'],'manual')
    def test_removed_manual_fence_recalculates_neighbours(self):
        fixed=mapping(self.en,self.ko,{'e1':['k3']});automatic=mapping(self.en,self.ko)
        self.assertNotEqual(fixed['e1']['method'],automatic['e1']['method']);self.assertNotIn('k4',fixed['e0']['targets'])

if __name__=='__main__':unittest.main()
