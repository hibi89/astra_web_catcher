'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const page = fs.readFileSync(process.argv[2], 'utf8');
const manifest = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const scriptStart = page.lastIndexOf('<script>') + 8;
const scriptEnd = page.indexOf('</script>', scriptStart);
assert(scriptStart >= 8 && scriptEnd > scriptStart);
const script = page.slice(scriptStart, scriptEnd);
const created = [];
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.textContent=''; this.disabled=false; this.attrs={}; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...nodes) { this.children=[...nodes]; }
  setAttribute(name, value) { this.attrs[name]=value; }
}
const mappingRows = new Element('tbody');
const feedback = new Element('p');
const dom = { 'mapping-rows':mappingRows, 'mapping-feedback':feedback };
const requested = [];
const sandbox = {
 document:{getElementById:id=>dom[id],createElement:tag=>{const e=new Element(tag);created.push(e);return e;}},
 fetch:async(url)=>{requested.push(url);return {ok:true,json:async()=>manifest};},
};
vm.runInNewContext(script,sandbox,{timeout:1000});
setImmediate(()=>{
  assert.deepStrictEqual(requested,['/api/review-manifest']);
  if (manifest.items.some(x=>x.enabled !== false)) {
    assert.strictEqual(mappingRows.children.length,0,'unsafe record must be suppressed');
    assert.strictEqual(feedback.attrs.role,'alert');
    process.stdout.write('DISABLED_TAMPER_BLOCKED\n');
  } else {
    assert.strictEqual(mappingRows.children.length,manifest.items.length);
    for (const row of mappingRows.children) {
      assert.strictEqual(row.children.length,5);
      const button = row.children[4].children[0];
      assert.strictEqual(button.tagName,'button');
      assert.strictEqual(button.disabled,true);
      assert.strictEqual(button.textContent,'검토 대기');
      assert.strictEqual(button.attrs['aria-label'].includes('검토 대기'),true);
    }
    assert(feedback.textContent.includes('승인/자동 적용 0건'));
    process.stdout.write('REVIEW_ONLY_DOM_PASS\n');
  }
});
