"""Offline OAuth tests with disposable keys, tokens, protected temp files and SSE."""
import sys,io,json,time,tempfile,unittest
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reader
import chatgpt_account as auth
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import hashes

class AccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        public=cls.key.public_key().public_numbers()
        enc=lambda n:auth.b64(n.to_bytes((n.bit_length()+7)//8,'big'))
        cls.jwks={'keys':[dict(kty='RSA',kid='offline-test',use='sig',n=enc(public.n),e=enc(public.e))]}
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.account=auth.ChatGPTAccount(self.tmp.name)
        self.account.metadata=dict(issuer=auth.ISSUER,jwks_uri=auth.ISSUER+'/.well-known/jwks.json',token_endpoint=auth.TOKEN_URL,revocation_endpoint=auth.ISSUER+'/api/accounts/oauth/revoke')
    def tearDown(self):self.tmp.cleanup()
    def jwt(self,client,expected_nonce,**changes):
        claims=dict(iss=auth.ISSUER,aud=client,sub='offline-account',email='offline@example.invalid',nonce=expected_nonce,iat=int(time.time()),exp=int(time.time()+3600))
        claims.update(changes)
        text=auth.b64(json.dumps(dict(alg='RS256',kid='offline-test')).encode())+'.'+auth.b64(json.dumps(claims).encode())
        sig=self.key.sign(text.encode(),padding.PKCS1v15(),hashes.SHA256())
        return text+'.'+auth.b64(sig)
    def authorize(self,scopes='openid email profile resource.invoke chatgpt.tokens.use.direct offline_access'):
        url=self.account.start(54321);q={k:v[0] for k,v in parse_qs(urlparse(url).query).items()}
        client='oaiapp_offline-test'
        tokens=dict(access_token='disposable-access-token',refresh_token='disposable-refresh-token',token_type='Bearer',expires_in=3600,scope=scopes,id_token=self.jwt(client,q['nonce']))
        def fake_json(url,form=None,bearer=None):
            if url==auth.TOKEN_URL:
                self.assertEqual(form['client_id'],client)
                self.assertEqual(form['redirect_uri'],q['redirect_uri'])
                self.assertNotIn('client_secret',form)
                self.assertEqual(auth.b64(auth.hashlib.sha256(form['code_verifier'].encode()).digest()),q['code_challenge'])
                return tokens
            return self.jwks
        with patch.object(self.account,'_json',fake_json):
            result=self.account.complete(dict(state=q['state'],client_id=client,code='disposable-code'))
        return result
    def test_pkce_stable_host_fresh_state_and_no_secret(self):
        first=parse_qs(urlparse(self.account.start(54321)).query)
        second=parse_qs(urlparse(self.account.start(54321)).query)
        self.assertEqual(first['client_id'],['dynamic_agent_client'])
        self.assertEqual(first['agent_name_hint'],['PaperLink'])
        self.assertEqual(first['ext_agent_host_id'],second['ext_agent_host_id'])
        self.assertNotEqual(first['state'],second['state'])
        self.assertEqual(first['redirect_uri'],['http://127.0.0.1:54321/auth/callback'])
        self.assertNotIn('access_token',first)
    def test_callback_state_and_client_are_bound(self):
        q={k:v[0] for k,v in parse_qs(urlparse(self.account.start(54321)).query).items()}
        with patch.object(self.account,'_json') as network:
            with self.assertRaises(ValueError):self.account.complete(dict(state='wrong',client_id='bad',code='x'))
            network.assert_not_called()
        self.assertTrue(self.account.status()['pending'])
        with self.assertRaises(ValueError):self.account.complete(dict(state=q['state'],error='access_denied'))
        self.assertFalse(self.account.status()['pending'])
    def test_valid_identity_scope_and_windows_protected_storage(self):
        result=self.authorize()
        self.assertTrue(result['plan_enabled'])
        self.assertNotIn('access_token',json.dumps(result))
        raw=(Path(self.tmp.name)/'chatgpt.dpapi').read_bytes()
        self.assertNotIn(b'disposable-access',raw)
        reloaded=auth.ChatGPTAccount(self.tmp.name)
        self.assertEqual(reloaded.record['client_id'],'oaiapp_offline-test')
        self.assertTrue(reloaded.status()['connected'])
    def test_signature_nonce_audience_and_expiry_rejected(self):
        with patch.object(self.account,'_json',return_value=self.jwks):
            for changes in [dict(aud='wrong'),dict(exp=time.time()-600),dict(iss='https://example.invalid'),dict(nonce='wrong')]:
                with self.assertRaises(ValueError):self.account.validate_identity(self.jwt('client','nonce',**changes),'client','nonce')
            token=self.jwt('client','nonce');pieces=token.split('.');pieces[1]=auth.b64(json.dumps({'sub':'forged'}).encode())
            with self.assertRaises(ValueError):self.account.validate_identity('.'.join(pieces),'client','nonce')
    def test_identity_alone_does_not_allow_plan_requests(self):
        result=self.authorize('openid email profile')
        self.assertTrue(result['connected']);self.assertFalse(result['plan_enabled'])
        with self.assertRaises(ValueError):self.account.access_token()
    def test_refresh_rotates_tokens_and_preserves_client(self):
        self.authorize();self.account.record['expires_at']=0
        def refresh(url,form=None,bearer=None):
            self.assertEqual(form['client_id'],'oaiapp_offline-test')
            self.assertNotIn('scope',form)
            return dict(access_token='renewed-test-access',refresh_token='renewed-test-refresh',expires_in=3600)
        with patch.object(self.account,'_json',refresh):self.assertEqual(self.account.access_token(),'renewed-test-access')
        reload=auth.ChatGPTAccount(self.tmp.name)
        self.assertEqual(reload.record['refresh_token'],'renewed-test-refresh')
    def test_models_and_inference_use_plan_contract(self):
        self.authorize();self.account.catalog=[dict(id='eligible-test-model',name='Test')];self.account.catalog_at=time.time()
        captured={}
        def fake(req,timeout):
            captured.update(json.loads(req.data));self.assertEqual(req.full_url,auth.RESOURCE+'/responses')
            return io.BytesIO(b'data: {"type":"response.output_text.delta","delta":"test answer"}\n\ndata: {"type":"response.completed","response":{"usage":{"input_tokens":30,"output_tokens":4}}}\n\n')
        self.account.open=fake
        answer,usage=self.account.infer('instruction',[dict(role='user',content='test')],'eligible-test-model')
        self.assertEqual(answer,'test answer');self.assertEqual(usage['billing_mode'],'chatgpt-plan')
        self.assertIs(captured['store'],False);self.assertIs(captured['stream'],True)
        self.assertNotIn('max_output_tokens',captured);self.assertNotIn('previous_response_id',captured)
        with self.assertRaises(ValueError):self.account.infer('',[],'not-permitted')
    def test_stream_limit_error_and_interruption_never_count_as_success(self):
        for stream in [b'data: {"type":"response.output_text.delta","delta":"unfinished"}\n\n',
                       b'data: {"type":"response.failed","response":{"error":{"code":"subscription_sharing_usage_limit_exceeded"}}}\n\n',
                       b'data: {"type":"response.incomplete"}\n\n']:
            with self.assertRaises(ValueError):auth.read_stream(io.BytesIO(stream),'test')
    def test_supported_reasoning_levels_default_lowest_and_validate(self):
        self.authorize()
        raw=dict(models=[dict(slug='reasoning-test',display_name='Test',visibility='list',supported_reasoning_levels=[{'effort':'max'},{'effort':'low'},{'effort':'medium'}])])
        with patch.object(self.account,'_json',return_value=raw):models=self.account.models()
        self.assertEqual(models[0]['reasoning_levels'],['low','medium','max'])
        requests=[]
        def fake(req,timeout):
            requests.append(json.loads(req.data))
            return io.BytesIO(b'data: {"type":"response.output_text.delta","delta":"ok"}\n\ndata: {"type":"response.completed","response":{"usage":{}}}\n\n')
        self.account.open=fake
        _,usage=self.account.infer('',[],'reasoning-test')
        self.assertEqual(requests[-1]['reasoning'],{'effort':'low'});self.assertEqual(usage['reasoning_effort'],'low')
        self.account.infer('',[],'reasoning-test','medium')
        self.assertEqual(requests[-1]['reasoning'],{'effort':'medium'})
        with self.assertRaises(ValueError):self.account.infer('',[],'reasoning-test','none')
        self.assertEqual(len(requests),2)
    def test_http429_never_falls_back_to_paid_api(self):
        self.authorize();self.account.catalog=[dict(id='test',name='Test')];self.account.catalog_at=time.time()
        def limited(req,timeout):raise HTTPError(req.full_url,429,'rate limit',{},None)
        self.account.open=limited
        with self.assertRaisesRegex(ValueError,'자동 전환하지 않습니다'):self.account.infer('',[],'test')
    def test_logout_clears_credentials_but_keeps_own_registration(self):
        self.authorize()
        class Empty(io.BytesIO):status=200
        self.account.open=lambda req,timeout:Empty(b'')
        result=self.account.logout()
        self.assertTrue(result['remote_revocation_confirmed']);self.assertFalse(self.account.status()['connected'])
        record=auth.ChatGPTAccount(self.tmp.name).record
        self.assertNotIn('refresh_token',record);self.assertNotIn('access_token',record)
        self.assertEqual(record['client_id'],'oaiapp_offline-test')

if __name__=='__main__':unittest.main(verbosity=2)
