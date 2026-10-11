import io
import json
import tempfile
import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import app
from app.accounts import User, Profile, current_user, now
from app.videos import Video, process_video, cleanup_videos
from app import video_render
import test_ads

class VideoTests(unittest.TestCase):
    setUp=test_ads.AdTests.setUp
    tearDown=test_ads.AdTests.tearDown

    def submit(self,count=2,key=None,**edits):
        options={'request_key':key or str(uuid.uuid4()),'duration':5,'theme':'ethiopian-warmth','language':'en',
                 'products':[{'name':f'Product {i+1}','price':'100','description':'A nice product'} for i in range(count)],**edits}
        files=[('photos',(f'{i}.png',self.png,'image/png')) for i in range(count)]
        return self.client.post('/videos',data={'options':json.dumps(options)},files=files)

    def process(self):
        with Session(self.engine) as db,patch('app.video_render.render',return_value=b'fake-video-for-state-test'):
            return process_video(db)

    def test_ready_private_download_range_and_fixed_expiry(self):
        result=self.submit();self.assertEqual(result.status_code,200)
        row=result.json();self.assertEqual(row['status'],'queued')
        self.process()
        value=self.client.get('/videos/'+row['id']).json();self.assertEqual(value['status'],'ready')
        path='/videos/'+row['id']+'/media'
        response=self.client.get(path,headers={'Range':'bytes=0-3'})
        self.assertEqual(response.status_code,206);self.assertEqual(response.content,b'fake');self.assertEqual(response.headers['content-range'],'bytes 0-3/25')
        self.assertEqual(self.client.get(path,headers={'Range':'bytes=-4'}).content,b'test')
        self.assertEqual(self.client.get(path,headers={'Range':'bytes=100-'}).status_code,416)
        self.assertIn('attachment',self.client.get(path+'?download=true').headers['content-disposition'])
        with Session(self.engine) as db:
            before=db.get(Video,row['id']).expires_at
        self.client.get(path)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Video,row['id']).expires_at,before)
            db.get(Video,row['id']).expires_at=now()-timedelta(seconds=1);db.commit()
        self.assertEqual(self.client.get(path).status_code,410)
        self.assertEqual(self.client.get('/videos').json(),[])

    def test_duplicate_submission_count_limits_and_owner_isolation(self):
        key=str(uuid.uuid4());first=self.submit(key=key).json();objects=len(self.objects)
        self.assertEqual(self.submit(key=key).json()['id'],first['id']);self.assertEqual(len(self.objects),objects)
        self.assertEqual(self.submit(count=11).status_code,422)
        self.assertEqual(self.submit(duration=7).status_code,422)
        self.assertEqual(self.submit(products=[{'name':'','price':'-1'}]).status_code,422)
        self.assertEqual(self.submit().status_code,200)
        self.assertEqual(self.submit().status_code,429)
        app.dependency_overrides[current_user]=lambda:User(id='other',username='other',email='other@example.com',password_hash='unused')
        self.assertEqual(self.client.get('/videos').json(),[])
        self.assertEqual(self.client.get('/videos/'+first['id']).status_code,404)
        self.assertEqual(self.client.get('/videos/'+first['id']+'/media').status_code,404)

    def test_storage_and_renderer_failures_do_not_claim_success(self):
        with patch('app.storage.put',side_effect=RuntimeError('secret')):
            row=self.submit().json()
        self.assertEqual(row['status'],'failed');self.assertNotIn('secret',row['error'])
        second=self.submit().json()
        with Session(self.engine) as db,patch('app.video_render.render',side_effect=RuntimeError('secret')):
            process_video(db)
        failed=self.client.get('/videos/'+second['id']).json();self.assertEqual(failed['status'],'failed')
        self.assertIsNone(failed['media_url']);self.assertEqual(self.client.get('/videos/'+second['id']+'/media').status_code,409)

    def test_restart_recovery_and_cleanup_retains_unexpired_video(self):
        first=self.submit().json();second=self.submit().json()
        with Session(self.engine) as db:
            row=db.get(Video,first['id']);row.status='processing';row.updated_at=now()-timedelta(minutes=11);db.commit()
        self.process();self.process()
        with Session(self.engine) as db:
            db.get(Video,first['id']).expires_at=now()-timedelta(seconds=1);db.commit()
            with patch('app.storage.remove_prefix',side_effect=RuntimeError()):
                self.assertEqual(cleanup_videos(db),0)
            self.assertEqual(cleanup_videos(db),1)
            self.assertIsNotNone(db.get(Video,second['id']))
        self.assertFalse(any(first['id'] in key for key in self.objects))

    def test_profile_and_logo_are_snapshots_not_live_references(self):
        self.objects['profiles/owner/logo']=self.png
        with Session(self.engine) as db:
            db.add(Profile(owner_id='owner',logo_key='profiles/owner/logo',data={'business_name':'Original shop','contacts':[{'kind':'Phone','value':'original'}],'address':'Original address'}));db.commit()
        video=self.submit().json()
        self.objects['profiles/owner/logo']=b'new-logo'
        with Session(self.engine) as db:
            profile=db.get(Profile,'owner');profile.data={**profile.data,'business_name':'Changed shop','contacts':[]};db.commit()
            row=db.get(Video,video['id'])
            self.assertEqual(row.details['business_name'],'Original shop')
            self.assertEqual(row.details['contacts'][0]['value'],'original')
            self.assertEqual(self.objects[row.assets['logo']],self.png)

    def test_real_transition_video_preserves_first_and_last_products(self):
        pictures=[]
        for color in ('red','blue'):
            image=io.BytesIO();Image.new('RGB',(500,500),color).save(image,format='PNG');pictures.append(image.getvalue())
        settings={'duration':5,'theme':'ethiopian-warmth','language':'am','business_name':'የሙከራ ሱቅ',
                  'contacts':[{'kind':'Phone','value':'0900000000'}],'address':'Addis Ababa'}
        products=[{'name':'ቀይ ጫማ','price':'100','description':'First'},{'name':'Blue shoes','price':'200','description':'Last'}]
        with tempfile.TemporaryDirectory() as directory:
            output=video_render.render(pictures,products,settings,directory)
            self.assertGreater(len(output),1000)
            for time,dominant in [('0.4',0),('4.5',2)]:
                frame=video_render.command(['ffmpeg','-v','error','-ss',time,'-i',directory+'/advertisement.mp4','-frames:v','1','-f','image2pipe','-vcodec','png','-threads','1','-'])
                with Image.open(io.BytesIO(frame)) as image:
                    rgb=image.getpixel((360,475))
                    self.assertGreater(rgb[dominant],200)
                    self.assertLess(rgb[2 if dominant==0 else 0],40)
