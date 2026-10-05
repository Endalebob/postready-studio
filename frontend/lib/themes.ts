import {ThemeId} from './types';
export const themes:Record<ThemeId,{name:string;description:string;background:string;text:string;price:string;contact:string;accent:string}>={
 'ethiopian-warmth':{name:'Ethiopian Warmth',description:'Cream, green and subtle woven accents',background:'#f6f2e7',text:'#252e28',price:'#326348',contact:'#252e28',accent:'#b08b3b'},
 'bold-contrast':{name:'Bold Contrast',description:'Black, green headlines and red contacts',background:'#121212',text:'#ffffff',price:'#78e895',contact:'#ff8585',accent:'#78e895'},
 'clean-modern':{name:'Clean Modern',description:'White, charcoal and blue details',background:'#ffffff',text:'#252e28',price:'#245fb5',contact:'#245fb5',accent:'#b9c4d2'}
};
