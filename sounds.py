"""
Управление звуковыми эффектами для игрового интерфейса
Sound effects management for game-like experience
"""
import threading
import time
from typing import Optional
import math

# Флаг для проверки доступности winsound
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False
    print("winsound not available - sound effects disabled")


class SoundManager:
    """Менеджер звуковых эффектов"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and WINSOUND_AVAILABLE
        self.lock = threading.Lock()
        self.current_thread = None
        
    def play_beep(self, frequency: int, duration: int):
        """Воспроизвести простой звук (только Windows)"""
        if not self.enabled or not WINSOUND_AVAILABLE:
            return
            
        def _play():
            try:
                winsound.Beep(frequency, duration)
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_catch_sound(self):
        """Звук успешного улова"""
        if not self.enabled:
            return
        # Восходящая мелодия: три ноты вверх
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    winsound.Beep(523, 100)  # C5
                    time.sleep(0.05)
                    winsound.Beep(659, 100)  # E5
                    time.sleep(0.05)
                    winsound.Beep(784, 150)  # G5
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_bite_sound(self):
        """Звук поклевки"""
        if not self.enabled:
            return
        # Короткий высокий звук
        self.play_beep(1500, 150)
        
    def play_achievement_sound(self):
        """Звук получения достижения"""
        if not self.enabled:
            return
        # Триумфальная мелодия
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    winsound.Beep(523, 120)  # C5
                    time.sleep(0.05)
                    winsound.Beep(659, 120)  # E5
                    time.sleep(0.05)
                    winsound.Beep(784, 120)  # G5
                    time.sleep(0.05)
                    winsound.Beep(1047, 200) # C6
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_level_up_sound(self):
        """Звук повышения уровня"""
        if not self.enabled:
            return
        # Мощная восходящая мелодия
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    winsound.Beep(392, 100)  # G4
                    time.sleep(0.03)
                    winsound.Beep(523, 100)  # C5
                    time.sleep(0.03)
                    winsound.Beep(659, 100)  # E5
                    time.sleep(0.03)
                    winsound.Beep(784, 100)  # G5
                    time.sleep(0.03)
                    winsound.Beep(1047, 250) # C6
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_error_sound(self):
        """Звук ошибки"""
        if not self.enabled:
            return
        # Нисходящая мелодия
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    winsound.Beep(784, 150)  # G5
                    time.sleep(0.05)
                    winsound.Beep(523, 200)  # C5
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_click_sound(self):
        """Звук клика по кнопке"""
        if not self.enabled:
            return
        # Короткий щелчок
        self.play_beep(800, 50)
        
    def play_notification_sound(self):
        """Звук уведомления"""
        if not self.enabled:
            return
        # Приятная двухтональная мелодия
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    winsound.Beep(1000, 100)
                    time.sleep(0.05)
                    winsound.Beep(1200, 100)
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def play_startup_sound(self):
        """Звук запуска"""
        if not self.enabled:
            return
        # Быстрая восходящая гамма
        def _play():
            try:
                if WINSOUND_AVAILABLE:
                    freqs = [262, 330, 392, 523, 659]  # C-E-G-C-E
                    for freq in freqs:
                        winsound.Beep(freq, 80)
                        time.sleep(0.02)
            except Exception as e:
                print(f"Sound error: {e}")
                
        threading.Thread(target=_play, daemon=True).start()
        
    def set_enabled(self, enabled: bool):
        """Включить/выключить звуки"""
        with self.lock:
            self.enabled = enabled and WINSOUND_AVAILABLE
            

# Глобальный экземпляр менеджера звуков
sound_manager = SoundManager()


# Простые функции для быстрого доступа
def play_catch():
    """Воспроизвести звук улова"""
    sound_manager.play_catch_sound()

def play_bite():
    """Воспроизвести звук поклевки"""
    sound_manager.play_bite_sound()

def play_achievement():
    """Воспроизвести звук достижения"""
    sound_manager.play_achievement_sound()

def play_level_up():
    """Воспроизвести звук повышения уровня"""
    sound_manager.play_level_up_sound()

def play_error():
    """Воспроизвести звук ошибки"""
    sound_manager.play_error_sound()

def play_click():
    """Воспроизвести звук клика"""
    sound_manager.play_click_sound()

def play_notification():
    """Воспроизвести звук уведомления"""
    sound_manager.play_notification_sound()

def play_startup():
    """Воспроизвести звук запуска"""
    sound_manager.play_startup_sound()
