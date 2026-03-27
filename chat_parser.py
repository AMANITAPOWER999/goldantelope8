import os
import json
import asyncio
import hashlib
import requests
from datetime import datetime
from telethon import TelegramClient

API_ID = int(os.environ.get('TELETHON_API_ID', 0))
API_HASH = os.environ.get('TELETHON_API_HASH', '')

BUNNY_STORAGE_ZONE = os.environ.get('BUNNY_STORAGE_ZONE', '')
BUNNY_ACCESS_KEY = os.environ.get('BUNNY_ACCESS_KEY', '')
BUNNY_CDN_URL = os.environ.get('BUNNY_CDN_URL', '')

CHAT_CHANNELS = [
    "phuket_ru", "Pkhuket_Chatx", "vmestenaphukete", "phuket_chat1",
    "bangkok_chat_znakomstva", "phangan_chat", "samui_chat", "chiangmai_chat",
    "svoi_thai_chat", "Tailand_chat2",
    "bali_chat", "Bali_chat_official", "chatotgleba", "bali_topchat",
    "kazakhbali", "networkingbali", "CHAT_BALI_REAL_ESTATE", "baly_chat"
]

def is_english_only(text):
    """Проверяет, полностью ли текст на английском"""
    for char in text:
        if ord(char) > 127 and char not in '.,!?-…()[]{}":;/\\ ':
            return False
    return True

def is_spam(text):
    """Проверяет, не является ли объявление спамом/промо"""
    if not text:
        return False
    spam_keywords = [
        'deriv.com', 'synthetic indices', 'trading account',
        'round-the-clock trading', 'forex', 'crypto trading',
        'kumpulan video viral', 'full video', 'join grup', 'klik link',
        'video-info-viral', 'join sekarang',
        'rent account', 'rent linkedin', 'rent facebook', 'make money',
        'passive income', 'rent out', 'advertising account',
        'grow your business', 'promote message', 'promotion packages',
        'reach more customers', 'boost visibility', 'drive engagement',
        'anda ingin sukses', 'ubah cara berfikir', 'positive thinking',
        'salam sukses', 'mulai sebelum orang',
        'notif sms', 'hak cipta hack', 'bootloader', 'fingerprint'
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in spam_keywords)

def upload_to_bunny(file_bytes, filename):
    if not BUNNY_STORAGE_ZONE or not BUNNY_ACCESS_KEY:
        return None
    try:
        file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
        remote_path = f"listings/{file_hash}_{filename}"
        url = f"https://storage.bunnycdn.com/{BUNNY_STORAGE_ZONE}/{remote_path}"
        headers = {"AccessKey": BUNNY_ACCESS_KEY, "Content-Type": "application/octet-stream"}
        response = requests.put(url, headers=headers, data=file_bytes, timeout=30)
        if response.status_code == 201:
            cdn_url = f"https://{BUNNY_STORAGE_ZONE}.b-cdn.net/{remote_path}"
            if BUNNY_CDN_URL and 'b-cdn.net' in BUNNY_CDN_URL:
                cdn_url = f"{BUNNY_CDN_URL.rstrip('/')}/{remote_path}"
            return cdn_url
    except:
        pass
    return None

async def connect_with_retry(max_retries=3):
    """Подключение с retry логикой (для обхода database is locked)"""
    for attempt in range(max_retries):
        try:
            client = TelegramClient('goldantelope_user', API_ID, API_HASH)
            await client.start()
            return client
        except Exception as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # 2, 4, 8 секунд
                print(f"⏳ База заблокирована, ожидаю {wait_time}сек...")
                await asyncio.sleep(wait_time)
            else:
                raise

async def parse_chats():
    try:
        client = await connect_with_retry()
    except Exception as e:
        print(f"❌ Не удалось подключиться: {str(e)[:100]}")
        return
    
    listings_file = "listings_chat.json"
    existing = []
    if os.path.exists(listings_file):
        try:
            with open(listings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                existing = data
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        existing.extend(v)
        except Exception:
            existing = []

    existing_ids = {item['id'] for item in existing if isinstance(item, dict)}
    existing_texts = {item.get('description', '')[:150] for item in existing if isinstance(item, dict)}
    existing_hashes = {item.get('image_hash') for item in existing if isinstance(item, dict) and item.get('image_hash')}
    existing_image_urls = {item.get('image_url') for item in existing if isinstance(item, dict) and item.get('image_url')}
    
    new_items = []
    
    total_skipped = 0
    for channel in CHAT_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            # Берем последние 5 сообщений для более частых обновлений (1 в минуту)
            messages = await client.get_messages(entity, limit=5)
            
            for msg in messages:
                if not msg.text or len(msg.text) < 20:
                    continue
                
                if is_english_only(msg.text):
                    total_skipped += 1
                    continue
                
                if is_spam(msg.text):
                    continue
                
                item_id = f"{channel}_{msg.id}"
                if item_id in existing_ids:
                    continue
                if msg.text[:150] in existing_texts:
                    continue
                
                image_url = None
                image_hash = None
                if msg.media and hasattr(msg.media, 'photo'):
                    try:
                        photo_bytes = await client.download_media(msg.media, bytes)
                        if photo_bytes:
                            image_hash = hashlib.md5(photo_bytes).hexdigest()
                            # Пропустить если фото по хешу уже есть
                            if image_hash in existing_hashes:
                                continue
                            filename = f"{channel}_{msg.id}.jpg"
                            image_url = upload_to_bunny(photo_bytes, filename)
                            # Пропустить если URL фото уже в системе
                            if image_url and image_url in existing_image_urls:
                                continue
                            if image_url:
                                print(f"   📷 {filename}")
                    except:
                        pass
                
                item = {
                    'id': item_id,
                    'category': 'chat',
                    'title': msg.text[:100],
                    'description': msg.text,
                    'date': msg.date.isoformat(),
                    'source_channel': f"@{channel}",
                    'message_id': msg.id,
                    'image_url': image_url,
                    'image_hash': image_hash,
                    'has_media': bool(msg.media),
                    'price': None
                }
                new_items.append(item)
            
            channel_count = len([i for i in new_items if i['source_channel'] == f'@{channel}'])
            if channel_count > 0:
                print(f"✓ @{channel}: +{channel_count}")
        except Exception as e:
            error_msg = str(e)[:50]
            if 'database is locked' not in error_msg:
                print(f"⚠️ @{channel}: {error_msg}")
        
        await asyncio.sleep(120)  # 2 минуты задержка между каналами (менее агрессивно)
    
    if new_items:
        all_items = existing + new_items
        with open(listings_file, 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"💬 Добавлено {len(new_items)} новых сообщений")
        if total_skipped > 0:
            print(f"🚫 Отклонено англоязычных: {total_skipped}")
    else:
        print("💬 Новых сообщений нет")
        if total_skipped > 0:
            print(f"🚫 (найдено {total_skipped} англ., но они отклонены)")
    
    try:
        await client.disconnect()
    except:
        pass

if __name__ == '__main__':
    print(f"🔄 Парсинг чатов: {datetime.now().strftime('%H:%M:%S')}")
    asyncio.run(parse_chats())
