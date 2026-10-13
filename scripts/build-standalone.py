"""Build a fully self-contained HTML file without images or external dependencies."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
html = (ROOT / 'index.html').read_text()
for name in ('layout','portrait'):
    css = (ROOT / 'styles' / (name + '.css')).read_text()
    html = html.replace(f'<link rel="stylesheet" href="./styles/{name}.css">', f'<style>\n{css}\n</style>')
source = '\n'.join(re.sub(r'^export ', '', (ROOT / 'src' / (name + '.mjs')).read_text(), flags=re.M) for name in ('parameters','geometry','i18n','app'))
source = re.sub(r'^import .*?;\n', '', source, flags=re.M)
html = html.replace('<script type="module" src="./src/app.mjs"></script>', f'<script type="module">\n{source}\n</script>')
out = ROOT / 'standalone.html'
out.write_text(html)
print(f'Generated {out} ({out.stat().st_size} bytes). No external runtime assets.')
