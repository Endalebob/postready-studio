import hashlib
import json
import os
import unittest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.main import app
from app.accounts import User, current_user, now
from app.ads import Ad
from app.telegram import Connection, PublishAttempt, BotState, poll_updates, process_publish
from app import telegram_api as provider
import test_ads

class TelegramTests(unittest.TestCase):
    generate=test_ads.AdTests.generate
    edit=test_ads.AdTests.edit
    save=test_ads.AdTests.save
    def setUp(self):
        test_ads.AdTests.setUp(self)
        self.token=patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'unit-test-bot'});self.token.start()
        self.bot=patch('app.telegram_api.bot',return_value={'id':999,'username':'demo_bot'});self.bot.start()
    def tearDown(self):
        self.bot.stop();self.token.stop();test_ads.AdTests.tearDown(self)
    def connected(self):
        with Session(self.engine) as db:
            row=Connection(owner_id='owner',connection_id='connection-one',active=True,telegram_user_id='123',chat_id='-100987',title='Demo Channel',username='demo_channel',checked_at=now())
            db.add(row);db.commit()
        return 'connection-one'
    def queued(self):
        ad=self.generate();self.save(ad['id']);self.connected()
        values={'revision':2,'connection_id':'connection-one','confirmed':True}
        r=self.client.post('/ads/'+ad['id']+'/publish',json=values);self.assertEqual(r.status_code,200)
        return ad,r.json(),values
    def test_identity_and_channel_challenge_before_connection(self):
        with patch('app.telegram_api.call',return_value={'url':''}):
            start=self.client.post('/telegram/challenge');self.assertEqual(start.status_code,200)
        code=start.json()['command'].split()[1]
        self.assertEqual(self.client.post('/telegram/connect',json={'confirmed':True}).status_code,409)
        updates=[{'update_id':1,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123,'is_bot':False},'text':'/start '+code}},
                 {'update_id':2,'channel_post':{'chat':{'id':-100987,'type':'channel','title':'Demo Channel','username':'demo_channel'},'text':'/postready_connect '+code}}]
        with Session(self.engine) as db,patch('app.telegram_api.call',return_value=updates):
            self.assertEqual(poll_updates(db),2)
        status=self.client.get('/telegram/connection').json();self.assertTrue(status['identity_verified']);self.assertFalse(status['active']);self.assertEqual(status['observed_channel']['title'],'Demo Channel')
        self.assertEqual(self.client.post('/telegram/connect',json={'confirmed':False}).status_code,409)
        with patch('app.telegram_api.verify_channel',return_value={'id':-100987,'title':'Demo Channel','username':'demo_channel','type':'channel'}) as verify:
            response=self.client.post('/telegram/connect',json={'confirmed':True});self.assertTrue(response.json()['active']);verify.assert_called_once_with('-100987','123')
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Connection,'owner').challenge_hash)
            self.assertEqual(db.get(BotState,hashlib.sha256(b'unit-test-bot').hexdigest()).offset,3)
    def test_expired_forwarded_and_bot_identity_proofs_rejected(self):
        with patch('app.telegram_api.call',return_value={'url':''}):start=self.client.post('/telegram/challenge').json()
        code=start['command'].split()[1]
        updates=[{'update_id':1,'message':{'chat':{'id':1,'type':'private'},'from':{'id':1,'is_bot':True},'text':'/start '+code}},
                 {'update_id':2,'channel_post':{'chat':{'id':-1001,'type':'channel'},'forward_origin':{'type':'channel'},'text':'/postready_connect '+code}}]
        with Session(self.engine) as db,patch('app.telegram_api.call',return_value=updates):poll_updates(db)
        status=self.client.get('/telegram/connection').json();self.assertFalse(status['identity_verified']);self.assertIsNone(status['observed_channel'])
        with Session(self.engine) as db:
            row=db.get(Connection,'owner');row.challenge_expires=now()-timedelta(seconds=1);row.telegram_user_id='123';row.observed_chat={'id':'-100987'};db.commit()
        self.assertEqual(self.client.post('/telegram/connect',json={'confirmed':True}).status_code,409)
    def test_live_permission_checks_require_both_administrators(self):
        good={'status':'administrator','can_post_messages':True}
        with patch('app.telegram_api.call',side_effect=[{'type':'channel'},good,{'status':'member'}]):
            with self.assertRaises(provider.TelegramRejected):provider.verify_channel('-100987','123')
        with patch('app.telegram_api.call',side_effect=[{'type':'channel'},{'status':'administrator','can_post_messages':False}]):
            with self.assertRaises(provider.TelegramRejected):provider.verify_channel('-100987','123')
        with patch('app.telegram_api.call',side_effect=[{'type':'channel'},good,{'status':'creator'}]):
            self.assertEqual(provider.verify_channel('-100987','123')['type'],'channel')
    def test_duplicate_submission_and_immutable_saved_revision(self):
        ad,attempt,values=self.queued()
        duplicate=self.client.post('/ads/'+ad['id']+'/publish',json=values).json();self.assertEqual(duplicate['id'],attempt['id'])
        preview=self.client.get('/ads/'+ad['id']+'/publish-preview?revision=2').json();self.assertEqual(preview['caption'],'Edited caption')
        edits=json.loads(self.edit(2));edits['social_caption']='Newer caption'
        self.assertEqual(self.client.put('/ads/'+ad['id'],data={'edits':json.dumps(edits)},files={'png':('ad.png',self.png)}).status_code,200)
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel'),patch('app.telegram_api.send_photo',return_value={'message_id':42}) as send:
            process_publish(db);send.assert_called_once_with('-100987',self.png,'Edited caption')
        status=self.client.get('/publishes/'+attempt['id']).json();self.assertEqual(status['status'],'published');self.assertEqual(status['link'],'https://t.me/demo_channel/42')
        self.assertEqual(self.client.post('/ads/'+ad['id']+'/publish',json=values).status_code,409)
    def test_uncertain_send_never_retried_automatically(self):
        ad,attempt,values=self.queued()
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel'),patch('app.telegram_api.send_photo',side_effect=provider.TelegramUncertain('timeout')) as send:
            process_publish(db);process_publish(db);self.assertEqual(send.call_count,1)
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).json()['status'],'unknown')
        self.assertEqual(self.client.post('/ads/'+ad['id']+'/publish',json=values).json()['id'],attempt['id'])
        self.assertEqual(self.client.post('/publishes/'+attempt['id']+'/retry',json={'confirmed':True}).status_code,409)
    def test_revoked_permissions_definite_failure_and_explicit_retry(self):
        ad,attempt,values=self.queued()
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel',side_effect=provider.TelegramRejected('Posting permission missing.')),patch('app.telegram_api.send_photo') as send:
            process_publish(db);send.assert_not_called()
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).json()['status'],'failed')
        self.assertEqual(self.client.post('/publishes/'+attempt['id']+'/retry',json={'confirmed':False}).status_code,409)
        self.assertEqual(self.client.post('/publishes/'+attempt['id']+'/retry',json={'confirmed':True}).status_code,409)
        self.assertFalse(self.client.get('/telegram/connection').json()['active'])
        # A newly verified connection has a fresh identity, so the old queue cannot use it.
        with Session(self.engine) as db:
            row=db.get(Connection,'owner');row.active=True;row.error=None;row.connection_id='new-connection';db.commit()
        values['connection_id']='new-connection'
        new_attempt=self.client.post('/ads/'+ad['id']+'/publish',json=values).json()
        self.assertNotEqual(new_attempt['id'],attempt['id'])
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel'),patch('app.telegram_api.send_photo',return_value={'message_id':1}) as send:
            process_publish(db);send.assert_called_once()
    def test_definite_send_rejection_requires_explicit_retry(self):
        ad,attempt,values=self.queued()
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel'),patch('app.telegram_api.send_photo',side_effect=provider.TelegramRejected('Telegram refused this post.')):
            process_publish(db)
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).json()['status'],'failed')
        self.assertEqual(self.client.post('/publishes/'+attempt['id']+'/retry',json={'confirmed':False}).status_code,409)
        self.assertEqual(self.client.post('/publishes/'+attempt['id']+'/retry',json={'confirmed':True}).json()['status'],'queued')
        with Session(self.engine) as db,patch('app.telegram_api.verify_channel'),patch('app.telegram_api.send_photo',return_value={'message_id':1}) as send:
            process_publish(db);send.assert_called_once()
    def test_disconnect_stops_queued_posts_and_status_is_owner_scoped(self):
        ad,attempt,values=self.queued()
        app.dependency_overrides[current_user]=lambda:User(id='other',username='other',email='other@example.com',password_hash='unused')
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).status_code,404)
        self.assertEqual(self.client.get('/ads/'+ad['id']+'/publishes').status_code,404)
        self.assertEqual(self.client.get('/ads/'+ad['id']+'/revisions/2/png').status_code,404)
        app.dependency_overrides[current_user]=lambda:User(id='owner',username='owner',email='owner@example.com',password_hash='unused')
        self.assertEqual(self.client.delete('/telegram/connection').status_code,200)
        with Session(self.engine) as db,patch('app.telegram_api.send_photo') as send:
            process_publish(db);send.assert_not_called()
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).json()['status'],'failed')
    def test_expiry_blocks_preview_and_provider_submission(self):
        ad,attempt,values=self.queued()
        with Session(self.engine) as db:
            row=db.get(Ad,ad['id']);row.expires_at=now()-timedelta(seconds=1);db.commit()
        self.assertEqual(self.client.get('/ads/'+ad['id']+'/publish-preview?revision=2').status_code,410)
        self.assertEqual(self.client.get('/ads/'+ad['id']+'/revisions/2/png').status_code,410)
        self.assertEqual(self.client.post('/ads/'+ad['id']+'/publish',json=values).status_code,410)
        with Session(self.engine) as db,patch('app.telegram_api.send_photo') as send:
            process_publish(db);send.assert_not_called()
    def test_crashed_inflight_attempt_becomes_unknown(self):
        ad,attempt,values=self.queued()
        with Session(self.engine) as db:
            row=db.get(PublishAttempt,attempt['id']);row.status='publishing';row.updated_at=now()-timedelta(minutes=6);db.commit()
            with patch('app.telegram_api.send_photo') as send:process_publish(db);send.assert_not_called()
        self.assertEqual(self.client.get('/publishes/'+attempt['id']).json()['status'],'unknown')
    def test_caption_limits_and_confirmation(self):
        ad=self.generate();self.save(ad['id']);self.connected()
        with Session(self.engine) as db:
            from app.ads import AdRevision
            row=db.get(AdRevision,(ad['id'],2));row.payload={**row.payload,'social_caption':'a'*1025};db.commit()
        self.assertEqual(self.client.get('/ads/'+ad['id']+'/publish-preview?revision=2').status_code,422)
        self.assertEqual(self.client.post('/ads/'+ad['id']+'/publish',json={'revision':2,'connection_id':'connection-one','confirmed':False}).status_code,422)
    def test_provider_errors_never_reveal_token_or_request_url(self):
        client=MagicMock();client.post.side_effect=RuntimeError('https://api.telegram.org/botSECRET/sendPhoto')
        client.__enter__.return_value=client
        with patch('app.telegram_api.httpx.Client',return_value=client):
            with self.assertRaises(provider.TelegramUncertain) as context:provider.call('sendPhoto')
        self.assertNotIn('SECRET',str(context.exception))
