import io
import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.details = dict(product_name='Shoes',current_price='100',contacts=[{'kind':'Phone','value':'demo-contact'}],language='en')
        out=io.BytesIO();Image.new('RGB',(40,40)).save(out,format='PNG');self.photo=out.getvalue()
    def post(self,details=None,photo=None):
        return self.client.post('/generate',data={'details':json.dumps(details or self.details)},files={'photo':('test.png',photo or self.photo,'image/png')})
    def test_fields_fail_before_provider(self):
        with patch('app.main.generate',new_callable=AsyncMock) as call:
            response=self.post({**self.details,'current_price':'0'})
            self.assertEqual(response.status_code,422);call.assert_not_called()
    def test_photo_fails_before_provider(self):
        with patch('app.main.generate',new_callable=AsyncMock) as call:
            self.assertEqual(self.post(photo=b'bad-file').status_code,415);call.assert_not_called()
    def test_provider_errors_are_sanitized(self):
        with patch('app.main.generate',new_callable=AsyncMock,side_effect=RuntimeError('private-provider-detail')):
            response=self.post();self.assertEqual(response.status_code,503)
            self.assertNotIn('private-provider-detail',response.text)
            self.assertIn('Please try again',response.text)
    def test_success_passes_validated_details(self):
        with patch('app.main.generate',new_callable=AsyncMock,return_value={'social_caption':'demo'}) as call:
            self.assertEqual(self.post().status_code,200)
            self.assertEqual(call.call_args.args[1].product_name,'Shoes')

if __name__=='__main__':unittest.main()
