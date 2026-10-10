export type ThemeId = 'ethiopian-warmth'|'bold-contrast'|'clean-modern';
export type Details = {product_name:string;description:string;current_price:string;old_price:string|null;address:string;contacts:{kind:string;value:string}[];language:'en'|'am';theme:ThemeId};
export type User = {id:string;username:string};
export type Profile = {business_name:string;address:string;contacts:{kind:string;value:string}[];language:'en'|'am';theme:ThemeId;logo_url:string|null};
export type Result = {logo?:{mime_type:string;base64:string};business_name?:string;artwork:{mime_type:string;base64:string};image_text:{headline:string;tagline:string};social_caption:string;details:Details;discount_percent:number|null};
