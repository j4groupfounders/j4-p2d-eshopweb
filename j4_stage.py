"""Boot the Web project against the in-memory DB and run the HTTP probe; no external services."""
import pathlib,subprocess,os,signal,sys

def run_http(dest,strict=True):
    dest=pathlib.Path(dest);dest.mkdir(parents=True,exist_ok=True)
    pathlib.Path('surface.actual.json').unlink(missing_ok=True)
    env=os.environ.copy()
    env['ASPNETCORE_URLS']='http://127.0.0.1:3000'
    with (dest/'boot.log').open('w') as log:
        server=subprocess.Popen(
            ['dotnet','run','--project','src/Web/Web.csproj','--configuration','Release','--no-build'],
            env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            with (dest/'probe.log').open('w') as log2:
                probe=subprocess.run([sys.executable,'j4_probe.py'],stdout=log2,stderr=subprocess.STDOUT,timeout=180)
            assert pathlib.Path('surface.actual.json').exists(),'server/probe infrastructure failure'
            import json
            surface=json.loads(pathlib.Path('surface.actual.json').read_text())
            assert all(r['status']<500 for r in surface),'server runtime error, not scored as detection'
            (dest/'surface.json').write_text(json.dumps(surface,indent=2))
            if strict:assert probe.returncode==0,'characterization drift'
            return probe.returncode!=0
        finally:
            try:os.killpg(server.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try:os.killpg(server.pid,signal.SIGKILL)
                except ProcessLookupError:pass

if __name__=='__main__':
    run_http('http-evidence')
