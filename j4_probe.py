import urllib.request,urllib.error,json,hashlib,time,re,pathlib
routes=[('GET','/',None),('GET','/health',None)]
for i in range(90):
    try:
        urllib.request.urlopen('http://127.0.0.1:3000/health',timeout=2)
        break
    except urllib.error.HTTPError:
        break
    except Exception:
        time.sleep(2);continue
else:
    raise SystemExit('BOOT FAILED')
def normalize(v):
    if isinstance(v,dict):return {k:normalize(x) for k,x in v.items() if k not in ('createdAt','updatedAt','timestamp','requestId')}
    if isinstance(v,list):return [normalize(x) for x in v]
    return v
out=[]
for method,path,body in routes:
    req=urllib.request.Request('http://127.0.0.1:3000'+path,method=method,headers={'Accept':'text/html,application/json'})
    try:r=urllib.request.urlopen(req,timeout=20)
    except urllib.error.HTTPError as e:r=e
    raw=r.read().decode('utf8','replace');ct=r.headers.get('Content-Type','').split(';')[0]
    try:raw=json.dumps(normalize(json.loads(raw)),sort_keys=True,separators=(',',':'))
    except ValueError:
        raw=re.sub(r'(name="__RequestVerificationToken"[^>]*value=")[^"]*',r'\1NORMALIZED',raw)
        raw=re.sub(r'\?v=[A-Za-z0-9_-]+','?v=NORMALIZED',raw)
        raw=re.sub(r';?\s*\.AspNetCore\.[A-Za-z.]+=[^;]+','',raw)
    out.append(dict(method=method,path=path,status=r.code,content_type=ct,sha256=hashlib.sha256(raw.encode()).hexdigest(),body=raw))
pathlib.Path('surface.actual.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
assert all(x['status']<500 for x in out),'server error in measured surface'
expected=pathlib.Path('surface.json')
if expected.exists():assert json.loads(expected.read_text())==out,'CHARACTERIZATION DRIFT'
print('BOOT + CHARACTERIZATION PASS')
