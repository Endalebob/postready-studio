import logging
import os
from functools import lru_cache
import httpx

# Telegram's API puts the bot credential in the URL. Never log request URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

class TelegramRejected(Exception):
    pass

class TelegramUncertain(Exception):
    pass

def configured():
    return bool(os.getenv('TELEGRAM_BOT_TOKEN'))

def call(method, data=None, files=None):
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        raise TelegramRejected('Telegram is not configured yet.')
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post('https://api.telegram.org/bot'+token+'/'+method, data=data or {}, files=files)
        payload = response.json()
        if not payload.get('ok'):
            raise TelegramRejected('Telegram rejected the request. Check the bot and channel permissions.')
        return payload['result']
    except TelegramRejected:
        raise
    except Exception:
        raise TelegramUncertain('Telegram did not return a confirmed response.') from None

@lru_cache(maxsize=1)
def identity(token):
    return call('getMe')

def bot():
    return identity(os.getenv('TELEGRAM_BOT_TOKEN',''))

def can_post(member):
    return member.get('status') == 'creator' or (member.get('status') == 'administrator' and member.get('can_post_messages') is True)

def verify_channel(chat_id, user_id):
    chat = call('getChat', {'chat_id': chat_id})
    if chat.get('type') != 'channel':
        raise TelegramRejected('Choose a Telegram channel for this release.')
    me = bot()
    if not can_post(call('getChatMember', {'chat_id': chat_id, 'user_id': me['id']})):
        raise TelegramRejected('Give the bot administrator permission to post in this channel.')
    if not can_post(call('getChatMember', {'chat_id': chat_id, 'user_id': user_id})):
        raise TelegramRejected('Your Telegram account must be a channel administrator with permission to post.')
    return chat

def send_photo(chat_id, png, caption):
    return call('sendPhoto', {'chat_id': chat_id, 'caption': caption}, {'photo': ('postready-ad.png', png, 'image/png')})
