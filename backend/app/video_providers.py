"""Independent video providers. Submission is never automatically retried."""
import base64
import os
import re
from urllib.parse import urlparse
import httpx

class ProviderFailure(Exception):
    pass

class UncertainSubmission(Exception):
    pass

def key(provider):
    value=os.getenv('BFL_API_KEY' if provider=='bfl' else 'GEMINI_API_KEY','')
    if not value:
        raise ProviderFailure('This video provider is not configured.')
    return value

def options():
    return [
        {'id':'bfl','name':'BFL FLUX 3 Draft','available':bool(os.getenv('BFL_API_KEY')),'durations':list(range(5,21)),
         'rate':0.06,'note':'One draft generation uses all product photos as ordered keyframes.'},
        {'id':'google','name':'Google Veo 3.1 Standard','available':bool(os.getenv('GEMINI_API_KEY')),'durations':[4,6,8],
         'rate':0.4,'note':'Multiple products use separate four-second generations, trimmed into the selected final length.'},
    ]

def estimate(provider,duration,count):
    return round(duration*.06 if provider=='bfl' else (duration if count==1 else 4*count)*.4,2)

def prompt(theme):
    style={'ethiopian-warmth':'warm cream studio background, subtle green and gold woven-textile accents',
           'bold-contrast':'black studio background with restrained green accent lighting',
           'clean-modern':'clean white studio background with subtle blue accents'}[theme]
    return ('Create a polished product advertisement with gentle camera movement and realistic lighting. '+style+'. '
            'Preserve the exact product shape, color, brand marks and details in the provided photograph. '
            'Keep the product visible. Do not add people, captions, prices, contact details or additional products. '
            'Use smooth product showcase motion; no distortion or morphing into a different product.')

def bfl_url(value):
    parsed=urlparse(value)
    host=parsed.hostname or ''
    if parsed.scheme!='https' or not (host=='api.bfl.ai' or host.endswith('.bfl.ai')) or parsed.username or parsed.password:
        raise ProviderFailure('The provider returned an invalid polling address.')
    return value

def google_operation(value):
    if not re.fullmatch(r'models/veo-3\.1-generate-preview/operations/[A-Za-z0-9_-]+',value):
        raise ProviderFailure('The provider returned an invalid operation.')
    return value

def submit(provider,photos,duration,theme):
    credentials=key(provider)
    if provider=='bfl':
        images=['data:image/jpeg;base64,'+base64.b64encode(photo).decode() for photo in photos]
        url='https://api.bfl.ai/v1/flux-3-video'
        frames=images[0] if len(images)==1 else [[round(i*duration/len(images),3),image] for i,image in enumerate(images)]
        instruction=prompt(theme)
        if len(images)>1:
            instruction+=' The pinned keyframes show separate products. Show them in order with clean shot cuts at the pinned times, never morphing one product into another. Hold each product until the next shot.'
        payload={'mode':'i2v','keyframes':frames,'prompt':instruction,
                 'duration':duration,'aspect_ratio':'9:16','resolution':'hd','draft':True,'generate_audio':False}
        headers={'x-key':credentials}
    else:
        url='https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning'
        payload={'instances':[{'prompt':prompt(theme),'image':{'mimeType':'image/jpeg','bytesBase64Encoded':base64.b64encode(photos[0]).decode()}}],
                 'parameters':{'durationSeconds':duration,'aspectRatio':'9:16','resolution':'720p','sampleCount':1}}
        headers={'x-goog-api-key':credentials}
    try:
        response=httpx.post(url,json=payload,headers=headers,timeout=60)
    except Exception:
        raise UncertainSubmission('The provider may have received this request. Check its dashboard before creating another.')
    if response.status_code>=500 or response.status_code in (408,):
        raise UncertainSubmission('The provider outcome is uncertain. Check its dashboard before creating another.')
    if not response.is_success:
        reason='Check the API key, video access and account credits.' if response.status_code in (400,401,403,404,429) else 'Please review the inputs and try again.'
        raise ProviderFailure('Video provider rejected this request. '+reason)
    try:
        data=response.json()
        if provider=='bfl':
            if not isinstance(data['id'],str) or not data['id']:
                raise ValueError()
            return {'id':data['id'],'poll':bfl_url(data['polling_url'])}
        operation=google_operation(data['name'])
        return {'id':operation,'poll':operation}
    except Exception:
        raise UncertainSubmission('The provider accepted the request but its task reference could not be saved. Check its dashboard.')

def poll(provider,task):
    headers={'x-key':key(provider)} if provider=='bfl' else {'x-goog-api-key':key(provider)}
    url=bfl_url(task['poll']) if provider=='bfl' else 'https://generativelanguage.googleapis.com/v1beta/'+google_operation(task['poll'])
    response=httpx.get(url,headers=headers,timeout=30)
    if response.status_code in (401,403,404):
        raise ProviderFailure('Could not access the existing provider task. Check video access in its dashboard.')
    response.raise_for_status()
    data=response.json()
    if provider=='bfl':
        state=data.get('status')
        if state=='Ready':
            return data['result']['sample']
        if state in ('Error','Request Moderated','Content Moderated','Task not found'):
            raise ProviderFailure('The provider could not generate this video. Please review your product photo.')
        return None
    if not data.get('done'):
        return None
    if data.get('error'):
        raise ProviderFailure('Google could not generate this video. Check video access, credits and your product photo.')
    try:
        return data['response']['generateVideoResponse']['generatedSamples'][0]['video']['uri']
    except (KeyError,IndexError,TypeError):
        raise ProviderFailure('Google returned no usable video for this product.')

def download(provider,url):
    # Only provider-owned download origins are allowed. API keys go solely to Google API hosts.
    host=urlparse(url).hostname or ''
    google=host=='generativelanguage.googleapis.com'
    bfl=host.endswith('.bfl.ai') or host.endswith('.bfl.ml') or host in ('storage.googleapis.com','bfldelivery.blob.core.windows.net')
    if urlparse(url).scheme!='https' or not (google if provider=='google' else bfl):
        raise ProviderFailure('The provider returned an unsupported media address.')
    headers={'x-goog-api-key':key(provider)} if google else {}
    with httpx.stream('GET',url,headers=headers,timeout=60,follow_redirects=False) as response:
        # Google downloads may redirect to Google storage; do not forward credentials to that host.
        if response.status_code in (301,302,303,307,308) and google:
            location=response.headers.get('location','')
            if urlparse(location).scheme!='https' or not (urlparse(location).hostname or '').endswith('.googleusercontent.com') and urlparse(location).hostname!='storage.googleapis.com':
                raise ProviderFailure('The provider returned an unsupported media redirect.')
            return download_public(location)
        response.raise_for_status()
        return bounded(response)

def bounded(response):
    output=bytearray()
    for chunk in response.iter_bytes():
        output.extend(chunk)
        if len(output)>100*1024*1024:
            raise ProviderFailure('The provider video exceeds the download limit.')
    if not output:
        raise ProviderFailure('The provider returned an empty video.')
    return bytes(output)

def download_public(url):
    with httpx.stream('GET',url,timeout=60,follow_redirects=False) as response:
        response.raise_for_status();return bounded(response)
