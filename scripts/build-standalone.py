"""Build the self-contained, offline portrait demo without fetching assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "index.html").read_text(encoding="utf-8")
for name in ("layout", "portrait"):
    css = (ROOT / "styles" / f"{name}.css").read_text(encoding="utf-8")
    link = f'<link rel="stylesheet" href="./styles/{name}.css">'
    assert link in html, f"Missing CSS placeholder: {link}"
    html = html.replace(link, f"<style>\n{css}\n</style>")
source = "\n".join(
    re.sub(r"^export ", "", (ROOT / "src" / f"{name}.mjs").read_text(encoding="utf-8"), flags=re.M)
    for name in ("parameters", "i18n", "app")
)
source = re.sub(r"^import .*?;\n", "", source, flags=re.M)
marker = '<script type="module" src="./src/app.mjs"></script>'
assert marker in html, "Missing module placeholder"
html = html.replace(marker, f'<script type="module">\n{source}\n</script>')
out = ROOT / "standalone.html"
out.write_text(html, encoding="utf-8")
print(f"Generated {out.name} ({out.stat().st_size} bytes), without external assets.")
