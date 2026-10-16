// The targeting regressions can be checked without touching real lights.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/ui/scope-ui.js','utf8');
function fixture(){
  const elements=new Map(),calls=[];
  function element(){return {textContent:'',innerHTML:'',hidden:false,value:'',dataset:{},classList:{add(){},toggle(){}},setAttribute(){},prepend(){},closest(){return element()}}}
  const context=vm.createContext({Set,console,S:{room:'room-tapo',selectedDevice:'lamp-a',selectedLights:new Set(['lamp-a','lamp-b','pc-keyboard']),selectedPc:new Set(),formDraft:{}},document:{addEventListener(){},createElement:element},$:selector=>{if(!elements.has(selector))elements.set(selector,element());return elements.get(selector)},$$:()=>[],devices:()=>[{id:'lamp-a',name:'A'},{id:'lamp-b',name:'B'}],pcDevices:()=>[{key:'pc-keyboard',name:'Keyboard'}],rooms:()=>[{id:'room-tapo',name:'Tapo room',device_ids:['lamp-a']},{id:'room-pc',name:'PC room',device_ids:[],pc_keys:['pc-keyboard']}],esc:String,opt:(id,label)=>`<option value="${id}">${label}</option>`,deviceCard:d=>`card:${d.id}`,renderDetail(){},renderPc(){},renderEffects(){},renderScenes(){},action(){},isOn:()=>true,byId:()=>null,effectsHubMembers:()=>({tapo:[],pc:[]}),targetLabel:String,command:async(name,params)=>calls.push({name,params}),toast:message=>calls.push({message})});
  vm.runInContext(source,context);return {context,elements,calls,run:code=>vm.runInContext(code,context)};
}
test('bulk Tapo command cannot include another room or a PC selection',async()=>{
  const f=fixture();await f.run("action('group-off')");
  assert.equal(f.calls[0].name,'target.apply');
  assert.deepEqual(Array.from(f.calls[0].params.target),['lamp-a']);
  assert.equal(f.calls[0].params.power,false);
});
test('select all targets visible Tapo, removes invisible detail and PC-only filters',async()=>{
  const f=fixture();f.run('S.selectedDevice="lamp-b"');await f.run("action('select-all')");
  assert.deepEqual(Array.from(f.context.S.selectedLights),['lamp-a']);
  assert.equal(f.context.S.selectedDevice,'lamp-a');
  assert.doesNotMatch(f.elements.get('#room-filters').innerHTML,/PC room/);
  assert.match(f.elements.get('#room-filters').innerHTML,/Tapo room/);
});
test('PC-only remembered room falls back to all Tapo and a valid detail',()=>{
  const f=fixture();f.run('S.room="room-pc"; S.selectedDevice="missing"; renderLights()');
  assert.equal(f.context.S.room,'Tutte');assert.equal(f.context.S.selectedDevice,'lamp-a');
  assert.match(f.elements.get('#light-devices').innerHTML,/card:lamp-a/);
  assert.match(f.elements.get('#light-devices').innerHTML,/card:lamp-b/);
});
test('bulk action requires an explicit selection',async()=>{
  const f=fixture();f.run('S.selectedLights.clear()');await f.run("action('group-on')");
  assert.equal(f.calls.length,1);assert.match(f.calls[0].message,/Seleziona/);
});

test('PC badge follows fresh MSI power readback and falls back to intent when stale',()=>{
  const f=fixture();
  assert.equal(f.run("pcDisplayedPower({on:true,native_observed:{power:false,source:'msi_sdk',observed_at:99}},100)"),false);
  assert.equal(f.run("pcDisplayedPower({on:false,native_observed:{power:true,source:'msi_sdk',observed_at:99}},100)"),true);
  assert.equal(f.run("pcDisplayedPower({on:true,native_observed:{power:false,source:'msi_sdk',observed_at:89}},100)"),true);
  assert.equal(f.run("pcDisplayedPower({on:false,native_observed:{power:null,source:'msi_sdk',observed_at:99}},100)"),false);
  assert.equal(f.run("pcDisplayedPower({on:true,native_observed:{power:false,source:'msi_sdk',observed_at:999}},100)"),true);
  assert.equal(f.calls.length,0,'Displaying observed power never writes a command');
});
