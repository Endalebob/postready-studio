export type ThemeId = 'ethiopian-warmth'|'bold-contrast'|'clean-modern';
export type Details = {product_name:string;description:string;current_price:string;old_price:string|null;address:string;contacts:{kind:string;value:string}[];language:'en'|'am';theme:ThemeId};
export type User = {id:string;username:string;access_status:'pending'|'approved'|'suspended';is_admin:boolean;image_limit:number;image_requests_used:number;image_requests_remaining:number|null};
export type Profile = {business_name:string;address:string;contacts:{kind:string;value:string}[];language:'en'|'am';theme:ThemeId;logo_url:string|null};
export type AdMetadata = {id?:string;revision?:number;expires_at?:string;created_at?:string;storage_ready?:boolean;has_png?:boolean;renderer_version?:number};
export type Result = AdMetadata & {receipt?:{id:string;expires_at:string;signature:string};source_photo?:{mime_type:string;base64:string};persistence_error?:string;logo?:{mime_type:string;base64:string};business_name?:string;artwork:{mime_type:string;base64:string};image_text:{headline:string;tagline:string};social_caption:string;details:Details;discount_percent:number|null};
export type LibraryAd = AdMetadata & {id:string;product_name:string;headline:string};
