import base64
import io
import json
import os
import unittest
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import select, event
from app.main import app
from app.accounts import User, current_user, Profile, now, aware
from app.ads import Ad, AdRevision, persist_generation, cleanup
from support import install_database

class AdTests(unittest.TestCase):
    def setUp(self):
        self.engine=install_database()
        self.client=TestClient(app,headers={'x-postready':'1'})
        self.user=User(id='owner',username='owner',email='owner@example.com',password_hash='unused')
        with Session(self.engine) as db:
            db.add(self.user);db.commit()
        app.dependency_overrides[current_user]=lambda:User(id='owner',username='owner',email='owner@example.com',password_hash='unused')
        self.env=patch.dict(os.environ,{'MINIO_SECRET_KEY':'only-for-unit-tests'});self.env.start()
        self.objects={}
        self.put=patch('app.storage.put',side_effect=lambda key,data,*args:self.objects.__setitem__(key,data));self.put.start()
        self.get=patch('app.storage.get',side_effect=lambda key:self.objects[key]);self.get.start()
        self.remove=patch('app.storage.remove_prefix',side_effect=lambda prefix:[self.objects.pop(k) for k in list(self.objects) if k.startswith(prefix)]);self.remove.start()
        output=io.BytesIO();Image.new('RGB',(1080,1080),'green').save(output,format='PNG');self.png=output.getvalue()
        self.asset={'mime_type':'image/png','base64':base64.b64encode(self.png).decode()}
        self.result={'artwork':self.asset,'logo':self.asset,'business_name':'Shop','details':{'product_name':'Shoes','description':'','current_price':'100','old_price':None,'address':'Addis','contacts':[{'kind':'Phone','value':'demo'}],'language':'en','theme':'ethiopian-warmth'},'image_text':{'headline':'Shoes','tagline':'Available now'},'social_caption':'Caption','discount_percent':None}
    def tearDown(self):
        self.remove.stop();self.get.stop();self.put.stop();self.env.stop();app.dependency_overrides.clear();self.engine.dispose()
    def generate(self):
        with Session(self.engine) as db:
            return persist_generation(db,'owner',self.result,self.png)
    def edit(self, revision=1):
        return json.dumps({'revision':revision,'details':self.result['details'],'image_text':{'headline':'Edited','tagline':'Available'},'social_caption':'Edited caption'})
    def save(self, ad_id, revision=1):
        return self.client.put('/ads/'+ad_id,data={'edits':self.edit(revision)},files={'png':('ad.png',self.png,'image/png')})
    def test_save_reopen_conflict_and_immutable_deadline(self):
        ad=self.generate();ad_id=ad['id'];expiry=ad['expires_at']
        self.assertTrue(ad['storage_ready'])
        self.assertEqual(self.client.get('/ads').json()[0]['id'],ad_id)
        self.assertEqual(self.client.get('/ads/'+ad_id+'/png').status_code,409)
        r=self.save(ad_id);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['revision'],2);self.assertEqual(r.json()['expires_at'],expiry)
        self.assertEqual(self.save(ad_id).status_code,409)
        reopened=self.client.get('/ads/'+ad_id).json();self.assertEqual(reopened['image_text']['headline'],'Edited');self.assertEqual(reopened['logo'],self.asset)
        self.assertEqual(self.client.get('/ads/'+ad_id+'/png').content,self.png)
        self.assertEqual(self.save(ad_id,2).json()['revision'],3)
        with Session(self.engine) as db:
            self.assertIsNotNone(db.get(AdRevision,(ad_id,2)));self.assertEqual(aware(db.get(Ad,ad_id).expires_at).isoformat(),expiry)
    def test_owner_scope_and_exact_boundary_all_routes(self):
        ad=self.generate();ad_id=ad['id'];self.save(ad_id)
        app.dependency_overrides[current_user]=lambda:User(id='other',username='other',email='other@example.com',password_hash='unused')
        self.assertEqual(self.client.get('/ads').json(),[])
        for method,path in [('GET','/ads/'+ad_id),('GET','/ads/'+ad_id+'/png'),('DELETE','/ads/'+ad_id)]:
            self.assertEqual(self.client.request(method,path).status_code,404)
        self.assertEqual(self.save(ad_id).status_code,404)
        app.dependency_overrides[current_user]=lambda:User(id='owner',username='owner',email='owner@example.com',password_hash='unused')
        with Session(self.engine) as db:
            expiry=aware(db.get(Ad,ad_id).expires_at)
        with patch('app.ads.now',return_value=expiry-timedelta(microseconds=1)):
            self.assertEqual(self.client.get('/ads/'+ad_id).status_code,200)
        with patch('app.ads.now',return_value=expiry):
            self.assertEqual(self.client.get('/ads').json(),[])
            self.assertEqual(self.client.get('/ads/'+ad_id).status_code,410)
            self.assertEqual(self.client.get('/ads/'+ad_id+'/png').status_code,410)
            self.assertEqual(self.save(ad_id,2).status_code,410)
            self.assertEqual(self.client.delete('/ads/'+ad_id).status_code,410)
    def test_storage_failure_recoverable_without_regeneration(self):
        with patch('app.storage.put',side_effect=RuntimeError('secret')):
            ad=self.generate()
        self.assertFalse(ad['storage_ready'])
        self.assertEqual(self.client.get('/ads/'+ad['id']).json()['artwork'],self.asset)
        with patch('app.storage.put',side_effect=RuntimeError('secret')):
            r=self.save(ad['id']);self.assertEqual(r.status_code,503);self.assertNotIn('secret',r.text)
        self.assertEqual(self.save(ad['id']).status_code,200)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Ad,ad['id']).pending_sources)
    def test_cleanup_retry_preserves_profile_logo(self):
        ad=self.generate();self.save(ad['id'])
        self.objects['logos/owner/profile.png']=b'profile'
        with Session(self.engine) as db:
            db.get(Ad,ad['id']).expires_at=now()-timedelta(seconds=1);db.commit()
            with patch('app.storage.remove_prefix',side_effect=RuntimeError('offline')):
                self.assertEqual(cleanup(db),0)
            self.assertIsNotNone(db.get(Ad,ad['id']))
            self.assertEqual(cleanup(db),1)
            self.assertIsNone(db.get(Ad,ad['id']))
        self.assertEqual(self.objects,{'logos/owner/profile.png':b'profile'})
    def test_delete_hides_immediately_and_cleanup_removes(self):
        ad=self.generate()
        self.assertEqual(self.client.delete('/ads/'+ad['id']).status_code,200)
        self.assertEqual(self.client.get('/ads').json(),[])
        self.assertEqual(self.client.get('/ads/'+ad['id']).status_code,404)
        with Session(self.engine) as db:self.assertEqual(cleanup(db),1)
        self.assertEqual(self.objects,{})
    def test_failed_database_generation_receipt_preserves_original_expiry(self):
        with Session(self.engine) as db,patch.object(db,'commit',side_effect=RuntimeError('offline')):
            result=persist_generation(db,'owner',self.result,self.png)
        self.assertNotIn('id',result);self.assertIn('receipt',result)
        response=self.client.post('/ads',data={'edits':self.edit()},files={'png':('ad.png',self.png,'image/png'),'generated':('generated.json',json.dumps(result),'application/json')})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['expires_at'],result['expires_at'])
        result['receipt']['expires_at']=(now()+timedelta(days=30)).isoformat()
        self.assertEqual(self.client.post('/ads',data={'edits':self.edit()},files={'png':('ad.png',self.png,'image/png'),'generated':('generated.json',json.dumps(result),'application/json')}).status_code,422)
    def test_invalid_png_and_invalid_details_rejected(self):
        ad=self.generate()
        self.assertEqual(self.client.put('/ads/'+ad['id'],data={'edits':self.edit()},files={'png':('bad.png',b'bad')}).status_code,422)
        values=json.loads(self.edit());values['details']['current_price']='0'
        self.assertEqual(self.client.put('/ads/'+ad['id'],data={'edits':json.dumps(values)},files={'png':('ad.png',self.png)}).status_code,422)
