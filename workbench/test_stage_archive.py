"""Stage proof archive: test real catalog, allowed PNG, mutation safety and review integrity."""
import unittest,hashlib
from stage_archive import stage_result,image_data,validate_stage_review

class StageArchiveTest(unittest.TestCase):
 def test_seven_stage_records(self):
  for i in range(7):
   record=stage_result('S'+str(i))
   self.assertEqual(record['id'],'S'+str(i))
   self.assertTrue(record['scenes'])
   self.assertEqual(record['artStatus'],'ART_UNVERIFIED')
   self.assertEqual(len(record['revision']),64)
 def test_real_archived_images(self):
  for stage in ('S3','S4','S5','S6'):
   stage_result_data=stage_result(stage)
   scenes=[s for s in stage_result_data['scenes'] if s['images']]
   self.assertTrue(scenes,stage)
   item=scenes[0]
   image=item['images'][0]
   self.assertEqual(hashlib.sha256(image_data(stage,item['id'],'0')).hexdigest(),image['sha256'])
 def test_missing_images_not_fabricated(self):
  for stage in ('S0','S1','S2'):
   self.assertFalse(stage_result(stage)['archivedImageCount'])
 def test_no_path_traversal(self):
  for scene in ('../secret','x/y','%2F',''):
   with self.assertRaises((ValueError,FileNotFoundError)):image_data('S5',scene,'0')
  with self.assertRaises((ValueError,FileNotFoundError)):image_data('S5','head-a-neutral-left','99')
  with self.assertRaises(ValueError):stage_result('../data')
 def test_real_review_needs_evidence_revision_and_confirmation(self):
  info=stage_result('S5')
  scene=info['scenes'][0]['id']
  values={k:3 for k in ('structure','volume','eyes','identity','realism')}
  valid={'stage':'S5','sceneId':scene,'revision':info['revision'],'verdict':'revise',
         'scores':values,'note':'眼窝转折需改善','humanConfirmed':True}
  record=validate_stage_review(valid)
  self.assertEqual(record['artStatus'],'ART_UNVERIFIED')
  for edit in ({'revision':'0'*64},{'humanConfirmed':False},{'sceneId':'fake'},
               {'scores':{**values,'realism':0}},{'verdict':'PASS'},
               {'unknown':'injected'}):
   with self.subTest(edit=edit),self.assertRaises(ValueError):
    validate_stage_review({**valid,**edit})
if __name__=='__main__':unittest.main()
