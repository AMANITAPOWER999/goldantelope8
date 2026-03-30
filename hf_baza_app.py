import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone

import gradio as gr
from huggingface_hub import HfApi
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    UserStatusOnline, UserStatusRecently, UserStatusOffline,
    UserStatusLastWeek, UserStatusLastMonth,
)
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError, FloodWaitError
)

API_ID = 32881984
API_HASH = 'd2588f09dfbc5103ef77ef21c07dbf8b'
SESSION = os.environ.get('TELETHON_SESSION', '')
HF_TOKEN = os.environ.get('HF_TOKEN', '')
HF_REPO = 'poweramanita/Baza'

CHAT_VN = [
    'nhatrang_bg','NhaTrangchat','NhaTrang55','svoi_nhatrang',
    'zhenskiy_nhatrang','NhaTrangLady','NhaTrangSun',
    'Danang_Viet','danang_women','danangchat_ask','zhenskiy_danang',
    'Danang_people','Vietnam_Danang1','chat_danang','danang_chats',
    'phanthietchat111','Nyachang_Vietnam','onus_vietnam','Viza_Vietnam',
    'Dalat_Vietnam','vietnam_chat1','vietnam_chats',
    'HoChiMinh_Saigon','HoChiMinhChatik','hochiminh01_bg',
    'phu_quoc_chat','phuquoc_getmir_chat','fukuok_chat','chat_fukuok',
    'hanoichatvip',
]
ENTERTAIN = [
    'nhatrang_tusa_afisha','nhatrang_affiche','nyachangafisha',
    'nhatrang_afisha','introconcertvn','afisha_nhatrang','T2TNhaTrangevents',
    'nachang_tusa','drinkparty666','nyachang_ru',
    'danangnew','ads_danang','danang_afisha','danangpals',
]
MED = [
    'viet_med','viet_medicine','viethandentalrus','VietnamDentist','doctor_viet',
    'Medicine_Vietnam','mediacenter_vietsovpetro_school','vietmedic','health_med_viet',
]
RE_VN = [
    'phuquoc_rent_wt','phyquocnedvigimost','Viet_Life_Phu_Quoc_rent','nhatrangapartment',
    'tanrealtorgh','viet_life_niachang','nychang_arenda','rent_nha_trang','nyachang_nedvizhimost',
    'nedvizimost_nhatrang','nhatrangforrent79','NhatrangRentl','arenda_v_nyachang','rent_appart_nha',
    'Arenda_Nyachang_Zhilye','NhaTrang_rental','realestatebythesea_1','NhaTrang_Luxury',
    'luckyhome_nhatrang','rentnhatrang','megasforrentnhatrang','viethome',
    'Vietnam_arenda','huynhtruonq','DaNangRentAFlat','danag_viet_life_rent','Danang_House',
    'DaNangApartmentRent','danang_arenda','arenda_v_danang','HoChiMinhRentI','hcmc_arenda',
    'Hanoirentapartment','HanoiRentl','Hanoi_Rent','PhuquocRentl',
]
BIKE_VN = [
    'bike_nhatrang','motohub_nhatrang','NhaTrang_moto_market','RentBikeUniq',
    'BK_rental','nha_trang_rent','RentTwentyTwo22NhaTrang',
    'danang_bike_rent','bikerental1','viet_sovet',
]
CHAT_TH = [
    'Phuket_chatBG','barakholka_pkhuket','chat_phuket','chats_phuket',
    'huahinrus','rentinthai','bangkok_chat_znakomstva','Bangkok_market_bg',
    'vse_svoi_bangkok','visa_thailand_chat','thailand_4at','rent_thailand_chat',
    'thailand_chatt1','chat_bangkok','Bangkok_chats','PattayaSale',
    'pattayachatonline','Pattayapar','chats_pattaya','phuketdating','KrabiChat',
]
RE_TH = [
    'arenda_phukets','THAILAND_REAL_ESTATE_PHUKET','housephuket','arenda_phuket_thailand',
    'phuket_nedvizhimost_rent','phuketsk_arenda','phuket_nedvizhimost_thailand','phuketsk_for_rent',
    'phuket_rentas','rentalsphuketonli','rentbuyphuket','Phuket_thailand05','nedvizhimost_pattaya',
    'arenda_pattaya','pattaya_realty_estate','HappyHomePattaya','sea_bangkok','Samui_for_you',
    'sea_phuket','realty_in_thailand','nedvig_thailand','thailand_nedvizhimost',
    'globe_nedvizhka_Thailand',
]
BIKE_TH = [
    'arenda_thailandd','thailand_market','rental_service_thailand',
    'samui_arenda2','motorrenta','nashi_phuket_auto',
    'thailand_drive','PKHUKET_BAYKOV','Pattaya_Arenda_ru',
    'pattaya_happy_auto','pattaya_arenda','pattayamoto',
]

vn_channels = (
    [('chat',c) for c in CHAT_VN] +
    [('entertainment',c) for c in ENTERTAIN] +
    [('medicine',c) for c in MED] +
    [('real_estate',c) for c in RE_VN] +
    [('transport',c) for c in BIKE_VN]
)
th_channels = (
    [('chat',c) for c in CHAT_TH] +
    [('real_estate',c) for c in RE_TH] +
    [('transport',c) for c in BIKE_TH]
)
TOTAL_VN = len(vn_channels)
TOTAL_TH = len(th_channels)
TOTAL = TOTAL_VN + TOTAL_TH

status = {'running':False,'done':False,'vn':0,'th':0,'idx':0,'cur':'','log':[],'errors':0}
RESULT = '/tmp/tg_users_database.json'

def log(m):
    t = datetime.now().strftime('%H:%M:%S')
    line = f"[{t}] {m}"
    status['log'].append(line)
    if len(status['log'])>800: status['log']=status['log'][-500:]
    print(line,flush=True)

def get_status_text(st):
    if isinstance(st, UserStatusOnline): return 'online'
    if isinstance(st, UserStatusRecently): return 'recently'
    if isinstance(st, UserStatusOffline):
        if st.was_online: return st.was_online.strftime('%Y-%m-%d %H:%M')
        return 'offline'
    if isinstance(st, UserStatusLastWeek): return 'last_week'
    if isinstance(st, UserStatusLastMonth): return 'last_month'
    return 'unknown'

async def get_all_users(client, entity):
    users = []
    count = 0
    async for u in client.iter_participants(entity, aggressive=True):
        count += 1
        if u.bot:
            continue
        users.append({
            'user_id': u.id,
            'username': u.username or '',
            'first_name': u.first_name or '',
            'last_name': u.last_name or '',
            'phone': u.phone or '',
            'last_seen': get_status_text(u.status),
        })
    return users, count

async def do_channel(client, ch, cat):
    try:
        if isinstance(ch, int) or (isinstance(ch, str) and ch.lstrip('-').isdigit()):
            ent = await asyncio.wait_for(client.get_entity(int(ch)), timeout=15)
        else:
            ent = await asyncio.wait_for(client.get_entity(ch), timeout=15)
        try:
            title = getattr(ent, 'title', ch)
            participants_count = getattr(ent, 'participants_count', '?')
            log(f"  @{ch} ({cat}) [{title}] ~{participants_count} подписчиков")
            users, total = await asyncio.wait_for(get_all_users(client, ent), timeout=600)
            log(f"    -> собрано {len(users)} из {total} (боты исключены)")
            return users
        except asyncio.TimeoutError:
            log(f"    -> ТАЙМАУТ (10 мин), пропуск")
            return []
    except ChatAdminRequiredError:
        log(f"  @{ch} — нет доступа (нужны права админа)")
        status['errors'] += 1
    except ChannelPrivateError:
        log(f"  @{ch} — приватный")
        status['errors'] += 1
    except FloodWaitError as e:
        w = min(e.seconds, 300)
        log(f"  @{ch} — FloodWait {e.seconds}с, жду {w}с")
        await asyncio.sleep(w + 3)
        return await do_channel(client, ch, cat)
    except asyncio.TimeoutError:
        log(f"  @{ch} — таймаут entity")
        status['errors'] += 1
    except Exception as e:
        log(f"  @{ch} — ошибка: {type(e).__name__}: {e}")
        status['errors'] += 1
    return []

def save(vn, th, st='in_progress'):
    both = set(vn.keys()) & set(th.keys())
    r = {
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'status': st,
        'mode': 'ALL_USERS (no 24h filter)',
        'stats': {
            'vietnam_unique': len(vn),
            'thailand_unique': len(th),
            'total_unique': len(set(vn.keys()) | set(th.keys())),
            'in_both_countries': len(both),
            'channels_vn': TOTAL_VN,
            'channels_th': TOTAL_TH,
        },
        'vietnam': list(vn.values()),
        'thailand': list(th.values()),
    }
    with open(RESULT, 'w') as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    try:
        if HF_TOKEN:
            api = HfApi(token=HF_TOKEN)
            api.upload_file(
                path_or_fileobj=RESULT,
                path_in_repo='tg_users_database.json',
                repo_id=HF_REPO,
                repo_type='space',
                commit_message=f'Update: VN={len(vn)} TH={len(th)} ({st})',
            )
            log(f"  [загружено в HF repo: VN={len(vn)} TH={len(th)}]")
    except Exception as e:
        log(f"  [ошибка загрузки в HF: {e}]")

async def run():
    status.update(running=True, done=False, log=[], vn=0, th=0, idx=0, errors=0)
    if not SESSION:
        log("ОШИБКА: TELETHON_SESSION не задана!")
        status['running'] = False
        return
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("ОШИБКА: сессия не авторизована!")
        await client.disconnect()
        status['running'] = False
        return
    me = await client.get_me()
    log(f"Авторизован: {me.first_name} id={me.id}")
    log(f"РЕЖИМ: ГЛУБОКИЙ ПАРСИНГ — ВСЕ УЧАСТНИКИ (без фильтра 24ч)")
    log(f"aggressive=True, лимит 10мин/канал")
    log(f"Каналов: VN={TOTAL_VN} TH={TOTAL_TH} всего={TOTAL}")
    log("")

    vn_u, th_u = {}, {}

    log("=" * 60)
    log("ВЬЕТНАМ")
    log("=" * 60)
    for i, (cat, ch) in enumerate(vn_channels, 1):
        status['idx'] = i
        status['cur'] = f"VN [{i}/{TOTAL_VN}] @{ch}"
        log(f"\n[{i}/{TOTAL_VN}] @{ch}")
        for u in await do_channel(client, ch, cat):
            uid = u['user_id']
            if uid not in vn_u:
                vn_u[uid] = {
                    'user_id': uid,
                    'username': u['username'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'phone': u['phone'],
                    'last_seen': u['last_seen'],
                    'channels': [],
                }
            if ch not in vn_u[uid]['channels']:
                vn_u[uid]['channels'].append(ch)
            if u['last_seen'] in ('online', 'recently') and vn_u[uid]['last_seen'] not in ('online',):
                vn_u[uid]['last_seen'] = u['last_seen']
        status['vn'] = len(vn_u)
        if i % 3 == 0:
            save(vn_u, th_u)
            log(f"  [сохранено: VN={len(vn_u)} уникальных]")
        await asyncio.sleep(3)

    save(vn_u, th_u)
    log(f"\nВьетнам завершён: {len(vn_u)} уникальных пользователей")

    log("")
    log("=" * 60)
    log("ТАЙЛАНД")
    log("=" * 60)
    for i, (cat, ch) in enumerate(th_channels, 1):
        status['idx'] = TOTAL_VN + i
        status['cur'] = f"TH [{i}/{TOTAL_TH}] @{ch}"
        log(f"\n[{i}/{TOTAL_TH}] @{ch}")
        for u in await do_channel(client, ch, cat):
            uid = u['user_id']
            if uid not in th_u:
                th_u[uid] = {
                    'user_id': uid,
                    'username': u['username'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'phone': u['phone'],
                    'last_seen': u['last_seen'],
                    'channels': [],
                }
            if ch not in th_u[uid]['channels']:
                th_u[uid]['channels'].append(ch)
            if u['last_seen'] in ('online', 'recently') and th_u[uid]['last_seen'] not in ('online',):
                th_u[uid]['last_seen'] = u['last_seen']
        status['th'] = len(th_u)
        if i % 3 == 0:
            save(vn_u, th_u)
            log(f"  [сохранено: TH={len(th_u)} уникальных]")
        await asyncio.sleep(3)

    save(vn_u, th_u, 'complete')
    total = len(set(vn_u.keys()) | set(th_u.keys()))
    both = len(set(vn_u.keys()) & set(th_u.keys()))
    log("")
    log("=" * 60)
    log("ГОТОВО!")
    log(f"Вьетнам: {len(vn_u)} уникальных")
    log(f"Тайланд: {len(th_u)} уникальных")
    log(f"ВСЕГО уникальных: {total}")
    log(f"В обоих странах: {both}")
    log(f"Ошибок: {status['errors']}")
    log(f"Файл: {RESULT}")
    log("=" * 60)

    await client.disconnect()
    status['running'] = False
    status['done'] = True

def start():
    if status['running']:
        return "Уже работает!"
    threading.Thread(target=lambda: asyncio.new_event_loop().run_until_complete(run()), daemon=True).start()
    return "Глубокий сбор запущен! (ВСЕ участники, без фильтра 24ч)"

def get_st():
    if not status['running'] and not status['done']:
        return "Ожидание. Нажмите Запустить."
    s = "РАБОТАЕТ" if status['running'] else "ЗАВЕРШЁН"
    return (
        f"Статус: {s}\n"
        f"Прогресс: {status['idx']}/{TOTAL} каналов\n"
        f"Текущий: {status['cur']}\n"
        f"VN: {status['vn']} | TH: {status['th']}\n"
        f"Ошибок: {status['errors']}"
    )

def get_log():
    return "\n".join(status['log'][-100:]) or "Пусто"

def dl():
    return RESULT if os.path.exists(RESULT) else None

with gr.Blocks(title="TG Deep Collector") as demo:
    gr.Markdown(f"# Глубокий сбор базы TG — ВСЕ участники")
    gr.Markdown(f"**{TOTAL_VN}** VN + **{TOTAL_TH}** TH = **{TOTAL}** каналов | aggressive=True | без фильтра 24ч")
    with gr.Row():
        b1 = gr.Button("🚀 Запустить глубокий сбор", variant="primary")
        b2 = gr.Button("🔄 Обновить статус")
    st = gr.Textbox(label="Статус", lines=6, interactive=False)
    lg = gr.Textbox(label="Лог", lines=25, interactive=False)
    b3 = gr.Button("📥 Скачать JSON")
    fo = gr.File(label="Результат")
    b1.click(fn=start, outputs=st)
    b2.click(fn=get_st, outputs=st)
    b2.click(fn=get_log, outputs=lg)
    b3.click(fn=dl, outputs=fo)
    demo.load(fn=get_st, outputs=st)

demo.launch(server_name="0.0.0.0", server_port=7860)
