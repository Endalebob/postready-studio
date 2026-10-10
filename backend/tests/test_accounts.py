import io
import unittest
from unittest.mock import patch, AsyncMock
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from PIL import Image
from app.main import app
from app.accounts import User, LoginSession, now
from support import install_database

class AccountTests(unittest.TestCase):
    def setUp(self):
        self.persist=patch('app.main.persist_generation',side_effect=lambda db,owner,result,photo:result)
        self.persist.start()
        self.engine=install_database()
        self.a=TestClient(app,headers={'x-postready':'1'})
        self.b=TestClient(app,headers={'x-postready':'1'})
    def tearDown(self):
        self.persist.stop()
        app.dependency_overrides.clear();self.engine.dispose()
    def register(self,client,name):
        return client.post('/auth/register',json={'username':name,'email':name+'@example.com','password':'A-long-test-password!','password_confirmation':'A-long-test-password!'})
    def profile(self,client,name='Shop'):
        return client.put('/profile',json={'business_name':name,'address':'Addis Ababa','contacts':[{'kind':'Phone','value':'demo'},{'kind':'Telegram','value':'@demo'}],'language':'am','theme':'ethiopian-warmth'})
    def test_session_password_and_logout(self):
        r=self.register(self.a,'owner');self.assertEqual(r.status_code,200)
        self.assertIn('HttpOnly',r.headers['set-cookie'])
        with Session(self.engine) as db:
            user=db.scalar(select(User));self.assertTrue(user.password_hash.startswith('$argon2'));self.assertNotIn('password!',user.password_hash)
        token=self.a.cookies.get('postready_session')
        self.assertEqual(self.a.get('/auth/me').status_code,200)
        self.a.post('/auth/logout')
        self.assertEqual(self.a.get('/auth/me').status_code,401)
        self.b.cookies.set('postready_session',token)
        self.assertEqual(self.b.get('/auth/me').status_code,401)
        self.assertEqual(self.a.post('/auth/login',json={'identifier':'OWNER@EXAMPLE.COM','password':'A-long-test-password!'}).status_code,200)
    def test_isolation_and_unauthorized_generation(self):
        self.register(self.a,'owner_a');self.register(self.b,'owner_b');self.profile(self.a,'Private Shop')
        self.assertIsNone(self.b.get('/profile').json())
        self.profile(self.b,'Other Shop')
        self.assertEqual(self.a.get('/profile').json()['business_name'],'Private Shop')
        self.assertEqual(TestClient(app,headers={'x-postready':'1'}).post('/generate',files={'photo':('p.png',b'bad')},data={'details':'{}'}).status_code,401)
    def test_csrf_and_expiration(self):
        self.assertEqual(TestClient(app).post('/auth/logout').status_code,403)
        self.assertEqual(self.a.post('/auth/logout',headers={'origin':'https://evil.example'}).status_code,403)
        self.register(self.a,'owner')
        with Session(self.engine) as db:
            session=db.scalar(select(LoginSession));session.expires_at=now()-timedelta(seconds=1);db.commit()
        self.assertEqual(self.a.get('/auth/me').status_code,401)
    def test_logo_isolation_validation_and_replacement(self):
        self.register(self.a,'owner_a');self.register(self.b,'owner_b');self.profile(self.a);self.profile(self.b)
        out=io.BytesIO();Image.new('RGBA',(20,20),(255,0,0,128)).save(out,format='PNG')
        objects={}
        with patch('app.storage.put',side_effect=lambda key,data:objects.__setitem__(key,data)),patch('app.storage.get',side_effect=lambda key:objects[key]),patch('app.storage.remove',side_effect=lambda key:objects.pop(key,None)):
            r=self.a.put('/profile/logo',files={'logo':('logo.png',out.getvalue(),'image/png')});self.assertEqual(r.status_code,200)
            self.assertEqual(self.a.get('/profile/logo').status_code,200)
            self.assertEqual(self.b.get('/profile/logo').status_code,404)
            self.assertEqual(self.a.put('/profile/logo',files={'logo':('bad.png',b'bad','image/png')}).status_code,415)
            self.assertEqual(len(objects),1)
            self.a.put('/profile/logo',files={'logo':('logo.png',out.getvalue(),'image/png')});self.assertEqual(len(objects),1)
            self.a.delete('/profile/logo');self.assertEqual(len(objects),0)
    def test_generic_login_rate_limit_and_duplicate(self):
        self.register(self.a,'owner')
        self.assertEqual(self.register(self.b,'OWNER').status_code,409)
        for _ in range(10):
            r=self.b.post('/auth/login',json={'identifier':'unknown','password':'incorrect'})
            self.assertEqual(r.status_code,401)
        self.assertEqual(self.b.post('/auth/login',json={'identifier':'unknown','password':'incorrect'}).status_code,429)
    def test_logo_storage_failure_keeps_profile(self):
        self.register(self.a,'owner');self.profile(self.a)
        out=io.BytesIO();Image.new('RGB',(20,20)).save(out,format='PNG')
        with patch('app.storage.put',side_effect=RuntimeError('secret')):
            r=self.a.put('/profile/logo',files={'logo':('l.png',out.getvalue(),'image/png')});self.assertEqual(r.status_code,503);self.assertNotIn('secret',r.text)
        self.assertIsNone(self.a.get('/profile').json()['logo_url'])

    def test_generation_uses_owned_logo_without_sending_it_to_model(self):
        import json
        self.register(self.a,'owner');self.profile(self.a)
        out=io.BytesIO();Image.new('RGB',(20,20),'red').save(out,format='PNG');photo=out.getvalue()
        with patch('app.storage.put'),patch('app.storage.get',return_value=photo):
            self.a.put('/profile/logo',files={'logo':('l.png',photo,'image/png')})
            facts={'product_name':'Shoes','current_price':'100','contacts':[{'kind':'Phone','value':'override'}],'language':'en'}
            with patch('app.main.generate',new_callable=AsyncMock,return_value={'social_caption':'caption'}) as call:
                r=self.a.post('/generate',data={'details':json.dumps(facts)},files={'photo':('p.png',photo,'image/png')})
                self.assertEqual(r.status_code,200);self.assertIn('logo',r.json());self.assertEqual(call.call_args.args[1].contacts[0].value,'override')
            with patch('app.main.generate',new_callable=AsyncMock,return_value={'social_caption':'caption'}):
                r=self.a.post('/generate',data={'details':json.dumps(facts),'include_logo':'false'},files={'photo':('p.png',photo,'image/png')})
                self.assertNotIn('logo',r.json())
        self.assertEqual(self.a.get('/profile').json()['contacts'][0]['value'],'demo')
