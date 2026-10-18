/* Amo Daily News UI v1.0 APPROVED. Public news data only; private notes never uploaded. */
(()=>{'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const icon=n=>`<svg class="icon" aria-hidden="true"><use href="#ic-${n}"/></svg>`;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cats=['全部','国际','国内','长三角','科技','财经','专题'];
const catIcons={'全部':'spark','国际':'globe','国内':'city','长三角':'city','科技':'ai','财经':'chart','专题':'book'};
let catalog=[],stories=[],todayCat='全部',archiveCat='全部',archiveMonth='全部',activePage='home',currentReader=null,editingId=null,notes=[],storageOk=true;
const storageKey='amo-daily-news-private-notes-v1';
const issueURL=x=>`./${encodeURI(x.html)}`;
const storyURL=x=>`./${encodeURI(x.issue.html)}`;
function safeHref(path){return (typeof path==='string' && /^issues\/\d{4}-\d{2}-\d{2}\/(index\.html|完整版\.pdf|播客版\.pdf)$/.test(path))?'./'+encodeURI(path):null;}
function alertToast(t){const el=$('#toast');el.textContent=t;el.classList.add('show');clearTimeout(alertToast.t);alertToast.t=setTimeout(()=>el.classList.remove('show'),3200)}
function cover(art,label=''){const sym={ai:'ai',world:'globe',city:'chart',book:'book',finance:'chart',science:'spark'}[art]||'book';return `<div class="cover ${['ai','world','city','book','finance','science'].includes(art)?art:'world'}"><svg class="icon" aria-hidden="true"><use href="#ic-${sym}"/></svg>${label?`<span class="cover-label">${esc(label)}</span>`:''}</div>`}
function flatten(){stories=catalog.flatMap(issue=>(issue.stories||[]).map(a=>({...a,issue,short:'查看已发布期刊中的原始报道、来源与分析。'})));}
function normalize(data){if(!Array.isArray(data?.issues))throw Error('Invalid catalog');const seen=new Set();return data.issues.filter(i=>{if(!i||!/^(20\d{2})-\d{2}-\d{2}$/.test(i.date)||!safeHref(i.html)||seen.has(i.date))return false;seen.add(i.date);return true}).map(i=>({...i,stories:Array.isArray(i.stories)?i.stories:[]})).sort((a,b)=>b.date.localeCompare(a.date));}
async function loadCatalog(){let data,offline=false;try{const r=await fetch('./site/catalog.json',{cache:'no-store'});if(!r.ok)throw Error(`HTTP ${r.status}`);data=await r.json();}catch(e){data=JSON.parse($('#catalog-fallback').textContent);offline=true;}
 catalog=normalize(data);flatten();const latest=catalog[0];$('.hero-date').textContent=latest?`最新已发布期刊 · ${latest.date}`:'暂无已发布期刊';
 renderHome();renderToday();renderArchive();fillIssueOptions();loadNotes();renderNotes();const hash=location.hash.replace('#','');if(['home','today','archive','board'].includes(hash))go(hash);
 if(offline)alertToast('正在使用随页面保存的目录快照；在线更新以正式网站数据为准。');
}
function getStory(id){return stories.find(s=>s.id===id)}
function getIssue(date){return catalog.find(i=>i.date===date)}
function linkHTML(i,text){return `<a class="btn primary slim" href="${esc(issueURL(i))}" rel="noopener">${esc(text)} ${icon('arrow')}</a>`}
function renderHome(){const latest=catalog[0],picks=latest?.stories?.length?stories.filter(s=>s.issue.date===latest.date).slice(0,3):[];
 $('#homeCards').innerHTML=picks.length?picks.map(a=>`<button type="button" class="news-card" data-story="${esc(a.id)}">${cover(a.art,'已发布报道')}<div class="card-body"><span class="chip terra">${esc(a.cat)} · ${esc(a.issue.date)}</span><h3>${esc(a.title)}</h3><p>点击阅读本篇新闻的完整内容与来源。</p><div class="card-meta"><span>${esc(a.issue.feature||'每日新闻')}</span><span>打开报道 →</span></div></div></button>`).join(''):latest?`<div class="empty" style="grid-column:1/-1">最新期刊 ${esc(latest.date)} 已发布。<a href="${esc(issueURL(latest))}">打开完整期刊 →</a></div>`:'<div class="empty">暂无已发布期刊。</div>';
 // A new publication can have a complete HTML issue without manually curated per-story summaries.
}
function renderToday(){const issue=catalog[0];if(!issue){$('#todayFeature').innerHTML='<div class="empty">暂无已发布期刊。</div>';$('#digestCards').innerHTML='';return;}
 const arr=(issue.stories||[]).map(s=>getStory(s.id)).filter(Boolean);const num={};cats.forEach(c=>num[c]=c==='全部'?arr.length:arr.filter(x=>x.cat===c).length);
 $('#todayFilters').innerHTML=cats.map(c=>`<button type="button" class="filter-btn ${todayCat===c?'active':''}" data-today-cat="${esc(c)}" aria-pressed="${todayCat===c}">${icon(catIcons[c])} ${esc(c)} <span class="count">${num[c]}</span></button>`).join('');
 const filtered=todayCat==='全部'?arr:arr.filter(s=>s.cat===todayCat),head=filtered[0];
 $('#todayFeature').innerHTML=head?`<div class="today-feature">${cover(head.art,'已发布 · '+issue.date)}<div class="text"><div class="section-label">LATEST PUBLISHED EDITION</div><h2>${esc(head.title)}</h2><span class="chip">${esc(head.cat)} · ${esc(issue.date)}</span><p class="description">这则报道刊登于 ${esc(issue.date)} 的 Amo Daily News。点击直接阅读本篇报道、解读与来源。</p><div class="feature-bottom"><span class="footnote">${esc(issue.feature||'每日新闻')} · 正文见原始期刊</span><button type="button" class="btn primary slim" data-story="${esc(head.id)}">查看新闻 ${icon('arrow')}</button></div></div></div>`:`<div class="today-feature">${cover('book','最新已发布期刊')}<div class="text"><div class="section-label">LATEST PUBLISHED EDITION</div><h2>${esc(issue.title)}</h2><span class="chip">${esc(issue.date)} · ${esc(issue.feature)}</span><p class="description">${todayCat==='全部'?'当前期刊暂无独立文章目录。可打开完整原刊阅读。':'本期没有收录这一分类的新闻标题。'}</p>${linkHTML(issue,'打开完整期刊')}</div></div>`;
 $('#digestTitle').textContent=todayCat==='全部'?'本期其他报道':`本期 · ${todayCat}`;$('#digestCount').textContent=`已发布 ${issue.date} · ${filtered.length} 则`;
 const tail=head?filtered.slice(1):[];$('#digestCards').innerHTML=tail.length?tail.map(s=>`<button type="button" class="digest-card" data-story="${esc(s.id)}">${cover(s.art)}<div><span class="chip">${esc(s.cat)}</span><h4>${esc(s.title)}</h4><small>阅读本篇 →</small></div></button>`).join(''):`<div class="empty" style="grid-column:1/-1">${todayCat==='全部'?'本期其他报道请在完整期刊中阅读。':'此分类没有更多已收录的新闻。'}</div>`;
 // Offer the complete dated issue and only those PDF downloads whose files exist.
 const dl=[['pdf_full','完整文字 PDF'],['pdf_podcast','播客版 PDF']].filter(([k])=>safeHref(issue[k]));
 $('#digestCards').insertAdjacentHTML('beforeend',`<div class="reading-issue" style="grid-column:1/-1;background:#fffdfa;border:1px solid #e7e1d8;border-radius:14px;padding:17px"><strong>本期原版 · ${esc(issue.date)}</strong><p style="font-size:12px;color:#667881">${esc(issue.summary||issue.feature||'完整新闻与来源')}${dl.length<2?' · 本期部分 PDF 暂未托管。':''}</p><div style="display:flex;gap:9px;flex-wrap:wrap">${linkHTML(issue,'阅读完整期刊')}${dl.map(([k,label])=>`<a class="btn ghost slim" href="${esc(safeHref(issue[k]))}" download>${esc(label)} ↓</a>`).join('')}</div></div>`);
}
function renderArchive(){const q=$('#archiveSearch').value.trim().toLowerCase();const available=['全部',...new Set(catalog.map(i=>i.category).filter(Boolean))];if(!available.includes(archiveCat))archiveCat='全部';
 $('#archiveFilters').innerHTML=available.map(c=>`<button class="${archiveCat===c?'active':''}" aria-pressed="${archiveCat===c}" type="button" data-archive-cat="${esc(c)}">${esc(c)}</button>`).join('');
 const months=[...new Set(catalog.map(i=>i.date.slice(0,7)))];$('#archiveMonths').innerHTML=[`<button class="month-item ${archiveMonth==='全部'?'active':''}" data-month="全部" type="button">全部月份 <small>${catalog.length} 期</small></button>`,...months.map(m=>`<button class="month-item ${archiveMonth===m?'active':''}" data-month="${esc(m)}" type="button">${esc(m.replace('-',' 年 '))} 月 <small>${catalog.filter(i=>i.date.startsWith(m)).length} 期</small></button>`)].join('');
 const matches=catalog.filter(i=>(archiveCat==='全部'||archiveCat===i.category)&&(archiveMonth==='全部'||i.date.startsWith(archiveMonth))&&(!q||[i.date,i.title,i.feature,i.summary,...i.stories.map(s=>s.title)].join(' ').toLowerCase().includes(q)));
 $('#archiveHeading').textContent=archiveMonth==='全部'?'全部已发布期刊':archiveMonth.replace('-',' 年 ')+' 月';$('#archiveCount').textContent=`共 ${matches.length} 期`;
 $('#archiveResults').innerHTML=matches.length?matches.map(i=>`<article class="archive-card">${cover(i.category==='财经'?'finance':i.category==='社会'?'book':'world')}<div class="archive-card-content"><span class="chip">${esc(i.feature||'每日新闻')}</span><h3>${esc(i.title)}</h3><p>${esc(i.summary||'打开已发布期刊阅读正文与来源。')}</p><small>${esc(i.date)} · ${i.pdf_full&&i.pdf_podcast?'HTML + 两份 PDF':'HTML 已发布 · PDF 未齐'}</small><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><a class="text-link" href="${esc(issueURL(i))}">阅读原刊 →</a>${i.pdf_full&&safeHref(i.pdf_full)?`<a class="text-link" href="${esc(safeHref(i.pdf_full))}" download>完整 PDF ↓</a>`:''}${i.pdf_podcast&&safeHref(i.pdf_podcast)?`<a class="text-link" href="${esc(safeHref(i.pdf_podcast))}" download>播客版 PDF ↓</a>`:''}</div></div></article>`).join(''):'<div class="empty" style="grid-column:1/-1">没有匹配的已发布期刊。</div>';
}
function fillIssueOptions(){const options=stories.map(s=>`<option value="${esc(s.id)}">${esc(s.issue.date)} · ${esc(s.title.slice(0,48))}</option>`);$('#noteArticle').innerHTML='<option value="">不关联新闻</option>'+options.join('')}
/* On-demand reading of the exact published story; no editorial facts are synthesized. */
const issueTextCache=new Map();
const articleSafeTags=new Set(['P','H2','H3','H4','H5','H6','DIV','SPAN','SMALL','B','STRONG','EM','I','U','UL','OL','LI','BLOCKQUOTE','A','BR','HR','TABLE','THEAD','TBODY','TR','TH','TD','PRE','CODE','SUP','SUB']);
const articleDiscardTags=new Set(['SCRIPT','STYLE','IFRAME','OBJECT','EMBED','FORM','INPUT','BUTTON','TEXTAREA','SELECT','SVG','CANVAS','VIDEO','AUDIO','IMG','NOSCRIPT']);
const sameHeadline=s=>String(s||'').normalize('NFKC').replace(/[\s\u00a0\u200b-\u200d]/g,'').toLocaleLowerCase();
async function loadPublishedDocument(issue){
 if(!issueTextCache.has(issue.date)){
  const p=fetch(issueURL(issue),{cache:'no-store'}).then(r=>{
   if(!r.ok)throw Error('HTTP '+r.status);
   return r.text();
  }).then(html=>{
   if(!/<html\b/i.test(html)||!/<\/html>/i.test(html))throw Error('期刊文件不完整');
   return new DOMParser().parseFromString(html,'text/html');
  }).catch(err=>{issueTextCache.delete(issue.date);throw err;});
  issueTextCache.set(issue.date,p);
 }
 return issueTextCache.get(issue.date);
}
function findPublishedStory(doc,story){
 const title=sameHeadline(story.title);
 const candidates=[...doc.querySelectorAll('section[id]')].filter(section=>{
  const body=section.querySelector('article.card,details.news-card')||section;
  return [...body.querySelectorAll('h2,h3')].some(h=>sameHeadline(h.textContent)===title);
 });
 // Prefer the innermost matching section; never guess by ordinal or by another article.
 candidates.sort((a,b)=>a.querySelectorAll('section').length-b.querySelectorAll('section').length);
 return candidates[0]||null;
}
function copySafeArticleNode(src,baseURL){
 if(src.nodeType===3)return document.createTextNode(src.nodeValue||'');
 if(src.nodeType!==1||articleDiscardTags.has(src.tagName))return null;
 const safe=articleSafeTags.has(src.tagName)?document.createElement(src.tagName.toLowerCase()):document.createDocumentFragment();
 if(src.tagName==='A'&&safe.nodeType===1){
  const raw=src.getAttribute('href');
  try{
   const target=new URL(raw||'',baseURL);
   if(raw&&['http:','https:'].includes(target.protocol)){
    safe.href=target.href;safe.target='_blank';safe.rel='noopener noreferrer';
   }
  }catch(_){}
 }
 for(const node of src.childNodes){
  const copied=copySafeArticleNode(node,baseURL);
  if(copied)safe.appendChild(copied);
 }
 return safe;
}
function addPublishedDetails(target,section,story,baseURL){
 const body=section.querySelector('article.card,details.news-card')||section;
 const main=body.querySelector('.expanded,.detail');
 const sources=body.querySelector('.sources');
 const intro=body.querySelector('p.deck,p.summary')||(main?null:section.querySelector('p'));
 const judgement=body.querySelector('p.one-line');
 const date=body.querySelector('p.dateline,div.dates');
 const holder=document.createElement('div');
 holder.className='reader-article-body';
 if(date){
  const info=document.createElement('p');info.className='reader-date';info.textContent=date.textContent.trim();holder.appendChild(info);
 }
 if(intro){
  const lead=document.createElement('p');lead.className='intro';lead.textContent=intro.textContent.trim();holder.appendChild(lead);
 }
 if(judgement){
  const line=document.createElement('p');line.className='reader-judgement';line.textContent=judgement.textContent.trim();holder.appendChild(line);
 }
 if(main){
  const safe=copySafeArticleNode(main,baseURL);
  if(safe)holder.appendChild(safe);
 }else{
  for(const child of section.children){
   if(child===intro||child.matches('.eyebrow'))continue;
   if(child.matches('h2,h3')&&sameHeadline(child.textContent)===sameHeadline(story.title))continue;
   const safe=copySafeArticleNode(child,baseURL);
   if(safe)holder.appendChild(safe);
  }
 }
 if(sources&&!(main&&main.contains(sources))){
  const sourceTitle=document.createElement('h4');sourceTitle.textContent='原始资料与来源';holder.appendChild(sourceTitle);
  const safe=copySafeArticleNode(sources,baseURL);
  if(safe)holder.appendChild(safe);
 }
 if(holder.textContent.trim().length<80)throw Error('没有找到这篇新闻的完整可阅读正文');
 target.appendChild(holder);
}
async function openArticle(id){
 const story=getStory(id);
 if(!story)return;
 currentReader=id;
 const issue=story.issue, reader=$('#readerContent');
 reader.innerHTML='<h2 id="readerTitle">'+esc(story.title)+'</h2>'+
  '<div class="muted" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px"><span class="chip terra">'+esc(story.cat)+'</span><span>'+esc(issue.date)+' · '+esc(issue.feature||'')+'</span></div>'+
  '<p class="reader-status" role="status">正在读取这篇报道的完整正文与来源…</p>';
 $('#readerModal').classList.remove('hidden');
 document.body.style.overflow='hidden';
 $('#closeReader').focus();
 try{
  const doc=await loadPublishedDocument(issue);
  if(currentReader!==id||$('#readerModal').classList.contains('hidden'))return;
  const section=findPublishedStory(doc,story);
  if(!section)throw Error('原刊没有找到与这张新闻卡片精确对应的正文');
  const old=reader.querySelector('.reader-status');
  if(old)old.remove();
  // Fetching and parsing is same-origin. Only safe text/links/markup are copied.
  addPublishedDetails(reader,section,story,new URL(issueURL(issue),location.href).href);
  const foot=document.createElement('p');foot.className='reader-foot';
  const full=document.createElement('a');full.href=issueURL(issue);full.textContent='阅读本日整期 HTML →';full.rel='noopener';
  foot.appendChild(full);reader.appendChild(foot);
 }catch(err){
  if(currentReader!==id||$('#readerModal').classList.contains('hidden'))return;
  const status=reader.querySelector('.reader-status');
  if(status)status.textContent='本篇正文暂时无法读取（'+String(err.message||err)+'）。请使用下方整期原刊备用入口。';
  const link=document.createElement('a');link.className='btn ghost slim';link.href=issueURL(issue);link.textContent='打开原刊';reader.appendChild(link);
 }
}
function closeArticle(){if($('#readerModal').classList.contains('hidden'))return;$('#readerModal').classList.add('hidden');document.body.style.overflow='';currentReader=null}
function go(page,cat){if(!['home','today','archive','board'].includes(page))return;closeArticle();activePage=page;$$('.page').forEach(p=>p.classList.toggle('active',p.dataset.page===page));$$('[data-go]').forEach(b=>{const on=b.dataset.go===page&&b.matches('.nav-btn,.mobile-nav button');b.classList.toggle('active',on);if(b.matches('.nav-btn,.mobile-nav button'))b.setAttribute('aria-current',on?'page':'false')});if(page==='today'){todayCat=cat&&cats.includes(cat)?cat:'全部';renderToday()}if(page==='archive')renderArchive();if(page==='board')renderNotes();window.scrollTo({top:0,behavior:'instant'});try{history.replaceState({},'',`#${page}`)}catch(e){}}
function loadNotes(){try{const v=localStorage.getItem(storageKey);notes=v?JSON.parse(v):[];if(!Array.isArray(notes))notes=[];notes=notes.filter(x=>x&&typeof x.text==='string'&&typeof x.id==='string');}catch(e){notes=[];storageOk=false;alertToast('本浏览器无法读取本地留言，请留意备份。')}}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(notes));storageOk=true;return true}catch(e){storageOk=false;alertToast('浏览器存储失败！请立即导出备份。');return false}}
function fmt(s){try{return new Date(s).toLocaleString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}catch(e){return ''}}
function renderNotes(){const q=$('#noteSearch').value.trim().toLowerCase(),filter=$('#noteFilter').value;$('#noteCount').textContent=`· ${notes.length} 条`;const a=notes.filter(n=>(filter==='全部'||n.tag===filter)&&(!q||[n.text,n.tag,getStory(n.article)?.title||''].join(' ').toLowerCase().includes(q))).sort((x,y)=>String(y.updated).localeCompare(String(x.updated)));
 $('#noteList').innerHTML=a.length?a.map(n=>`<article class="note-card"><div class="note-card-top"><span class="chip terra"># ${esc(n.tag||'随想')}</span><div class="note-actions"><button data-edit-note="${esc(n.id)}" type="button" aria-label="编辑留言">编辑</button><button data-delete-note="${esc(n.id)}" type="button" aria-label="删除留言">删除</button></div></div><p>${esc(n.text)}</p><div class="row-between"><small>${esc(fmt(n.updated))}</small>${getStory(n.article)?`<button class="text-link" type="button" data-story="${esc(n.article)}" style="font-size:10px">关联：${esc(getStory(n.article).title.slice(0,22))}… →</button>`:''}</div></article>`).join(''):`<div class="empty">${notes.length?'没有符合条件的留言。':'还没有留言。在左侧写下第一条思考吧。'}</div>`;
}
function clearEdit(){editingId=null;$('#noteForm').reset();$('#composerTitle').textContent='写下今天的想法';$('#saveNote').innerHTML=icon('check')+' 保存留言';$('#cancelEdit').classList.add('hidden');$('#charCount').textContent='0 / 2500 字'}
function editNote(id){const n=notes.find(n=>n.id===id);if(!n)return;editingId=id;$('#noteText').value=n.text;$('#noteTag').value=n.tag||'随想';$('#noteArticle').value=getStory(n.article)?n.article:'';$('#composerTitle').textContent='编辑这条留言';$('#saveNote').innerHTML=icon('check')+' 保存修改';$('#cancelEdit').classList.remove('hidden');$('#charCount').textContent=n.text.length+' / 2500 字';$('#noteForm').scrollIntoView({behavior:'smooth',block:'center'});$('#noteText').focus()}
function deleteNote(id){if(!notes.some(n=>n.id===id))return;if(!confirm('确定删除这条私人留言吗？删除后不能撤销，建议先导出备份。'))return;notes=notes.filter(n=>n.id!==id);persist();if(editingId===id)clearEdit();renderNotes();alertToast('留言已删除')}
function saveNote(e){e.preventDefault();const content=$('#noteText').value.trim();if(!content){alertToast('请先输入留言。');return}if(content.length>2500){alertToast('留言超出 2500 字。');return}const now=new Date().toISOString();const found=notes.find(n=>n.id===editingId);const n={id:found?.id||(crypto?.randomUUID?.()||('n'+Date.now())),text:content,tag:$('#noteTag').value,article:$('#noteArticle').value,created:found?.created||now,updated:now};notes=editingId?notes.map(x=>x.id===editingId?n:x):[n,...notes];persist();clearEdit();renderNotes();alertToast(storageOk?'留言已保存在当前浏览器':'当前页暂存成功，请立即导出备份')}
function exportNotes(){if(!notes.length){alertToast('暂时没有可导出的留言。');return}const out=['# Amo Daily News｜私人留言','','> 仅包含本浏览器保存的私人留言，请勿上传到公开仓库。','',...notes.map(n=>`## ${esc(n.updated?.slice(0,10)||'')} · ${n.tag}\n\n${n.text}\n\n${getStory(n.article)?`关联新闻（${getStory(n.article).issue.date}）：${getStory(n.article).title}\n` : ''}\n---\n`)].join('\n');const u=URL.createObjectURL(new Blob([out],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download=`AmoDailyNews_PrivateNotes_${new Date().toISOString().slice(0,10)}.md`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1500);alertToast('私人留言已导出 Markdown 文件')}
 document.addEventListener('click',e=>{const g=e.target.closest('[data-go]');if(g){go(g.dataset.go,g.dataset.category);return}const story=e.target.closest('[data-story]');if(story){openArticle(story.dataset.story);return}const t=e.target.closest('[data-today-cat]');if(t){todayCat=t.dataset.todayCat;renderToday();return}const c=e.target.closest('[data-archive-cat]');if(c){archiveCat=c.dataset.archiveCat;renderArchive();return}const m=e.target.closest('[data-month]');if(m){archiveMonth=m.dataset.month;renderArchive();return}const ed=e.target.closest('[data-edit-note]');if(ed){editNote(ed.dataset.editNote);return}const del=e.target.closest('[data-delete-note]');if(del){deleteNote(del.dataset.deleteNote);return}});
 $('#closeReader').addEventListener('click',closeArticle);$('#backReader').addEventListener('click',closeArticle);$('#readerModal').addEventListener('click',e=>{if(e.target===$('#readerModal'))closeArticle()});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeArticle()});$('#reflectBtn').addEventListener('click',()=>{const id=currentReader;go('board');$('#noteArticle').value=id||'';$('#noteText').focus()});$('#topSearch').addEventListener('click',()=>{go('archive');$('#archiveSearch').focus()});$('#archiveSearch').addEventListener('input',renderArchive);$('#noteSearch').addEventListener('input',renderNotes);$('#noteFilter').addEventListener('change',renderNotes);$('#noteText').addEventListener('input',e=>$('#charCount').textContent=e.target.value.length+' / 2500 字');$('#noteForm').addEventListener('submit',saveNote);$('#cancelEdit').addEventListener('click',clearEdit);$('#exportNotes').addEventListener('click',exportNotes);
 window.addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(['home','today','archive','board'].includes(h)&&h!==activePage)go(h)});
 loadCatalog().catch(e=>{alertToast('新闻目录暂不可用：'+String(e));loadNotes();renderNotes()});
})();