'use strict';
(() => {
  const START='[추가 검토 · 체크박스 자동 반영]',END='[/추가 검토]';
  function userText(value){
    // Checkbox-owned blocks can be rebuilt without touching text outside them.
    let text=String(value||''),start;
    while((start=text.indexOf(START))!==-1){
      const end=text.indexOf(END,start+START.length);
      if(end===-1)break;
      let left=start;
      if(text.slice(Math.max(0,left-2),left)==='\n\n')left-=2;
      text=text.slice(0,left)+text.slice(end+END.length);
    }
    return text;
  }
  function compose(value,selected,catalog){
    const text=userText(value),chosen=new Set(selected),items=(catalog?.items||[]).filter(item=>chosen.has(item.id));
    if(!items.length)return text;
    const suffix=catalog.heading+items.map(item=>item.label).join(', ')+'\n'+catalog.guide+'\n'+items.map(item=>item.label+': '+item.instruction).join('\n');
    return text+'\n\n'+START+'\n'+suffix+'\n'+END;
  }
  window.QuestionPrompt={userText,compose};
})();
