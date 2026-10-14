"""Build offline, no-network Research 010 blind-rating and results pages.
The archived renderer is a pinned Git blob, NOT a separately evolved drawing.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'study'
EXPECTED_BLOB='673e76657792a3c808c4a51c4f0f09c659624b9f'


def get_plain_js(path):
    source=path.read_text(encoding='utf-8')
    source=re.sub(r'(?m)^import .*?;\n','',source)
    source=re.sub(r'(?m)^export ','',source)
    return source


def renderer():
    blob=(STUDY/'010-renderer.html').read_bytes()
    git_blob=hashlib.sha1(b'blob '+str(len(blob)).encode('ascii')+b'\0'+blob).hexdigest()
    if git_blob!=EXPECTED_BLOB:
        raise ValueError('R010 renderer snapshot has changed; the blind study must not silently change art.')
    return blob.decode('utf-8')


def render_file(kind):
    html=(STUDY/f'010-{kind}.html').read_text(encoding='utf-8')
    body=get_plain_js(STUDY/f'010-{kind}.mjs')
    before=get_plain_js(ROOT/'src'/'blind010.mjs')
    prefix=''
    if kind=='blind':
        pinned=json.dumps(renderer(),ensure_ascii=True).replace('<',r'\u003c').replace('>',r'\u003e')
        prefix='const INLINED_HTML = '+pinned+';\n'
        target='frame.src=`./010-renderer.html?r009=${encodeURIComponent(variant)}&embed=1`;'
        replacement='frame.srcdoc=INLINED_HTML.replace("const strokeVariant = qs.get(\\\'r009\\\');", "const strokeVariant = \\\'"+variant+"\\\';").replace("const researchEmbed = qs.get(\\\'embed\\\') === \\\'1\\\'", "const researchEmbed = true");'
        if target not in body:raise ValueError('Browser study renderer URL pattern changed')
        body=body.replace(target,replacement)
    script=f'<script type="module" src="./010-{kind}.mjs"></script>'
    if script not in html:raise ValueError('Study module reference changed')
    html=html.replace(script,f'<script type="module">\n{prefix}{before}\n{body}\n</script>')
    # The distributed files must not link to unavailable HTTP/module pages.
    if kind=='blind':
        html=html.replace('href="010-results.html"','href="010-results-offline.html"')
        html=html.replace('href="../index.html"','href="#experiment"')
        html=html.replace('href="../docs/RESEARCH-010.md"','href="#experiment"')
    else:
        html=html.replace('href="010-blind.html"','href="010-blind-offline.html"')
        html=html.replace('href="../docs/RESEARCH-010.md"','href="#summary"')
    return html


def main():
    check='--check' in sys.argv[1:]
    for kind in ('blind','results'):
        output=STUDY/f'010-{kind}-offline.html'
        intended=render_file(kind)
        if check:
            if not output.is_file() or output.read_text(encoding='utf-8')!=intended:
                raise ValueError(f'{output.name} is stale. Run: python3 scripts/build-r010-study.py')
        else:output.write_text(intended,encoding='utf-8')
        print(f'RESEARCH010_OFFLINE_{"MATCH" if check else "BUILT"}: {output.name} ({len(intended.encode("utf-8"))} bytes)')

if __name__=='__main__':main()
