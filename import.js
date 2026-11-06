'use strict';
(() => {
  const dialog=$('importDialog'),form=$('importForm'),status=$('importStatus');
  let editing=null;
  function open(paper=null){
    editing=paper;form.reset();status.textContent='';
    $('importHeading').textContent=paper?'PDF 변경':'PDF 불러오기';$('importSubmit').textContent=paper?'변경 저장':'보관함에 추가';
    $('importSource').required=!paper;$('importTranslation').required=!paper;$('currentPdfFiles').hidden=!paper;$('replacePdfHint').hidden=!paper;
    if(paper){$('importTitle').value=paper.title;$('currentPdfFiles').textContent='현재 원문: '+paper.original_name+'\n현재 번역: '+paper.translation_name;}
    dialog.showModal();
  }
  window.PaperImport={edit:paper=>open(paper)};
  $('openImport').onclick=()=>open();
  $('emptyImport').onclick=$('openImport').onclick;
  $('closeImport').onclick=()=>dialog.close();
  form.addEventListener('submit',async event=>{
    event.preventDefault();const source=$('importSource').files[0],translation=$('importTranslation').files[0];
    const target=editing;
    if(!target&&(!source||!translation)){status.textContent='원문 PDF와 번역 PDF를 모두 선택하세요.';return;}
    if((source?.size||0)+(translation?.size||0)>100*1024*1024){status.textContent='두 PDF의 합계가 100MB 이하여야 합니다.';return;}
    $('importSubmit').disabled=true;status.textContent='PDF를 확인하고 이 PC의 보관함에 복사하는 중…';
    try{
      const response=await fetch(target?'/api/replace?paper='+encodeURIComponent(target.id):'/api/import',{method:'POST',headers:{'X-Reader-Token':token},body:new FormData(form)});
      const result=await response.json();if(!response.ok)throw Error(result.error||'PDF를 등록하지 못했습니다.');
      state.libraryTrash=false;await library();const paper=state.papers.find(p=>p.id===result.paper.id);
      if(!paper)throw Error('등록한 PDF를 목록에서 찾지 못했습니다. 목록을 새로고침하세요.');
      await openPaper(paper);openLibrary(false);dialog.close();form.reset();
      const message=target?(result.changed?'PDF를 변경했습니다. 이전 논문쌍은 휴지통에서 복원할 수 있습니다.':result.title_updated?'제목을 변경했습니다.':'변경된 PDF 내용이 없습니다.'):(result.restored?'논문쌍을 복원했습니다.':result.duplicate?'이미 등록된 PDF를 열었습니다.':'PDF를 보관함에 추가했습니다.');
      toast(message+(result.warnings?.length?' '+result.warnings.join(' '):''));
    }catch(error){status.textContent=error.message;}
    finally{$('importSubmit').disabled=false;}
  });
})();
