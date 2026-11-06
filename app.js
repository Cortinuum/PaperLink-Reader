'use strict';
const $=id=>document.getElementById(id),token=document.querySelector('meta[name="reader-token"]').content;
const EFFORT_LABELS={none:'없음',minimal:'최소',low:'낮음',medium:'중간',high:'높음',xhigh:'매우 높음',max:'최대',ultra:'울트라'};
const state={papers:[],paper:null,page:1,data:null,anchor:null,side:'en',context:null,history:[],busy:false,epoch:0,selection:0,mode:'pdf'};
async function api(path,data){const r=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Reader-Token':token},body:JSON.stringify(data)});const out=await r.json();if(!r.ok)throw Error(out.error||'요청 실패');return out;}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,5000);}
const guard=fn=>(...args)=>{try{return Promise.resolve(fn(...args)).catch(e=>toast(e.message));}catch(e){toast(e.message);}};
const allSentences=side=>state.data['sentences_'+side];
const payload=()=>{if(!state.anchor)throw Error('먼저 문장을 선택하세요.');return {paper:state.paper.id,page:state.page,side:state.side,anchor:state.anchor};};
function setChat(open){document.body.classList.toggle('chat-closed',!open);$('toggleChat').setAttribute('aria-expanded',String(open));}
function setMode(mode){state.mode=mode;$('sentenceReader').hidden=mode!=='sentence';$('viewport').hidden=mode!=='pdf';$('sentenceMode').classList.toggle('active',mode==='sentence');$('pdfMode').classList.toggle('active',mode==='pdf');$('zoom').hidden=mode!=='pdf';$('toggleBoxes').hidden=mode!=='pdf';$('wordSelect').hidden=mode!=='pdf';window.WordTools?.modeChanged(mode);}

async function library(){
  const info=await api('/api/library');state.papers=info.papers;state.removedPapers=info.removed||[];state.reviewCatalog=info.review_catalog;syncReviewQuestion();
  updateAccount(info.account).catch(e=>toast(e.message));renderLibrary();
  if(!info.papers.length){
    ++state.epoch;clearSelection();state.paper=null;state.data=null;setMode('pdf');$('notes').replaceChildren();
    $('spread').hidden=true;$('libraryEmpty').hidden=false;$('title').textContent='원문과 번역 PDF를 불러오세요.';$('pageStatus').textContent='내 논문 → PDF 불러오기';$('total').textContent='';$('page').value=1;$('page').disabled=true;$('prev').disabled=true;$('next').disabled=true;return;
  }
  if(!state.paper||!info.papers.some(p=>p.id===state.paper.id))await openPaper(info.papers[0]);
}
function renderLibrary(){
  $('papers').replaceChildren();const trash=!!state.libraryTrash;
  $('togglePaperTrash').textContent=trash?'← 내 논문으로':'휴지통 ('+(state.removedPapers?.length||0)+')';$('togglePaperTrash').setAttribute('aria-pressed',String(trash));
  const papers=trash?(state.removedPapers||[]):state.papers;
  if(!papers.length){const empty=document.createElement('p');empty.className='library-list-empty';empty.textContent=trash?'휴지통이 비어 있습니다.':'등록한 논문쌍이 없습니다.';$('papers').append(empty);}
  for(const p of papers){
    const card=document.createElement('article');card.className='paper-card';card.dataset.paperId=p.id;
    const item=document.createElement(trash?'div':'button');item.className='paper';item.dataset.id=p.id;item.classList.toggle('active',!trash&&state.paper?.id===p.id);item.append(document.createTextNode(p.title.replace(/^\d+_/,'')));
    const small=document.createElement('small');small.textContent=p.pages+'쪽 · '+(trash?(p.replaced_by?'PDF 변경 전 버전':'휴지통'):'영어 → 한국어');item.append(small);
    if(!trash)item.onclick=guard(async()=>{await openPaper(p);openLibrary(false);$(state.mode==='pdf'?'viewport':'sentenceReader').focus();});
    const actions=document.createElement('div');actions.className='paper-actions';
    if(trash){const restore=document.createElement('button');restore.textContent='복원';restore.setAttribute('aria-label',p.title+' 복원');restore.onclick=guard(async()=>{await api('/api/library/restore',{paper:p.id});state.libraryTrash=false;await library();toast('논문쌍을 복원했습니다.');});actions.append(restore);}
    else{
      const edit=document.createElement('button');edit.textContent='PDF 변경';edit.setAttribute('aria-label',p.title+' PDF 변경');edit.onclick=()=>window.PaperImport.edit(p);
      const remove=document.createElement('button');remove.textContent='제거';remove.setAttribute('aria-label',p.title+' 제거');remove.onclick=guard(async()=>{await api('/api/library/trash',{paper:p.id});await library();toast('휴지통으로 옮겼습니다. 내 논문 → 휴지통에서 복원할 수 있습니다.');});actions.append(edit,remove);
    }
    card.append(item,actions);$('papers').append(card);
  }
}
$('togglePaperTrash').onclick=()=>{state.libraryTrash=!state.libraryTrash;renderLibrary();};
async function openPaper(p){$('page').disabled=false;$('spread').hidden=false;$('libraryEmpty').hidden=true;state.paper=p;let saved={};try{saved=JSON.parse(localStorage.getItem('paperlink-position')||'{}');}catch{}state.page=saved.paper===p.id?Math.min(p.pages,Math.max(1,saved.page||1)):1;$('title').textContent=p.title.replace(/^\d+_/, '');$('total').textContent=`/ ${p.pages}`;$('page').max=p.pages;document.querySelectorAll('.paper').forEach(b=>b.classList.toggle('active',b.dataset.id===p.id));await showPage();}
function clearSelection(){window.WordTools?.beforePageChange();state.selection++;state.anchor=null;state.context=null;state.history=[];$('anchorLabel').textContent='';$('selection').hidden=true;$('empty').hidden=false;$('answers').replaceChildren();}
async function showPage(){const epoch=++state.epoch;clearSelection();$('page').value=state.page;$('prev').disabled=state.page<=1;$('next').disabled=state.page>=state.paper.pages;const data=await api(`/api/page?paper=${state.paper.id}&page=${state.page}`);if(epoch!==state.epoch)return;state.data=data;for(const side of ['en','ko']){$(side+'Img').src=`/api/image?paper=${state.paper.id}&page=${state.page}&side=${side}`;renderOverlay(side);}renderSentences();localStorage.setItem('paperlink-position',JSON.stringify({paper:state.paper.id,page:state.page}));$('viewport').scrollTop=0;$('sentenceReader').scrollTop=0;$('subtitle').textContent='문장 클릭 → GPT 비교';$('pageStatus').textContent=`영어 ${data.sentences_en.length}문장 · 한국어 ${data.sentences_ko.length}문장 · 자동 문장 연결 후보`;renderNotes();}
async function turnPage(delta){if(!state.paper)return;const next=Math.min(state.paper.pages,Math.max(1,state.page+delta));if(next===state.page)return;state.page=next;await showPage();}
function renderOverlay(side){const layer=$(side+'Overlay');layer.replaceChildren();const [w,h]=state.data.size;allSentences(side).forEach((s,i)=>{for(const rect of s.rects){const el=document.createElement('button');el.className='region';el.dataset.id=s.id;el.title=`${side==='en'?'원문':'번역'} 문장 ${i+1}: ${s.text}`;el.setAttribute('aria-label',el.title);const [x0,y0,x1,y1]=rect;Object.assign(el.style,{left:x0/w*100+'%',top:y0/h*100+'%',width:(x1-x0)/w*100+'%',height:(y1-y0)/h*100+'%'});el.onclick=guard(()=>selectSentence(side,s.id));el.ondblclick=e=>{if(window.WordTools?.lookupAt(side,e)){e.preventDefault();e.stopPropagation();}else setChat(true);};layer.append(el);}});window.WordTools?.render(side);}
function sentenceButton(s,side){const b=document.createElement('button');b.className='sentence-text '+(side==='en'?'english-sentence':'');b.dataset.id=s.id;b.dataset.side=side;b.textContent=s.text;b.onclick=guard(()=>selectSentence(side,s.id));b.ondblclick=()=>setChat(true);return b;}
function renderSentences(){const list=$('sentenceReader');list.replaceChildren();const note=document.createElement('div');note.className='sentence-notice';note.textContent='한 문장씩 읽고 선택하세요. GPT 비교는 Ctrl+I · 자동 문장 연결은 확인이 필요합니다. 합치거나 나뉜 번역은 여러 문장이 함께 표시됩니다.';list.append(note);const ko=new Map(state.data.sentences_ko.map(s=>[s.id,s])),used=new Set();for(const [i,s] of state.data.sentences_en.entries()){const link=state.data.sentence_links.find(l=>l.source===s.id);const row=document.createElement('div');row.className='sentence-row';row.dataset.source=s.id;const en=document.createElement('div');en.className='sentence-cell';const label=document.createElement('small');label.textContent=`${String(i+1).padStart(2,'0')} · ${s.id}`;en.append(label,sentenceButton(s,'en'));const kr=document.createElement('div');kr.className='sentence-cell';for(const id of link.targets){const t=ko.get(id);if(t){kr.append(sentenceButton(t,'ko'));used.add(id);}}if(!kr.children.length){const missing=document.createElement('span');missing.className='unmatched';missing.textContent='대응 문장을 지정하세요';kr.append(missing);}const action=document.createElement('button');action.className='sentence-ask';action.textContent='↗';action.title='이 문장을 GPT 비교 패널에서 질문';action.setAttribute('aria-label',`문장 ${i+1} GPT 비교`);action.onclick=guard(async()=>{await selectSentence('en',s.id);setChat(true);$('question').focus();});row.append(en,kr,action);list.append(row);}for(const s of state.data.sentences_ko.filter(s=>!used.has(s.id))){const row=document.createElement('div');row.className='sentence-row unmatched-row';const en=document.createElement('div');en.className='sentence-cell unmatched';en.textContent='대응 원문 미지정';const kr=document.createElement('div');kr.className='sentence-cell';kr.append(sentenceButton(s,'ko'));row.append(en,kr);list.append(row);}}
async function selectSentence(side,id){const selection=++state.selection;state.anchor=id;state.side=side;state.context=null;state.history=[];$('answers').replaceChildren();$('selection').hidden=false;$('empty').hidden=true;$('anchorLabel').textContent=`p.${state.page}`;$('anchorLabel').title=id;$('chatReadingArea').scrollTop=0;$('focusedSentence').textContent=allSentences(side).find(s=>s.id===id).text;const request=payload();await updateContext(selection);const saved=await api(`/api/history?paper=${request.paper}&page=${request.page}&anchor=${id}`);if(selection!==state.selection)return;for(const chat of saved.chats){appendAnswer(chat.question,chat.answer,JSON.parse(chat.usage));state.history.push({role:'user',content:historyQuestion(chat.question,JSON.parse(chat.usage))},{role:'assistant',content:chat.answer});}}
async function updateContext(selection=state.selection){const context=await api('/api/context',payload());if(selection!==state.selection)return;state.context=context;$('english').textContent=context.english.map(s=>s.text).join('\n\n')||'대응 영어 문장 없음';$('korean').textContent=context.korean.map(s=>s.text).join('\n\n')||'대응 한국어 문장 없음';$('sourceIds').textContent=context.english.map(s=>s.id).join(', ');$('alignment').textContent=context.alignment+'. 필요하면 문장 연결을 수정하세요.';highlight();}
function highlight(){const ctx=state.context,linked=ctx?new Set([...ctx.english,...ctx.korean].map(s=>s.id)):new Set();document.querySelectorAll('.region,.sentence-text').forEach(el=>{el.classList.toggle('selected',el.dataset.id===state.anchor);el.classList.toggle('linked',linked.has(el.dataset.id)&&el.dataset.id!==state.anchor);});}
function appendAnswer(question,answer,usage={},follow=false){
  const div=document.createElement('article');div.className='answer';
  const questionBox=document.createElement('section');questionBox.className='chat-message chat-question';questionBox.setAttribute('aria-label','내 질문');
  const questionLabel=document.createElement('b');questionLabel.className='chat-message-label';questionLabel.textContent='내 질문';
  const questionText=document.createElement('div');questionText.className='chat-question-text';questionText.textContent=question;questionBox.append(questionLabel,questionText);if(usage.review_options?.length){const selected=document.createElement('div');selected.className='chat-request-options';selected.textContent='추가 검토: '+usage.review_options.join(', ');questionBox.append(selected);}
  const answerBox=document.createElement('section');answerBox.className='chat-message chat-answer';answerBox.setAttribute('aria-label','GPT 답변');
  const answerLabel=document.createElement('b');answerLabel.className='chat-message-label';answerLabel.textContent='GPT 답변'+(usage.model?' · '+usage.model:'');
  const text=document.createElement('div');text.className='markdown-body';
  if(window.PaperMarkdown)text.innerHTML=window.PaperMarkdown.render(answer);else{text.textContent=answer;text.style.whiteSpace='pre-wrap';}
  const meta=document.createElement('div');meta.className='hint';meta.textContent=`입력 ${usage.input_tokens||0} / 출력 ${usage.output_tokens||0} 토큰 · `+(usage.billing_mode==='chatgpt-plan'?'ChatGPT 구독 사용':`이전 API 기록 · 추정 $${Number(usage.estimated_usd||0).toFixed(5)}`);
  if(usage.reasoning_effort)meta.textContent+=' · 추론 '+(EFFORT_LABELS[usage.reasoning_effort]||usage.reasoning_effort);answerBox.append(answerLabel,text,meta);div.append(questionBox,answerBox);$('answers').prepend(div);if(follow)div.scrollIntoView({block:'nearest',behavior:'smooth'});
}
function renderNotes(){$('notes').replaceChildren();for(const n of state.data.notes){const d=document.createElement('div');d.className='note';d.textContent=n.body;const meta=document.createElement('small');meta.textContent=`p.${n.page} · ${n.anchor}`;d.append(meta);$('notes').append(d);}}
async function ask(){if(state.busy)return;if(!state.context||state.context.missing_match)throw Error('대응 문장 연결을 먼저 지정하세요.');if(!state.account?.plan_enabled){$('config').showModal();throw Error('Continue with ChatGPT로 먼저 로그인하세요.');}if(!$('paid').checked)throw Error('선택 근거 전송 및 ChatGPT 구독 사용에 동의해 주세요.');const request=payload(),question=QuestionPrompt.userText($('question').value).trim(),selection=state.selection;if(!$('chatModel').value)throw Error('사용할 모델을 선택하세요.');if(!question)throw Error('질문을 입력하세요.');state.busy=true;$('ask').disabled=true;$('ask').textContent='답변 중…';try{const result=await api('/api/ask',{...request,question,allow_plan:true,model:$('chatModel').value,reasoning_effort:$('reasoningEffort').value||null,review_options:selectedReviewOptions().join(','),history:state.history});if(selection!==state.selection){toast('이전 문장의 답변이 저장됐습니다. 해당 문장을 다시 선택하세요.');return;}state.history.push({role:'user',content:historyQuestion(question,result.usage)},{role:'assistant',content:result.answer});appendAnswer(question,result.answer,result.usage,true);$('question').value='';syncReviewQuestion();}finally{state.busy=false;$('ask').disabled=false;$('ask').textContent='질문 ↗';}}
$('prev').onclick=guard(()=>turnPage(-1));$('next').onclick=guard(()=>turnPage(1));$('page').onchange=guard(async()=>{state.page=Math.min(state.paper.pages,Math.max(1,Math.trunc(Number($('page').value)||1)));await showPage();});function applyZoom(){$('spread').style.width=(Number($('zoom').value)*100)+'%';}$('zoom').onchange=applyZoom;$('toggleBoxes').onclick=()=>{$('spread').classList.toggle('show-boxes');};$('sentenceMode').onclick=()=>setMode('sentence');$('pdfMode').onclick=()=>setMode('pdf');$('toggleChat').onclick=()=>setChat(document.body.classList.contains('chat-closed'));$('closeChat').onclick=()=>{setChat(false);$('sentenceReader').focus();};$('shortcuts').onclick=()=>$('shortcutDialog').showModal();
document.addEventListener('keydown',guard(async e=>{if(e.isComposing||e.defaultPrevented)return;const editing=e.target.closest('input,textarea,select,[contenteditable="true"],[role="textbox"]');if((e.ctrlKey||e.metaKey)&&!e.altKey&&!e.shiftKey&&e.key.toLowerCase()==='i'){e.preventDefault();setChat(document.body.classList.contains('chat-closed'));return;}if(document.querySelector('dialog[open]'))return;if(editing)return;if(e.key==='Escape'){if($('libraryDrawer').classList.contains('open'))openLibrary(false);else setChat(false);return;}if(e.ctrlKey||e.metaKey||e.altKey)return;if(e.key==='?'){e.preventDefault();$('shortcutDialog').showModal();return;}if(e.shiftKey)return;const delta={'ArrowLeft':-1,'PageUp':-1,'ArrowRight':1,'PageDown':1}[e.key];if(delta){e.preventDefault();await turnPage(delta);}else if((e.key==='Home'||e.key==='End')&&state.paper){e.preventDefault();state.page=e.key==='Home'?1:state.paper.pages;await showPage();}}));
let drag=null;const sash=$('resizeChat');sash.onpointerdown=e=>{drag=e.clientX;sash.setPointerCapture(e.pointerId);};sash.onpointermove=e=>{if(drag===null)return;document.documentElement.style.setProperty('--chat-width',Math.min(window.innerWidth*.6,Math.max(300,window.innerWidth-e.clientX))+'px');};sash.onpointerup=()=>{drag=null;};sash.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();e.stopPropagation();const current=$('chatPanel').getBoundingClientRect().width;document.documentElement.style.setProperty('--chat-width',Math.min(window.innerWidth*.6,Math.max(300,current+(e.key==='ArrowLeft'?30:-30)))+'px');}};
$('ask').onclick=guard(ask);$('saveNote').onclick=guard(async()=>{await api('/api/note',{...payload(),body:$('note').value});$('note').value='';state.data=await api(`/api/page?paper=${state.paper.id}&page=${state.page}`);renderNotes();toast('메모를 저장했습니다.');});$('refresh').onclick=guard(async()=>{await library();toast('목록을 갱신했습니다.');});$('export').onclick=guard(async()=>{if(!state.paper)throw Error('논문을 선택하세요.');const data=await api('/api/export?paper='+state.paper.id);const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=state.paper.title+'_읽기기록.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});


function openLibrary(open){$('libraryDrawer').classList.toggle('open',open);$('libraryHandle').setAttribute('aria-expanded',String(open));}
$('libraryDrawer').onpointerenter=()=>openLibrary(true);
$('libraryDrawer').onpointerleave=()=>openLibrary(false);
$('libraryHandle').onclick=()=>openLibrary(true);
$('libraryDrawer').addEventListener('focusout',e=>{if(!e.currentTarget.contains(e.relatedTarget))openLibrary(false);});
document.addEventListener('pointerdown',e=>{if(!$('libraryDrawer').contains(e.target))openLibrary(false);});
let authPoll=null,authPopup=null;
async function updateAccount(account,reloadModels=false){
  const previous=state.account;state.account=account;
  const ready=!!account?.plan_enabled;
  $('settings').textContent=ready?'ChatGPT 계정':'ChatGPT 로그인';
  $('accountState').textContent=ready?'ChatGPT 구독 사용 · 로그인됨':'ChatGPT 계정으로 로그인하세요';
  $('panelLogin').hidden=ready;
  $('authMessage').textContent=account?.error||(ready?((account.email||'계정')+'에 연결되어 있습니다.'):'로그인 전입니다. API 키를 입력할 필요가 없습니다.');
  $('logout').disabled=!account?.connected;
  $('newAccount').hidden=!account?.connected;
  if(ready){
    if(reloadModels||!previous?.plan_enabled||!$('chatModel').options.length){
      const data=await api('/api/auth/models');state.models=data.models;const select=$('chatModel');const old=select.value;select.replaceChildren();
      for(const model of data.models){const opt=document.createElement('option');opt.value=model.id;opt.textContent=model.name;select.append(opt);}
      const chosen=data.models.some(m=>m.id===old)?old:data.default_model;
      if(chosen)select.value=chosen;
      else{const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='모델을 선택하세요';select.prepend(placeholder);select.value='';}
      select.disabled=!data.models.length;$('modelLabel').hidden=!data.models.length;updateReasoning();
      if(!data.models.length)toast('이 계정에서 사용할 수 있는 모델이 없습니다.');
    }
    if(account.needs_welcome&&!$('planWelcome').open){$('config').close();$('planWelcome').showModal();}
  }else{$('modelLabel').hidden=true;$('chatModel').replaceChildren();$('reasoningLabel').hidden=true;updateReasoning();}
}
async function beginLogin(newAccount=false){
  authPopup=window.open('about:blank','paperlink-sign-in','popup,width=580,height=780');
  try{
    const result=await api('/api/auth/start',{new_account:newAccount});
    if(authPopup){authPopup.opener=null;authPopup.location=result.url;}else{throw Error('로그인 창이 차단되었습니다. 이 리더의 팝업을 허용한 뒤 다시 눌러주세요.');}
    $('authMessage').textContent='OpenAI 로그인 창에서 계정과 권한을 확인하세요. 비밀번호는 그 창에서만 입력하세요.';
    clearInterval(authPoll);
    authPoll=setInterval(async()=>{
      try{
        const status=await api('/api/auth/status');
        if(!status.pending){clearInterval(authPoll);await updateAccount(status,true);if(status.plan_enabled){if(authPopup&&!authPopup.closed)authPopup.close();toast('ChatGPT 구독으로 연결했습니다.');}else if(status.error)toast(status.error);}
        else if(authPopup?.closed){clearInterval(authPoll);$('authMessage').textContent='로그인 창을 닫았습니다. 필요할 때 다시 로그인하세요.';}
      }catch(e){clearInterval(authPoll);toast(e.message);}
    },1800);
  }catch(e){if(authPopup&&!authPopup.closed)authPopup.close();throw e;}
}
$('settings').onclick=guard(async()=>{await updateAccount(await api('/api/auth/status'));$('config').showModal();});
$('login').onclick=guard(()=>beginLogin(false));$('panelLogin').onclick=guard(()=>{if(!$('config').open)$('config').showModal();return beginLogin(false);});
$('newAccount').onclick=guard(()=>beginLogin(true));
$('logout').onclick=guard(async()=>{if(state.busy)throw Error('답변이 끝난 후 로그아웃해 주세요.');const result=await api('/api/auth/logout',{});await updateAccount(await api('/api/auth/status'));toast(result.remote_revocation_confirmed?'로그아웃했습니다.':'이 PC에서 로그아웃했습니다. 서버 권한 해제는 확인되지 않았으므로 ChatGPT 설정에서 연결을 확인하세요.');});
$('welcomeDone').onclick=guard(async()=>{await api('/api/auth/welcome',{});$('planWelcome').close();});
applyZoom();setMode('pdf');library().catch(e=>toast(e.message));

function updateModelSummary(){const model=$('chatModel').selectedOptions[0]?.textContent||'기본: GPT-6 Luna';const effort=$('reasoningEffort').value;$('modelSummary').textContent=model+(effort?' · '+EFFORT_LABELS[effort]:'');}
$('chatModel').onchange=updateReasoning;
$('reasoningEffort').onchange=updateModelSummary;
$('question').addEventListener('input',fitQuestion);
$('question').addEventListener('blur',syncReviewQuestion);
document.querySelectorAll('input[name="reviewOption"]').forEach(input=>input.addEventListener('change',updateReviewSummary));
updateReviewSummary();

function selectedReviewOptions(){return [...document.querySelectorAll('input[name="reviewOption"]:checked')].map(input=>input.value);}
function updateReviewSummary(){
  const labels=[...document.querySelectorAll('input[name="reviewOption"]:checked')].map(input=>input.parentElement.textContent.trim());
  $('reviewSummary').textContent=labels.length?labels.join(', '):'선택 없음';$('reviewSummary').title=labels.join(', ');
  syncReviewQuestion();
}
function fitQuestion(){
  const input=$('question');input.style.height='auto';
  const minimum=selectedReviewOptions().length?145:76;
  input.style.height=Math.min(220,Math.max(minimum,input.scrollHeight+2))+'px';
}
function syncReviewQuestion(){
  if(!state.reviewCatalog)return;
  const input=$('question'),start=input.selectionStart,end=input.selectionEnd;
  const ownText=QuestionPrompt.userText(input.value);
  input.value=QuestionPrompt.compose(input.value,selectedReviewOptions(),state.reviewCatalog);
  input.setSelectionRange(Math.min(start,ownText.length),Math.min(end,ownText.length));
  fitQuestion();input.scrollTop=selectedReviewOptions().length?input.scrollHeight:0;
}
function historyQuestion(question,usage){return question+(usage?.review_options?.length?'\n추가 검토: '+usage.review_options.join(', '):'');}
function updateReasoning(){
  const model=state.models?.find(m=>m.id===$('chatModel').value),select=$('reasoningEffort');select.replaceChildren();
  const levels=model?.reasoning_levels||[];
  for(const value of levels){const option=document.createElement('option');option.value=value;option.textContent=EFFORT_LABELS[value]||value;select.append(option);}
  if(!levels.length){const option=document.createElement('option');option.value='';option.textContent='지원 설정 없음';select.append(option);}
  select.disabled=!levels.length;$('reasoningLabel').hidden=!model;if(levels.length)select.value=levels[0];updateModelSummary();
}
