"""Reproducible offline lab. This compiles text and never embeds reference images."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'research/sketch/s0-scenes.json').read_text())
source=(ROOT/'study/sketch-s0.mjs').read_text()
html=(ROOT/'study/sketch-s0.template.html').read_text().replace('__SCENES__',json.dumps(config,ensure_ascii=False,separators=(',',':'))).replace('__MODULE__',source)
out=ROOT/'test-results/sketch-s0/lab.html'
out.parent.mkdir(parents=True,exist_ok=True)
if '--check' in sys.argv:
    if not out.exists() or out.read_text()!=html: raise SystemExit('S0 offline source drift')
else: out.write_text(html,encoding='utf-8')
print('S0_OFFLINE_MATCH' if '--check' in sys.argv else 'S0_OFFLINE_BUILT',len(html.encode()))
