import pyautogui, pyaudio, audioop, threading, time, win32api, configparser, mss, mss.tools, cv2, numpy
import dearpygui.dearpygui as dpg
import random
import sys
import os

# Загрузка настроек
parser = configparser.ConfigParser()
parser.read('settings.ini')
debugmode = parser.getboolean('Settings', 'debug')
max_volume = parser.getint('Settings', 'volume_threshold')  # Исправлено: 'Volume_Threshold' на 'volume_threshold'
screen_area = parser.get('Settings', 'tracking_zone')
detection_threshold = parser.getfloat('Settings', 'detection_threshold')

screen_area = screen_area.strip('(')
screen_area = screen_area.strip(')')
cordies = screen_area.split(',')
screen_area = int(cordies[0]), int(cordies[1]), int(cordies[2]), int(cordies[3])

# Координаты для заброса
coords = []

# Громкость звука
total = 0

# Текущее состояние бота
STATE = "IDLE"

# Остановка потоков
stop_button = False

# Состояние кнопок мыши
state_left = win32api.GetKeyState(0x01)
state_right = win32api.GetKeyState(0x02)

# Счетчики
fish_count = 0
bait_counter = 0
food_timer = 0
fish_since_move = 0
move_threshold = random.randint(5, 7)

# Логгер для DearPyGui
logger_id = None

# Предзагрузка изображения поплавка
bobber_path = 'bobber.png'
if os.path.exists(bobber_path):
    bobber_img = cv2.imread(bobber_path)
    # Сохраняем предобработку как в оригинале, чтобы не сломать логику
    bobber_img = numpy.array(bobber_img, dtype=numpy.uint8)
    bobber_img = numpy.flip(bobber_img[:, :, :3], 2)
    bobber_img = cv2.cvtColor(bobber_img, cv2.COLOR_RGB2BGR)
else:
    bobber_img = None
    print("Error: bobber.png not found!")

##########################################################
# Функции бота
##########################################################

def check_volume():
    global total, STATE, max_volume, stop_button
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True, frames_per_buffer=1024)
    while True:
        if stop_button:
            break
        total = 0
        for i in range(2):
            data = stream.read(1024)
            reading = audioop.max(data, 2)
            total += reading
            if total > max_volume and STATE not in ["SOLVING", "DELAY", "CASTING"]:
                do_minigame()
    stream.stop_stream()
    stream.close()
    p.terminate()

def get_new_spot():
    return random.choice(coords)

def move_character():
    global fish_since_move, move_threshold
    log_info("Anti-Exhaustion: Moving character...")
    
    # Получаем разрешение экрана
    screen_width, screen_height = pyautogui.size()
    
    # Центр экрана
    center_x, center_y = screen_width // 2, screen_height // 2
    
    # Генерируем случайное смещение
    offset_x = random.randint(-200, 200)
    offset_y = random.randint(-200, 200)
    
    # Убедимся, что не кликаем совсем в центр (персонаж стоит там)
    if abs(offset_x) < 50: offset_x = 50 if offset_x >= 0 else -50
    if abs(offset_y) < 50: offset_y = 50 if offset_y >= 0 else -50

    target_x = center_x + offset_x
    target_y = center_y + offset_y
    
    # Двигаем мышь и кликаем ПКМ
    current_x, current_y = pyautogui.position()
    pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.2, 0.4))
    time.sleep(0.1)
    pyautogui.click(button='right')
    time.sleep(random.uniform(1.5, 2.5)) # Ждем пока добежит
    
    # Возвращаем мышь обратно (опционально, но удобно)
    # pyautogui.moveTo(current_x, current_y, duration=0.2)
    
    fish_since_move = 0
    move_threshold = random.randint(5, 7)
    log_info(f"Moved. Next move in {move_threshold} fish.")

def cast_hook():
    global STATE
    while True:
        if stop_button:
            break
        if STATE == "CASTING" or STATE == "STARTED":
            time.sleep(2.6)
            pyautogui.mouseUp()
            x, y = get_new_spot()
            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.2)
            pyautogui.mouseDown()
            time.sleep(random.uniform(0.6, 1.5))
            pyautogui.mouseUp()
            log_info(f"Casted towards: {x}, {y}")
            time.sleep(2.5)
            STATE = "CAST"
        elif STATE == "CAST":
            time.sleep(20)
            if STATE == "CAST":
                log_info("Seems to be stuck on cast. Recasting")
                STATE = "CASTING"
                pyautogui.mouseUp()

def do_minigame():
    global STATE, fish_count, bait_counter, fish_since_move
    # Проверяем, что мы не в процессе решения другой игры
    if STATE not in ["SOLVING", "DELAY"]:
        STATE = "SOLVING"
        log_info('Bite detected! Attempting to catch...')
        
        # 1. ПОДСЕЧКА
        pyautogui.mouseDown()
        time.sleep(0.1)
        pyautogui.mouseUp()
        
        # 2. ОЖИДАНИЕ ПОЯВЛЕНИЯ ШКАЛЫ
        time.sleep(0.6) 
        
        log_info('Searching for minigame bar...')
        
        # 3. ЦИКЛ РЕШЕНИЯ МИНИ-ИГРЫ
        start_time = time.time()
        fail_count = 0 # Счетчик потерянных кадров (Flicker protection)
        
        while True:
            # Прерываем, если прошло слишком много времени
            if time.time() - start_time > 15: 
                break
                
            valid, location, size = Detect_Bobber()
            
            if valid == "TRUE":
                fail_count = 0 # Сброс счетчика ошибок
                # Если поплавок левее центра — тянем
                if location[0] < size / 2:
                    pyautogui.mouseDown()
                else:
                    pyautogui.mouseUp()
            else:
                fail_count += 1
                if fail_count > 5: # Если потеряли поплавок на 5+ кадров подряд
                    log_info('Minigame ended.')
                    break
        
        # Завершение
        pyautogui.mouseUp()
        fish_count += 1
        bait_counter += 1
        fish_since_move += 1
        
        # Anti-Exhaustion check
        if fish_since_move >= move_threshold:
            move_character()
            
        STATE = "CASTING"

##########################################################
# Функции интерфейса
##########################################################

def generate_coords(sender, app_data):
    global coords, STATE, state_left
    amount_of_coords = dpg.get_value("Amount Of Spots")
    for n in range(int(amount_of_coords)):
        temp = []
        log_info(f'[spot:{n+1}] | Press Spacebar over the spot you want')
        time.sleep(1)
        while True:
            a = win32api.GetKeyState(0x20)
            if a != state_left:
                state_left = a
                if a < 0:
                    break
            time.sleep(0.001)
        x, y = pyautogui.position()
        temp.append(x)
        temp.append(y)
        coords.append(temp)
        log_info(f'Position {n+1} Saved. | {x}, {y}')

def Grab_Screen(sender, app_data):
    global screen_area
    state_left = win32api.GetKeyState(0x20)
    image_coords = []
    log_info('Please hold and drag space over tracking zone (top left to bottom right)')
    while True:
        a = win32api.GetKeyState(0x20)
        if a != state_left:
            state_left = a
            if a < 0:
                x, y = pyautogui.position()
                image_coords.append([x, y])
            else:
                x, y = pyautogui.position()
                image_coords.append([x, y])
                break
        time.sleep(0.001)
    start_point = image_coords[0]
    end_point = image_coords[1]
    screen_area = start_point[0], start_point[1], end_point[0], end_point[1]
    log_info(f'Updated tracking area to {screen_area}')

def Detect_Bobber():
    global bobber_img
    if bobber_img is None:
        return ["FALSE", (0, 0), 0]
        
    start_time = time.time()
    with mss.mss() as sct:
        base = numpy.array(sct.grab(screen_area))
        base = numpy.flip(base[:, :, :3], 2)
        base = cv2.cvtColor(base, cv2.COLOR_RGB2BGR)
        
        # Проверка размеров (Assertion Error protection)
        if bobber_img.shape[0] > base.shape[0] or bobber_img.shape[1] > base.shape[1]:
             return ["FALSE", (0, 0), base.shape[1]]
        
        result = cv2.matchTemplate(base, bobber_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val > 0.5:
            # print(f"Bobber Found! Match certainty: {max_val}")
            # print(f"{time.time() - start_time} seconds to calculate")
            return ["TRUE", max_loc, base.shape[1]]
        else:
            # print(f"Bobber not found. Match certainty: {max_val}")
            # print(f"{time.time() - start_time} seconds to calculate")
            return ["FALSE", max_loc, base.shape[1]]

def start(sender, app_data):
    global max_volume, stop_button, STATE
    STATE = "STARTING"
    stop_button = False
    max_volume = dpg.get_value("Set Volume Threshold")
    if len(coords) == 0:
        log_info('Please Select Fishing Coords first')
        return
    volume_manager = threading.Thread(target=check_volume)
    hook_manager = threading.Thread(target=cast_hook)
    volume_manager.start()
    log_info('Volume Scanner Started')
    hook_manager.start()
    log_info('Hook Manager Started')
    log_info('Bot Started')
    STATE = "STARTED"
    pyautogui.press("1")

def stop(sender, app_data):
    global stop_button, STATE
    STATE = "STOPPING"
    stop_button = True
    log_info('Stopping Hook Manager')
    log_info('Stopping Volume Scanner')
    pyautogui.mouseUp()
    STATE = "STOPPED"
    log_info('Stopped Bot')

def save_volume(sender, app_data):
    global max_volume
    max_volume = dpg.get_value("Set Volume Threshold")
    log_info(f'Max Volume Updated to: {max_volume}')

def save_threshold(sender, app_data):
    global detection_threshold
    detection_threshold = dpg.get_value("Set Detection Threshold")
    log_info(f'Detection Threshold Updated to: {detection_threshold}')

def Setup_title():
    global bait_counter
    while True:
        dpg.set_viewport_title(f"Fisherman | Status: {STATE} | Fish Hits: {fish_count} | Current Volume: {max_volume} \\ {total} | {STATE}")
        time.sleep(0.1)
        if bait_counter == 10:
            bait_counter = 0
            pyautogui.press("1")

def save_settings(sender, app_data):
    p = configparser.ConfigParser()
    p.read('settings.ini')
    p.set('Settings', 'volume_threshold', str(max_volume))
    p.set('Settings', 'tracking_zone', str(screen_area))
    p.set('Settings', 'detection_threshold', str(detection_threshold))
    with open('settings.ini', 'w') as f:
        p.write(f)
    log_info('Saved New Settings to settings.ini')

def log_info(message):
    global logger_id
def log_info(message):
    global logger_id
    if logger_id:
        dpg.add_text(message, parent=logger_id)
        # Исправлено: скроллим "log_window", а не logger_id (группу)
        dpg.set_y_scroll("log_window", -1.0)

##########################################################
# Инициализация DearPyGui
##########################################################

dpg.create_context()

with dpg.window(label="Fisherman Window", width=684, height=460):
    dpg.add_input_int(label="Amount Of Spots", default_value=1, min_value=0, max_value=10, tag="Amount Of Spots")
    dpg.add_input_int(label="Set Volume Threshold", default_value=max_volume, min_value=0, max_value=100000, callback=save_volume, tag="Set Volume Threshold")
    dpg.add_input_float(label="Set Detection Threshold", default_value=detection_threshold, min_value=0.1, max_value=1.0, callback=save_threshold, tag="Set Detection Threshold")
    dpg.add_spacing(count=3)
    dpg.add_button(label="Set Fishing Spots", callback=generate_coords, width=130)
    dpg.add_same_line()
    dpg.add_button(label="Set Tracking Zone", callback=Grab_Screen)
    dpg.add_spacing(count=5)
    dpg.add_button(label="Start Bot", callback=start)
    dpg.add_same_line()
    dpg.add_button(label="Stop Bot", callback=stop)
    dpg.add_same_line()
    dpg.add_button(label="Save Settings", callback=save_settings)
    dpg.add_spacing(count=5)
    
   # Создаем логгер
    # Мы даем этому окну тег "log_window", чтобы обращаться к нему позже
    with dpg.child_window(height=200, border=True, tag="log_window"):
        logger_id = dpg.add_group()
        dpg.add_text("Log:", parent=logger_id)

dpg.create_viewport(title='Fisherman', width=700, height=500, resizable=False)
dpg.setup_dearpygui()
dpg.show_viewport()

# Запуск потока обновления заголовка
threading.Thread(target=Setup_title, daemon=True).start()

log_info(f'Loaded Settings. Volume Threshold: {max_volume}, Tracking Zone: {screen_area}, Debug Mode: {debugmode}')

dpg.start_dearpygui()
dpg.destroy_context()