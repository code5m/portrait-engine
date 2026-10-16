"""Download only pinned MIT reference geometry into ignored QA output. No code execution."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/sketch-s0'
lock=json.loads((ROOT/'research/sketch/sources.lock.json').read_text())['ict']
base='https://raw.githubusercontent.com/'+lock['repository']+'/'+lock['commit']+'/'
report={'repository':lock['repository'],'commit':lock['commit'],'files':[]}
(OUT/'vendor').mkdir(parents=True,exist_ok=True)
for item in lock['files']:
    target=OUT/'vendor'/item['destination']
    data=target.read_bytes() if target.exists() else urllib.request.urlopen(base+item['path'],timeout=60).read(8*1024*1024)
    sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if sha!=item['gitBlob']:raise SystemExit('Pinned upstream blob mismatch: '+item['path'])
    target.write_bytes(data)
    report['files'].append({'path':item['path'],'gitBlob':sha,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(OUT/'source-verification.json').write_text(json.dumps(report,indent=2))
print('S0_PINNED_SOURCE_VERIFIED',json.dumps(report))
