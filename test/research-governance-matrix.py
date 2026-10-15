"""Real-browser generative research gate: rendered scenes are evidence, not art success.

Run: python test/research-governance-matrix.py
PR baseline protection: GOVERNANCE_BASE_SHA=<40-char base git SHA> python ...
Only HTML and CSS may draw the portrait; screenshot PNGs are QA OUTPUTS only.
"""
import asyncio
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PIL import Image, ImageChops, ImageDraw, ImageStat
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results" / "research-governance"
IDS = ("lin-che", "zhou-qishan", "third-portrait")
LIGHTS = ("front", "side", "top")
EXPRESSIONS = ("neutral", "happy", "sad", "angry", "fear")
MIN_DELTA = 0.01  # Detects "nothing painted changed", never a realism threshold.
# Same-code Chromium captures may differ by ~0.036 due to subpixel raster noise.
# 0.08 is a conservative anti-aliasing tolerance, NOT permission to change art.
DEFAULT_IMAGE_NOISE_TOLERANCE = 0.08

def diff_mean(a, b):
    with Image.open(a) as aa, Image.open(b) as bb:
        x, y = aa.convert("RGB"), bb.convert("RGB")
        if x.size != y.size:
            raise AssertionError(f"Different CSS portrait sizes: {a} {x.size} vs {b} {y.size}")
        return max(ImageStat.Stat(ImageChops.difference(x, y)).mean)

def image_detail(file):
    with Image.open(file) as img:
        rgb = img.convert("RGB")
        return {
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "pixelWidth": rgb.width,
            "pixelHeight": rgb.height,
            "lumaStd": round(ImageStat.Stat(rgb.convert("L")).stddev[0], 3),
        }

async def capture_matrix(browser, port, mode, document="standalone.html", query="", expressions=EXPRESSIONS):
    dest = OUT / mode
    dest.mkdir(parents=True, exist_ok=True)
    context = await browser.new_context(viewport={"width": 1440, "height": 1040},
                                        device_scale_factor=1, reduced_motion="reduce")
    errors = []
    illegal_requests = []
    def on_request(req):
        if req.resource_type in ("image", "media", "font") or not req.url.startswith(f"http://127.0.0.1:{port}/"):
            illegal_requests.append({"url": req.url, "resourceType": req.resource_type})
    context.on("request", on_request)
    page = await context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(f"http://127.0.0.1:{port}/{document}{query}", wait_until="load")
    await page.evaluate("() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))")
    check = await page.locator("#portrait").evaluate("""el => ({
       mediaTags: el.querySelectorAll('img,svg,canvas,picture,video,iframe,object,embed').length,
       faceEngine: el.dataset.faceEngine,
       studyFlags: Object.fromEntries([...el.attributes]
         .filter(a => /^data-r\d{3}$/.test(a.name)).map(a => [a.name,a.value]))
    })""")
    assert check["mediaTags"] == 0, (mode, check)
    assert check["faceEngine"] == "v1", (mode, check)
    declared = json.loads((ROOT / "research/experiments.json").read_text(encoding="utf8"))
    for experiment in declared["experiments"]:
        key = "data-" + experiment["id"].lower()
        if mode == experiment["id"].lower():
            assert check["studyFlags"].get(key) == experiment["candidateQuery"].split("=", 1)[-1], (
                mode, "study was not activated", check)
        else:
            assert not check["studyFlags"].get(key), (mode, "another experiment leaked into this control arm", check)

    scenes = {}
    try:
        for identity in IDS:
            await page.locator('[data-identity="' + identity + '"]').click()
            for light in LIGHTS:
                await page.locator('[data-light-mode="' + light + '"]').click()
                for expression in expressions:
                    tick = time.perf_counter()
                    await page.locator('[data-expression="' + expression + '"]').click()
                    await page.evaluate("() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))")
                    state = await page.locator("#portrait").evaluate("""el => {
                      const face = el.querySelector('.face');
                      const style = el.style;
                      const value = prop => style.getPropertyValue(prop);
                      return {
                        head: value('--fg-leftJaw-x'),
                        orbit: value('--fg-leftOrbit-y'),
                        nose: value('--fg-noseBase-y'),
                        skull: value('--dna-skull-height'),
                        lightX: value('--light-x'),
                        lightElevation: value('--light-elevation'),
                        mouthOpen: value('--expr-mouth-open'),
                        browShift: value('--expr-brow-shift'),
                        r013Contour: value('--r013-head-contour'),
                        computedContour: getComputedStyle(face).clipPath,
                        domCount: el.querySelectorAll('*').length
                      };
                    }""")
                    for key in ("head", "orbit", "nose", "skull", "lightX", "mouthOpen", "browShift"):
                        assert state[key], (mode, identity, light, expression, key, state)
                    assert state["domCount"] < 750, (mode, "DOM blowup", state["domCount"])
                    if mode == "r013":
                        assert state["r013Contour"].startswith("polygon("), (mode, "missing contour", state)
                        assert state["computedContour"].startswith("polygon("), (mode, "inert CSS contour", state)
                    name = f"{identity}-{light}-{expression}"
                    file = dest / (name + ".png")
                    await page.locator("#portrait").screenshot(path=str(file))
                    detail = image_detail(file)
                    assert detail["lumaStd"] > 5, (mode, "blank portrait", name, detail)
                    detail.update({"id": identity, "light": light, "expression": expression,
                                   "file": str(file.relative_to(ROOT)), "style": state,
                                   "captureMs": round((time.perf_counter()-tick)*1000, 1)})
                    scenes[name] = detail
        assert not illegal_requests, (mode, "Renderer requested forbidden external/pixel asset", illegal_requests)
        assert not errors, (mode, "JavaScript runtime error", errors)
    finally:
        await context.close()
    return scenes

def verify_invariants(label, scenes, expressions):
    for identity in IDS:
        for light in LIGHTS:
            neutral = scenes[f"{identity}-{light}-neutral"]
            for expression in expressions:
                sample = scenes[f"{identity}-{light}-{expression}"]
                for key in ("head","orbit","nose","skull"):
                    assert sample["style"][key] == neutral["style"][key], (
                        label, "expression illegally changed identity geometry",identity, light,expression,key)
                if expression != "neutral":
                    assert diff_mean(ROOT / sample["file"], ROOT / neutral["file"]) > MIN_DELTA, (
                        label, "expression has no visible CSS response",identity, light, expression)
        for light in LIGHTS:
            a = scenes[f"{identity}-front-neutral"]
            b = scenes[f"{identity}-{light}-neutral"]
            for key in ("head","orbit","nose","skull"):
                assert a["style"][key] == b["style"][key], (
                    label, "light illegally mutated identity anatomy",identity,light,key)
            if light != "front":
                assert a["style"]["lightX"] != b["style"]["lightX"] or (
                    a["style"]["lightElevation"] != b["style"]["lightElevation"]), (
                        label, "lighting rig is not changing",identity,light)
                assert diff_mean(ROOT / a["file"], ROOT / b["file"]) > MIN_DELTA, (
                    label, "lighting did not visibly change portrait",identity,light)
    for light in LIGHTS:
        checks = [scenes[f"{identity}-{light}-neutral"] for identity in IDS]
        assert len({x["style"]["head"] + ":" + x["style"]["orbit"] + ":" + x["style"]["nose"] + ":" + x["style"]["skull"] for x in checks}) == len(IDS), (
            label, "multiple character presets share exact same geometry",light)
        assert all(diff_mean(ROOT/checks[i]["file"],ROOT/checks[j]["file"]) > MIN_DELTA
                   for i in range(len(checks)) for j in range(i+1,len(checks))), (
            label, "different DNA identities rendered pixel-identical",light)

def contact_sheet(mode, scenes):
    # Nine fixed identity×light neutral cases; never cherry-pick a "best" face.
    out = OUT / (mode + "-nine-scene-contact.jpg")
    tile_w, tile_h = 360, 510
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 3), "#e4e0da")
    pen = ImageDraw.Draw(sheet)
    for i, identity in enumerate(IDS):
        for j, light in enumerate(LIGHTS):
            entry = scenes[f"{identity}-{light}-neutral"]
            with Image.open(ROOT / entry["file"]) as img:
                photo = img.convert("RGB")
                photo.thumbnail((335, 465), Image.Resampling.LANCZOS)
                x, y = j * tile_w + (tile_w-photo.width)//2, i * tile_h + 32
                sheet.paste(photo, (x,y))
                pen.text((j*tile_w+10,i*tile_h+11),f"{mode.upper()}: {identity} / {light}",fill="#262626")
    sheet.save(out, quality=78, optimize=True)

def eligible_human_promotion():
    ledger = json.loads((ROOT / "research" / "experiments.json").read_text(encoding="utf8"))
    return [x["id"] for x in ledger["experiments"]
            if x["status"] == "ART_VERIFIED_WITH_INDEPENDENT_EVIDENCE"
            and (ROOT / "research" / "promotions" / (x["id"] + ".json")).exists()]

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sha = os.environ.get("GOVERNANCE_BASE_SHA", "").strip()
    previous = None
    if sha:
        assert re.fullmatch(r"[0-9a-f]{40}",sha), "GOVERNANCE_BASE_SHA must be PR base commit SHA"
        baseline_file = OUT / "previous-main.html"
        with baseline_file.open("wb") as writer:
            subprocess.run(["git","show",sha+":standalone.html"],cwd=ROOT,stdout=writer,check=True)
        previous = str(baseline_file.relative_to(ROOT)).replace("\\","/")
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,directory=str(ROOT),**kwargs)
        def log_message(self,*args): pass
    server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                default = await capture_matrix(browser,server.server_port,"default")
                verify_invariants("default",default,EXPRESSIONS)
                contact_sheet("default",default)
                ledger = json.loads((ROOT / "research" / "experiments.json").read_text(encoding="utf8"))
                experiments = {}
                for experiment in ledger["experiments"]:
                    mode = experiment["id"].lower()
                    subset = ("neutral",) if experiment["status"] == "REJECTED_FIRST_VIEW" else EXPRESSIONS
                    scenes = await capture_matrix(browser,server.server_port,mode,
                                                  query=experiment["candidateQuery"],expressions=subset)
                    if len(subset) == len(EXPRESSIONS):
                        verify_invariants(mode,scenes,EXPRESSIONS)
                    contact_sheet(mode,scenes)
                    comparisons = [
                        diff_mean(ROOT / default[name]["file"], ROOT / entry["file"])
                        for name, entry in scenes.items()
                    ]
                    # Every registered experiment must produce a visible response,
                    # but nonzero difference is NEVER proof of artistic improvement.
                    assert sum(delta > MIN_DELTA for delta in comparisons) >= 3, (
                        experiment["id"], "registered candidate has almost no painted effect")
                    experiments[experiment["id"]] = {
                        "status": experiment["status"],
                        "query": experiment["candidateQuery"],
                        "coverage": len(scenes),
                        "scenes": scenes,
                        "differentFromDefault": sum(delta > MIN_DELTA for delta in comparisons),
                        "maxChannelMeanDifference": round(max(comparisons),4)
                    }
                cross = []
                if previous:
                    before=await capture_matrix(browser,server.server_port,"previous-default",
                                                document=previous,expressions=("neutral",))
                    contact_sheet("previous-default",before)
                    for identity in IDS:
                        for light in LIGHTS:
                            key=f"{identity}-{light}-neutral"
                            delta=diff_mean(ROOT/before[key]["file"],ROOT/default[key]["file"])
                            cross.append({"scene":key,"maxChannelMeanDifference":round(delta,6)})
                times=[x["captureMs"] for x in default.values()]
                for experiment in experiments.values():
                    times.extend(x["captureMs"] for x in experiment["scenes"].values())
                default_drift = any(item["maxChannelMeanDifference"] > DEFAULT_IMAGE_NOISE_TOLERANCE
                                    for item in cross)
                # Identity/lighting/expression CSS state is also part of the
                # default contract; small screenshot raster variance is tolerated.
                if previous:
                    for identity in IDS:
                        for light in LIGHTS:
                            key=f"{identity}-{light}-neutral"
                            for variable in ("head","orbit","nose","skull","lightX","lightElevation","mouthOpen","browShift"):
                                assert default[key]["style"][variable] == before[key]["style"][variable], (
                                    "DEFAULT_STRUCTURE_REGRESSION_BLOCKED",key,variable,
                                    before[key]["style"][variable],default[key]["style"][variable])
                report={
                    "mission":"General generation; artwork is evidence; realism is primary criterion",
                    "engineStatus":"ENGINE_PASS",
                    "renderStatus":"RENDER_PASS",
                    "artStatus":"ART_UNVERIFIED",
                    "humanReviewers":0,
                    "neverClaim":"Pixel differences do not certify human realism or artistic merit",
                    "coverage":{"identities":len(IDS),"lights":len(LIGHTS),"expressions":len(EXPRESSIONS),
                                "default":len(default),
                                "candidateModes":{name:data["coverage"] for name,data in experiments.items()}},
                    "performanceDiagnosticsMs":{"median":round(statistics.median(times),1),
                                                 "p95":round(sorted(times)[int(.95*(len(times)-1))],1)},
                    "baselineSHA":sha or None,
                    "defaultVisualDiff":cross,
                    "defaultNoiseTolerance":DEFAULT_IMAGE_NOISE_TOLERANCE,
                    "defaultDriftBeyondTolerance":default_drift,
                    "experimentSummary":{name:{k:v for k,v in data.items() if k!="scenes"}
                                         for name,data in experiments.items()},
                    "scenes":{"default":default,
                              "experiments":{name:data["scenes"] for name,data in experiments.items()}}
                }
                (OUT/"evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
                if default_drift:
                    if not eligible_human_promotion():
                        raise AssertionError("DEFAULT_VISUAL_REGRESSION_BLOCKED: main default portrait visibly "
                                             "differs from PR base beyond measured Chromium subpixel tolerance "
                                             "without replicated, structurally validated human review. "
                                             "See docs/RESEARCH-CONSTITUTION.md. Deviations: "+json.dumps(cross))
                    # Even a complete dataset has unverified human-source authenticity.
                    print("DEFAULT_CHANGED_WITH_REVIEW_RECORDS: human provenance still requires human verification.")
                print("RESEARCH_RENDER_PASS: 3 identities × 3 lights × 5 expressions across current default and "
                      +str([name for name,data in experiments.items() if data["coverage"]==45]))
                print("REJECTED experiments stay diagnostic; adding a registered RNNN automatically expands CI coverage.")
                print("ART_UNVERIFIED: pixels, scores schema and CI cannot authenticate visual realism")
                print("Evidence manifest:",str(OUT/"evidence.json"))
            finally:
                await browser.close()
    finally:
        server.shutdown()

if __name__=="__main__":
    asyncio.run(main())
