"""Build a fully self-contained HTML file without images or external dependencies."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
html = (ROOT / 'index.html').read_text()
for name in ('layout','portrait','anatomy','graphite','likeness','study004','study005','study006','study007','study008','study009','face-engine','research013'):
    css = (ROOT / 'styles' / (name + '.css')).read_text()
    html = html.replace(f'<link rel="stylesheet" href="./styles/{name}.css">', f'<style>\n{css}\n</style>')
# Explicit dependency order also preserves each research script's own scope.
modules = ('parameters','geometry','volume','face-model','face-dna','face-geometry',
           'lighting','surface-field','stroke-field','identity/identity-model',
           'identity/identity-registry','expression/expression-dna',
           'expression/expression-engine','hair/hair-field',
           'hair/hair-generator','material/skin-material',
           'material/artistic-surface','engine','anatomy/identity-contour','i18n','app')
module_registry = []
for name in modules:
    code = (ROOT / 'src' / (name + '.mjs')).read_text()
    # Namespace import declarations are resolved to the exporting module scope.
    imports = re.findall(r"^import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"];?\s*$", code, flags=re.M)
    code = re.sub(r"^import\s*\{[^}]+\}\s*from\s*['\"][^'\"]+['\"];?\s*\n", '', code, flags=re.M)
    aliases = []
    for symbols, relative in imports:
        path = (pathlib.PurePosixPath(name).parent / relative).as_posix()
        # pathlib does not normalize ..; use posixpath.normpath.
        import posixpath
        path = posixpath.normpath(path).removesuffix('.mjs')
        names = []
        for entry in symbols.split(','):
            part = entry.strip().split(' as ')
            names.append(part[0].strip() if len(part) == 1 else (part[0].strip() + ': ' + part[-1].strip()))
        aliases.append('const {' + ', '.join(names) + '} = modules[' + repr(path) + '];')
    exports = re.findall(r'^export\s+(?:const|let|function|class)\s+(\w+)', code, flags=re.M)
    code = re.sub(r'^export\s+', '', code, flags=re.M)
    # Legacy DOM script runs inside its own closure; shared symbols are imported.
    module_registry.append('{\n' + '\n'.join(aliases) + '\n' + code +
        '\nmodules[' + repr(name) + '] = {' + ','.join(exports) + '};\n}')
source = 'const modules = Object.create(null);\n' + '\n'.join(module_registry)
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
