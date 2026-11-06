'use strict';
(() => {
  const popup=$('wordPopup'),book=$('vocabularyDialog');
  let wordMode=false,draft=null,lookupSerial=0,listSerial=0,searchTimer=null;
  let dictionarySerial=0,dictionaryTimer=null;
  const drafts=new Map();
  const getFields=()=>({term:$('wordTermInput').value,general_meaning:$('wordGeneral').value,
    paper_meaning:$('wordSpecific').value,category:draft?.source?.category||'미분류',notes:draft?.source?.notes||''});
  const keyFor=d=>d.id?'entry:'+d.id:JSON.stringify(d.origin);
  function rememberDraft(){if(draft&&popup.open)drafts.set(keyFor(draft),getFields());}
  function clearPicked(){document.querySelectorAll('.word-selection-layer').forEach(el=>el.replaceChildren());document.querySelectorAll('.word-picked').forEach(el=>el.classList.remove('word-picked'));}
  function closeWord(){rememberDraft();lookupSerial++;dictionarySerial++;clearTimeout(dictionaryTimer);popup.close();clearPicked();}
  function fitPopup(){
    if(!popup.open)return;
    const rect=popup.getBoundingClientRect();
    popup.style.top=Math.max(12,Math.min(rect.top,innerHeight-rect.height-12))+'px';
    popup.style.left=Math.max(12,Math.min(rect.left,innerWidth-rect.width-12))+'px';
  }
  async function lookupDictionary(){
    clearTimeout(dictionaryTimer);const serial=++dictionarySerial,term=$('wordTermInput').value.trim();
    const area=$('dictionaryResults');area.replaceChildren();
    if(!term)return;
    area.textContent='사전 조회 중…';
    try{
      const result=await api('/api/dictionary?'+new URLSearchParams({term,side:draft?.source.side||'en'}));
      if(serial!==dictionarySerial||!popup.open)return;
      area.replaceChildren();
      if(!result.entries.length){area.textContent=result.message||'검색 결과가 없습니다.';return;}
      const posNames={'n.':'명사','v.':'동사','adj.':'형용사','adv.':'부사','prep.':'전치사','pron.':'대명사','conj.':'접속사','interj.':'감탄사','num.':'수사','det.':'한정사','phr.':'구'};
      const entries=result.entries.filter(entry=>entry.source!=='Quick English-Korean');
      const preferred=result.preferred_source||'Open English-Korean Dictionary';
      const primary=entries.find(entry=>entry.source===preferred)||entries.find(entry=>entry.source!=='PaperLink 공학 보충')||entries[0];
      if(!primary){area.textContent='검색 결과가 없습니다.';return;}
      const alternatives=document.createElement('details'),alternativeLabel=document.createElement('summary');alternatives.className='dictionary-alternatives';alternativeLabel.textContent='다른 사전·추가 결과 ('+(entries.length-1)+')';alternatives.append(alternativeLabel);
      alternatives.addEventListener('toggle',fitPopup);
      for(const entry of entries){
        const card=document.createElement('div');card.className='dictionary-entry';
        const heading=document.createElement('div');heading.className='dictionary-entry-title';
        const word=document.createElement('b');word.textContent=entry.headword;
        const source=document.createElement('small');source.textContent=entry.source==='PaperLink 공학 보충'?'공학 보충':entry.source==='Open English-Korean Dictionary'?'커뮤니티 보충':entry.source==='Quick English-Korean'?'Quick 영한 · 구판':'공개 사전';
        heading.append(word,source);card.append(heading);
        if(entry.matched_form){const form=document.createElement('small');form.className='dictionary-form';form.textContent=term+' → '+entry.headword+(entry.match_method==='lemma'?' · 기본형 후보':entry.match_method==='component'?' · 복합어 구성 단어':'');card.append(form);}
        for(const sense of entry.senses){
          const line=document.createElement('div');line.className='dictionary-sense';
          const meaning=document.createElement('span');meaning.textContent=(posNames[sense.pos]?'['+posNames[sense.pos]+'] ':'')+sense.meaning;
          const use=document.createElement('button');use.type='button';use.textContent='사용';use.title='뜻 추가에 넣기';use.setAttribute('aria-label',sense.meaning+' 뜻 사용');
          use.onclick=()=>{$('wordGeneral').value=sense.meaning;};line.append(meaning,use);card.append(line);
        }
        if(entry===primary){card.classList.add('dictionary-primary');area.append(card);}else alternatives.append(card);
      }
      if(alternatives.children.length>1)area.append(alternatives);
    }catch(error){if(serial===dictionarySerial)area.textContent='사전을 불러오지 못했습니다. '+error.message;}
    finally{if(serial===dictionarySerial)fitPopup();}
  }
  function updateLinks(){
    const text=$('wordTermInput').value.trim(),side=draft?.source.side||'en';
    $('wordUsageLookup').href='https://www.google.com/search?q='+encodeURIComponent(text+' 뜻');
  }
  function putFields(fields){$('wordTermInput').value=fields.term||'';$('wordGeneral').value=fields.general_meaning||'';$('wordSpecific').value=fields.paper_meaning||'';updateLinks();}
  function showMatches(matches){
    const area=$('wordMatches');area.replaceChildren();area.hidden=!matches?.length;
    if(!matches?.length)return;
    const title=document.createElement('b');title.className='saved-meaning-heading';title.textContent='저장된 뜻';area.append(title);
    for(const entry of matches){
      const div=document.createElement('div');div.className='word-match';
      if(entry.general_meaning){const meaning=document.createElement('strong');meaning.className='saved-meaning';meaning.textContent=entry.general_meaning;div.append(meaning);}
      if(entry.paper_meaning){const description=document.createElement('p');description.className='saved-description';description.textContent=entry.paper_meaning;div.append(description);}
      const source=document.createElement('small');source.textContent=`${entry.paper_title} · p.${entry.source_page}`;div.append(source);area.append(div);
    }
  }
  function showEditor(fields,matches,position,modal=false){
    putFields(drafts.get(keyFor(draft))||fields);showMatches(matches);
    $('wordHeading').textContent=draft.id?'단어장 수정':'단어 뜻 찾기';
    $('saveWord').textContent=draft.id?'수정 저장':'단어장 저장';
    $('wordSourceLabel').textContent=`${draft.source.paper_title} · p.${draft.source.source_page} · PDF 표기: ${draft.source.source_word}`;
    $('wordSourceLabel').title=$('wordSourceLabel').textContent;
    $('wordFormStatus').textContent='';
    if(!popup.open){if(modal)popup.showModal();else popup.show();}
    popup.style.left='12px';popup.style.top='12px';
    const rect=popup.getBoundingClientRect();
    const x=position?.x??(innerWidth-rect.width)/2,y=position?.y??(innerHeight-rect.height)/2;
    popup.style.left=Math.max(12,Math.min(innerWidth-rect.width-12,x))+'px';
    popup.style.top=Math.max(12,Math.min(innerHeight-rect.height-12,y))+'px';
    popup.scrollTop=0;
    lookupDictionary();
  }
  async function openWord(side,word,event){
    clearHover();rememberDraft();const serial=++lookupSerial;
    const origin={paper:state.paper.id,page:state.page,side,word_id:word.id};
    const response=await api('/api/word?'+new URLSearchParams(origin));
    if(serial!==lookupSerial)return;
    if(popup.open)popup.close();
    draft={origin,source:response.source,id:null};
    clearPicked();drawWord($(side+'WordSelection'),word);
    document.querySelectorAll('.word-picked').forEach(el=>el.classList.remove('word-picked'));
    document.querySelectorAll('.word-region').forEach(el=>el.classList.toggle('word-picked',el.dataset.wordId===word.id));
    showEditor({term:response.word.term},response.matches,{x:event?.clientX??100,y:(event?.clientY??100)+14});
  }
  function wordAt(side,event){
    if(!state.data||state.mode!=='pdf')return null;
    const rect=$(side+'Img').getBoundingClientRect(),size=state.data.size;
    const x=(event.clientX-rect.left)*size[0]/rect.width,y=(event.clientY-rect.top)*size[1]/rect.height;
    const candidates=(state.data['words_'+side]||[]).filter(w=>(w.rects||[w.bbox]).some(r=>r[0]-.5<=x&&x<=r[2]+.5&&r[1]-.5<=y&&y<=r[3]+.5));
    return candidates[0]||null;
  }
  function clearHover(){
    document.querySelectorAll('.word-hover-layer').forEach(el=>{el.replaceChildren();delete el.dataset.wordId;});
  }
  function drawWord(layer,word){
    layer.replaceChildren();
    const [width,height]=state.data.size;
    for(const [x0,y0,x1,y1] of word.rects||[word.bbox]){
      const box=document.createElement('span');box.className='word-hover-box';
      Object.assign(box.style,{left:x0/width*100+'%',top:y0/height*100+'%',width:(x1-x0)/width*100+'%',height:(y1-y0)/height*100+'%'});layer.append(box);
    }
  }
  function hoverAt(side,event){
    if(event.pointerType==='touch'||popup.open||book.open){clearHover();return;}
    const word=wordAt(side,event),layer=$(side+'WordHover');
    if(!word){clearHover();return;}
    if(layer.dataset.wordId===word.id)return;
    clearHover();layer.dataset.wordId=word.id;
    drawWord(layer,word);
  }
  function lookupAt(side,event){
    const word=wordAt(side,event);if(!word)return false;
    clearHover();guard(()=>openWord(side,word,event))();return true;
  }
  function render(side){
    clearHover();
    let layer=$(side+'Words');
    if(!layer){layer=document.createElement('div');layer.id=side+'Words';layer.className='overlays word-overlays';$(side+'Sheet').append(layer);}
    layer.replaceChildren();layer.hidden=!wordMode;$(side+'Overlay').hidden=wordMode;
    if(!state.data)return;
    const [width,height]=state.data.size;
    for(const word of state.data['words_'+side]||[])for(const rect of word.rects||[word.bbox]){const b=document.createElement('button');b.className='region word-region';b.dataset.wordId=word.id;b.title=word.term;b.setAttribute('aria-label',(side==='en'?'영어':'한국어')+' 단어: '+word.term);
      const [x0,y0,x1,y1]=rect;Object.assign(b.style,{left:x0/width*100+'%',top:y0/height*100+'%',width:(x1-x0)/width*100+'%',height:(y1-y0)/height*100+'%'});
      b.onclick=guard(e=>openWord(side,word,e));layer.append(b);}
  }
  function toggleWords(on){wordMode=on;$('wordSelect').setAttribute('aria-pressed',String(on));$('wordSelect').classList.toggle('active',on);for(const side of ['en','ko']){const layer=$(side+'Words');if(layer)layer.hidden=!on;$(side+'Overlay').hidden=on;}}
  function modeChanged(mode){clearHover();if(mode!=='pdf'){toggleWords(false);closeWord();}}
  function beforePageChange(){clearHover();closeWord();}
  window.WordTools={render,lookupAt,modeChanged,beforePageChange};
  for(const side of ['en','ko']){
    const sheet=$(side+'Sheet'),hover=document.createElement('div');hover.id=side+'WordHover';hover.className='overlays word-hover-layer';hover.setAttribute('aria-hidden','true');sheet.append(hover);
    const picked=document.createElement('div');picked.id=side+'WordSelection';picked.className='overlays word-selection-layer';picked.setAttribute('aria-hidden','true');sheet.append(picked);
    sheet.addEventListener('pointermove',e=>hoverAt(side,e));sheet.addEventListener('pointerleave',clearHover);
    sheet.addEventListener('dblclick',e=>{if(lookupAt(side,e)){e.preventDefault();e.stopPropagation();}});if(state.data)render(side);
  }
  $('viewport').addEventListener('scroll',clearHover,{passive:true});
  window.addEventListener('blur',clearHover);window.addEventListener('resize',clearHover);
  $('wordSelect').onclick=()=>toggleWords(!wordMode);
  $('closeWord').onclick=closeWord;
  $('viewport').addEventListener('pointerdown',event=>{
    if(popup.open&&!popup.contains(event.target))closeWord();
  });
  popup.addEventListener('cancel',rememberDraft);popup.addEventListener('close',()=>{if(!popup.open)clearPicked();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&popup.open){e.preventDefault();e.stopImmediatePropagation();closeWord();}},true);
  $('wordTermInput').addEventListener('input',()=>{updateLinks();dictionarySerial++;clearTimeout(dictionaryTimer);dictionaryTimer=setTimeout(lookupDictionary,180);});
  $('wordForm').addEventListener('submit',guard(async event=>{
    event.preventDefault();if(!draft)return;
    const selected=draft,fields=getFields();$('saveWord').disabled=true;
    try{
      const result=selected.id?await api('/api/vocabulary/update',{id:selected.id,...fields}):await api('/api/vocabulary/add',{...selected.origin,...fields});
      drafts.delete(keyFor(selected));draft=null;popup.close();clearPicked();
      toast('단어장에 저장했습니다.');if(book.open)await renderBook();
      return result;
    }catch(error){$('wordFormStatus').textContent=error.message;}finally{$('saveWord').disabled=false;}
  }));

  async function editEntry(entry){
    rememberDraft();if(popup.open)popup.close();
    draft={id:entry.id,source:entry,origin:null};
    showEditor(entry,[],null,true);
  }
  function addMeaning(parent,label,text){if(!text)return;const line=document.createElement('div');line.className='vocab-meaning';const tag=document.createElement('small');tag.textContent=label;const body=document.createElement('span');body.textContent=text;line.append(tag,body);parent.append(line);}
  async function jumpToEntry(entry){
    const paper=state.papers.find(p=>p.id===entry.paper_id);
    if(!paper)throw Error('이 항목의 번역본이 현재 논문 목록에 없습니다. 저장된 출처 문장은 계속 볼 수 있습니다.');
    book.close();if(popup.open)closeWord();
    await openPaper(paper);state.page=entry.source_page;setMode('pdf');await showPage();
    const word=(state.data['words_'+entry.side]||[]).find(w=>w.id===entry.word_id);
    if(word){toggleWords(true);await openWord(entry.side,word,{clientX:innerWidth*.25,clientY:180});}
  }
  async function renderBook(){
    const serial=++listSerial;const query={q:$('vocabSearch').value,paper:$('vocabScope').value==='current'?(state.paper?.id||'__none__'):'',category:$('vocabCategory').value,trash:$('vocabTrash').checked?'1':'0'};
    const result=await api('/api/vocabulary?'+new URLSearchParams(query));if(serial!==listSerial)return;
    const trash=$('vocabTrash').checked;$('vocabExport').disabled=trash;$('vocabList').replaceChildren();$('vocabCount').textContent=`${trash?'휴지통 · ':''}${result.total}개`+(result.entries.length<result.total?' · 최근 500개 표시':'');
    if(!result.entries.length){const empty=document.createElement('div');empty.className='vocab-empty';empty.textContent=trash?'휴지통이 비어 있습니다.':'저장된 단어가 없습니다. PDF에서 단어를 두 번 클릭해 뜻을 기록하세요.';$('vocabList').append(empty);}
    for(const entry of result.entries){
      const card=document.createElement('article');card.className='vocab-card';
      const top=document.createElement('div');top.className='vocab-card-top';const term=document.createElement('strong');term.textContent=entry.term;const category=document.createElement('span');category.className='vocab-category-tag';category.textContent=entry.category;top.append(term,category);card.append(top);
      addMeaning(card,'뜻',entry.general_meaning);addMeaning(card,'설명',entry.paper_meaning);
      const source=document.createElement('div');source.className='vocab-source';source.textContent=`${entry.paper_title} · p.${entry.source_page}`;card.append(source);
      const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent='출처 문장 · 메모';detail.append(summary);const quote=document.createElement('div');quote.className='word-context';quote.textContent=entry.source_text;detail.append(quote);if(entry.notes){const notes=document.createElement('p');notes.textContent=entry.notes;detail.append(notes);}card.append(detail);
      const buttons=document.createElement('div');buttons.className='vocab-card-actions';
      if(trash){const restore=document.createElement('button');restore.textContent='복원';restore.onclick=guard(async()=>{await api('/api/vocabulary/restore',{id:entry.id});await renderBook();toast('단어를 복원했습니다.');});buttons.append(restore);}
      else{
        const edit=document.createElement('button');edit.textContent='수정';edit.onclick=guard(()=>editEntry(entry));
        const jump=document.createElement('button');jump.textContent='원문 위치';jump.onclick=guard(()=>jumpToEntry(entry));
        const remove=document.createElement('button');remove.textContent='휴지통으로';remove.onclick=guard(async()=>{await api('/api/vocabulary/trash',{id:entry.id});await renderBook();toast('휴지통으로 이동했습니다. 휴지통에서 복원할 수 있습니다.');});buttons.append(edit,jump,remove);
      }
      card.append(buttons);$('vocabList').append(card);
    }
  }
  $('openVocabulary').onclick=guard(async()=>{if(popup.open)closeWord();if(!book.open)book.showModal();await renderBook();$('vocabSearch').focus();});
  $('vocabSearch').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(guard(renderBook),160);});
  for(const id of ['vocabScope','vocabCategory','vocabTrash'])$(id).addEventListener('change',guard(renderBook));
  $('vocabExport').onclick=guard(async()=>{
    const format=$('vocabExportFormat').value,response=await fetch('/api/vocabulary/export?format='+format);
    if(!response.ok){const error=await response.json();throw Error(error.error||'내보내기에 실패했습니다.');}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='PaperLink_단어장.'+format;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
})();
