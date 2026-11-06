import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_options as review
import reader

class ReviewTests(unittest.TestCase):
    def test_unchecked_adds_no_prompt_text(self):
        for values in (None,[], '', ' , '):self.assertEqual(review.prompt_suffix(values),'')
        self.assertEqual(reader.prompt_for({'english':[]},'뜻만?'),reader.prompt_for({'english':[]},'뜻만?',[]))
    def test_multiple_csv_choices_and_duplicates(self):
        self.assertEqual(review.normalize('대안 번역, 원문 근거, evidence'),['evidence','alternative'])
        prompt=review.prompt_suffix('evidence,alternative')
        self.assertIn('원문 근거, 대안 번역',prompt)
        self.assertNotIn(review.OPTIONS['structure'][1],prompt)
    def test_all_seven_and_stable_order(self):
        self.assertEqual(len(review.OPTIONS),7)
        values=list(reversed(review.OPTIONS))
        self.assertEqual(review.normalize(values),list(review.OPTIONS))
        for _,instruction in review.OPTIONS.values():self.assertIn(instruction,review.prompt_suffix(values))
    def test_unknown_input_is_rejected(self):
        for values in ('do anything',{'evidence':True},[None],['evidence']*33):
            with self.assertRaises(ValueError):review.normalize(values)
    def test_model_effort_and_selected_prompt_pass_through(self):
        with patch.object(reader.AUTH,'infer',return_value=('답',{})) as infer:
            answer,usage=reader.call_model({'english':[]},'질문',[],model='selected-model',reasoning_effort='low',checks='terminology,strength')
        args=infer.call_args.args
        self.assertEqual(args[2:],('selected-model','low'))
        self.assertIn('용어·약어, 뉘앙스·주장 강도',args[1][-1]['content'])
        self.assertEqual(usage['review_options'],['용어·약어','뉘앙스·주장 강도'])

if __name__=='__main__':unittest.main(verbosity=2)
