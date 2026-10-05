from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Contact(BaseModel):
    kind: str = Field(min_length=1, max_length=30)
    value: str = Field(min_length=1, max_length=120)


class Details(BaseModel):
    product_name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=600)
    current_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    old_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    address: str = Field(default='', max_length=160)
    contacts: list[Contact] = Field(min_length=1, max_length=4)
    language: Literal['am', 'en']
    theme: Literal['ethiopian-warmth', 'bold-contrast', 'clean-modern'] = 'ethiopian-warmth'

    @model_validator(mode='after')
    def check_values(self):
        if not self.product_name.strip() or any(not c.value.strip() for c in self.contacts):
            raise ValueError('Product name and contact information are required.')
        if self.old_price is not None and self.old_price <= self.current_price:
            raise ValueError('Old price must be greater than current price.')
        return self

    @property
    def discount(self):
        if self.old_price is None:
            return None
        return int(((self.old_price-self.current_price)/self.old_price*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class Copy(BaseModel):
    headline: str = Field(min_length=1, max_length=100)
    tagline: str = Field(max_length=180)
    social_caption: str = Field(min_length=1, max_length=1500)
