'use strict';
(() => {
  const dialog=$('linkEditor');
  let pageData=null,sourceId=null,drafts=new Map(),saving=false,reviewOnly=false;
  const linkFor=id=>pageData.sentence_links.find(l=>l.source===id);
  const choice=id=>drafts.get(id)||linkFor(id);
  const targetIds=id=>choice(id)?.targets||[];
  function stage(targets,reset=false){
    const saved=linkFor(sourceId);
    const same=JSON.stringify(targets)===JSON.stringify(saved.targets);
    if(same&&!reset)drafts.delete(sourceId);
    else if(reset&&saved.method!=='manual')drafts.delete(sourceId);
    else drafts.set(sourceId,{source:sourceId,targets,reset});
    renderSelection();
  }
  function renderSelection(){
    const source=pageData.sentences_en.find(s=>s.id===sourceId),selected=new Set(targetIds(sourceId));
    $('linkSourcePreview').textContent=source?.text||'왼쪽에서 원문을 선택하세요.';
    $('linkTargetPreview').textContent=pageData.sentences_ko.filter(s=>selected.has(s.id)).map(s=>s.text).join('\n\n')||'연결 없음 · 번역문을 체크하거나 이 상태로 저장해 잘못된 연결을 해제하세요.';
    $('linkTargetCount').textContent=selected.size+'개 연결';
    const current=linkFor(sourceId);
    $('linkMethod').textContent=drafts.has(sourceId)?(drafts.get(sourceId).reset?'자동 연결 복원 예정':'수정 중 · 미저장'):current.method==='manual'?'고정 · 직접 지정':current.status==='unlinked'?'확인 필요 · 미연결':current.status==='needs-review'?'확인 필요':'규칙 기반 후보';
    $('linkRuleReason').textContent=(current.region_label||'본문')+' · '+(current.review_reasons?.join(' · ')||current.evidence?.join(' · ')||'영역·길이·위치 규칙으로 추정 · 의미 일치 미검증');
    $('linkCandidates').replaceChildren();
    if(['unlinked','needs-review'].includes(current.status)&&!drafts.has(sourceId))for(const [i,ids] of (current.candidates||[]).entries()){
      const b=document.createElement('button');b.type='button';b.textContent='후보 '+(i+1)+' · 번역 '+ids.map(id=>pageData.sentences_ko.findIndex(s=>s.id===id)+1).join(', ');
      b.title=pageData.sentences_ko.filter(s=>ids.includes(s.id)).map(s=>s.text).join(' / ');b.onclick=()=>{stage(ids.slice());$('linkTargets').querySelector('.chosen')?.scrollIntoView({block:'center'});};$('linkCandidates').append(b);
    }
    $('linkPending').textContent=drafts.size?drafts.size+'개 원문 연결 변경 · 아직 저장하지 않음':'변경 사항 없음';
    $('saveConnections').disabled=!drafts.size||saving;
    document.querySelectorAll('#linkSources .link-choice').forEach(el=>{
      const active=el.dataset.id===sourceId;el.classList.toggle('chosen',active);el.querySelector('input').checked=active;
      el.classList.toggle('modified',drafts.has(el.dataset.id));
      const link=linkFor(el.dataset.id),suspect=['needs-review','unlinked'].includes(link.status);
      el.hidden=reviewOnly&&!suspect&&!drafts.has(el.dataset.id)&&!active;
      el.classList.toggle('suspect',suspect);el.title=link.review_reasons?.join(' · ')||'';
      el.querySelector('.link-choice-status').textContent=(drafts.has(el.dataset.id)?'미저장 · ':suspect?'⚠ 확인 필요 · ':'')+(link.region_label||'')+' · '+targetIds(el.dataset.id).length+'개 연결';
    });
    document.querySelectorAll('#linkTargets .link-choice').forEach(el=>{const active=selected.has(el.dataset.id);el.classList.toggle('chosen',active);el.querySelector('input').checked=active;});
  }
  function makeChoice(s,index,side){
    const label=document.createElement('label');label.className='link-choice';label.dataset.id=s.id;
    const input=document.createElement('input');input.type=side==='en'?'radio':'checkbox';input.name=side==='en'?'linkSource':'linkTarget';input.value=s.id;input.setAttribute('aria-label',(side==='en'?'원문 ':'번역 ')+(index+1)+' · '+s.text);
    const body=document.createElement('span');body.className='link-choice-body';
    const heading=document.createElement('span');heading.className='link-choice-heading';
    const number=document.createElement('b');number.textContent=String(index+1).padStart(2,'0');
    const status=document.createElement('small');status.className='link-choice-status';
    if(side==='ko'){
      const shared=pageData.sentence_links.filter(l=>l.targets.includes(s.id)).length;
      status.textContent=shared>1?shared+'개 원문과 연결 중':'';
    }
    heading.append(number,status);
    const text=document.createElement('span');text.className='link-choice-text';text.textContent=s.text;
    const id=document.createElement('small');id.className='link-choice-id';id.textContent=s.id;
    body.append(heading,text,id);label.append(input,body);
    input.onchange=()=>{
      if(side==='en'){
        sourceId=s.id;renderSelection();
        $('linkTargets').querySelector('.chosen')?.scrollIntoView({block:'center'});
      }else{
        const selected=new Set(targetIds(sourceId));if(input.checked)selected.add(s.id);else selected.delete(s.id);
        stage(pageData.sentences_ko.filter(t=>selected.has(t.id)).map(t=>t.id));
      }
    };
    return label;
  }
  $('editConnections').onclick=()=>{
    if(!state.paper||!state.data?.sentences_en.length){toast('먼저 연결을 수정할 논문 페이지를 여세요.');return;}
    window.WordTools?.beforePageChange();pageData=state.data;drafts=new Map();reviewOnly=false;$('filterReviewLinks').setAttribute('aria-pressed','false');
    sourceId=state.side==='en'&&pageData.sentences_en.some(s=>s.id===state.anchor)?state.anchor:
      pageData.sentence_links.find(l=>l.targets.includes(state.anchor))?.source||pageData.sentences_en[0].id;
    $('linkPageLabel').textContent='p. '+state.page;
    $('linkSources').replaceChildren(...pageData.sentences_en.map((s,i)=>makeChoice(s,i,'en')));
    $('linkTargets').replaceChildren(...pageData.sentences_ko.map((s,i)=>makeChoice(s,i,'ko')));
    renderSelection();dialog.showModal();
    $('linkSources').querySelector('.chosen')?.scrollIntoView({block:'center'});
    $('linkTargets').querySelector('.chosen')?.scrollIntoView({block:'center'});
  };
  $('filterReviewLinks').onclick=()=>{reviewOnly=!reviewOnly;$('filterReviewLinks').setAttribute('aria-pressed',String(reviewOnly));renderSelection();};
  window.LinkEditor={openReview:()=>{$('editConnections').click();if(!dialog.open)return;const first=pageData.sentence_links.find(l=>['needs-review','unlinked'].includes(l.status));if(first)sourceId=first.source;reviewOnly=true;$('filterReviewLinks').setAttribute('aria-pressed','true');renderSelection();$('linkSources').querySelector('.chosen')?.scrollIntoView({block:'center'});$('linkTargets').querySelector('.chosen')?.scrollIntoView({block:'center'});}};
  function close(){if(!saving){dialog.close();drafts.clear();}}
  $('closeLinkEditor').onclick=close;$('cancelConnections').onclick=close;
  dialog.addEventListener('cancel',e=>{if(saving)e.preventDefault();});
  $('resetConnection').onclick=()=>stage(linkFor(sourceId).automatic_targets||[],true);
  $('saveConnections').onclick=guard(async()=>{
    if(saving||!drafts.size)return;
    saving=true;$('saveConnections').disabled=true;
    dialog.querySelectorAll('input').forEach(input=>input.disabled=true);
    $('saveConnections').textContent='저장 중…';
    for(const button of ['closeLinkEditor','cancelConnections','resetConnection'])$(button).disabled=true;
    try{
      await api('/api/sentence-link',{paper:state.paper.id,page:state.page,updates:[...drafts.values()]});
      state.data=await api(`/api/page?paper=${state.paper.id}&page=${state.page}`);
      renderSentences();renderOverlay('en');renderOverlay('ko');renderAlignmentStatus();await selectSentence('en',sourceId);dialog.close();toast('수동 연결을 저장하고 주변 자동 연결을 다시 계산했습니다.');drafts.clear();
    }finally{
      saving=false;$('saveConnections').textContent='연결 저장';
      dialog.querySelectorAll('input').forEach(input=>input.disabled=false);
      for(const button of ['closeLinkEditor','cancelConnections','resetConnection'])$(button).disabled=false;
      if(dialog.open)renderSelection();
    }
  });
})();
