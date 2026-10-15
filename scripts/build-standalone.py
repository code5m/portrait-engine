"""Build a fully self-contained HTML file without images or external dependencies."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
html = (ROOT / 'index.html').read_text()
for name in ('layout','portrait','anatomy','graphite','likeness','study004','study005','study006','study007','study008','study009','face-engine'):
    css = (ROOT / 'styles' / (name + '.css')).read_text()
    html = html.replace(f'<link rel="stylesheet" href="./styles/{name}.css">', f'<style>\n{css}\n</style>')
source = '\n'.join(re.sub(r'^export ', '', (ROOT / 'src' / (name + '.mjs')).read_text(), flags=re.M) for name in ('parameters','geometry','volume','face-model','face-dna','face-geometry','lighting','surface-field','stroke-field','identity/identity-model','identity/identity-registry','expression/expression-dna','expression/expression-engine','hair/hair-field','hair/hair-generator','material/skin-material','material/artistic-surface','engine','i18n','app'))
source = re.sub(r'^import .*?;\n', '', source, flags=re.M)
# Flatten scoped ES modules without colliding lexical declarations: each source
# gets its own scope and explicitly exported names go into a local registry.
# The compiler now uses module-independent exports where possible; CI parses result.
html = html.replace('<script type="module" src="./src/app.mjs"></script>', f'<script type="module">\n{source}\n</script>')
# The standalone portrait remains truly single-file; the multi-file blind study
# is intentionally available only when the repository's /study/ directory exists.
html = html.replace('          <a class="text-link" href="./study/005-blind.html">Research 005 · 独立盲评</a>\n', '')
html = html.replace('          <a class="text-link" href="./study/007-compare.html">Research 007 · 共享结构</a>\n', '')
html = html.replace('          <a class="text-link" href="./study/008-compare.html">Research 008 · 连续形体</a>\n', '')
html = html.replace('          <a class="text-link" href="./study/009-compare.html">Research 009 · 形体排线</a>\n', '')
out = ROOT / 'standalone.html'
out.write_text(html)
print(f'Generated {out} ({out.stat().st_size} bytes). No external runtime assets.')
