"""Synthetic surface regression tests, not human artwork observations."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box
from playwright.sync_api import sync_playwright
from model import ROOT,canonical
from geometry import Projection
from study_light import compile_light,describe as light_description,content_hash
from study_edges import describe_edges
from surface_registry import S5,S6,cases,case_specs,validate_payload,source_digest,geometry_spec
from surface import prepare_geometry,describe,sections,rings_area,from_percent
from surface_document import document
from validate_studies import document as base_document
from archive_surface import image_check
import server


class Plane:
    camera={'center':[0,0],'span':6}
    def mesh(self,weights):
        v=np.array([[-2.,-2.,0],[2.,-2.,0],[2.,2.,0],[-2.,2.,0],[-.4,-.4,.2],[.4,-.4,.2],[.4,.4,.2],[-.4,.4,.2]])
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]])
        return v,f,np.tile([0.,0.,1.],(8,1)),np.array([1,1,7,7])
    def signature(self,weights):return {'geometryHash':'1'*64,'weights':weights,'camera':self.camera,'surfaceOnly':True}


class SurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=Projection(Plane(),[0]*6);scene=compile_light(Plane(),[0]*6,[0,0,1],cls.p)
        cls.parent=describe_edges(scene,light_description(scene));cls.g=prepare_geometry(cls.p)
        cls.d=describe(cls.parent,cls.g)
    def test_registered_complete_case_counts(self):
        self.assertEqual(len(cases('S5'))*3,18);self.assertEqual(len(cases('S6'))*3,45)
        self.assertEqual(len({c['id'] for c in cases('S5')+cases('S6')}),21)
        for c in cases('S5')+cases('S6'):self.assertEqual(len(case_specs(c['id'])),3)
        self.assertNotEqual(source_digest('S5'),source_digest('S6'))
    def test_stage_inputs_reject_ambiguity_and_injection(self):
        for change in [{'stage':'S9'},{'hair':'../../x'},{'material':'url(x)'},{'expression':'smile'},{'url':'https://x'},{'weights':[True]*6},{'weights':[float('nan')]*6}]:
            with self.assertRaises(ValueError):validate_payload({'stage':'S5','identity':'head-a',**change})
        with self.assertRaises(ValueError):validate_payload({'stage':'S6','weights':[0]*6})
        self.assertEqual(server.validate_render_payload({'stage':'S6','identity':'novel-a','expression':'smile'})['expression'],'smile')
        self.assertEqual(server.validate_render_payload({'identity':'head-a'})['stage'],'S2')
    def test_geometry_key_does_not_depend_on_drawing_material(self):
        spec=case_specs('novel-a-smile')[0]
        self.assertEqual(geometry_spec(spec),geometry_spec({**spec,'hair':'none','material':'charcoal'}))
    def test_parent_geometry_and_form_are_immutable(self):
        before=copy.deepcopy(self.parent);describe(self.parent,self.g)
        self.assertEqual(before,self.parent)
        for name in ('geometry','toneRegions','edgeRegions','structureRegions'):self.assertEqual(self.parent[name],self.d[name])
        self.assertEqual(self.d['contentHash'],content_hash(self.d));self.assertEqual(self.d['artStatus'],'ART_UNVERIFIED')
    def test_scap_and_material_regions_respect_protected_area(self):
        protected=self.g['protected']
        for layer in self.d['surfaceRegions']:
            area=from_percent(rings_area(layer['rings']),self.p.camera)
            self.assertLess(area.intersection(protected.buffer(-.02)).area,1e-6)
        self.assertGreater(self.g['scalp'].area,0)
    def test_none_hair_is_not_a_hidden_cap(self):
        result=describe(self.parent,self.g,hair='none')
        self.assertEqual([r['rings'] for r in result['surfaceRegions'][-2:]],[[],[]])
        self.assertNotEqual(result['contentHash'],self.d['contentHash'])
    def test_section_field_validation_and_nonempty_geometry(self):
        self.assertGreater(self.g['primary'].length,0)
        with self.assertRaises(ValueError):sections(self.p,np.zeros((2,2)),10,box(-1,-1,1,1))
        with self.assertRaises(ValueError):describe(self.parent,self.g,material='unsupported')
        with self.assertRaises(ValueError):image_check('bad.png',b'not a PNG')
    def test_openapi_keeps_old_and_new_stage_contracts(self):
        schema=server.openapi_schema();arms=schema['components']['schemas']['RenderPayload']['oneOf']
        self.assertEqual(arms[0]['properties']['stage']['enum'],['S2','S3','S4'])
        self.assertEqual(arms[1]['properties']['stage']['enum'],['S5','S6'])
        self.assertIn('material-control',schema['components']['schemas']['Review']['properties']['viewMode']['enum'])
    def test_compiler_has_no_image_or_screen_grid_input(self):
        for path in ['surface.py','surface_model.py']:
            source=(ROOT/'workbench'/path).read_text()
            for forbidden in ['Image.open','np.mgrid','getImageData','read_pixels']:
                self.assertNotIn(forbidden,source)
    def test_native_css_disable_is_pixel_exact_parent_and_budget_rejects(self):
        with tempfile.TemporaryDirectory() as td,sync_playwright() as p:
            root=Path(td);browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page()
            def capture_html(text,name):
                path=root/(name+'.html');path.write_text(text);page.goto(path.as_uri());page.wait_for_selector('body[data-ready="1"]')
                self.assertEqual(page.locator('#portrait img,#portrait svg,#portrait canvas').count(),0)
                return page.locator('#portrait').screenshot()
            parent=capture_html(base_document(self.parent),'parent')
            disabled=capture_html(document(self.d,'material-control'),'off');self.assertEqual(parent,disabled)
            capture_html(document(self.d),'full');self.assertEqual(page.locator('.surface-region').count(),5)
            bad=copy.deepcopy(self.d);bad['surfaceContourPoints']+=1
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            path=root/'bad.html';path.write_text(document(bad));page.goto(path.as_uri());page.wait_for_timeout(50)
            self.assertTrue(any('budget' in error for error in errors));browser.close()
if __name__=='__main__':unittest.main()
