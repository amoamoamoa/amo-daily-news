/* Functional integration of unmodified app.js with generated catalog.
 * Minimal DOM stubs: NOT a browser, responsive/layout or device acceptance test.
 */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const catalog = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const elements = new Map(), documentEvents = {}, storage = new Map();
const oldStory = catalog.issues[1].stories[0];
storage.set('amo-daily-news-private-notes-v1', JSON.stringify([
  {id:'test-private-note', text:'TEST ONLY private note', article:oldStory.id, updated:'2026-10-16'}
]));
const initialStorage = storage.get('amo-daily-news-private-notes-v1');
function el(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    value: '', textContent: '', innerHTML: '', events: {}, dataset: {},
    classList: {add(){}, remove(){}, toggle(){}, contains(){return true;}},
    addEventListener(name, fn){this.events[name] = fn;},
    insertAdjacentHTML(_, html){this.innerHTML += html;},
    focus(){}, reset(){}, scrollIntoView(){}
  });
  return elements.get(selector);
}
el('#noteFilter').value = '全部';
const requests = [];
const context = {
  document: {querySelector:el, querySelectorAll:()=>[], body:{style:{}},
    addEventListener:(name,fn)=>documentEvents[name]=fn},
  window: {addEventListener(){}, scrollTo(){}},
  localStorage: {getItem:key=>storage.get(key), setItem:(key,value)=>storage.set(key,value)},
  location:{hash:''}, history:{replaceState(){}},
  fetch: async (url,options)=>{requests.push({url,options});return {ok:true,json:async()=>catalog};},
  setTimeout:()=>0, clearTimeout(){}, crypto:{randomUUID:()=> 'synthetic-note-2'},
};
vm.runInNewContext(fs.readFileSync(process.argv[3],'utf8'), context);
setImmediate(()=>{
  try {
    const latest = catalog.issues[0], count = latest.stories.length;
    assert.equal(el('.hero-date').textContent, '最新已发布期刊 · '+latest.date);
    for (const s of latest.stories.slice(0,3)) assert.ok(el('#homeCards').innerHTML.includes(s.title));
    assert.equal((el('#homeCards').innerHTML.match(/class="news-card"/g)||[]).length, Math.min(3,count));
    assert.ok(el('#todayFeature').innerHTML.includes(latest.stories[0].title));
    for(const s of latest.stories.slice(1)) assert.ok(el('#digestCards').innerHTML.includes(s.title));
    assert.ok(el('#digestCount').textContent.endsWith(`${count} 则`));
    assert.equal((el('#archiveResults').innerHTML.match(/class="archive-card"/g)||[]).length,catalog.issues.length);
    assert.ok(el('#noteArticle').innerHTML.includes(latest.stories[0].id));
    assert.ok(el('#noteList').innerHTML.includes(oldStory.title.slice(0,22)));
    assert.equal(storage.get('amo-daily-news-private-notes-v1'),initialStorage);
    const click = dataset => documentEvents.click({target:{closest:s=>s==='[data-today-cat]'?{dataset}:null}});
    click({todayCat:'专题'});
    assert.ok(el('#todayFeature').innerHTML.includes(latest.stories[0].title));
    click({todayCat:'国际'});
    assert.ok(el('#todayFeature').innerHTML.includes('本期没有收录这一分类'));
    el('#noteText').value='TEST ONLY new private note';
    el('#noteTag').value='随想';
    el('#noteArticle').value=latest.stories[0].id;
    el('#noteForm').events.submit({preventDefault(){}});
    const notes=JSON.parse(storage.get('amo-daily-news-private-notes-v1'));
    assert.equal(notes.length,2);
    assert.equal(notes[0].article,latest.stories[0].id);
    assert.equal(notes[1].article,oldStory.id);
    assert.equal(requests.length,1);
    assert.equal(requests[0].url,'./site/catalog.json');
    console.log('PASS: generated cards, filters, archive, note associations and local-only storage (DOM stubs)');
  } catch(e) {console.error(e);process.exitCode=1;}
});
