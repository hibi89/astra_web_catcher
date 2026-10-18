'use strict';
// DOM simulation of embedded HTML controls without opening restricted Chromium.
const vm=require('node:vm');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {html,table}=JSON.parse(fs.readFileSync(0,'utf8'));
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
assert(match,'generated HTML must contain the controller script');
const code=match[1];
new vm.Script(code,{filename:'query-ui-controller.js'});
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.value='';this.textContent='';this.disabled=false;this.attributes={};}
  addEventListener(type,handler){this.listeners[type]=handler;}
  appendChild(el){this.children.push(el);if(this.tag==='select' && this.children.length===1)this.value=el.value;}
  replaceChildren(...els){this.children=[...els];}
  setAttribute(k,v){this.attributes[k]=v;}
  removeAttribute(k){delete this.attributes[k];}
  getAttribute(k){return this.attributes[k];}
}
const elements={};
for(const id of ['sort-field','sort-direction','filter-field','filter-value','results','columns','feedback','dataset','apply','query-form']){
  elements[id]=new Element(['sort-field','sort-direction','filter-field'].includes(id)?'select':'div');
}
elements['sort-direction'].value='asc';
elements['filter-field'].value='';
const emptyFilter=new Element('option');emptyFilter.value='';elements['filter-field'].appendChild(emptyFilter);
const document={getElementById:id=>elements[id],createElement:tag=>new Element(tag)};
const fields=table.bindings.map(b=>({name:b.source_field,type:b.logical_field==='score'?'integer':'text'}));
const calls=[];
async function fetch(url){
  calls.push(url);
  if(url==='/api/preview-schema')return {ok:true,json:async()=>({synthetic:true,original_site_behavior_verified:false,table_name:table.table_name,fields})};
  const u=new URL(url,'http://127.0.0.1');
  assert.equal(u.pathname,'/api/rows');
  const p=u.searchParams;let rows=[...table.rows];
  if(p.has('filter_by')){
    let val=p.get('filter_value');
    const f=fields.find(f=>f.name===p.get('filter_by'));
    assert(f);
    if(f.type==='integer')val=Number(val);
    rows=rows.filter(row=>row[f.name]===val);
  }
  rows.sort((a,b)=>{
    const x=a[p.get('sort_by')],y=b[p.get('sort_by')];
    return (x<y?-1:x>y?1:0)*(p.get('direction')==='desc'?-1:1);
  });
  return {ok:true,json:async()=>({synthetic:true,original_site_behavior_verified:false,items:rows})};
}
const sandbox={document,fetch,URLSearchParams,console};
vm.createContext(sandbox);
const delay=()=>new Promise(resolve=>setTimeout(resolve,5));
async function apply(){elements['query-form'].listeners.submit({preventDefault(){}});await delay();}
(async()=>{
 vm.runInContext(code,sandbox,{timeout:1000});
 await delay();
 assert.equal(elements.results.children.length,table.rows.length);
 const intField=fields.find(f=>f.type==='integer').name;
 elements['sort-field'].value=intField;
 elements['sort-direction'].value='desc';
 await apply();
 const numbers=elements.results.children.map(tr=>Number(tr.children[fields.findIndex(f=>f.name===intField)].textContent));
 assert.deepEqual(numbers,[...numbers].sort((a,b)=>b-a));
 const stringField=fields.find(f=>f.type==='text' && ['family','lane'].includes(f.name)).name;
 const value=table.rows[0][stringField];
 elements['filter-field'].value=stringField;
 elements['filter-field'].listeners.change();
 elements['filter-value'].value=value;
 await apply();
 assert.equal(elements.results.children.length,table.rows.filter(x=>x[stringField]===value).length);
 elements['filter-field'].value=intField;
 elements['filter-field'].listeners.change();
 assert.equal(elements['filter-value'].type,'number');
 elements['filter-value'].value=String(table.rows[0][intField]);
 await apply();
 assert.equal(elements.results.children.length,table.rows.filter(x=>x[intField]===table.rows[0][intField]).length);
 assert(calls.some(x=>x.includes('filter_by=')));
 assert.equal(elements['feedback'].getAttribute('role'),undefined);
 console.log('UI_DOM_SIM_PASS '+table.table_name);
})().catch(e=>{console.error(e);process.exitCode=1});
