/* Run against test_ui_contract.py --serve --rich. All MSI devices are simulated. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
  const base=process.argv[2];assert(base,'Provide the simulated UI URL');
  const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
  try {
    const page=await browser.newPage({viewport:{width:1100,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base);await page.waitForFunction(()=>typeof S!=='undefined'&&S.data.devices.length===3);
    const fixture=await page.request.get(base+'calls');assert(fixture.ok(),'Use the isolated simulation server');
    await page.evaluate(()=>{
      loadStatus=async()=>{};
      loadPc=async()=>{};
      window.msiCalls=[];
      command=async(name,params)=>{window.msiCalls.push({name,params});return {ok:true}};
      S.data.pc.devices=[{key:'msi:a',id:'msi:a',name:'MSI zone A',type:'motherboard',backend:'mystic',online:true},{key:'msi:b',id:'msi:b',name:'MSI zone B',type:'motherboard',backend:'mystic',online:true}];
      S.data.pc.effects=[{id:'statico',label:'Statico',supported_keys:['msi:a','msi:b']},{id:'respiro',label:'Respiro',supported_keys:['msi:a','msi:b']},{id:'msi:Rainbow',label:'Rainbow',native:true,supported_keys:['msi:a'],capabilities:{color:false,speed:true,brightness:false}},{id:'msi:Breathing',label:'Breathing',native:true,supported_keys:['msi:a','msi:b'],capabilities:{color:true,speed:true,brightness:true}}];
      S.data.presets=[{id:'native-demo',name:'Demo rainbow',kind:'pc_effect',effect:'msi:Rainbow'}];S.selectedPc=new Set(['msi:a']);S.formDraft['effect-target']='selected';renderPc();renderEffects();nav('pc');
    });
    for(const lang of ['en','it']){
      await page.evaluate(lang=>{S.data.settings.language=lang;SmartlightI18n.setLanguage(lang);S.selectedPc=new Set(['msi:a']);renderPc()},lang);
      await page.locator('#pc-effect').selectOption('msi:Rainbow');
      assert.equal(await page.locator('#pc-color').isVisible(),false);
      assert.equal(await page.locator('#pc-color2').isVisible(),false);
      assert.equal(await page.locator('#pc-brightness').isVisible(),false);
      assert.equal(await page.locator('#pc-speed').isVisible(),true);
      await page.locator('[data-action="pc-apply"]').click();
      const call=await page.evaluate(()=>msiCalls.at(-1));
      assert.equal(call.params.patch.effect,'msi:Rainbow');assert.equal(call.params.patch.color,undefined);assert.equal(call.params.patch.brightness,undefined);assert.equal(typeof call.params.patch.speed,'number');
      await page.evaluate(()=>{S.selectedPc=new Set(['msi:a','msi:b']);renderPc()});
      assert.equal(await page.locator('#pc-effect option[value="msi:Rainbow"]').count(),0);
      assert.equal(await page.locator('#pc-effect option[value="msi:Breathing"]').count(),1);
      await page.evaluate(()=>{S.data.pc.effects.find(e=>e.id==='msi:Breathing').device_parameters={'msi:a':{max_speed:5,max_brightness:10},'msi:b':{max_speed:0,max_brightness:10,supports_speed:false}};renderPc()});
      await page.locator('#pc-effect').selectOption('msi:Breathing');
      assert.equal(await page.locator('#pc-speed').isVisible(),false,'All targeted zones must support a control');
      assert.equal(await page.locator('#pc-brightness').isVisible(),true);
      await page.evaluate(()=>{S.selectedPc=new Set(['msi:a']);renderEffects();nav('effects');effectsCategory('effects-pc')});
      await page.locator('[data-hub-pc="msi:Rainbow"]').click();
      assert.equal(await page.locator('#modal [name="color"]').count(),0);
      if(process.env.SMARTLIGHT_QA_SCREENSHOTS){fs.mkdirSync(process.env.SMARTLIGHT_QA_SCREENSHOTS,{recursive:true});await page.screenshot({path:path.join(process.env.SMARTLIGHT_QA_SCREENSHOTS,`msi-native-${lang}.png`)})}
      await page.locator('#modal [name="native_speed"]').evaluate(el=>{el.value='2';el.dispatchEvent(new Event('input',{bubbles:true}))});
      await page.locator('#modal-submit').click();
      assert.equal((await page.evaluate(()=>msiCalls.at(-1))).params.patch.speed,2);
      await page.locator('[data-hub-pc-save="msi:Rainbow"]').click();
      assert.equal(await page.locator('#modal [name="pc_color"]').isVisible(),false);
      assert.equal(await page.locator('#modal [name="pc_brightness"]').isVisible(),false);
      await page.locator('#modal-submit').click();
      const saved=await page.evaluate(()=>msiCalls.at(-1));assert.equal(saved.name,'preset_save');assert.equal(saved.params.effect,'msi:Rainbow');assert.equal(saved.params.color,undefined);
      await page.evaluate(()=>scheduleModal({id:'test-schedule',name:'Demo',time:'20:00',days:[1,2,3,4,5],device_id:'msi:a',action:{preset_id:'native-demo'}}));
      assert.equal(await page.locator('#modal [name="action"]').inputValue(),'preset');
      assert.equal(await page.locator('#modal [name="preset_id"]').inputValue(),'native-demo');
      if(process.env.SMARTLIGHT_QA_SCREENSHOTS){await page.locator('#modal [name="preset_id"]').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(process.env.SMARTLIGHT_QA_SCREENSHOTS,`msi-schedule-${lang}.png`)})}
      await page.locator('#modal-submit').click();
      assert.deepEqual((await page.evaluate(()=>msiCalls.at(-1))).params.action,{preset_id:'native-demo'});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.evaluate(()=>nav('pc'));
    }
    await page.evaluate(()=>{S.data.pc.effects.push({id:'msi:Unknown',label:'Unknown style',native:true,supported_keys:['msi:a'],capabilities:{color:null,speed:null,brightness:null},device_parameters:{'msi:a':{max_speed:5,max_brightness:10,limits_scope:'current_style'}}});S.selectedPc=new Set(['msi:a']);renderPc()});
    await page.locator('#pc-effect').selectOption('msi:Unknown');
    assert.equal(await page.locator('#pc-speed').isVisible(),true);
    await page.locator('[data-action="pc-apply"]').click();
    assert.deepEqual((await page.evaluate(()=>msiCalls.at(-1))).params.patch,{effect:'msi:Unknown'});
    await page.locator('#pc-speed').evaluate(el=>{el.value='2';el.dispatchEvent(new Event('input',{bubbles:true}))});
    await page.locator('[data-action="pc-apply"]').click();
    assert.deepEqual((await page.evaluate(()=>msiCalls.at(-1))).params.patch,{effect:'msi:Unknown',speed:2});
    await page.evaluate(()=>{S.data.pc.devices[0].native_apply_result={unsupported:['speed']};renderPc()});
    assert.match(await page.locator('#pc-native-warning').innerText(),/MSI zone A/);
    assert.deepEqual(errors,[]);console.log('MSI UI: bilingual selection, capabilities, native controls, presets and layout passed.');
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
