import asyncio
import io
import json
import unittest
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from types import SimpleNamespace
from fastapi import HTTPException
from app import gemini
from app.schemas import Details
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import app
from app.accounts import User, now, consume_image_request
from app.admin import bootstrap, AccessAudit
from app.preparations import Preparation
from app.ads import Ad, AdRevision
from app.videos import Video, process_video
from app.video_motion import advance
from app.telegram import PublishAttempt, process_publish
from support import install_database
import test_preparations

class WaitlistTests(unittest.TestCase):
    def setUp(self):
        self.engine=install_database()
        self.admin=TestClient(app,headers={'x-postready':'1'})
        self.tester=TestClient(app,headers={'x-postready':'1'})
        self.admin_id=self.register(self.admin,'operator')['id']
        self.user=self.register(self.tester,'waitlisted')
        with Session(self.engine) as db:bootstrap(db,'operator')
        photo=io.BytesIO();Image.new('RGB',(40,40),'red').save(photo,format='PNG');self.photo=photo.getvalue()
        self.facts={'product_name':'Shoes','current_price':'100','contacts':[{'kind':'Phone','value':'demo'}],'language':'en'}
    def tearDown(self):
        app.dependency_overrides.clear();self.engine.dispose()
    def register(self,client,name,**extras):
        response=client.post('/auth/register',json={'username':name,'email':name+'@example.test','password':'Local-test-password!','password_confirmation':'Local-test-password!',**extras})
        self.assertEqual(response.status_code,200,response.text);return response.json()
    def change(self,status='approved',limit=3,revision=None):
        if revision is None:
            with Session(self.engine) as db:revision=db.get(User,self.user['id']).access_revision
        return self.admin.put('/admin/users/'+self.user['id']+'/access',json={'revision':revision,'status':status,'image_limit':limit})
    def generate(self):
        return self.tester.post('/generate',data={'details':json.dumps(self.facts)},files={'photo':('p.png',self.photo,'image/png')})
    def test_waitlist_has_session_but_no_workspace_or_provider_access(self):
        self.assertEqual(self.user['access_status'],'pending');self.assertFalse(self.user['is_admin']);self.assertEqual(self.user['image_requests_remaining'],0)
        self.assertEqual(self.tester.get('/auth/me').status_code,200)
        with patch('app.main.generate',new_callable=AsyncMock) as generate,patch('app.storage.get') as storage:
            for path in ['/profile','/ads','/gallery','/campaigns','/videos','/videos/providers/options','/telegram/connection','/admin/users','/preparations/'+str(uuid.uuid4())]:
                self.assertEqual(self.tester.get(path).status_code,403,path)
            self.assertEqual(self.generate().status_code,403)
            self.assertEqual(self.tester.post('/videos',data={'options':'{}'},files={'photos':('p.png',self.photo)}).status_code,403)
            generate.assert_not_awaited();storage.assert_not_called()
        self.assertEqual(self.tester.post('/auth/logout').status_code,200)
    def test_approval_grants_exactly_three_image_attempts_and_keeps_other_features_closed(self):
        result=self.change();self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.tester.get('/auth/me').json()['image_requests_remaining'],3)
        self.assertEqual(self.tester.get('/profile').status_code,200)
        with patch('app.main.generate',new_callable=AsyncMock,return_value={'social_caption':'Test'}),patch('app.main.persist_generation',side_effect=lambda db,owner,result,photo:result):
            for _ in range(3):self.assertEqual(self.generate().status_code,200)
        with patch('app.main.generate',new_callable=AsyncMock) as generate:
            self.assertEqual(self.generate().status_code,403);generate.assert_not_awaited()
        self.assertEqual(self.tester.get('/auth/me').json()['image_requests_remaining'],0)
        for path in ['/videos','/gallery','/campaigns','/telegram/connection','/admin/users']:
            self.assertEqual(self.tester.get(path).status_code,403,path)
    def test_approved_tester_can_read_own_saved_revision_without_publishing_access(self):
        self.change()
        with Session(self.engine) as db:
            ad=Ad(id='private-ad',owner_id=self.user['id'],created_at=now(),expires_at=now()+timedelta(days=30),revision=1,payload={},sources={},pending_sources=None,deleted=False)
            db.add(ad);db.flush();db.add(AdRevision(ad_id=ad.id,revision=1,payload={},png_key='private.png'));db.commit()
        with patch('app.storage.get',return_value=self.photo):
            self.assertEqual(self.tester.get('/ads/private-ad/revisions/1/png').status_code,200)
            self.assertEqual(self.admin.get('/ads/private-ad/revisions/1/png').status_code,404)
        self.assertEqual(self.tester.get('/ads/private-ad/publish-preview?revision=1').status_code,403)
        self.change(status='suspended')
        self.assertEqual(self.tester.get('/ads/private-ad/revisions/1/png').status_code,403)
    def test_attempt_is_consumed_after_provider_error_but_not_bad_input(self):
        self.change()
        with patch('app.main.generate',new_callable=AsyncMock,side_effect=RuntimeError('secret')) as generate:
            self.assertEqual(self.generate().status_code,503)
            bad=self.tester.post('/generate',data={'details':'{}'},files={'photo':('p.png',b'bad','image/png')})
            self.assertEqual(bad.status_code,422);self.assertEqual(generate.await_count,1)
        self.assertEqual(self.tester.get('/auth/me').json()['image_requests_remaining'],2)
    def test_suspension_blocks_existing_session_and_keeps_account_data(self):
        self.change()
        response=self.tester.put('/profile',json={'business_name':'Private shop','contacts':[{'kind':'Phone','value':'demo'}]});self.assertEqual(response.status_code,200)
        self.assertEqual(self.change(status='suspended').status_code,200)
        self.assertEqual(self.tester.get('/profile').status_code,403)
        self.assertEqual(self.tester.get('/auth/me').json()['access_status'],'suspended')
        self.change();self.assertEqual(self.tester.get('/profile').json()['business_name'],'Private shop')
    def test_admin_updates_are_revision_checked_audited_and_cannot_grant_admin_role(self):
        response=self.change(revision=1);self.assertEqual(response.status_code,200)
        self.assertEqual(self.change(revision=1).status_code,409)
        self.assertEqual(self.tester.put('/admin/users/'+self.admin_id+'/access',json={'revision':1,'status':'approved','image_limit':99}).status_code,403)
        self.assertEqual(self.admin.put('/admin/users/'+self.user['id']+'/access',json={'revision':2,'status':'approved','image_limit':3,'is_admin':True}).status_code,422)
        with Session(self.engine) as db:
            self.assertFalse(db.get(User,self.user['id']).is_admin)
            self.assertEqual(db.query(AccessAudit).count(),2)
        self.assertEqual(self.admin.get('/admin/users?status=approved').json()['total'],1)
    def test_allowance_cannot_erase_usage_and_bootstrap_is_explicit_and_idempotent(self):
        self.change()
        with Session(self.engine) as db:consume_image_request(db,self.user['id']);db.commit()
        self.assertEqual(self.change(limit=0).status_code,422)
        self.assertEqual(self.change(limit=1).json()['image_requests_remaining'],0)
        with Session(self.engine) as db:
            bootstrap(db,'operator');self.assertEqual(db.query(AccessAudit).filter(AccessAudit.action=='bootstrap_admin').count(),1)
            with self.assertRaises(ValueError):bootstrap(db,'missing')
    def test_regular_account_cannot_override_registration_access_fields(self):
        c=TestClient(app,headers={'x-postready':'1'})
        account=self.register(c,'forged',is_admin=True,access_status='approved',image_limit=100)
        self.assertFalse(account['is_admin']);self.assertEqual(account['access_status'],'pending');self.assertEqual(account['image_limit'],0)

class WorkerGateTests(unittest.TestCase):
    def setUp(self):
        self.engine=install_database()
        with Session(self.engine) as db:
            db.add(User(id='blocked',username='blocked',email='blocked@example.test',password_hash='unused',access_status='pending',is_admin=False));db.commit()
    def tearDown(self):app.dependency_overrides.clear();self.engine.dispose()
    def test_queued_video_and_publish_do_not_reach_storage_or_providers(self):
        with Session(self.engine) as db:
            for mode in ['motion','transitions']:
                db.add(Video(id=mode,owner_id='blocked',request_key=mode,status='queued',details={'mode':mode},assets={},created_at=now(),updated_at=now()))
            db.add(PublishAttempt(id='post',owner_id='blocked',ad_id=None,revision=1,connection_id='old',chat_id='-100',title='Old channel',status='queued',created_at=now(),updated_at=now()));db.commit()
            with patch('app.video_providers.submit') as submit,patch('app.video_providers.poll') as poll,patch('app.storage.get') as get,patch('app.telegram_api.verify_channel') as verify,patch('app.telegram_api.send_photo') as send:
                process_video(db);process_publish(db)
                submit.assert_not_called();poll.assert_not_called();get.assert_not_called();verify.assert_not_called();send.assert_not_called()
            self.assertEqual(db.get(Video,'motion').status,'failed');self.assertEqual(db.get(Video,'transitions').status,'failed');self.assertEqual(db.get(PublishAttempt,'post').status,'failed')

class PreparationRevocationTests(unittest.TestCase):
    setUp=test_preparations.PreparationTests.setUp
    tearDown=test_preparations.PreparationTests.tearDown
    start=test_preparations.PreparationTests.start
    tick=test_preparations.PreparationTests.tick
    def test_revocation_stops_queued_preparation_before_provider(self):
        job=self.start().json()
        with Session(self.engine) as db:
            owner=db.get(User,'owner');owner.is_admin=False;owner.access_status='pending';db.commit()
        self.tick()
        self.copy_mock.assert_not_awaited();self.art_mock.assert_not_awaited()
        with Session(self.engine) as db:self.assertEqual(db.get(Preparation,job['id']).status,'failed')

class ImmediateRevocationTests(unittest.TestCase):
    def test_revocation_between_copy_and_image_prevents_second_paid_phase(self):
        details=Details(product_name='Shoes',current_price='100',contacts=[{'kind':'Phone','value':'demo'}],language='en')
        call=AsyncMock(return_value=SimpleNamespace(text='{"headline":"Shoes","tagline":"","social_caption":"Shoes available"}'))
        client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=call)))
        check=Mock(side_effect=HTTPException(403,'Access paused'))
        with patch.dict(__import__('os').environ,{'GEMINI_API_KEY':'unit-test'}),patch('app.gemini.get_client',return_value=client):
            with self.assertRaises(HTTPException):asyncio.run(gemini.generate(b'test',details,before_artwork=check))
        self.assertEqual(call.await_count,1);check.assert_called_once()
