import pathlib,subprocess,time,json,urllib.request,base64,tempfile,shutil
from websockets.sync.client import connect
from PIL import Image,ImageOps,ImageDraw
root=pathlib.Path(r'C:\Users\ahmad\Desktop\idk\Gym_Backend\design\mobile')
profile=pathlib.Path(tempfile.mkdtemp(prefix='form-design-browser-'))
edge=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
proc=subprocess.Popen([edge,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9227','--remote-debugging-address=127.0.0.1','--remote-allow-origins=http://localhost:9227','--user-data-dir='+str(profile),'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)
ws=None
try:
    for _ in range(100):
        try:
            tabs=json.load(urllib.request.urlopen('http://127.0.0.1:9227/json',timeout=1))
            target=next(t for t in tabs if t['type']=='page')
            break
        except Exception: time.sleep(.1)
    ws=connect(target['webSocketDebuggerUrl'],origin='http://localhost:9227',max_size=20_000_000)
    serial=0;errors=[]
    def cdp(method,params=None):
        global serial
        serial+=1;sid=serial
        ws.send(json.dumps({'id':sid,'method':method,'params':params or {}}))
        while True:
            msg=json.loads(ws.recv())
            if msg.get('method')=='Runtime.exceptionThrown': errors.append(msg['params'])
            if msg.get('id')==sid:
                if 'error' in msg: raise RuntimeError(msg['error'])
                return msg.get('result',{})
    def js(code):
        r=cdp('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
        if r.get('exceptionDetails'): raise RuntimeError(r['exceptionDetails'])
        return r.get('result',{}).get('value')
    def shot(name):
        data=cdp('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (root/name).write_bytes(base64.b64decode(data['data']))
    cdp('Page.enable');cdp('Runtime.enable')
    cdp('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    cdp('Page.navigate',{'url':(root/'index.html').as_uri()})
    for _ in range(100):
        try:
            if js("typeof views==='object'"): break
        except Exception: pass
        time.sleep(.05)
    js("document.fonts.ready")
    js("const qaStyle=document.createElement('style');qaStyle.textContent='*{animation:none!important;transition:none!important}';document.head.appendChild(qaStyle);state=structuredClone(initial);current='home';render()")
    time.sleep(.25)
    shot('preview-desktop.png')
    cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
    names=js('Object.keys(views)')
    results=[]
    for name in names:
        result=js("current="+json.dumps(name)+";render();({screen:current,overflow:document.querySelector('.screen').scrollWidth>document.querySelector('.screen').clientWidth+1,bodyOverflow:document.body.scrollWidth>390,buttons:document.querySelectorAll('#screen button').length})")
        results.append(result)
    # Interactive member paths, actual DOM event dispatch.
    js("state=structuredClone(initial);current='water';render();document.querySelector('[data-action=\"quick-water\"]').click()")
    assert js('state.water')==1500,'Water logging'
    js("current='class';selectedClass=1;render();document.querySelector('[data-action=\"book\"]').click()")
    assert js('state.booked.includes(1)'),'Class booking'
    js("document.querySelector('[data-action=\"cancel-booking\"]').click();document.querySelector('[data-action=\"confirm-cancel\"]').click()")
    assert not js('state.booked.includes(1)'),'Class cancellation'
    js("current='product';selectedProduct=0;render();document.querySelector('[data-action=\"add-cart\"]').click();current='cart';render();document.querySelector('[data-delta=\"1\"]').click()")
    assert js('total()')==84,'Cart pricing and quantity'
    js("current='checkout';render();document.querySelector('[name=\"address\"]').value='Hamra Street, Beirut';document.querySelector('[name=\"phone\"]').value='+96170000000';document.querySelector('#checkout-form').requestSubmit()")
    assert js("current==='order'&&state.orders.length===1&&state.cart.length===0"),'Checkout'
    js("current='nutrition';render();actions.meal();const mf=document.querySelector('#meal-form');mf.elements.name.value='Test meal';mf.elements.cal.value='300';mf.elements.p.value='20';mf.requestSubmit()")
    assert js('state.meals.length')==3,'Meal logging'
    js("current='chat';render();document.querySelector('#message').value='Thanks coach';document.querySelector('#chat-form').requestSubmit()")
    assert js("state.messages.at(-1)==='Thanks coach'"),'Chat'
    js("current='session';render();const cb=document.querySelector('input[type=checkbox]');cb.checked=true;cb.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('[data-action=\"finish\"]').click();document.querySelector('[data-action=\"confirm-finish\"]').click()")
    assert js("state.completed&&current==='complete'"),'Session logging'
    js("state.role='admin';current='admin-orders';render();actions['advance-order']();actions['advance-order']();actions['advance-order']()")
    assert js("state.adminOrderStatus==='OUT_FOR_DELIVERY'"),'Order transitions'
    js("state=structuredClone(initial);save();draftSets.forEach(s=>s.done=false);current='home';render();history=[];clearTimeout(toast.timer);document.querySelector('#toast').classList.remove('show')")
    captures=[('home','Today'),('workouts','Training'),('classes','Classes'),('progress','Progress'),('shop','Shop'),('membership','Membership')]
    for name,label in captures:
        js("current="+json.dumps(name)+";render()")
        time.sleep(.1)
        shot('screen-'+name+'.png')
    # Recheck the layouts at a narrow phone size.
    cdp('Emulation.setDeviceMetricsOverride',{'width':360,'height':780,'deviceScaleFactor':1,'mobile':True})
    narrow=[]
    for name in names:
        r=js("current="+json.dumps(name)+";render();({screen:current,overflow:document.querySelector('.screen').scrollWidth>document.querySelector('.screen').clientWidth+1})")
        if r['overflow']: narrow.append(r)
    board=Image.new('RGB',(1320,1930),'#eaeae7');draw=ImageDraw.Draw(board)
    draw.text((44,24),'FORM.   /   MOBILE APP DESIGN   /   RED - BLACK - WHITE',fill='#111111')
    for i,(name,label) in enumerate(captures):
        x=44+(i%3)*428;y=74+(i//3)*922
        im=Image.open(root/('screen-'+name+'.png')).convert('RGB')
        board.paste(im,(x,y))
        draw.text((x,y+860),str(i+1).zfill(2)+'  '+label.upper(),fill='#333333')
    board.save(root/'design-overview.png')
    report={'screens_reviewed':len(names),'screens':results,'narrow_overflow':narrow,'runtime_errors':errors,'interaction_checks':['water','booking','cancellation','cart quantity','checkout','meal logging','chat','workout completion','admin order transitions']}
    (root/'review-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'screens':len(names),'overflow':[r for r in results if r['overflow'] or r['bodyOverflow']],'narrow_overflow':narrow,'runtime_errors':len(errors),'interaction_checks':len(report['interaction_checks'])}))
finally:
    if ws:
        try: cdp('Browser.close')
        except Exception: pass
        try: ws.close()
        except Exception: pass
    try: proc.wait(timeout=5)
    except Exception: proc.terminate()
    resolved=profile.resolve()
    if resolved.parent==pathlib.Path(tempfile.gettempdir()).resolve() and resolved.name.startswith('form-design-browser-'):
        shutil.rmtree(resolved,ignore_errors=True)

