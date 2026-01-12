"""
Система сбора и расчета метрик для рыболовного бота
Tracking fishing metrics: catches, success rate, uptime, etc.
"""
import time
from collections import deque
from typing import Optional, Dict, List
import threading


class FishingMetrics:
    """Класс для отслеживания метрик рыбалки"""
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Основные счетчики
        self.total_catches = 0
        self.total_attempts = 0
        self.total_failures = 0
        
        # Временные метрики
        self.start_time = time.time()
        self.last_catch_time = None
        self.active_time = 0  # Время активной работы
        self.idle_time = 0     # Время простоя
        self.last_state_change = time.time()
        self.is_active = False
        
        # История уловов (для расчета рыб/час)
        self.catch_history = deque(maxlen=100)  # Последние 100 уловов
        
        # История времени ловли (для среднего времени)
        self.catch_times = deque(maxlen=50)  # Последние 50 времен ловли
        
        # Текущая сессия
        self.session_start = None
        self.current_attempt_start = None
        
        # Аудио данные для визуализации спектра
        self.current_volume = 0
        self.volume_history = deque(maxlen=100)
        self.audio_spectrum = [0] * 32  # 32 бара для спектра
        
        # Уровень мастерства
        self.mastery_level = 0
        self.mastery_exp = 0
        
        # Предполагаемая ценность улова (условные единицы)
        self.estimated_value = 0
        self.value_per_fish = 100  # Базовая ценность одной рыбы
        
    def start_session(self):
        """Начать новую сессию"""
        with self.lock:
            self.session_start = time.time()
            self.is_active = True
            self.last_state_change = time.time()
            
    def stop_session(self):
        """Остановить текущую сессию"""
        with self.lock:
            if self.is_active and self.last_state_change:
                self.active_time += time.time() - self.last_state_change
            self.is_active = False
            
    def start_attempt(self):
        """Начать попытку поймать рыбу"""
        with self.lock:
            self.current_attempt_start = time.time()
            self.total_attempts += 1
            
    def record_catch(self, success: bool = True):
        """Записать результат попытки ловли"""
        with self.lock:
            catch_time = time.time()
            
            if success:
                self.total_catches += 1
                self.last_catch_time = catch_time
                self.catch_history.append(catch_time)
                
                # Записать время ловли
                if self.current_attempt_start:
                    duration = catch_time - self.current_attempt_start
                    self.catch_times.append(duration)
                    
                # Увеличить опыт мастерства
                self.mastery_exp += 10
                self._update_mastery_level()
                
                # Увеличить предполагаемую ценность
                self.estimated_value += self.value_per_fish
            else:
                self.total_failures += 1
                
            self.current_attempt_start = None
            
    def update_volume(self, volume: int):
        """Обновить текущий уровень громкости"""
        with self.lock:
            self.current_volume = volume
            self.volume_history.append(volume)
            
    def update_audio_spectrum(self, spectrum: List[float]):
        """Обновить данные аудио спектра"""
        with self.lock:
            if len(spectrum) == len(self.audio_spectrum):
                self.audio_spectrum = spectrum[:]
            else:
                # Если размер не совпадает, интерполируем
                self.audio_spectrum = self._interpolate_spectrum(spectrum)
                
    def _interpolate_spectrum(self, spectrum: List[float]) -> List[float]:
        """Интерполировать спектр до нужного размера"""
        if not spectrum:
            return [0] * 32
        target_len = 32
        result = []
        for i in range(target_len):
            idx = int(i * len(spectrum) / target_len)
            result.append(spectrum[idx])
        return result
        
    def _update_mastery_level(self):
        """Обновить уровень мастерства на основе опыта"""
        # Уровни: 0-99: Новичок, 100-299: Опытный, 300-699: Мастер, 700+: Легенда
        if self.mastery_exp < 100:
            self.mastery_level = 0  # Новичок
        elif self.mastery_exp < 300:
            self.mastery_level = 1  # Опытный
        elif self.mastery_exp < 700:
            self.mastery_level = 2  # Мастер
        else:
            self.mastery_level = 3  # Легенда
            
    def get_mastery_title(self) -> str:
        """Получить название уровня мастерства"""
        titles = ["Новичок", "Опытный", "Мастер", "Легенда"]
        return titles[self.mastery_level]
        
    def get_mastery_progress(self) -> float:
        """Получить прогресс до следующего уровня (0-1)"""
        thresholds = [0, 100, 300, 700, 1000]
        current_threshold = thresholds[self.mastery_level]
        next_threshold = thresholds[min(self.mastery_level + 1, len(thresholds) - 1)]
        
        if self.mastery_level >= 3:
            return 1.0  # Максимальный уровень
            
        progress = (self.mastery_exp - current_threshold) / (next_threshold - current_threshold)
        return max(0.0, min(1.0, progress))
        
    def get_fish_per_hour(self) -> float:
        """Рассчитать рыб в час"""
        with self.lock:
            if len(self.catch_history) < 2:
                return 0.0
                
            # Берем последние уловы за определенное время
            now = time.time()
            recent_catches = [t for t in self.catch_history if now - t < 3600]  # За последний час
            
            if len(recent_catches) < 2:
                # Если уловов мало, экстраполируем
                if self.catch_history:
                    time_span = now - self.catch_history[0]
                    if time_span > 0:
                        return (len(self.catch_history) / time_span) * 3600
                return 0.0
            
            time_span = now - recent_catches[0]
            if time_span > 0:
                return (len(recent_catches) / time_span) * 3600
            return 0.0
            
    def get_success_rate(self) -> float:
        """Получить процент успешных попыток"""
        with self.lock:
            if self.total_attempts == 0:
                return 0.0
            return (self.total_catches / self.total_attempts) * 100
            
    def get_average_catch_time(self) -> float:
        """Получить среднее время ловли в секундах"""
        with self.lock:
            if not self.catch_times:
                return 0.0
            return sum(self.catch_times) / len(self.catch_times)
            
    def get_uptime(self) -> float:
        """Получить время активной работы в секундах"""
        with self.lock:
            uptime = self.active_time
            if self.is_active and self.last_state_change:
                uptime += time.time() - self.last_state_change
            return uptime
            
    def get_total_time(self) -> float:
        """Получить общее время с начала сессии"""
        with self.lock:
            if self.session_start:
                return time.time() - self.session_start
            return 0.0
            
    def get_downtime(self) -> float:
        """Получить время простоя"""
        return self.get_total_time() - self.get_uptime()
        
    def get_stats_dict(self) -> Dict:
        """Получить все статистики в виде словаря"""
        with self.lock:
            return {
                'total_catches': self.total_catches,
                'total_attempts': self.total_attempts,
                'total_failures': self.total_failures,
                'fish_per_hour': self.get_fish_per_hour(),
                'success_rate': self.get_success_rate(),
                'average_catch_time': self.get_average_catch_time(),
                'uptime': self.get_uptime(),
                'downtime': self.get_downtime(),
                'total_time': self.get_total_time(),
                'current_volume': self.current_volume,
                'audio_spectrum': self.audio_spectrum[:],
                'mastery_level': self.mastery_level,
                'mastery_title': self.get_mastery_title(),
                'mastery_progress': self.get_mastery_progress(),
                'mastery_exp': self.mastery_exp,
                'estimated_value': self.estimated_value,
            }


# Глобальный экземпляр метрик
metrics = FishingMetrics()
