import pathlib,urllib.request,shutil
root=pathlib.Path(r'C:\Users\ahmad\Desktop\idk\Gym_Backend\design\mobile').resolve()
qa=root/'review-design.py'
s=qa.read_text(encoding='utf-8')
s=s.replace("current='home';render();history=[]", "current='home';render();history=[];clearTimeout(toast.timer);document.querySelector('#toast').classList.remove('show')")
qa.write_text(s,encoding='utf-8')
readme=root/'README.md'
s=readme.read_text(encoding='utf-8').replace('Typography: condensed display headings and neutral sans-serif body.','Typography: Barlow Condensed (700/800) headings and Arial/Helvetica body; fonts are bundled locally.')
s+='\n## Review results\n31 screens rendered at 390px and 360px without horizontal overflow. Nine interaction paths checked. No browser runtime errors. See review-report.json.\nOpen design-overview.png for six key screens and preview-desktop.png for the desktop review layout.\n\n## Assets\nBarlow Condensed by Jeremy Tribby, distributed under SIL Open Font License; see assets/OFL.txt.\nIllustrative gym photo: https://images.unsplash.com/photo-1534438327276-14e5300c3a48 (Unsplash).\n'
readme.write_text(s,encoding='utf-8')
try:
    urllib.request.urlretrieve('https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/OFL.txt',root/'assets'/'OFL.txt')
except Exception as e: print('Font license:',e)
for name in ['design-payload.txt','refine-design.py','app-check.js']:
    target=(root/name).resolve()
    if target.parent==root and target.is_file(): target.unlink()
browser=(root/'.browser-preview').resolve()
if browser.parent==root and browser.name=='.browser-preview' and browser.is_dir():
    print('Removing generated browser cache:',browser)
    shutil.rmtree(browser,ignore_errors=True)
print('Handoff finalized.')

