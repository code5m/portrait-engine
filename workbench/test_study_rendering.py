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
            page.evaluate('(rings)=>{document.getElementById("portrait").style.clipPath=clipPath(rings)}',rings)
            bad=np.asarray(Image.open(io.BytesIO(page.locator('#portrait').screenshot())).convert('RGB'))
            self.assertFalse(np.array_equal(frames['S3'],bad),'Regression control must detect re-clipping')
            self.assertEqual(errors,[]);browser.close()

    def test_native_css_edge_subpaths_preserve_holes_and_empty_gaps(self):
        full=[[[0,0],[100,0],[100,100],[0,100]]]
        rings=[[[10,10],[30,10],[30,30],[10,30]],[[15,15],[25,15],[25,25],[15,25]],
               [[70,70],[90,70],[90,90],[70,90]]]
        d={'renderer':'HTML_CSS_REGIONS','stage':'S4','geometry':{'geometryHash':'synthetic'},
           'contentHash':'synthetic','contourPoints':4,'toneRegions':[{'gray':200,'rings':full}],
           'silhouetteRings':full,'edgeContourPoints':12,
           'edgeRegions':[{'gray':25,'opacity':.45,'blurPixels':0,'rings':rings},
                          {'gray':25,'opacity':.18,'blurPixels':.35,'rings':[]}],
           'controlEdgeRegions':[]}
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page()
            path=Path(tmp)/'subpaths.html';path.write_text(document(d),encoding='utf8')
            page.goto(path.as_uri());page.wait_for_selector('body[data-ready="1"]')
            target=page.locator('#portrait')
            pixels=np.asarray(Image.open(io.BytesIO(target.screenshot())).convert('RGB'))
            self.assertEqual(int(pixels[64,64,0]),200,'Hole must not receive ink')
            self.assertEqual(int(pixels[160,160,0]),200,'Separate rings must not be connected by ink')
            self.assertLess(int(pixels[40,40,0]),150);self.assertLess(int(pixels[256,256,0]),150)
            self.assertTrue(target.locator('.edge-ribbon i').first.evaluate('(el)=>el.style.clipPath.startsWith("shape(")'))
            self.assertEqual(target.locator('img,svg,canvas').count(),0)
            self.assertEqual(page.evaluate('()=>{try{edgeClipPath([[[0,0],[NaN,1],[1,0]]]);return "bad"}catch(e){return e.name}}'),'RangeError')
            browser.close()
if __name__=='__main__':unittest.main()
