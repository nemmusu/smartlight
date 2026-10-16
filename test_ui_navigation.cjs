/* Browser regression test against test_ui_contract.py --serve --rich; simulated hardware only. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
async function main(){
  const base = process.argv[2];assert(base,'Pass local QA server URL');
  const output=path.resolve('.testdata/qa-ui-20261016');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
  const page=await browser.newPage({viewport:{width:1420,height:900},timezoneId:'Europe/Rome'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const screenshot=async name=>page.screenshot({path:path.join(output,name+'.png'),fullPage:false});
  const nav=async name=>{await page.locator(`[data-page="${name}"]`).click();await page.waitForTimeout(100);};
  const call=async(command,params={})=>{const r=await page.request.post(base+'invoke',{data:{command,params}});const json=await r.json();assert.equal(json.ok,true,JSON.stringify(json));return json.data;};
  let initialLanguage;
  try{
    const marker=await page.request.get(base+'calls');assert(Array.isArray(await marker.json()),'Use only the simulated QA server');
    initialLanguage=(await call('settings_get')).language||'en';
    await call('settings_set',{language:'it'});
    await page.goto(base);await page.waitForFunction(()=>document.querySelector('#connection-text').textContent==='Controller connesso');
    await call('target.apply',{target:'all',power:true});await page.evaluate(()=>loadStatus());
    const initial=await call('status');assert.equal(initial.pc.devices.length,12);assert.equal(initial.rooms.length,6);
    await screenshot('workspace');
    const bottom=await page.locator('#workspace-rooms').boundingBox();assert(bottom.y+bottom.height<900,'All six room cards must fit in the desktop viewport');
    assert.equal(await page.locator('.workspace-pool-drawer').getAttribute('open'),null);
    const camera=initial.rooms.find(r=>r.name==='Camera');
    const roomCard=page.locator(`[data-workspace-target="room:${camera.id}"]`);
    await roomCard.locator('[data-workspace-action="off"]').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    let state=await call('status');assert(state.devices.every(d=>!d.on));assert(Object.values(state.pc.state).every(d=>d.on));
    await roomCard.locator('[data-workspace-action="on"]').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    await roomCard.locator('summary').click();await page.waitForTimeout(100);await call('status');
    await page.evaluate(()=>loadStatus());assert(await roomCard.locator('details').evaluate(d=>d.open),'Room disclosure survives polling');
    await roomCard.locator('summary').click();

    await nav('lights');await screenshot('tapo-single');
    assert(!(await page.locator('#room-filters').innerText()).includes('PC senza tastiera'));
    await page.locator(`[data-room="${initial.rooms.find(r=>r.name==='Lampadine camera').id}"]`).click();
    assert.equal(await page.locator('#light-devices [data-device]').count(),2);
    assert((await page.locator('#light-detail').innerText()).includes('Lampadina'));
    assert(!(await page.locator('#light-detail').innerText()).includes('LED scrivania'));
    await page.locator('[data-select-light="bulb1"]').check();await screenshot('tapo-selection');
    assert.equal(await page.locator('#light-detail').isVisible(),false);
    assert.equal(await page.locator('#page-lights .group-card').isVisible(),true);
    await page.locator('[data-action="group-off"]').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    state=await call('status');assert.equal(state.devices.find(d=>d.id==='bulb1').on,false);assert.equal(state.devices.find(d=>d.id==='strip').on,true);assert(Object.values(state.pc.state).every(d=>d.on));
    await page.locator('[data-device="bulb2"] h3').click();assert.equal(await page.locator('#light-detail').isVisible(),true);assert.equal(await page.locator('#page-lights .group-card').isVisible(),false);

    for(const definition of [
      {name:'Bianco',color:'#dddfff',brightness:80},
      {name:'Preset con un nome lungo per controllare la scheda',color:'#00aaff',brightness:65},
      {name:'Relax della sera',kind:'native_effect',effect:'Relax'},
      {name:'Onda del PC',kind:'pc_effect',effect:'onda'},
      {name:'Atmosfera coordinata',kind:'theme',theme_id:initial.themes[0].id}
    ])await call('presets.save',definition);
    await page.evaluate(()=>loadStatus());
    await nav('effects');await screenshot('effects-presets');
    for(const width of [1420,1100,850,600]){
      await page.setViewportSize({width,height:900});
      const failures=await page.locator('#preset-list .effects-hub-preset').evaluateAll(cards=>cards.flatMap(card=>{
        const outer=card.getBoundingClientRect(),copy=card.querySelector('.preset-copy').getBoundingClientRect(),name=card.querySelector('strong');
        const errors=[];if(copy.width<120||!name.textContent.trim())errors.push('Preset name hidden');
        for(const button of card.querySelectorAll('button')){const box=button.getBoundingClientRect();if(box.left<outer.left||box.right>outer.right||box.bottom>outer.bottom)errors.push('Preset button outside card')}
        return errors;
      }));assert.deepEqual(failures,[],`Preset card layout at ${width}`);await screenshot('presets-'+width);
    }
    await page.setViewportSize({width:1420,height:900});
    for(const category of ['effects-themes','effects-custom','effects-tapo','effects-pc']){
      await page.locator(`.effects-hub-jumps a[href="#${category}"]`).click();
      assert.equal(await page.locator('#page-effects .effects-hub-section:visible').count(),1);await screenshot(category);
    }
    await page.locator('#effect-target').selectOption('bulb1');assert.equal(await page.locator('#effects-pc-list [data-hub-pc]:enabled').count(),0);

    await nav('pc');await screenshot('pc');await page.locator('[data-select-pc="keyboard"]').check();
    assert((await page.locator('[data-action="pc-off"]').innerText()).includes('1 luci PC selezionate'));
    await page.locator('[data-action="pc-off"]').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    state=await call('status');assert.equal(state.pc.state.keyboard.on,false);assert.equal(state.pc.state.mouse.on,true);
    await page.locator('[data-action="pc-on"]').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    const cooling=page.locator('[data-pc-group-select="cooling"]'),memory=page.locator('[data-pc-group-select="memory"]');
    await cooling.click();assert.equal(await cooling.innerText(),'Deseleziona categoria');
    await memory.click();assert.equal(await page.locator('[data-select-pc]:checked').count(),9);
    await cooling.click();assert.equal(await cooling.innerText(),'Seleziona categoria');assert.equal(await page.locator('[data-select-pc]:checked').count(),5);
    assert(await page.locator('[data-select-pc="keyboard"]').isChecked());
    await memory.click();assert.equal(await page.locator('[data-select-pc]:checked').count(),1);
    await cooling.click();await page.locator('[data-select-pc="fan1"]').uncheck();assert.equal(await cooling.innerText(),'Seleziona categoria');
    await cooling.click();assert.equal(await cooling.innerText(),'Deseleziona categoria');await cooling.click();

    await nav('automation');await screenshot('automation-programs');
    for(const name of ['automation-timer','automation-away','automation-energy']){
      await page.locator(`[data-section-panel="${name}"]`).click();assert.equal(await page.locator('#'+name).isVisible(),true);await screenshot(name);
    }
    await page.locator('[data-section-panel="automation-programs"]').click();await page.locator('[data-action="new-schedule"]').first().click();
    await page.getByRole('button',{name:'Una volta',exact:true}).click();await page.locator('#modal-body [name="once_date"]').fill('2026-12-20');
    await page.getByRole('button',{name:'Sera 19:00'}).click();assert.equal(await page.locator('#modal-body [name="once_date"]').inputValue(),'2026-12-20');
    await page.locator('#modal-body [name="name"]').fill('Calendario QA');await screenshot('schedule-calendar');
    await page.locator('#modal-submit').click();await page.waitForSelector('#modal',{state:'hidden'});assert((await call('schedules.list')).some(s=>s.once_date==='2026-12-20'));
    await page.locator('[data-action="new-schedule"]').first().click();await page.getByRole('button',{name:'Lun–Ven',exact:true}).click();
    assert.equal(await page.locator('[data-schedule-day]:checked').count(),5);await screenshot('schedule-week');await page.locator('[data-modal-close]').first().click();

    await nav('scenes');
    for(const category of ['saved','colors','sync']){await page.locator(`[data-scene-category="${category}"]`).click();assert.equal(await page.locator('[data-scene-panel]:visible').count(),1);await screenshot('scenes-'+category);}
    await nav('settings');
    if(initial.settings.os==='posix'){
      assert((await page.locator('#setting-auto-start').evaluate(el=>el.closest('label').textContent)).includes('all’accesso'));
      assert(!(await page.locator('#auto-start-help').innerText()).includes('Windows'));
    }
    for(const category of ['general','tapo','network','mcp','backup','help']){await page.locator(`[data-section-panel="settings-${category}"]`).click();assert.equal(await page.locator('#settings-'+category).isVisible(),true);await screenshot('settings-'+category);}
    await page.locator('[data-section-panel="settings-mcp"]').click();assert.equal(await page.locator('#mcp-path').isVisible(),true);
    await page.locator('[data-section-panel="mcp-http-method"]').click();assert.equal(await page.locator('#mcp-scope').isVisible(),true);await screenshot('settings-mcp-http');
    await page.locator('#all-off-btn').click();await page.waitForFunction(()=>!document.body.classList.contains('loading'));
    state=await call('status');assert(state.devices.every(d=>!d.on));assert(Object.values(state.pc.state).every(d=>!d.on));
    for(const width of [1100,850]){
      await page.setViewportSize({width,height:850});
      for(const name of ['home','lights','effects','automation','pc','scenes','settings']){await nav(name);const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false,`Horizontal overflow ${name}@${width}`);await screenshot(name+'-'+width);}
    }
    assert.deepEqual(errors,[],'No uncaught UI errors');
    console.log(JSON.stringify({ok:true,screenshots:output,sections:7,categories:18,viewports:[1420,1100,850],checks:'target scoping, single/bulk editor, polling, repeated power, calendar, category visibility, keyboard scope, overflow',errors},null,2));
  }finally{if(initialLanguage)await call('settings_set',{language:initialLanguage}).catch(()=>{});await browser.close();}
}
main().catch(e=>{console.error(e);process.exit(1)});
