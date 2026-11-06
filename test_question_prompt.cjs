const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const sandbox={window:{}};
vm.runInNewContext(fs.readFileSync('question_prompt.js','utf8'),sandbox);
const {compose,userText}=sandbox.window.QuestionPrompt;
const catalog={heading:'추가 선택: ',guide:'선택한 사항만 간결하게 답하세요.',items:[
 {id:'evidence',label:'원문 근거',instruction:'근거를 인용하세요.'},
 {id:'alternative',label:'대안 번역',instruction:'대안을 하나 제시하세요.'}
]};
test('no choice preserves user text verbatim',()=>{
 const original='내 질문, 두 번째 부분\n한국어와 English.  \n';
 assert.equal(compose(original,[],catalog),original);
});
test('multiple choices show comma-separated labels and instructions once',()=>{
 const value=compose('뜻은?', ['evidence','alternative','evidence'],catalog);
 assert.match(value,/원문 근거, 대안 번역/);
 for(const item of catalog.items)assert.equal(value.split(item.instruction).length-1,1);
});
test('unchecking one removes only its generated instruction',()=>{
 const previous=compose('직접 쓴 질문', ['evidence','alternative'],catalog);
 const next=compose(previous,['alternative'],catalog);
 assert.doesNotMatch(next,/근거를 인용하세요/);assert.match(next,/대안을 하나/);
 assert.equal(userText(next),'직접 쓴 질문');
});
test('unchecking all restores the original after repeated toggles',()=>{
 const original='내 질문\n두 번째 줄\n';let value=original;
 for(let i=0;i<5;i++){value=compose(value,['evidence'],catalog);value=compose(value,[],catalog);}
 assert.equal(value,original);
});
test('new user writing after the managed block is preserved',()=>{
 const old=compose('앞 질문',['evidence'],catalog)+'\n추가로 직접 쓴 질문';
 const next=compose(old,['alternative'],catalog);
 assert.equal(userText(next),'앞 질문\n추가로 직접 쓴 질문');
});
test('submission extraction prevents a duplicate optional prompt',()=>{
 const original='원문 근거라는 말을 포함하는 질문';
 const visible=compose(original,['evidence'],catalog);
 assert.equal(userText(visible),original);
 assert.doesNotMatch(userText(visible),/근거를 인용하세요/);
});
test('edited automatic content is rebuilt without changing the original question',()=>{
 const old=compose('보존할 질문',['evidence'],catalog).replace('근거를 인용하세요.','자동 영역 임시 수정');
 const next=compose(old,['alternative'],catalog);
 assert.equal(userText(next),'보존할 질문');assert.doesNotMatch(next,/자동 영역 임시 수정/);
});
