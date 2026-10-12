import io
import json
import os
import tempfile
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import httpx
from PIL import Image
from sqlalchemy.orm import Session
from app.accounts import now
from app.videos import Video, cleanup_videos
from app import video_motion, video_providers as providers, video_render
import test_ads
import test_videos

class MotionTests(unittest.TestCase):
    setUp=test_ads.AdTests.setUp
    tearDown=test_ads.AdTests.tearDown
    submit=test_videos.VideoTests.submit

    def advance(self):
        with Session(self.engine) as db:
            for row in db.query(Video).filter(Video.status=='generating'):
                row.updated_at=now()-timedelta(seconds=10)
            db.commit()
            return video_motion.advance(db)

    def test_durable_google_segments_resume_without_duplicate_paid_submits(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test'}):
            row=self.submit(mode='motion',provider='google',duration=6,cost_acknowledged=True).json()
        self.assertEqual(row['estimated_cost'],3.2)
        with patch('app.video_providers.submit',side_effect=[{'id':'one','poll':'one'},{'id':'two','poll':'two'}]) as submit,patch('app.video_providers.poll',side_effect=[None,'url-one','url-two']) as poll,patch('app.video_providers.download',return_value=b'clip'),patch('app.video_render.motion',return_value=b'composed'):
            self.advance();self.advance();self.advance();self.advance();self.advance();self.advance()
            self.assertEqual(submit.call_count,2);self.assertEqual(poll.call_count,3)
            self.assertEqual([call.args[2] for call in submit.call_args_list],[4,4])
        result=self.client.get('/videos/'+row['id']).json();self.assertEqual(result['status'],'ready');self.assertEqual(result['duration'],6)
        with Session(self.engine) as db:
            tasks=db.get(Video,row['id']).assets['tasks'];self.assertEqual(len(tasks),2);self.assertTrue(all(t['asset'] for t in tasks))
        self.assertNotIn('tasks',result)

    def test_uncertain_submission_and_interrupted_send_never_resubmit(self):
        with patch.dict(os.environ,{'BFL_API_KEY':'test'}):
            first=self.submit(mode='motion',cost_acknowledged=True).json()
        with patch('app.video_providers.submit',side_effect=providers.UncertainSubmission('Check provider dashboard')) as submit:
            self.advance();self.advance();self.assertEqual(submit.call_count,1)
        self.assertEqual(self.client.get('/videos/'+first['id']).json()['status'],'uncertain')
        with patch.dict(os.environ,{'BFL_API_KEY':'test'}):
            second=self.submit(mode='motion',cost_acknowledged=True).json()
        with Session(self.engine) as db:
            row=db.get(Video,second['id']);row.status='submitting';row.updated_at=now()-timedelta(minutes=11);db.commit()
        with patch('app.video_providers.submit') as submit:
            self.advance();submit.assert_not_called()
        self.assertEqual(self.client.get('/videos/'+second['id']).json()['status'],'uncertain')
        with Session(self.engine) as db:
            for id in [first['id'],second['id']]:
                db.get(Video,id).updated_at=now()-timedelta(days=8)
            db.commit();self.assertEqual(cleanup_videos(db),2)

    def test_saved_task_poll_failure_restart_and_rejection(self):
        with patch.dict(os.environ,{'BFL_API_KEY':'test'}):
            row=self.submit(mode='motion',cost_acknowledged=True).json()
        with patch('app.video_providers.submit',return_value={'id':'saved','poll':'poll'}) as submit:
            self.advance()
            with Session(self.engine) as db:
                video=db.get(Video,row['id']);video.status='processing';video.updated_at=now()-timedelta(minutes=11);db.commit()
            with patch('app.video_providers.poll',side_effect=RuntimeError('temporary')):
                self.advance()
            self.assertEqual(submit.call_count,1)
            with patch('app.video_providers.poll',side_effect=providers.ProviderFailure('Provider rejected this photo')):
                self.advance()
            self.assertEqual(submit.call_count,1)
        result=self.client.get('/videos/'+row['id']).json();self.assertEqual(result['status'],'failed');self.assertIsNone(result['media_url'])

    def test_cost_acknowledgment_provider_durations_and_config(self):
        self.assertEqual(self.submit(mode='motion').status_code,422)
        self.assertEqual(self.submit(mode='motion',provider='google',cost_acknowledged=True,duration=5).status_code,422)
        with patch.dict(os.environ,{'BFL_API_KEY':'','GEMINI_API_KEY':''}):
            self.assertEqual(self.submit(mode='motion',cost_acknowledged=True).status_code,503)
            self.assertTrue(all(not p['available'] for p in self.client.get('/videos/providers/options').json()))
        self.assertEqual(providers.estimate('bfl',5,10),.3);self.assertEqual(providers.estimate('google',8,10),16)

    def test_real_motion_composition_labels_and_all_products(self):
        photos=[]
        for color in ['red','blue']:
            output=io.BytesIO();Image.new('RGB',(500,500),color).save(output,format='PNG');photos.append(output.getvalue())
        products=[{'name':'Red product','price':'100'},{'name':'Blue product','price':'200'}]
        settings={'duration':5,'theme':'ethiopian-warmth','language':'am'}
        with tempfile.TemporaryDirectory() as directory:
            source=video_render.render(photos,products,settings,directory)
            result=video_render.motion([source],photos,products,settings,directory)
            Path(directory+'/result.mp4').write_bytes(result)
            for time,dominant in [('0.5',0),('4.5',2)]:
                png=video_render.command(['ffmpeg','-v','error','-ss',time,'-i',directory+'/result.mp4','-frames:v','1','-f','image2pipe','-vcodec','png','-threads','1','-'])
                with Image.open(io.BytesIO(png)) as image:
                    self.assertEqual(image.size,(720,1280));self.assertGreater(image.getpixel((360,390))[dominant],190)
            # Independent Google-style scene clips are assembled into the requested total duration.
            result=video_render.motion([source,source],photos,products,{**settings,'duration':6},directory)
            self.assertGreater(len(result),1000)

class ProviderTests(unittest.TestCase):
    def response(self,status,data):
        return httpx.Response(status,json=data,request=httpx.Request('POST','https://api.bfl.ai/v1/flux-3-video'))

    def test_request_contracts_headers_and_safe_poll_references(self):
        with patch.dict(os.environ,{'BFL_API_KEY':'test-bfl','GEMINI_API_KEY':'test-google'}):
            with patch('app.video_providers.httpx.post',return_value=self.response(200,{'id':'id','polling_url':'https://api.bfl.ai/v1/get_result?id=id'})) as post:
                providers.submit('bfl',[b'photo',b'photo-two'],5,'bold-contrast')
                payload=post.call_args.kwargs['json'];self.assertTrue(payload['draft']);self.assertFalse(payload['generate_audio']);self.assertEqual(len(payload['keyframes']),2)
                self.assertEqual([f[0] for f in payload['keyframes']],[0,2.5])
                self.assertEqual(post.call_args.kwargs['headers'],{'x-key':'test-bfl'})
            operation='models/veo-3.1-generate-preview/operations/test'
            with patch('app.video_providers.httpx.post',return_value=self.response(200,{'name':operation})) as post:
                providers.submit('google',[b'photo'],4,'clean-modern')
                payload=post.call_args.kwargs['json'];self.assertIn('bytesBase64Encoded',payload['instances'][0]['image']);self.assertEqual(payload['parameters']['durationSeconds'],4)
            with self.assertRaises(providers.ProviderFailure):providers.bfl_url('https://example.com/steal')
            with self.assertRaises(providers.ProviderFailure):providers.google_operation('../../secret')
            with patch('app.video_providers.httpx.post',return_value=self.response(500,{})):
                with self.assertRaises(providers.UncertainSubmission):providers.submit('bfl',[b'photo'],5,'clean-modern')
            with patch('app.video_providers.httpx.post',return_value=self.response(403,{})):
                with self.assertRaises(providers.ProviderFailure):providers.submit('google',[b'photo'],4,'clean-modern')
