"""Synthetic parser/security regressions; never publishes or certifies heads."""
import contextlib,copy,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import archive_studies as archive

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.rootpatch=patch.object(archive,'ROOT',self.root);self.rootpatch.start()
        self.envpatch=patch.dict(os.environ,{'GITHUB_RUN_ID':'123','SOURCE_HEAD_SHA':'a'*40});self.envpatch.start()
        self.identity={'id':'head-a','split':'baseline'};self.config={'lights':[{'id':x} for x in ('left','front','right')]}
        p=self.root/'research/sketch';p.mkdir(parents=True)
        (self.root/'synthetic.txt').write_text('UNIT TEST ONLY')
        for stage in ('s3','s4'):(p/(stage+'-sources.json')).write_text('["synthetic.txt"]')
        (p/'s3-protocol.json').write_text(json.dumps({'levels':31,'radiometryCalibrationMAE':2,'shadowErrorRatio':.85,'thresholds':{'fullMAE':7,'interiorMAE':10,'featureMAE':15,'maxContourPoints':60000}}))
        (p/'s4-protocol.json').write_text(json.dumps({'maxInkFraction':.12,'outsideEdgePixelTolerance':1,'maxAddedInteriorError':2.5,'maxEdgePoints':32000}))
        self.report={'ciRun':'123','sourceHeadCommit':'a'*40,'stage':'S3','status':'PASS',
          'sourceDigest':archive.source_digest('S3'),'humanObservers':0,'artStatus':'ART_UNVERIFIED',
          'split':'baseline','transport':'file','counts':{'identities':1,'scenes':3,'cssFrames':12},'calibrationMAE':[.3,.4,.5],
          'metrics':[{'id':'head-a-'+x,'status':'PASS','failures':[],
            'metrics':{'fullMAE':1,'interiorMAE':2,'featureMAE':3,'silhouetteIoU':.99},
            'toneRegions':31,'contourPoints':30000,'unshadowedFidelity':{'interiorMAE':2},
            'shadowPixels':200,'shadowError':4,'controlShadowError':40} for x in ('left','front','right')]}
    def tearDown(self):self.envpatch.stop();self.rootpatch.stop();self.tmp.cleanup()
    def test_parser_accepts_complete_synthetic_shape_without_network(self):
        archive.check_report(self.report,'S3',self.identity,self.config)
    def test_rejects_partial_failure_drift_and_weakened_limit(self):
        for modify in [lambda r:r['metrics'].pop(),lambda r:r.update(status='FAIL'),
                       lambda r:r.update(sourceHeadCommit='b'*40),lambda r:r.update(sourceDigest='0'*64),
                       lambda r:r['metrics'][0].update(shadowError=100)]:
            r=copy.deepcopy(self.report);modify(r)
            with self.assertRaises(ValueError):archive.check_report(r,'S3',self.identity,self.config)
    def test_rejects_fake_human_claim_and_missing_ui_steps(self):
        ui={'ciRun':'123','sourceHead':'a'*40,'status':'PASS','humanObservers':0,
            'reviewData':'temporary AUTOMATED_TEST database only','steps':list(archive.STEPS)}
        archive.check_ui(ui)
        ui['humanObservers']=1
        with self.assertRaises(ValueError):archive.check_ui(ui)
        ui['humanObservers']=0;ui['steps'].pop()
        with self.assertRaises(ValueError):archive.check_ui(ui)
    def test_checksum_rejects_replaced_png_and_bad_dimensions(self):
        png=b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+(320).to_bytes(4,'big')*2+b'SYNTHETIC_HEADER_ONLY'
        h=archive.digest(png);reports={'S3':{'metrics':[{'id':'a','captureHash':h,'referenceHash':h}]},'S4':{'metrics':[{'id':'a','captureHash':h,'controlHash':h}]}}
        files={name:png for name in ('images/a-S3.png','reference/a-shadow.png','images/a-S4.png','images/a-all-edges.png')}
        archive.verify_image_hashes(reports,files)
        files['images/a-S4.png']=png+b'CORRUPTED'
        with self.assertRaises(ValueError):archive.verify_image_hashes(reports,files)
        files['images/a-S4.png']=png[:16]+(1).to_bytes(4,'big')+png[20:]
        with self.assertRaises(ValueError):archive.verify_image_hashes(reports,files)
    def test_complete_synthetic_pack_collection_and_corruption_rejection(self):
        identities=[{'id':name,'split':'baseline' if name.startswith('head-') else 'holdout'}
                    for name in ('head-a','head-b','head-c','reserved-d','reserved-e','reserved-f')]
        config={**self.config,'identities':identities}
        archive.write(self.root/'research/sketch/s2-protocol.json',archive.encoded(config))
        source=self.root/'data/workbench/studies';packs=self.root/'data/workbench/receipts'
        png=b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+(320).to_bytes(4,'big')*2+b'UNIT_TEST_HEADER_ONLY'
        h=archive.digest(png)
        with patch.object(archive,'PACKS',packs),contextlib.redirect_stdout(io.StringIO()):
            for identity in identities:
                s3=copy.deepcopy(self.report);s3.update(split=identity['split'],ciCommit='c'*40)
                s4=copy.deepcopy(s3);s4.update(stage='S4',counts={'identities':1,'scenes':3,'cssFrames':6})
                for index,light in enumerate(config['lights']):
                    case=identity['id']+'-'+light['id']
                    s3['metrics'][index].update(id=case,captureHash=h,referenceHash=h,geometryHash='d'*64)
                    s4['metrics'][index].update(id=case,captureHash=h,controlHash=h,geometryHash='d'*64,
                        parentInteriorMAE=2,inkFraction=.05,outsideAllowedChange=0,edgePoints=200,
                        classification={'hard':1,'soft':1,'lost':10})
                    for label in archive.LABELS:archive.write(source/'captures'/f'{case}-{label}.png',png)
                    for arm in ('shadow','unshadowed'):
                        archive.write(source/'reference'/f'{case}-{arm}.png',png)
                        archive.write(source/'reference'/f'{case}-{arm}.json',b'{}')
                for stage,report in [('S3',s3),('S4',s4)]:
                    archive.write(source/f'{stage}-{identity["split"]}-result.json',archive.encoded(report))
                for cosine in (.25,.65,1.0):archive.write(source/'reference'/f'calibration-{cosine}.png',png)
                archive.write(source/f'comparison-{identity["split"]}.png',png)
                if identity['id']=='head-a':
                    ui={'ciRun':'123','sourceHead':'a'*40,'status':'PASS','humanObservers':0,
                        'reviewData':'temporary AUTOMATED_TEST database only','steps':list(archive.STEPS)}
                    archive.write(source/'UI-result.json',archive.encoded(ui))
                    for stage in ('S3','S4'):archive.write(source/f'workbench-{stage}.png',png)
                archive.pack(identity['id'])
            files=archive.collect()
            self.assertEqual(len(files),222);self.assertEqual(sum(n.endswith('.png') for n in files),170)
            record=json.loads(files['research/sketch/evidence/S4.json'])
            self.assertEqual(len(record['metrics']),18);self.assertEqual(record['humanObservers'],0)
            (packs/'reserved-f/images/reserved-f-right-S4.png').write_bytes(png+b'CORRUPTED')
            with self.assertRaises(ValueError):archive.collect()
    def test_no_redirect_can_forward_credentials(self):
        with self.assertRaises(RuntimeError):archive.NoRedirect().redirect_request(None,None,302,'',{},'https://untrusted.invalid')
if __name__=='__main__':unittest.main()
