"""Syntax gate for the *concatenated* standalone JS (not only source modules).

Research 008 discovered that separately valid ES modules can redeclare one
identifier when merged into a single script; Node --check of each source file
alone did not catch it. This gate runs after build before unit tests and CI.
"""
import pathlib
import re
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
html = (root / 'standalone.html').read_text(encoding='utf8')
scripts = re.findall(r'<script type="module">\s*(.*?)\s*</script>', html, flags=re.S)
if len(scripts) != 1:
    raise SystemExit(f'Expected exactly one inline standalone module, found {len(scripts)}')
if 'src="./src/app.mjs"' in html or '<link rel="stylesheet"' in html:
    raise SystemExit('Standalone contains external runtime source')
with tempfile.TemporaryDirectory(prefix='portrait-js-check-') as scratch:
    path = pathlib.Path(scratch) / 'standalone-script.mjs'
    path.write_text(scripts[0], encoding='utf8')
    subprocess.run(['node', '--check', str(path)], check=True)
print('STANDALONE_JS_CHECK_PASS: bundled module parses without identifier collisions')
