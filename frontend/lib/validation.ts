import {Details} from './types';
export function validate(d:Details):Record<string,string>{
 const errors:Record<string,string>={};
 if(!d.product_name.trim()) errors.product_name='Enter the product name.';
 else if(d.product_name.length>100) errors.product_name='Keep the product name under 100 characters.';
 const money=/^\d{1,10}(\.\d{1,2})?$/;
 if(!money.test(d.current_price)||Number(d.current_price)<=0) errors.current_price='Enter a positive price with up to two decimal places.';
 if(d.old_price && (!money.test(d.old_price)||Number(d.old_price)<=Number(d.current_price))) errors.old_price='Old price must be greater than current price (up to two decimal places).';
 if(!d.contacts.length||d.contacts.some(c=>!c.value.trim())) errors.contact='Fill in each contact, or remove the empty row.';
 return errors;
}
