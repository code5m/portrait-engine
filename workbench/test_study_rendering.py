"""Small actual-browser and even-odd geometry regressions, NOT head/ART evidence."""
import io,math,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import Point
from playwright.sync_api import sync_playwright
from validate_studies import document,contour_geometry

class StudyRenderingTests(unittest.TestCase):
    def test_evenodd_keeps_self_crossing_lobes_holes_and_duplicate_cancellation(self):
        outer=[[0,0],[10,0],[10,10],[0,10]]
        hole=[[2,2],[4,2],[4,4],[2,4]]
        crossing=[[12,0],[14,2],[12,2],[14,0]]
        g=contour_geometry([outer,hole,crossing])
        self.assertTrue(g.is_valid);self.assertAlmostEqual(g.area,98)
        self.assertFalse(g.contains(Point(3,3)))
        self.assertTrue(g.contains(Point(13,.25)));self.assertTrue(g.contains(Point(13,1.75)))
        self.assertTrue(contour_geometry([outer,outer]).is_empty)

    def test_empty_edge_layers_preserve_every_base_pixel(self):
        rings=[[[50+37*math.cos(i*math.pi/50),50+43*math.sin(i*math.pi/50)] for i in range(100)],
               [[35,43],[43,43],[43,50],[35,50]]]
        d={'renderer':'HTML_CSS_REGIONS','stage':'S3','geometry':{'geometryHash':'synthetic'},
           'contentHash':'synthetic','contourPoints':104,'toneRegions':[{'gray':75,'rings':rings}],
           'silhouetteRings':rings,'edgeContourPoints':0,
           'edgeRegions':[{'gray':25,'opacity':.45,'blurPixels':0,'rings':[]},
                          {'gray':25,'opacity':.18,'blurPixels':.35,'rings':[]}],
           'controlEdgeRegions':[]}
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':640,'height':480});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            frames={}
            for stage in ['S3','S4']:
                d['stage']=stage;path=Path(tmp)/(stage+'.html');path.write_text(document(d),encoding='utf8')
                page.goto(path.as_uri());page.wait_for_selector('body[data-ready="1"]')
                target=page.locator('#portrait')
                frames[stage]=np.asarray(Image.open(io.BytesIO(target.screenshot())).convert('RGB'))
                self.assertEqual(target.evaluate('(el)=>getComputedStyle(el).clipPath'),'none')
            self.assertTrue(np.array_equal(frames['S3'],frames['S4']),'Empty ink must be an exact no-op')
            # Negative control reproduces the removed double-antialiasing bug.
            page.evaluate('(rings)=>{document.getElementById("portrait").style.clipPath=clipPath(rings)}',rings)
            bad=np.asarray(Image.open(io.BytesIO(page.locator('#portrait').screenshot())).convert('RGB'))
            self.assertFalse(np.array_equal(frames['S3'],bad),'Regression control must detect re-clipping')
            self.assertEqual(errors,[]);browser.close()
if __name__=='__main__':unittest.main()
