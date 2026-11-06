import sys,json,socket,threading,unittest,tempfile
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from local_dictionary import LocalDictionary
import reader

class DictionaryTests(unittest.TestCase):
    def setUp(self):self.dictionary=reader.DICTIONARY
    def test_multiple_senses_and_exact_priority(self):
        prop=self.dictionary.lookup('property')['entries']
        self.assertTrue(any('특성' in s['meaning'] for e in prop for s in e['senses']))
        carbon=self.dictionary.lookup('carbon')['entries']
        self.assertEqual({e['headword'] for e in carbon},{'carbon'})
    def test_plural_irregular_and_possessive_indexes(self):
        for term,lemma in [('properties','property'),('films','film'),('went','go'),('electrode’s','electrode')]:
            entries=self.dictionary.lookup(term)['entries']
            self.assertTrue(any(e['headword']==lemma for e in entries),term)
    def test_technical_supplement_is_distinguished(self):
        entries=self.dictionary.lookup('films')['entries']
        self.assertEqual(entries[0]['source'],'PaperLink 공학 보충')
        self.assertIn('박막',entries[0]['senses'][0]['meaning'])
        self.assertTrue(any(e['source'].startswith('Wiktionary') for e in entries))
    def test_unknown_side_missing_and_malicious_input(self):
        for word in ['Nafion','zzzz-not-a-real-word',"' OR 1=1 --",'<script>alert(1)</script>']:
            self.assertEqual(self.dictionary.lookup(word)['entries'],[])
        self.assertEqual(self.dictionary.lookup('탄소','ko')['entries'],[])
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(LocalDictionary(Path(folder)/'absent').lookup('carbon')['available'])
        with self.assertRaises(ValueError):self.dictionary.lookup('x'*201)
    def test_no_network_and_no_file_modification(self):
        before=self.dictionary.path.read_bytes()
        with patch.object(socket,'create_connection',side_effect=AssertionError('No remote network allowed')):
            self.assertTrue(self.dictionary.lookup('robustness')['offline'])
        self.assertEqual(self.dictionary.path.read_bytes(),before)
    def test_expanded_general_words_and_marked_lemma_candidates(self):
        for word in ('mechanical','thermal','actuator','onto','structural'):
            result=self.dictionary.lookup(word)
            self.assertTrue(result['entries'],word)
            self.assertTrue(any(e['source']=='Open English-Korean Dictionary' for e in result['entries']),word)
        for word,lemma in [('thermally','thermal'),('actuators','actuator')]:
            entries=self.dictionary.lookup(word)['entries']
            self.assertTrue(any(e['headword']==lemma and e.get('match_method')=='lemma' for e in entries),word)
    def test_compound_components_are_labeled_and_unknown_parts_not_invented(self):
        entries=self.dictionary.lookup('micro-mechanical')['entries']
        self.assertTrue(entries)
        self.assertTrue(all(e.get('match_method')=='component' for e in entries))
        self.assertEqual(self.dictionary.lookup('zzzz-mechanical')['entries'],[])
    def test_quick_is_excluded_and_primary_source_is_declared(self):
        entries=self.dictionary.lookup('fabrication')['entries']
        self.assertTrue(any(e['source']=='Open English-Korean Dictionary' for e in entries))
        for word in ['fabrication','mechanical','thermally','micro-mechanical','delamination']:
            result=self.dictionary.lookup(word)
            self.assertFalse(any(e['source']=='Quick English-Korean' for e in result['entries']))
            self.assertEqual(result['preferred_source'],'Open English-Korean Dictionary')
    def test_http_lookup_without_model_calls(self):
        server=reader.ThreadingHTTPServer(('127.0.0.1',0),reader.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with patch.object(reader.AUTH,'infer',side_effect=AssertionError('No GPT calls')):
                with urlopen(f'http://127.0.0.1:{server.server_port}/api/dictionary?'+urlencode({'term':'properties','side':'en'})) as response:
                    result=json.load(response)
                self.assertTrue(result['offline']);self.assertEqual(result['entries'][0]['headword'],'property')
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main(verbosity=2)
