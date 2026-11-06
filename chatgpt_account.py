"""Official Sign in with ChatGPT for a personal, locally hosted reader.

Uses this app's own OAuth client and Windows-protected storage. Never imports
credentials from Codex, browsers, an API key file, or another application.
"""
import base64, ctypes, hashlib, json, os, secrets, threading, time, uuid
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

ISSUER='https://auth.openai.com'
AUTHORIZE=ISSUER+'/api/accounts/authorize'
TOKEN_URL=ISSUER+'/api/accounts/oauth/token'
RESOURCE='https://api.openai.com/v1'
REQUIRED={'resource.invoke','chatgpt.tokens.use.direct'}
EFFORT_ORDER=('none','minimal','low','medium','high','xhigh','max','ultra')

def reasoning_levels(raw):
    values={v.get('effort') if isinstance(v,dict) else v for v in raw or []}
    return [value for value in EFFORT_ORDER if value in values]

def b64(data):return base64.urlsafe_b64encode(data).decode().rstrip('=')
def unb64(value):return base64.urlsafe_b64decode(value+'='*((-len(value))%4))

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def transport(req,timeout=30):
    # Do not forward bearer credentials or token grants across HTTP redirects.
    return build_opener(NoRedirect).open(req,timeout=timeout)

def protected(raw,decrypt=False):
    if os.name!='nt':raise ValueError('이 로그인 저장 기능은 Windows에서 사용할 수 있습니다.')
    class Blob(ctypes.Structure):
        _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(raw)
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    func=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    func.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(Blob)]
    func.restype=ctypes.c_int
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not func(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise ValueError('Windows의 로그인 정보 보호 기능을 사용할 수 없습니다.')
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(ctypes.cast(target.data,ctypes.c_void_p))

def atomic_write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+secrets.token_hex(5)+'.tmp')
    try:
        temp.write_bytes(raw)
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def safe_error(code):
    return {
      'subscription_sharing_usage_limit_exceeded':'ChatGPT 구독 또는 이 앱의 사용 한도에 도달했습니다. ChatGPT 사용량 설정을 확인하세요.',
      'subscription_sharing_usage_unavailable':'이 계정에서 ChatGPT 구독 사용이 허용되지 않았습니다. 로그인 권한과 구독 상태를 확인하세요.',
      'access_denied':'ChatGPT 로그인이 취소되었거나 권한이 승인되지 않았습니다.',
      'invalid_grant':'로그인 연결이 만료되었습니다. 다시 로그인하세요.',
    }.get(code,'ChatGPT 요청을 완료하지 못했습니다. 잠시 후 다시 시도하세요.')

class ChatGPTAccount:
    def __init__(self,storage=None,opener=None):
        self.storage=Path(storage) if storage else Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'PaperLink'/'auth'
        self.open=opener or transport
        self.lock=threading.RLock();self.pending=None;self.record={};self.last_error=''
        self.metadata=None;self.catalog=[];self.catalog_at=0
        self._load()

    def _load(self):
        path=self.storage/'chatgpt.dpapi'
        if path.is_file():
            try:self.record=json.loads(protected(path.read_bytes(),decrypt=True))
            except (ValueError,OSError,json.JSONDecodeError):self.last_error='저장된 로그인을 열 수 없습니다. 다시 로그인하세요.'

    def _save(self):
        atomic_write(self.storage/'chatgpt.dpapi',protected(json.dumps(self.record).encode()))

    def _json(self,url,form=None,bearer=None):
        headers={'Accept':'application/json'};data=None
        if form is not None:
            data=urlencode(form).encode();headers['Content-Type']='application/x-www-form-urlencoded'
        if bearer:headers['Authorization']='Bearer '+bearer
        with self.open(Request(url,data=data,headers=headers),timeout=30) as response:
            raw=response.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('로그인 서비스 응답이 너무 큽니다.')
            return json.loads(raw)

    def discovery(self):
        if self.metadata is None:
            data=self._json(ISSUER+'/.well-known/openid-configuration')
            if data.get('issuer')!=ISSUER or data.get('token_endpoint')!=TOKEN_URL:
                raise ValueError('OpenAI 로그인 서비스의 주소를 확인할 수 없습니다.')
            for field in ('jwks_uri','revocation_endpoint'):
                url=data.get(field,'')
                if url and (urlparse(url).scheme!='https' or urlparse(url).netloc!='auth.openai.com'):
                    raise ValueError('로그인 서비스의 보안 주소를 확인할 수 없습니다.')
            self.metadata=data
        return self.metadata

    def host_id(self):
        path=self.storage/'host.json'
        if path.is_file():
            value=json.loads(path.read_text())['id']
            if value.startswith('urn:uuid:'):return value
            raise ValueError('이 PC의 로그인 식별 정보를 확인하세요.')
        value='urn:uuid:'+str(uuid.uuid4())
        atomic_write(path,json.dumps({'id':value}).encode())
        return value

    def status(self):
        with self.lock:
            scopes=set(self.record.get('scopes',[]))
            connected=bool(self.record.get('access_token') or self.record.get('refresh_token'))
            return dict(connected=connected,plan_enabled=connected and REQUIRED<=scopes,
              email=self.record.get('email','') if connected else '',pending=bool(self.pending and self.pending['expires']>time.time()),
              error=self.last_error,needs_welcome=connected and not self.record.get('welcomed',False))

    def start(self,port,new_account=False):
        with self.lock:
            verifier=secrets.token_urlsafe(64);state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32)
            client='' if new_account else self.record.get('client_id','')
            redirect=f'http://127.0.0.1:{int(port)}/auth/callback'
            self.pending=dict(state=state,nonce=nonce,verifier=verifier,redirect=redirect,client=client,
                subject=self.record.get('subject','') if client else '',expires=time.time()+600)
            self.last_error=''
            params=dict(client_id=client or 'dynamic_agent_client',ext_agent_host_id=self.host_id(),
                response_type='code',redirect_uri=redirect,scope='openid profile email offline_access resource.invoke chatgpt.tokens.use.direct',
                resource=RESOURCE,state=state,nonce=nonce,code_challenge_method='S256',
                code_challenge=b64(hashlib.sha256(verifier.encode()).digest()))
            if not client:params['agent_name_hint']='PaperLink'
            return AUTHORIZE+'?'+urlencode(params)

    def validate_identity(self,token,client,nonce):
        if not isinstance(token,str) or len(token)>65536:raise ValueError('로그인 확인 정보가 올바르지 않습니다.')
        try:
            header64,payload64,sig64=token.split('.')
            header=json.loads(unb64(header64));claims=json.loads(unb64(payload64))
            if header.get('alg')!='RS256':raise ValueError()
            jwks=self._json(self.discovery()['jwks_uri'])
            key=next(k for k in jwks['keys'] if k.get('kid')==header.get('kid') and k.get('kty')=='RSA' and k.get('use','sig')=='sig')
            public=rsa.RSAPublicNumbers(int.from_bytes(unb64(key['e']),'big'),int.from_bytes(unb64(key['n']),'big')).public_key()
            public.verify(unb64(sig64),(header64+'.'+payload64).encode(),padding.PKCS1v15(),hashes.SHA256())
            aud=claims.get('aud');aud=[aud] if isinstance(aud,str) else aud
            if not isinstance(aud,list) or client not in aud:raise ValueError()
            if len(aud)>1 and claims.get('azp')!=client:raise ValueError()
            if claims.get('iss')!=ISSUER or float(claims.get('exp',0))<=time.time()-30:raise ValueError()
            if float(claims.get('iat',0))>time.time()+120 or not claims.get('sub'):raise ValueError()
            if not secrets.compare_digest(str(claims.get('nonce','')),nonce):raise ValueError()
            return claims
        except Exception:
            raise ValueError('로그인 서명 또는 계정 확인에 실패했습니다. 새 로그인을 시작하세요.') from None

    def complete(self,query):
        with self.lock:
            attempt=self.pending
            if not attempt or attempt['expires']<time.time() or not secrets.compare_digest(query.get('state',''),attempt['state']):
                raise ValueError('로그인 요청이 만료되었거나 이 리더에서 시작한 요청이 아닙니다.')
            self.pending=None
            if query.get('error'):
                self.last_error=safe_error(query['error']);raise ValueError(self.last_error)
            client=query.get('client_id') or attempt['client']
            if not client or client=='dynamic_agent_client' or len(client)>256:
                raise ValueError('OpenAI에서 앱 등록 정보를 받지 못했습니다.')
            if attempt['client'] and client!=attempt['client']:raise ValueError('이전 로그인과 다른 앱 등록 정보입니다.')
            code=query.get('code','')
            if not code or len(code)>8192:raise ValueError('로그인 확인 코드를 받지 못했습니다.')
            try:
                tokens=self._json(TOKEN_URL,dict(grant_type='authorization_code',client_id=client,code=code,
                    code_verifier=attempt['verifier'],redirect_uri=attempt['redirect'],resource=RESOURCE))
                claims=self.validate_identity(tokens.get('id_token'),client,attempt['nonce'])
                if attempt['subject'] and claims['sub']!=attempt['subject']:
                    raise ValueError('선택한 계정과 다른 계정입니다. 다른 계정 추가로 로그인하세요.')
                scopes=tokens.get('scope','').split()
                if tokens.get('token_type','').lower()!='bearer':raise ValueError('로그인 연결 방식을 확인할 수 없습니다.')
                previous=self.record
                self.record=dict(client_id=client,subject=claims['sub'],email=claims.get('email',''),
                    issuer=ISSUER,ext_agent_host_id=self.host_id(),id_token=tokens['id_token'],
                    access_token=tokens.get('access_token',''),refresh_token=tokens.get('refresh_token',''),
                    scopes=scopes,expires_at=time.time()+int(tokens.get('expires_in',3600)),
                    welcomed=bool(previous.get('subject')==claims['sub'] and previous.get('welcomed')))
                try:self._save()
                except Exception:self.record=previous;raise
                self.catalog=[];self.catalog_at=0;self.last_error=''
            except HTTPError as exc:
                self.last_error='OpenAI 로그인 연결에 실패했습니다. 새 로그인을 시작하세요. (HTTP '+str(exc.code)+')'
                raise ValueError(self.last_error) from None
            if not REQUIRED<=set(scopes):self.last_error='로그인은 되었지만 ChatGPT 구독 사용 권한이 승인되지 않았습니다. 다시 로그인해 권한을 확인하세요.'
            return self.status()

    def access_token(self):
        with self.lock:
            if not REQUIRED<=set(self.record.get('scopes',[])):raise ValueError('먼저 Continue with ChatGPT로 로그인해 구독 사용을 승인하세요.')
            if self.record.get('access_token') and self.record.get('expires_at',0)>time.time()+90:return self.record['access_token']
            refresh=self.record.get('refresh_token')
            if not refresh:raise ValueError('ChatGPT 로그인이 만료되었습니다. 다시 로그인하세요.')
            try:
                result=self._json(TOKEN_URL,dict(grant_type='refresh_token',client_id=self.record['client_id'],refresh_token=refresh,resource=RESOURCE))
            except (HTTPError,URLError):raise ValueError('ChatGPT 로그인을 갱신하지 못했습니다. 다시 로그인하세요.') from None
            if not result.get('access_token'):raise ValueError('새 로그인 연결 정보를 받지 못했습니다.')
            updated=dict(self.record,access_token=result['access_token'],refresh_token=result.get('refresh_token',refresh),
                         expires_at=time.time()+int(result.get('expires_in',3600)))
            if 'scope' in result:updated['scopes']=result['scope'].split()
            if not REQUIRED<=set(updated['scopes']):raise ValueError('ChatGPT 구독 사용 권한이 해제되었습니다.')
            self.record=updated;self._save()
            return self.record['access_token']

    def models(self):
        with self.lock:
            if self.catalog and time.time()-self.catalog_at<300:return list(self.catalog)
            try:result=self._json(RESOURCE+'/models',bearer=self.access_token())
            except HTTPError as exc:raise ValueError('이 계정의 ChatGPT 모델 목록을 가져오지 못했습니다. (HTTP '+str(exc.code)+')') from None
            self.catalog=[dict(id=m['slug'],name=m.get('display_name',m['slug']),reasoning_levels=reasoning_levels(m.get('supported_reasoning_levels',[]))) for m in result.get('models',[])
                if m.get('visibility')=='list' and isinstance(m.get('slug'),str)]
            self.catalog_at=time.time()
            return list(self.catalog)

    def infer(self,instructions,messages,model=None,reasoning_effort=None):
        catalog=self.models()
        if not catalog:raise ValueError('이 계정에서 사용할 수 있는 ChatGPT 모델이 없습니다.')
        chosen=model or catalog[0]['id']
        if chosen not in {m['id'] for m in catalog}:
            if chosen=='gpt-6-luna':raise ValueError('이 계정에서 GPT-6 Luna를 사용할 수 없습니다. 다른 모델로 전환하지 않습니다.')
            raise ValueError('로그인한 계정에서 사용할 모델을 선택하세요.')
        body=dict(model=chosen,input=messages,instructions=instructions,store=False,stream=True)
        levels=next(m for m in catalog if m['id']==chosen).get('reasoning_levels',[])
        effort=reasoning_effort if reasoning_effort not in (None,'') else (levels[0] if levels else None)
        if effort is not None:
            if effort not in levels:raise ValueError('선택한 모델이 지원하는 추론 수준을 선택하세요.')
            body['reasoning']=dict(effort=effort)
        req=Request(RESOURCE+'/responses',data=json.dumps(body).encode(),headers={
            'Authorization':'Bearer '+self.access_token(),'Content-Type':'application/json','Accept':'text/event-stream'})
        try:
            with self.open(req,timeout=150) as response:
                answer,usage=read_stream(response,chosen)
                if effort is not None:usage['reasoning_effort']=effort
                return answer,usage
        except HTTPError as exc:
            if exc.code==401:raise ValueError('ChatGPT 로그인이 만료되었거나 해제되었습니다. 다시 로그인하세요.') from None
            if exc.code==429:raise ValueError('ChatGPT 사용 한도에 도달했습니다. ChatGPT 사용량 설정을 확인하세요. 유료 API로 자동 전환하지 않습니다.') from None
            raise ValueError('ChatGPT 요청 실패 (HTTP '+str(exc.code)+'). 유료 API로 전환하지 않았습니다.') from None

    def welcome(self):
        with self.lock:
            if self.record.get('subject'):self.record['welcomed']=True;self._save()

    def logout(self):
        with self.lock:
            confirmed=True;refresh=self.record.get('refresh_token')
            if refresh:
                try:
                    endpoint=self.discovery().get('revocation_endpoint')
                    if not endpoint:raise ValueError()
                    req=Request(endpoint,data=urlencode(dict(token=refresh,token_type_hint='refresh_token',client_id=self.record['client_id'])).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
                    with self.open(req,timeout=15) as response:confirmed=response.status==200
                except Exception:confirmed=False
            self.record={k:v for k,v in self.record.items() if k in ('client_id','subject','email','issuer','ext_agent_host_id','welcomed')}
            self.pending=None;self.catalog=[];self.catalog_at=0;self.last_error=''
            self._save()
            return dict(ok=True,remote_revocation_confirmed=confirmed)

def read_stream(response,model):
    chunks=[];event=[];total=0;completed=False;usage={}
    def process(lines):
        nonlocal completed,usage
        payload='\n'.join(lines)
        if not payload or payload=='[DONE]':return
        try:data=json.loads(payload)
        except json.JSONDecodeError:raise ValueError('ChatGPT 응답 형식을 읽지 못했습니다.') from None
        kind=data.get('type','')
        if kind=='response.output_text.delta':chunks.append(data.get('delta',''))
        elif kind in ('error','response.failed'):
            err=data.get('response',{}).get('error') or data.get('error') or data
            raise ValueError(safe_error(err.get('code','')))
        elif kind=='response.incomplete':raise ValueError('ChatGPT 답변이 중간에 종료되었습니다. 완성된 답변으로 저장하지 않았습니다.')
        elif kind=='response.completed':
            completed=True;result=data.get('response',{});usage=result.get('usage',{}) or {}
            if not chunks:
                chunks.extend(part.get('text','') for item in result.get('output',[]) if item.get('type')=='message'
                    for part in item.get('content',[]) if part.get('type')=='output_text')
    for raw in response:
        total+=len(raw)
        if total>8_000_000:raise ValueError('ChatGPT 응답이 너무 커서 중단했습니다.')
        line=raw.decode('utf-8').rstrip('\r\n')
        if not line:
            process(event);event=[]
        elif line.startswith('data:'):event.append(line[5:].lstrip())
    if event:process(event)
    if not completed:raise ValueError('ChatGPT 연결이 완료되기 전에 끊겼습니다. 다시 질문하기 전에 상태를 확인하세요.')
    text=''.join(chunks).strip()
    if not text:raise ValueError('ChatGPT에서 텍스트 답변을 받지 못했습니다.')
    usage.update(billing_mode='chatgpt-plan',model=model)
    return text,usage
