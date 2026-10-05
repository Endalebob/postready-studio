import io
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock
from PIL import Image
from fastapi import HTTPException
from app.schemas import Details
from app.images import normalize_image
from app.gemini import retry, artwork_prompt

class ValidationTests(unittest.TestCase):
    def values(self, **updates):
        return Details.model_validate(dict(product_name='Shoes',current_price='100',contacts=[{'kind':'Phone','value':'demo'}],language='en',**updates))
    def test_discount_and_absence(self):
        self.assertIsNone(self.values().discount)
        self.assertEqual(self.values(old_price='125').discount,20)
    def test_invalid_prices(self):
        for price in ['100','90']:
            with self.assertRaises(ValueError): self.values(old_price=price)
    def test_blank_product(self):
        with self.assertRaises(ValueError): Details(product_name=' ',current_price=Decimal(100),contacts=[{'kind':'Phone','value':'demo'}],language='en')
    def test_multiple_contacts_are_preserved(self):
        d=Details(product_name='Shoes',current_price='100',language='en',contacts=[{'kind':'Phone','value':'0900000000'},{'kind':'Telegram','value':'@demo_shop'}])
        self.assertEqual([c.kind for c in d.contacts],['Phone','Telegram'])
        self.assertEqual(d.model_dump()['contacts'][1]['value'],'@demo_shop')
    def test_theme_contract(self):
        self.assertEqual(self.values().theme,'ethiopian-warmth')
        for theme,word in [('bold-contrast','black'),('clean-modern','white'),('ethiopian-warmth','cream')]:
            d=self.values(theme=theme)
            self.assertEqual(d.model_dump()['theme'],theme)
            self.assertIn(word,artwork_prompt(d.theme))
        with self.assertRaises(ValueError): self.values(theme='arbitrary prompt')
    def test_invalid_photo(self):
        with self.assertRaises(HTTPException): normalize_image(b'not an image')
    def test_valid_photo(self):
        out=io.BytesIO(); Image.new('RGB',(40,40)).save(out,format='PNG')
        self.assertTrue(normalize_image(out.getvalue()).startswith(b'\xff\xd8'))

class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_is_retried(self):
        call=AsyncMock(side_effect=[ConnectionError(), 'ok'])
        self.assertEqual(await retry(call),'ok'); self.assertEqual(call.await_count,2)
    async def test_permanent_is_not_retried(self):
        call=AsyncMock(side_effect=ValueError())
        with self.assertRaises(ValueError): await retry(call)
        self.assertEqual(call.await_count,1)

if __name__=='__main__': unittest.main()
