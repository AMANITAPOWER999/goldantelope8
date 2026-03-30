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
)
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError, FloodWaitError
)

API_ID = 32881984
API_HASH = 'd2588f09dfbc5103ef77ef21c07dbf8b'
SESSION = os.environ.get('TELETHON_SESSION', '')

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

status = {'running':False,'done':False,'vn':0,'th':0,'idx':0,'cur':'','log':[]}
RESULT = '/tmp/tg_users_database.json'

def log(m):
    t = datetime.now().strftime('%H:%M:%S')
    line = f"[{t}] {m}"
    status['log'].append(line)
    if len(status['log'])>500: status['log']=status['log'][-300:]
    print(line,flush=True)

def active24(s):
    if s is None: return False
    if isinstance(s,UserStatusOnline): return True
    if isinstance(s,UserStatusRecently): return True
    if isinstance(s,UserStatusOffline) and s.was_online:
        return s.was_online > datetime.now(timezone.utc)-timedelta(hours=24)
    return False

async def get_users(client,entity):
    users=[]; count=0
    async for u in client.iter_participants(entity,limit=10000):
        count+=1
        if u.bot: continue
        if not active24(u.status): continue
        users.append({'user_id':u.id,'username':u.username or ''})
    return users,count

async def do_channel(client,ch,cat):
    try:
        ent = await asyncio.wait_for(client.get_entity(ch),timeout=15)
        try:
            users,total = await asyncio.wait_for(get_users(client,ent),timeout=120)
            log(f"  @{ch} ({cat}) -> {total} всего, {len(users)} акт.")
            return users
        except asyncio.TimeoutError:
            log(f"  @{ch} — таймаут, пропуск"); return []
    except ChatAdminRequiredError: log(f"  @{ch} — нет доступа")
    except ChannelPrivateError: log(f"  @{ch} — приватный")
    except FloodWaitError as e:
        w=min(e.seconds,180); log(f"  @{ch} — FloodWait {e.seconds}с, жду {w}с")
        await asyncio.sleep(w+3); return await do_channel(client,ch,cat)
    except asyncio.TimeoutError: log(f"  @{ch} — таймаут entity")
    except Exception as e: log(f"  @{ch} — ошибка: {e}")
    return []

def save(vn,th,st='in_progress'):
    both=set(vn.keys())&set(th.keys())
    r={'collected_at':datetime.now(timezone.utc).isoformat(),'status':st,
       'stats':{'vn':len(vn),'th':len(th),'both':len(both)},
       'vietnam':list(vn.values()),'thailand':list(th.values())}
    with open(RESULT,'w') as f: json.dump(r,f,ensure_ascii=False,indent=2)

async def run():
    status.update(running=True,done=False,log=[],vn=0,th=0,idx=0)
    if not SESSION: log("ОШИБКА: TELETHON_SESSION не задана!"); status['running']=False; return
    client=TelegramClient(StringSession(SESSION),API_ID,API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("ОШИБКА: сессия не авторизована!"); await client.disconnect(); status['running']=False; return
    me=await client.get_me(); log(f"Авторизован: {me.first_name} id={me.id}")
    log(f"Каналов: VN={TOTAL_VN} TH={TOTAL_TH} всего={TOTAL}\n")
    vn_u,th_u={},{}
    log("="*40+" ВЬЕТНАМ "+"="*40)
    for i,(cat,ch) in enumerate(vn_channels,1):
        status['idx']=i; status['cur']=f"VN @{ch}"
        log(f"[{i}/{TOTAL_VN}] @{ch}")
        for u in await do_channel(client,ch,cat):
            uid=u['user_id']
            if uid not in vn_u: vn_u[uid]={'user_id':uid,'username':u['username'],'channels':[]}
            if ch not in vn_u[uid]['channels']: vn_u[uid]['channels'].append(ch)
        status['vn']=len(vn_u)
        if i%5==0: save(vn_u,th_u); log(f"  [сохранено VN={len(vn_u)}]")
        await asyncio.sleep(2)
    save(vn_u,th_u); log(f"\nВьетнам: {len(vn_u)} уникальных\n")
    log("="*40+" ТАЙЛАНД "+"="*40)
    for i,(cat,ch) in enumerate(th_channels,1):
        status['idx']=TOTAL_VN+i; status['cur']=f"TH @{ch}"
        log(f"[{i}/{TOTAL_TH}] @{ch}")
        for u in await do_channel(client,ch,cat):
            uid=u['user_id']
            if uid not in th_u: th_u[uid]={'user_id':uid,'username':u['username'],'channels':[]}
            if ch not in th_u[uid]['channels']: th_u[uid]['channels'].append(ch)
        status['th']=len(th_u)
        if i%5==0: save(vn_u,th_u); log(f"  [сохранено TH={len(th_u)}]")
        await asyncio.sleep(2)
    save(vn_u,th_u,'complete')
    both=set(vn_u.keys())&set(th_u.keys())
    log(f"\nГОТОВО! VN={len(vn_u)} TH={len(th_u)} в обоих={len(both)}")
    await client.disconnect(); status['running']=False; status['done']=True

def start():
    if status['running']: return "Уже работает!"
    threading.Thread(target=lambda:asyncio.new_event_loop().run_until_complete(run()),daemon=True).start()
    return "Сбор запущен!"

def get_status():
    if not status['running'] and not status['done']: return "Ожидание. Нажмите Запустить."
    s="РАБОТАЕТ" if status['running'] else "ЗАВЕРШЁН"
    return f"Статус: {s}\nПрогресс: {status['idx']}/{TOTAL}\nТекущий: {status['cur']}\nVN: {status['vn']} | TH: {status['th']}"

def get_log(): return "\n".join(status['log'][-80:]) or "Пусто"

def dl():
    if os.path.exists(RESULT): return RESULT
    return None

with gr.Blocks(title="TG Collector") as demo:
    gr.Markdown(f"# Сбор базы TG ({TOTAL_VN} VN + {TOTAL_TH} TH = {TOTAL})")
    with gr.Row():
        b1=gr.Button("Запустить",variant="primary"); b2=gr.Button("Обновить статус")
    st=gr.Textbox(label="Статус",lines=5,interactive=False)
    lg=gr.Textbox(label="Лог",lines=20,interactive=False)
    b3=gr.Button("Скачать JSON"); fo=gr.File(label="Результат")
    b1.click(fn=start,outputs=st); b2.click(fn=get_status,outputs=st); b2.click(fn=get_log,outputs=lg)
    b3.click(fn=dl,outputs=fo); demo.load(fn=get_status,outputs=st)

demo.launch(server_name="0.0.0.0",server_port=7860)
