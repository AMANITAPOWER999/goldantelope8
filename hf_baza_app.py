"""
HuggingFace Space: Сбор базы TG пользователей
Загрузить как app.py в https://huggingface.co/spaces/poweramanita/Baza

Секреты (Settings -> Repository secrets):
  TELETHON_SESSION = <ваша строка сессии>

requirements.txt:
  telethon
  gradio
"""

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import gradio as gr
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    UserStatusOnline, UserStatusRecently, UserStatusOffline,
    UserStatusLastWeek, UserStatusLastMonth
)
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError, FloodWaitError
)

API_ID = 32881984
API_HASH = 'd2588f09dfbc5103ef77ef21c07dbf8b'
SESSION = os.environ.get('TELETHON_SESSION', '')

CHAT_VN_CHANNELS = [
    'nhatrang_bg', 'NhaTrangchat', 'NhaTrang55', 'svoi_nhatrang',
    'zhenskiy_nhatrang', 'NhaTrangLady', 'NhaTrangSun',
    'Danang_Viet', 'danang_women', 'danangchat_ask', 'zhenskiy_danang',
    'Danang_people', 'Vietnam_Danang1', 'chat_danang', 'danang_chats',
    'phanthietchat111', 'Nyachang_Vietnam', 'onus_vietnam', 'Viza_Vietnam',
    'Dalat_Vietnam', 'vietnam_chat1', 'vietnam_chats',
    'HoChiMinh_Saigon', 'HoChiMinhChatik', 'hochiminh01_bg',
    'phu_quoc_chat', 'phuquoc_getmir_chat', 'fukuok_chat', 'chat_fukuok',
    'hanoichatvip',
]

CHAT_TH_CHANNELS = [
    'Phuket_chatBG', 'barakholka_pkhuket', 'chat_phuket', 'chats_phuket',
    'huahinrus', 'rentinthai', 'bangkok_chat_znakomstva', 'Bangkok_market_bg',
    'vse_svoi_bangkok', 'visa_thailand_chat', 'thailand_4at', 'rent_thailand_chat',
    'thailand_chatt1', 'chat_bangkok', 'Bangkok_chats', 'PattayaSale',
    'pattayachatonline', 'Pattayapar', 'chats_pattaya', 'phuketdating', 'KrabiChat',
]

ENTERTAIN_CHANNELS = [
    'nhatrang_tusa_afisha', 'nhatrang_affiche', 'nyachangafisha',
    'nhatrang_afisha', 'introconcertvn', 'afisha_nhatrang', 'T2TNhaTrangevents',
    'nachang_tusa', 'drinkparty666', 'nyachang_ru',
    'danangnew', 'ads_danang', 'danang_afisha', 'danangpals',
]

MED_CHANNELS = [
    'viet_med', 'viet_medicine', 'viethandentalrus', 'VietnamDentist', 'doctor_viet',
    'Medicine_Vietnam', 'mediacenter_vietsovpetro_school', 'vietmedic', 'health_med_viet',
]

RE_CHANNELS_THAI = [
    'arenda_phukets', 'THAILAND_REAL_ESTATE_PHUKET', 'housephuket', 'arenda_phuket_thailand',
    'phuket_nedvizhimost_rent', 'phuketsk_arenda', 'phuket_nedvizhimost_thailand', 'phuketsk_for_rent',
    'phuket_rentas', 'rentalsphuketonli', 'rentbuyphuket', 'Phuket_thailand05', 'nedvizhimost_pattaya',
    'arenda_pattaya', 'pattaya_realty_estate', 'HappyHomePattaya', 'sea_bangkok', 'Samui_for_you',
    'sea_phuket', 'realty_in_thailand', 'nedvig_thailand', 'thailand_nedvizhimost',
    'globe_nedvizhka_Thailand',
]

RE_CHANNELS_VIET = [
    'phuquoc_rent_wt', 'phyquocnedvigimost', 'Viet_Life_Phu_Quoc_rent', 'nhatrangapartment',
    'tanrealtorgh', 'viet_life_niachang', 'nychang_arenda', 'rent_nha_trang', 'nyachang_nedvizhimost',
    'nedvizimost_nhatrang', 'nhatrangforrent79', 'NhatrangRentl', 'arenda_v_nyachang', 'rent_appart_nha',
    'Arenda_Nyachang_Zhilye', 'NhaTrang_rental', 'realestatebythesea_1', 'NhaTrang_Luxury',
    'luckyhome_nhatrang', 'rentnhatrang', 'megasforrentnhatrang', 'viethome',
    'Vietnam_arenda', 'huynhtruonq', 'DaNangRentAFlat', 'danag_viet_life_rent', 'Danang_House',
    'DaNangApartmentRent', 'danang_arenda', 'arenda_v_danang', 'HoChiMinhRentI', 'hcmc_arenda',
    'Hanoirentapartment', 'HanoiRentl', 'Hanoi_Rent', 'PhuquocRentl',
]

BIKE_CHANNELS_VIET = [
    'bike_nhatrang', 'motohub_nhatrang', 'NhaTrang_moto_market', 'RentBikeUniq',
    'BK_rental', 'nha_trang_rent', 'RentTwentyTwo22NhaTrang',
    'danang_bike_rent', 'bikerental1', 'viet_sovet',
]

BIKE_CHANNELS_THAI = [
    'arenda_thailandd', 'thailand_market', 'rental_service_thailand',
    'samui_arenda2', 'motorrenta', 'nashi_phuket_auto',
    'thailand_drive', 'PKHUKET_BAYKOV', 'Pattaya_Arenda_ru',
    'pattaya_happy_auto', 'pattaya_arenda', 'pattayamoto',
]

vietnam_channels = []
thailand_channels = []
for ch in CHAT_VN_CHANNELS:
    vietnam_channels.append(('chat', ch))
for ch in ENTERTAIN_CHANNELS:
    vietnam_channels.append(('entertainment', ch))
for ch in MED_CHANNELS:
    vietnam_channels.append(('medicine', ch))
for ch in RE_CHANNELS_VIET:
    vietnam_channels.append(('real_estate', ch))
for ch in BIKE_CHANNELS_VIET:
    vietnam_channels.append(('transport', ch))
for ch in CHAT_TH_CHANNELS:
    thailand_channels.append(('chat', ch))
for ch in RE_CHANNELS_THAI:
    thailand_channels.append(('real_estate', ch))
for ch in BIKE_CHANNELS_THAI:
    thailand_channels.append(('transport', ch))

ALL_VN = len(vietnam_channels)
ALL_TH = len(thailand_channels)
ALL_TOTAL = ALL_VN + ALL_TH

STATUS = {
    'running': False,
    'done': False,
    'log': [],
    'vn_count': 0,
    'th_count': 0,
    'channel_idx': 0,
    'channel_total': ALL_TOTAL,
    'current_channel': '',
    'errors': [],
    'result_file': None,
}

RESULT_PATH = '/tmp/tg_users_database.json'


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    STATUS['log'].append(line)
    if len(STATUS['log']) > 500:
        STATUS['log'] = STATUS['log'][-300:]
    print(line, flush=True)


def is_active_24h(status):
    if status is None:
        return False
    if isinstance(status, UserStatusOnline):
        return True
    if isinstance(status, UserStatusRecently):
        return True
    if isinstance(status, UserStatusOffline):
        if status.was_online:
            return status.was_online > datetime.now(timezone.utc) - timedelta(hours=24)
    return False


async def fetch_participants(client, entity):
    users = []
    count = 0
    async for user in client.iter_participants(entity, limit=10000):
        count += 1
        if user.bot:
            continue
        if not is_active_24h(user.status):
            continue
        users.append({'user_id': user.id, 'username': user.username or ''})
    return users, count


async def collect_channel(client, ch, category, country):
    try:
        entity = await asyncio.wait_for(client.get_entity(ch), timeout=15)
        try:
            users, total = await asyncio.wait_for(
                fetch_participants(client, entity), timeout=120
            )
            log(f"  @{ch} ({category}) -> {total} всего, {len(users)} активных за 24ч")
            return users
        except asyncio.TimeoutError:
            log(f"  @{ch} — таймаут (120с), пропуск")
            return []
    except ChatAdminRequiredError:
        log(f"  @{ch} — нет доступа (нужны права админа)")
    except ChannelPrivateError:
        log(f"  @{ch} — приватный канал")
    except FloodWaitError as e:
        wait = min(e.seconds, 180)
        log(f"  @{ch} — FloodWait {e.seconds}с, жду {wait}с...")
        await asyncio.sleep(wait + 3)
        return await collect_channel(client, ch, category, country)
    except asyncio.TimeoutError:
        log(f"  @{ch} — таймаут get_entity")
    except Exception as e:
        err = f"  @{ch} — ошибка: {type(e).__name__}: {e}"
        log(err)
        STATUS['errors'].append(err)
    return []


def save_result(vn_users, th_users, status='in_progress'):
    both = set(vn_users.keys()) & set(th_users.keys())
    result = {
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'status': status,
        'stats': {
            'vietnam_unique_users': len(vn_users),
            'thailand_unique_users': len(th_users),
            'users_in_both': len(both),
            'vietnam_channels_total': ALL_VN,
            'thailand_channels_total': ALL_TH,
        },
        'vietnam': list(vn_users.values()),
        'thailand': list(th_users.values()),
    }
    with open(RESULT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    STATUS['result_file'] = RESULT_PATH


async def run_collection():
    STATUS['running'] = True
    STATUS['done'] = False
    STATUS['log'] = []
    STATUS['errors'] = []
    STATUS['vn_count'] = 0
    STATUS['th_count'] = 0
    STATUS['channel_idx'] = 0

    if not SESSION:
        log("ОШИБКА: TELETHON_SESSION не задана в секретах!")
        STATUS['running'] = False
        return

    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log("ОШИБКА: сессия не авторизована!")
        await client.disconnect()
        STATUS['running'] = False
        return

    me = await client.get_me()
    log(f"Авторизован: {me.first_name} (id={me.id})")
    log(f"Каналов: Вьетнам={ALL_VN}, Тайланд={ALL_TH}, всего={ALL_TOTAL}")
    log("")

    vn_users = {}
    th_users = {}

    log("═" * 50)
    log("ВЬЕТНАМ")
    log("═" * 50)
    for i, (cat, ch) in enumerate(vietnam_channels, 1):
        STATUS['channel_idx'] = i
        STATUS['current_channel'] = f"VN @{ch}"
        log(f"\n[{i}/{ALL_VN}] @{ch}")
        users = await collect_channel(client, ch, cat, 'vietnam')
        for u in users:
            uid = u['user_id']
            if uid not in vn_users:
                vn_users[uid] = {'user_id': uid, 'username': u['username'], 'channels': []}
            if ch not in vn_users[uid]['channels']:
                vn_users[uid]['channels'].append(ch)
        STATUS['vn_count'] = len(vn_users)
        if i % 5 == 0:
            save_result(vn_users, th_users)
            log(f"  [сохранено: VN={len(vn_users)}]")
        await asyncio.sleep(2)

    save_result(vn_users, th_users)
    log(f"\nВьетнам завершён: {len(vn_users)} уникальных")

    log("")
    log("═" * 50)
    log("ТАЙЛАНД")
    log("═" * 50)
    for i, (cat, ch) in enumerate(thailand_channels, 1):
        STATUS['channel_idx'] = ALL_VN + i
        STATUS['current_channel'] = f"TH @{ch}"
        log(f"\n[{i}/{ALL_TH}] @{ch}")
        users = await collect_channel(client, ch, cat, 'thailand')
        for u in users:
            uid = u['user_id']
            if uid not in th_users:
                th_users[uid] = {'user_id': uid, 'username': u['username'], 'channels': []}
            if ch not in th_users[uid]['channels']:
                th_users[uid]['channels'].append(ch)
        STATUS['th_count'] = len(th_users)
        if i % 5 == 0:
            save_result(vn_users, th_users)
            log(f"  [сохранено: TH={len(th_users)}]")
        await asyncio.sleep(2)

    save_result(vn_users, th_users, status='complete')
    both = set(vn_users.keys()) & set(th_users.keys())

    log("")
    log("═" * 50)
    log("ГОТОВО!")
    log(f"Вьетнам: {len(vn_users)} уникальных пользователей")
    log(f"Тайланд: {len(th_users)} уникальных пользователей")
    log(f"В обоих странах: {len(both)}")
    log(f"Файл: {RESULT_PATH}")
    log("═" * 50)

    await client.disconnect()
    STATUS['running'] = False
    STATUS['done'] = True


def start_collection():
    if STATUS['running']:
        return "Сбор уже запущен!"
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=lambda: loop.run_until_complete(run_collection()), daemon=True)
    t.start()
    return "Сбор запущен!"


def get_status():
    if not STATUS['running'] and not STATUS['done']:
        return "Ожидание запуска. Нажмите кнопку для старта."
    progress = f"{STATUS['channel_idx']}/{STATUS['channel_total']}"
    state = "РАБОТАЕТ" if STATUS['running'] else "ЗАВЕРШЁН"
    return (
        f"Статус: {state}\n"
        f"Прогресс: {progress} каналов\n"
        f"Текущий: {STATUS['current_channel']}\n"
        f"Вьетнам: {STATUS['vn_count']} пользователей\n"
        f"Тайланд: {STATUS['th_count']} пользователей\n"
        f"Ошибок: {len(STATUS['errors'])}"
    )


def get_log():
    return "\n".join(STATUS['log'][-100:]) if STATUS['log'] else "Лог пуст"


def download_result():
    if os.path.exists(RESULT_PATH):
        return RESULT_PATH
    return None


with gr.Blocks(title="TG Users Collector") as demo:
    gr.Markdown("# Сбор базы TG пользователей (Вьетнам + Тайланд)")
    gr.Markdown(f"Каналов: **{ALL_VN}** Вьетнам + **{ALL_TH}** Тайланд = **{ALL_TOTAL}** всего")

    with gr.Row():
        start_btn = gr.Button("🚀 Запустить сбор", variant="primary", scale=1)
        refresh_btn = gr.Button("🔄 Обновить статус", scale=1)

    status_box = gr.Textbox(label="Статус", lines=7, interactive=False)
    log_box = gr.Textbox(label="Лог (последние 100 строк)", lines=20, interactive=False)

    with gr.Row():
        download_btn = gr.Button("📥 Скачать результат (JSON)")
    file_output = gr.File(label="Файл результата")

    start_btn.click(fn=start_collection, outputs=status_box)
    refresh_btn.click(fn=get_status, outputs=status_box)
    refresh_btn.click(fn=get_log, outputs=log_box)
    download_btn.click(fn=download_result, outputs=file_output)

    demo.load(fn=get_status, outputs=status_box)

if __name__ == '__main__':
    demo.launch(server_name="0.0.0.0", server_port=7860)
