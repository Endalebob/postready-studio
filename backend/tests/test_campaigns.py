import json
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.main import app
from app.accounts import User, current_user, now
from app.campaigns import Campaign, Schedule, occurrences
from app.gallery import GalleryAsset
from app.telegram import Connection, PublishAttempt
from app.ads import Ad
import test_ads

class ScheduleTests(unittest.TestCase):
    def times(self, after, **values):
        return occurrences(Schedule(**values), datetime.fromisoformat(after))

    def test_weekly_default_timezone_and_strict_future(self):
        rows=self.times('2026-11-16T07:00:00+00:00',weekday=0,local_time='10:00')
        self.assertEqual(rows[0]['utc'],'2026-11-23T07:00:00+00:00')
        self.assertEqual(rows[0]['local'],'2026-11-23T10:00:00+03:00')
        self.assertEqual(len(rows),3)

    def test_monthly_short_month_leap_year_and_no_drift(self):
        rows=self.times('2028-01-31T11:00:00+00:00',frequency='monthly',day_of_month=31,local_time='10:00',timezone='UTC')
        self.assertEqual([r['utc'][:10] for r in rows],['2028-02-29','2028-03-31','2028-04-30'])
        rows=self.times('2027-12-31T11:00:00+00:00',frequency='monthly',day_of_month=31,local_time='10:00',timezone='UTC')
        self.assertEqual(rows[0]['utc'][:10],'2028-01-31')

    def test_daily_dst_gap_and_repeat_once(self):
        rows=self.times('2026-03-07T08:00:00+00:00',frequency='daily',local_time='02:30',timezone='America/New_York')
        self.assertEqual(rows[0]['utc'],'2026-03-09T06:30:00+00:00')
        rows=self.times('2026-11-01T04:00:00+00:00',frequency='daily',local_time='01:30',timezone='America/New_York')
        self.assertEqual(rows[0]['utc'],'2026-11-01T05:30:00+00:00')
        self.assertEqual(rows[1]['utc'],'2026-11-02T06:30:00+00:00')
        rows=self.times('2026-11-01T06:00:00+00:00',frequency='daily',local_time='01:30',timezone='America/New_York')
        self.assertEqual(rows[0]['utc'],'2026-11-02T06:30:00+00:00')

    def test_invalid_schedules_and_irrelevant_fields(self):
        for data in [dict(local_time='24:00',weekday=0),dict(local_time='10:00'),dict(local_time='10:00',weekday=7),dict(local_time='10:00',weekday=True),dict(local_time='10:00',weekday=0,timezone='invalid/zone'),dict(local_time='10:00',frequency='monthly',day_of_month=0)]:
            with self.assertRaises(ValueError):Schedule(**data)
        daily=Schedule(local_time='10:00',frequency='daily',weekday=3,day_of_month=31)
        self.assertIsNone(daily.weekday);self.assertIsNone(daily.day_of_month)

class CampaignTests(unittest.TestCase):
    tearDown=test_ads.AdTests.tearDown
    def setUp(self):
        test_ads.AdTests.setUp(self)
        self.product_id=str(uuid.uuid4());self.connection_id=str(uuid.uuid4())
        with Session(self.engine) as db:
            db.add(GalleryAsset(id=self.product_id,owner_id='owner',request_key=str(uuid.uuid4()),storage_key='private/test.jpg',details=self.result['details'],campaign_notes='',revision=1,active=True,ready=True,deleted=False,approved_at=now(),created_at=now(),updated_at=now()))
            db.add(Connection(owner_id='owner',connection_id=self.connection_id,active=True,chat_id='-100123',telegram_user_id='123',title='Test channel'))
            db.commit()
        self.settings={'name':'Weekly shoes','gallery_ids':[self.product_id],'connection_id':self.connection_id,'schedule':{'frequency':'weekly','weekday':0,'local_time':'10:00','timezone':'Africa/Addis_Ababa'},'language':'en','theme':'ethiopian-warmth','instructions':''}

    def create(self, key=None, settings=None):
        return self.client.post('/campaigns',json={'request_key':key or str(uuid.uuid4()),'settings':settings or self.settings})

    def test_create_reopen_edit_duplicate_and_no_side_effects(self):
        key=str(uuid.uuid4())
        with patch('app.telegram_api.call') as telegram,patch('app.gemini.generate') as generate:
            response=self.create(key);self.assertEqual(response.status_code,200,response.text);row=response.json()
            duplicate=self.create(key);self.assertEqual(duplicate.json()['id'],row['id'])
            telegram.assert_not_called();generate.assert_not_called()
        self.assertEqual(row['status'],'paused');self.assertEqual(len(row['preview']),3)
        url='/campaigns/'+row['id']
        self.assertEqual(self.client.get(url).json()['settings']['name'],'Weekly shoes')
        changed={**self.settings,'schedule':{'frequency':'monthly','day_of_month':31,'local_time':'09:00','timezone':'UTC'}}
        result=self.client.put(url,json={'revision':1,'settings':changed});self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['status'],'paused');self.assertEqual(result.json()['revision'],2)
        self.assertEqual(self.client.put(url,json={'revision':1,'settings':changed}).status_code,409)
        self.assertEqual(self.client.request('DELETE',url,json={'revision':1}).status_code,409)
        self.assertEqual(len(self.client.get('/campaigns').json()),1)
        with Session(self.engine) as db:
            self.assertEqual(db.query(Ad).count(),0);self.assertEqual(db.query(PublishAttempt).count(),0)

    def test_owner_scope_and_reference_validation(self):
        row=self.create().json();url='/campaigns/'+row['id']
        with Session(self.engine) as db:
            db.add(User(id='other',username='other',email='other@example.com',password_hash='unused',access_status='approved',is_admin=True,image_limit=0,image_requests_used=0));db.commit()
        app.dependency_overrides[current_user]=lambda:User(id='other',username='other',email='other@example.com',password_hash='unused',access_status='approved',is_admin=True,image_limit=0,image_requests_used=0)
        self.assertEqual(self.client.get('/campaigns').json(),[])
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.put(url,json={'revision':1,'settings':self.settings}).status_code,404)
        self.assertEqual(self.client.request('DELETE',url,json={'revision':1}).status_code,404)
        self.assertEqual(self.create().status_code,409)

    def test_changed_references_warn_and_cannot_save(self):
        row=self.create().json();url='/campaigns/'+row['id']
        with Session(self.engine) as db:
            db.get(GalleryAsset,self.product_id).approved_at=None;db.get(Connection,'owner').active=False;db.commit()
        reopened=self.client.get(url).json();self.assertEqual(len(reopened['warnings']),2)
        self.assertEqual(reopened['unavailable_gallery_ids'],[self.product_id])
        self.assertEqual(self.client.put(url,json={'revision':1,'settings':self.settings}).status_code,409)
        self.assertEqual(self.create().status_code,409)
        with Session(self.engine) as db:
            db.get(Connection,'owner').active=True;db.commit()
        self.assertEqual(self.create().status_code,409)

    def test_limits_delete_replay_and_validation(self):
        key=str(uuid.uuid4());row=self.create(key).json();url='/campaigns/'+row['id']
        with patch('app.campaigns.MAX_DRAFTS',1):self.assertEqual(self.create().status_code,409)
        self.assertEqual(self.create(settings={**self.settings,'name':'  '}).status_code,422)
        self.assertEqual(self.create(settings={**self.settings,'gallery_ids':[self.product_id,self.product_id]}).status_code,422)
        self.assertEqual(self.create(settings={**self.settings,'gallery_ids':[str(uuid.uuid4())]}).status_code,409)
        self.assertEqual(self.client.request('DELETE',url,json={'revision':1}).status_code,200)
        self.assertEqual(self.create(key).status_code,410)
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.get('/campaigns').json(),[])
        with patch('app.campaigns.MAX_DRAFTS',1):self.assertEqual(self.create().status_code,200)

    def test_preview_requires_auth_and_valid_input(self):
        self.assertEqual(len(self.client.post('/campaigns/preview',json=self.settings['schedule']).json()['preview']),3)
        self.assertEqual(self.client.post('/campaigns/preview',json={'local_time':'25:00','weekday':0}).status_code,422)
        self.assertIn('Africa/Addis_Ababa',self.client.get('/campaigns/options').json()['timezones'])
        app.dependency_overrides.pop(current_user)
        self.assertEqual(self.client.post('/campaigns/preview',json=self.settings['schedule']).status_code,401)
