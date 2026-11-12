import io
import json
import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from sqlalchemy.orm import Session
from app.main import app
from app.accounts import User, current_user, now, aware
from app.gallery import GalleryAsset, cleanup
from app.ads import Ad, persist_generation, receipt
import test_ads

class GalleryTests(unittest.TestCase):
    setUp=test_ads.AdTests.setUp
    tearDown=test_ads.AdTests.tearDown

    def create(self,key=None,photo=None,**facts):
        return self.client.post('/gallery',data={'request_key':key or str(uuid.uuid4()),'facts':json.dumps({'details':self.result['details'],**facts})},files={'photo':('product.png',self.png if photo is None else photo,'image/png')})

    def edit(self,row,**changes):
        return self.client.put('/gallery/'+row['id'],json={'revision':row['revision'],'details':row['details'],'campaign_notes':row['campaign_notes'],'active':row['active'],**changes})

    def test_approval_edits_conflicts_and_deactivation(self):
        row=self.create().json();self.assertFalse(row['eligible']);self.assertIsNone(row['approved_at'])
        url='/gallery/'+row['id']
        approved=self.client.post(url+'/approve',json={'revision':1}).json();self.assertTrue(approved['eligible'])
        self.assertEqual(self.client.post(url+'/deactivate',json={'revision':1}).status_code,409)
        edited=self.edit(approved,details={**approved['details'],'product_name':'አዲስ ጫማ'}).json()
        self.assertFalse(edited['eligible']);self.assertIsNone(edited['approved_at'])
        self.assertEqual(self.edit(approved).status_code,409)
        approved=self.client.post(url+'/approve',json={'revision':edited['revision']}).json()
        inactive=self.client.post(url+'/deactivate',json={'revision':approved['revision']}).json();self.assertFalse(inactive['active']);self.assertFalse(inactive['eligible'])
        self.assertEqual(self.client.post(url+'/approve',json={'revision':inactive['revision']}).status_code,409)
        active=self.edit(inactive,active=True).json();self.assertFalse(active['eligible'])

    def test_every_route_is_owner_scoped_before_storage(self):
        row=self.create().json();url='/gallery/'+row['id']
        app.dependency_overrides[current_user]=lambda:User(id='other',username='other',email='other@example.com',password_hash='unused',access_status='approved',is_admin=True,image_limit=0,image_requests_used=0)
        self.assertEqual(self.client.get('/gallery').json(),[])
        with patch('app.storage.get') as get:
            for suffix in ['', '/image','/image?thumbnail=true']:
                self.assertEqual(self.client.get(url+suffix).status_code,404)
            get.assert_not_called()
        self.assertEqual(self.edit(row).status_code,404)
        for action in ['approve','deactivate']:
            self.assertEqual(self.client.post(url+'/'+action,json={'revision':1}).status_code,404)
        self.assertEqual(self.client.request('DELETE',url,json={'revision':1}).status_code,404)

    def test_private_normalized_upload_thumbnail_validation_and_idempotency(self):
        key=str(uuid.uuid4());response=self.create(key);self.assertEqual(response.status_code,200);row=response.json()
        self.assertEqual(self.create(key).json()['id'],row['id']);self.assertEqual(len(self.objects),1)
        self.assertNotIn('storage_key',row)
        image=self.client.get('/gallery/'+row['id']+'/image');self.assertEqual(image.status_code,200);self.assertEqual(image.headers['cache-control'],'private, no-store')
        with Image.open(io.BytesIO(image.content)) as decoded:self.assertEqual(decoded.format,'JPEG')
        thumb=self.client.get('/gallery/'+row['id']+'/image?thumbnail=true')
        with Image.open(io.BytesIO(thumb.content)) as decoded:self.assertLessEqual(max(decoded.size),360)
        self.assertEqual(self.create(photo=b'not-image').status_code,415)
        self.assertEqual(self.create(details={**row['details'],'old_price':'1'}).status_code,422)
        with patch('app.gallery.MAX_ITEMS',1):self.assertEqual(self.create().status_code,409)

    def test_failed_upload_and_delete_cleanup_are_retryable(self):
        with patch('app.storage.put',side_effect=RuntimeError('secret')):
            response=self.create();self.assertEqual(response.status_code,503);self.assertNotIn('secret',response.text)
        self.assertEqual(self.client.get('/gallery').json(),[])
        with Session(self.engine) as db:self.assertEqual(cleanup(db),1)
        row=self.create().json();url='/gallery/'+row['id']
        self.assertEqual(self.client.request('DELETE',url,json={'revision':1}).status_code,200)
        self.assertEqual(self.client.get(url).status_code,404);self.assertEqual(self.client.get(url+'/image').status_code,404)
        with Session(self.engine) as db:
            with patch('app.storage.remove_prefix',side_effect=RuntimeError('offline')):self.assertEqual(cleanup(db),0)
            self.assertIsNotNone(db.get(GalleryAsset,row['id']));self.assertEqual(cleanup(db),1)
        self.assertEqual(self.objects,{})

    def test_gallery_survives_ad_expiry_and_stale_upload_cleanup(self):
        row=self.create().json();ad=self.generate()
        with Session(self.engine) as db:
            db.get(Ad,ad['id']).expires_at=now()-timedelta(seconds=1);db.commit()
            test_ads.cleanup(db)
            gallery=db.get(GalleryAsset,row['id']);gallery.created_at=now()-timedelta(days=100);gallery.updated_at=gallery.created_at;db.commit()
            self.assertEqual(cleanup(db),0)
        self.assertEqual(self.client.get('/gallery/'+row['id']+'/image').status_code,200)
        with Session(self.engine) as db:
            gallery=db.get(GalleryAsset,row['id']);gallery.ready=False;gallery.updated_at=now()-timedelta(minutes=11);db.commit();self.assertEqual(cleanup(db),1)

    def test_new_retention_and_legacy_receipt_recovery_preserve_exact_deadlines(self):
        with Session(self.engine) as db:
            result=persist_generation(db,'owner',self.result,self.png)
            row=db.get(Ad,result['id']);self.assertEqual(aware(row.expires_at)-aware(row.created_at),timedelta(days=30))
        for days,modern in [(7,False),(30,True)]:
            created=now();expiry=created+timedelta(days=days);id=str(uuid.uuid4())
            signed=receipt('owner',id,expiry.isoformat(),created.isoformat()) if modern else receipt('owner',id,expiry.isoformat())
            result={**self.result,'source_photo':self.asset,'receipt':signed}
            response=self.client.post('/ads',data={'edits':test_ads.AdTests.edit(self)},files={'png':('ad.png',self.png,'image/png'),'generated':('generated.json',json.dumps(result),'application/json')})
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['expires_at'],expiry.isoformat())
            with Session(self.engine) as db:
                row=db.get(Ad,id);self.assertEqual(aware(row.created_at),created)

    generate=test_ads.AdTests.generate
