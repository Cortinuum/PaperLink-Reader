'use strict';
(() => {
  const markdown=window.markdownit({html:false,breaks:true,linkify:false,typographer:false});
  // Remote images never load as a side effect of displaying an answer.
  markdown.renderer.rules.image=(tokens,index)=>markdown.utils.escapeHtml(tokens[index].content||'이미지');
  const linkOpen=markdown.renderer.rules.link_open||((tokens,index,options,env,self)=>self.renderToken(tokens,index,options));
  markdown.renderer.rules.link_open=(tokens,index,options,env,self)=>{
    tokens[index].attrSet('target','_blank');tokens[index].attrSet('rel','noopener noreferrer');
    return linkOpen(tokens,index,options,env,self);
  };
  window.PaperMarkdown={render:text=>markdown.render(String(text||''))};
})();
