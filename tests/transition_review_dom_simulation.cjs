'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2],'utf8');
const ledger=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const start=html.lastIndexOf('<script>')+8, end=html.indexOf('</script>',start);
assert(start>=8&&end>start);
const script=html.slice(start,end);
class Node {
  constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.disabled=false;this.attrs={}}
  appendChild(x){this.children.push(x);return x}
  replaceChildren(...x){this.children=x}
  setAttribute(k,v){this.attrs[k]=v}
}
const rows=new Node('tbody'),feedback=new Node('p');
const used=[];
const env={
  document:{getElementById:id=>({'transition-rows':rows,'transition-feedback':feedback})[id],
            createElement:tag=>new Node(tag)},
  fetch:async(url)=>{used.push(url);return {ok:true,json:async()=>ledger}}
};
vm.runInNewContext(script,env,{timeout:1000});
setImmediate(()=>{
  assert.deepStrictEqual(used,['/api/transition-ledger']);
  if(ledger.findings.some(x=>x.enabled!==false)){
    assert.strictEqual(rows.children.length,0);
    assert.strictEqual(feedback.attrs.role,'alert');
    process.stdout.write('FORGED_TRANSITION_BLOCKED\n');
  } else {
    assert.strictEqual(rows.children.length,ledger.findings.length);
    for(const row of rows.children){
      assert.strictEqual(row.children.length,6);
      const btn=row.children[5].children[0];
      assert.strictEqual(btn.disabled,true);
      assert.strictEqual(btn.textContent,'근거 검토 필요');
    }
    assert(feedback.textContent.includes('기능 활성화 0건'));
    process.stdout.write('TRANSITION_DOM_DISABLED_PASS\n');
  }
});
