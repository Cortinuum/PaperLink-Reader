const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const sandbox={window:{markdownit:require('./vendor/markdown-it.min.js')}};
vm.runInNewContext(fs.readFileSync('markdown.js','utf8'),sandbox);
const render=sandbox.window.PaperMarkdown.render;
test('headings, emphasis and nested lists render',()=>{
 const html=render('## 핵심\n\n**견고성**\n\n- 첫 항목\n  - 근거');
 assert.match(html,/<h2>핵심<\/h2>/);assert.match(html,/<strong>견고성<\/strong>/);assert.equal((html.match(/<ul>/g)||[]).length,2);
});
test('tables and code remain readable',()=>{
 const html=render('| 원문 | 번역 |\n|---|---|\n| a | 가 |\n\n```python\na < b\n```');
 assert.match(html,/<table>/);assert.match(html,/<th>원문<\/th>/);assert.match(html,/a &lt; b/);
});
test('raw HTML is inert text',()=>{
 const html=render('<script>alert(1)</script>\n<img src=x onerror=alert(1)>');
 assert.doesNotMatch(html,/<script|<img|<iframe/i);assert.match(html,/&lt;script/);
});
test('unsafe links are not clickable',()=>{
 for(const input of ['[x](javascript:alert(1))','[x](data:text/html;base64,AAAA)','[x](vbscript:msgbox(1))'])assert.doesNotMatch(render(input),/<a /);
});
test('images do not trigger remote loads',()=>{
 const html=render('![원격 그림](https://example.org/tracking.png)');
 assert.doesNotMatch(html,/<img|src=/);assert.match(html,/원격 그림/);
});
test('normal links open separately with isolated opener',()=>{
 const html=render('[논문](https://example.org/paper)');
 assert.match(html,/target="_blank"/);assert.match(html,/rel="noopener noreferrer"/);
});
