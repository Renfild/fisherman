import pyautogui, pyaudio, audioop, threading, time, win32api, configparser, mss, cv2, numpy, os, random
import dearpygui.dearpygui as dpg

# Gaming Dashboard imports
try:
    from metrics import metrics as fishing_metrics
    from dashboard import create_dashboard
    from sounds import sound_manager
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    print(f"Dashboard not available: {e}")
    DASHBOARD_AVAILABLE = False
    fishing_metrics = None
    sound_manager = None

# Настройки стабильности
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
config_file = 'settings.ini'
parser = configparser.ConfigParser()

def save_all_settings():
    parser['Settings'] = {
        'volume_threshold': str(dpg.get_value("vol_input")),
        'detection_threshold': str(dpg.get_value("det_input")),
        'coords': str(coords),
        'bait_step1': str(bait_step1),
        'bait_step2': str(bait_step2),
        'move_spot': str(move_spot),
        'screen_area': str(screen_area)
    }
    with open(config_file, 'w') as f:
        parser.write(f)
    log_info("All Settings Saved!")

def load_all_settings():
    global coords, bait_step1, bait_step2, move_spot, screen_area
    if os.path.exists(config_file):
        try:
            parser.read(config_file)
            s = parser['Settings']
            dpg.set_value("vol_input", int(s.get('volume_threshold', 5000)))
            dpg.set_value("det_input", float(s.get('detection_threshold', 0.5)))
            coords[:] = eval(s.get('coords', '[]'))
            bait_step1 = eval(s.get('bait_step1', 'None'))
            bait_step2 = eval(s.get('bait_step2', 'None'))
            move_spot = eval(s.get('move_spot', 'None'))
            screen_area.update(eval(s.get('screen_area', '{}')))
            log_info("Settings Loaded!")
        except Exception as e:
            log_info(f"Load error: {e}")

# Состояние
STATE = "IDLE"
stop_button = False
total_vol, fish_count, ignore_audio_until = 0, 0, 0
coords, bait_step1, bait_step2, move_spot = [], None, None, None
screen_area = {"left": 0, "top": 0, "width": 400, "height": 100}
bobber_img = cv2.imread('bobber.png') if os.path.exists('bobber.png') else None

# Dashboard
show_dashboard = False
dashboard_instance = None

def log_info(msg):
    if dpg.is_dearpygui_running():
        dpg.add_text(f"[{time.strftime('%H:%M:%S')}] {msg}", parent="log_group")
        dpg.set_y_scroll("log_window", -1.0)

def get_point():
    while win32api.GetKeyState(0x20) >= 0: time.sleep(0.01)
    p = pyautogui.position()
    while win32api.GetKeyState(0x20) < 0: time.sleep(0.01)
    return (p.x, p.y)

# ==========================================
# ЛОГИКА МИНИ-ИГРЫ
# ==========================================

def Detect_Bobber():
    global bobber_img, screen_area
    if bobber_img is None: return "ERROR", (0, 0), 0
    try:
        with mss.mss() as sct:
            monitor = {"top": int(screen_area["top"]), "left": int(screen_area["left"]), 
                       "width": int(screen_area["width"]), "height": int(screen_area["height"])}
            img = numpy.array(sct.grab(monitor))
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            res = cv2.matchTemplate(img, bobber_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > dpg.get_value("det_input"):
                return "TRUE", max_loc, monitor["width"]
    except: return "FALSE", (0, 0), 0
    return "FALSE", (0, 0), 0

def mini_game_logic():
    log_info("Mini-game started...")
    if DASHBOARD_AVAILABLE and fishing_metrics:
        fishing_metrics.start_attempt()
    
    start_time = time.time()
    last_seen = time.time()
    
    while time.time() - start_time < 16 and not stop_button:
        status, loc, width = Detect_Bobber()
        
        if status == "TRUE":
            last_seen = time.time() # Обновляем время последнего обнаружения
            if loc[0] < (width / 2): pyautogui.mouseDown()
            else: pyautogui.mouseUp()
        else:
            # Если поплавок не виден более 3 секунд — это ошибка, перезапускаем
            if time.time() - last_seen > 3.0:
                log_info("LOST BOBBER! Resetting cycle...")
                if DASHBOARD_AVAILABLE and fishing_metrics:
                    fishing_metrics.record_catch(success=False)
                break
        time.sleep(0.01)
        
    pyautogui.mouseUp()
    log_info("Restarting cast...")

# ==========================================
# ОСНОВНЫЕ ПОТОКИ
# ==========================================

def press_key_safe(key, duration=5):
    pyautogui.keyDown(key); time.sleep(duration); pyautogui.keyUp(key)

def apply_bait():
    if not bait_step1 or not bait_step2: return
    pyautogui.click(pyautogui.size().width//2, pyautogui.size().height//2)
    time.sleep(0.5); press_key_safe('i'); time.sleep(1.5)
    pyautogui.click(bait_step1[0], bait_step1[1]); time.sleep(0.8)
    pyautogui.click(bait_step2[0], bait_step2[1]); time.sleep(5.5)
    press_key_safe('i'); time.sleep(1.0)

def action_loop():
    global STATE, ignore_audio_until
    n_bait, n_food, n_move = 0, 0, time.time() + 300
    while not stop_button:
        if STATE in ["STARTED", "CASTING"]:
            if time.time() > n_move and move_spot:
                pyautogui.click(move_spot[0], move_spot[1], button='right')
                n_move = time.time() + 300
            if time.time() > n_food:
                press_key_safe('2'); n_food = time.time() + 1800
            if time.time() > n_bait and bait_step1:
                apply_bait(); n_bait = time.time() + 600
            if coords:
                x, y = random.choice(coords)
                pyautogui.moveTo(x, y, duration=0.4)
                pyautogui.mouseDown(); time.sleep(random.uniform(0.8, 1.2)); pyautogui.mouseUp()
                ignore_audio_until = time.time() + 3.0; STATE = "WAITING"
        time.sleep(0.1)

def audio_loop():
    global total_vol, STATE, fish_count
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True, frames_per_buffer=1024)
    while not stop_button:
        if STATE != "WAITING" or time.time() < ignore_audio_until:
            if stream.get_read_available() > 0: stream.read(stream.get_read_available(), False)
            time.sleep(0.05); continue
        try:
            data = stream.read(1024, False)
            vol = audioop.max(data, 2); total_vol = vol
            
            # Update metrics
            if DASHBOARD_AVAILABLE and fishing_metrics:
                fishing_metrics.update_volume(vol)
            
            if vol > dpg.get_value("vol_input"):
                time.sleep(0.5); STATE = "SOLVING"
                
                # Play bite sound
                if DASHBOARD_AVAILABLE and sound_manager:
                    sound_manager.play_bite_sound()
                
                pyautogui.click(); time.sleep(0.3)
                mini_game_logic()
                fish_count += 1
                
                # Record successful catch
                if DASHBOARD_AVAILABLE and fishing_metrics:
                    fishing_metrics.record_catch(success=True)
                    if sound_manager:
                        sound_manager.play_catch_sound()
                
                STATE = "CASTING"
        except: pass
    stream.stop_stream(); p.terminate()

# ==========================================
# DASHBOARD FUNCTIONS
# ==========================================

def toggle_dashboard():
    """Переключить отображение дашборда"""
    global show_dashboard, dashboard_instance
    show_dashboard = not show_dashboard
    
    if show_dashboard and DASHBOARD_AVAILABLE:
        if dashboard_instance is None:
            dashboard_instance = create_dashboard(fishing_metrics)
            if sound_manager:
                sound_manager.play_startup_sound()
        log_info("Dashboard ENABLED")
    else:
        log_info("Dashboard DISABLED")

def start_bot_with_metrics():
    """Запустить бота с отслеживанием метрик"""
    global STATE, stop_button
    STATE = "STARTED"
    stop_button = False
    
    if DASHBOARD_AVAILABLE and fishing_metrics:
        fishing_metrics.start_session()
    
    threading.Thread(target=audio_loop, daemon=True).start()
    threading.Thread(target=action_loop, daemon=True).start()
    
    log_info("Bot STARTED with metrics tracking")

def stop_bot_with_metrics():
    """Остановить бота"""
    global stop_button, STATE
    stop_button = True
    STATE = "IDLE"
    
    if DASHBOARD_AVAILABLE and fishing_metrics:
        fishing_metrics.stop_session()
    
    log_info("Bot STOPPED")

# ==========================================
# ИНТЕРФЕЙС
# ==========================================

dpg.create_context()
with dpg.window(label="Albion Fisher v2.0 by xietoru", width=580, height=620):
    with dpg.group(horizontal=True):
        dpg.add_button(label="LOAD ALL", callback=load_all_settings, width=150)
        dpg.add_button(label="SAVE ALL", callback=save_all_settings, width=150)
    
    dpg.add_separator()
    dpg.add_button(label="1. Add Fishing Spot (Space)", callback=lambda: coords.append(get_point()) or log_info("Spot OK"), width=250)
    
    # НОВЫЙ ВЫБОР ЗОНЫ (ОДИН РАЗ СВЕРХУ-ВНИЗ)
    def set_zone_logic():
        log_info("STEP 1: Hover TOP-LEFT + SPACE")
        p1 = get_point()
        log_info("STEP 2: Hover BOTTOM-RIGHT + SPACE")
        p2 = get_point()
        globals().update(screen_area={
            "left": min(p1[0], p2[0]), "top": min(p1[1], p2[1]),
            "width": abs(p2[0] - p1[0]), "height": abs(p2[1] - p1[1])
        })
        log_info("Zone Set Success!")

    dpg.add_button(label="2. Set Tracking Zone (Space)", callback=lambda: threading.Thread(target=set_zone_logic).start(), width=250)
    dpg.add_button(label="3. Setup Bait (Inv + Use)", callback=lambda: threading.Thread(target=lambda: (log_info("Bait+Space"), globals().update(bait_step1=get_point()), log_info("Use+Space"), globals().update(bait_step2=get_point()))).start(), width=250)
    dpg.add_button(label="4. Set Move Point (Space)", callback=lambda: threading.Thread(target=lambda: globals().update(move_spot=get_point())).start(), width=250)
    
    dpg.add_separator()
    
    # Dashboard toggle
    if DASHBOARD_AVAILABLE:
        with dpg.group(horizontal=True):
            dpg.add_button(label="🎮 SHOW DASHBOARD", callback=toggle_dashboard, width=250, height=40)
            dpg.add_text("Gaming metrics & stats!", color=(0, 255, 255, 255))
        dpg.add_separator()
    
    dpg.add_input_int(label="Volume Threshold", default_value=5000, tag="vol_input")
    dpg.add_input_float(label="Detection Sens", default_value=0.5, tag="det_input")
    
    with dpg.group(horizontal=True):
        dpg.add_button(label="START", callback=start_bot_with_metrics, width=120, height=40)
        dpg.add_button(label="STOP", callback=stop_bot_with_metrics, width=120, height=40)

    with dpg.child_window(tag="log_window", height=180):
        dpg.add_group(tag="log_group")

dpg.create_viewport(title='Fisherman v13.0', width=600, height=650)
dpg.setup_dearpygui(); dpg.show_viewport()
while dpg.is_dearpygui_running():
    dpg.set_viewport_title(f"Fisherman v13.0 | Vol: {total_vol} | Fish: {fish_count} | {STATE}")
    
    # Update dashboard if visible
    if show_dashboard and dashboard_instance and DASHBOARD_AVAILABLE:
        dashboard_instance.update_dashboard()
    
    dpg.render_dearpygui_frame()
dpg.destroy_context()