"""Independent preregistered faults; failures in test infrastructure never score."""
import pathlib,json,subprocess,shutil,xml.etree.ElementTree as ET
from j4_stage import run_http
cfg=json.loads(pathlib.Path('j4_config.json').read_text())
mut=json.loads(pathlib.Path('j4_mutations.json').read_text())
NS={'t':'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
results=[]
for name,file,old,new in mut:
    p=pathlib.Path(file);original=p.read_text();assert old in original,(name,'missing mutation target')
    dest=pathlib.Path('seed-evidence')/name;dest.mkdir(parents=True,exist_ok=True)
    try:
        p.write_text(original.replace(old,new,1))
        # The Razor source generator / static-web-assets incremental caches corrupt across
        # repeated same-process rebuilds in this loop (stale generated code, or a stale assets
        # manifest, for files we never touched). `dotnet clean` first removes obj/bin so each
        # mutation gets a truly fresh build instead of trying to debug either cache.
        with (dest/'clean.log').open('w') as log:
            subprocess.run(['dotnet','clean','Everything.sln','--configuration','Release'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
        with (dest/'build.log').open('w') as log:
            b=subprocess.run(['dotnet','build','Everything.sln','--configuration','Release'],stdout=log,stderr=subprocess.STDOUT,timeout=300)
        assert b.returncode==0,'build infrastructure failure (not scored as a detection)'
        shutil.rmtree('TestResults',ignore_errors=True)
        with (dest/'test.log').open('w') as log:
            t=subprocess.run(['dotnet','test','Everything.sln','--configuration','Release','--no-build',
                               '--logger','trx','--results-directory','TestResults'],
                              stdout=log,stderr=subprocess.STDOUT,timeout=300)
        trxs=list(pathlib.Path('TestResults').rglob('*.trx'));assert len(trxs)==4,('expected 4 project trx files',len(trxs))
        cases=[]
        for f in trxs:
            root=ET.parse(f).getroot()
            cases += root.findall('.//t:UnitTestResult',NS)
        assert len(cases)==cfg['test_count'],('test inventory changed',len(cases))
        failed=sum(c.attrib.get('outcome')=='Failed' for c in cases)
        for f in trxs:shutil.copy(f,dest/f.name)
        harness_detected=run_http(str(dest),strict=False)
        results.append({'fault':name,'project_detected':failed>0,'project_failures':failed,'harness_detected':harness_detected})
        pathlib.Path('seed-results.json').write_text(json.dumps(results,indent=2))
    finally:
        p.write_text(original)
print(json.dumps(results,indent=2))
if len(results)==5:
    a=sum(x['project_detected'] for x in results);b=sum(x['project_detected'] or x['harness_detected'] for x in results)
    assert b>=4 and 5-b<=(5-a)/2,'seed threshold missed'
