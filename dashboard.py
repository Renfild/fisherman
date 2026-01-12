"""
Игровой дашборд с метриками рыбалки
Professional gaming dashboard with real-time metrics
"""
import dearpygui.dearpygui as dpg
import time
import math
import json
import os
from typing import Optional, Dict, List
from metrics import FishingMetrics
from ui_theme import (COLORS, SIZES, FONTS, MASTERY_LEVELS, ACHIEVEMENTS, 
                      apply_theme_to_dpg, get_mastery_color, get_health_color,
                      interpolate_color, EMOJI)
from sounds import sound_manager


class GameDashboard:
    """Игровой дашборд с метриками и красивым UI"""
    
    def __init__(self, metrics: FishingMetrics, config_path: str = "config_ui.json"):
        self.metrics = metrics
        self.config = self._load_config(config_path)
        self.current_tab = "main"
        
        # Флаги для отслеживания достижений
        self.unlocked_achievements = set()
        self.last_mastery_level = 0
        
        # Анимация
        self.animation_time = 0
        self.pulse_phase = 0
        
        # Теги для элементов UI
        self.ui_tags = {
            'fish_count': 'fish_count_text',
            'fish_per_hour': 'fish_per_hour_text',
            'success_rate': 'success_rate_text',
            'avg_catch_time': 'avg_catch_time_text',
            'uptime': 'uptime_text',
            'downtime': 'downtime_text',
            'volume': 'volume_text',
            'estimated_value': 'value_text',
            'mastery_bar': 'mastery_progress_bar',
            'mastery_text': 'mastery_text',
            'mastery_exp': 'mastery_exp_text',
            'spectrum_plot': 'spectrum_plot',
            'main_tab': 'main_tab',
            'stats_tab': 'stats_tab',
            'achievements_tab': 'achievements_tab',
        }
        
    def _load_config(self, path: str) -> Dict:
        """Загрузить конфигурацию UI"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return self._default_config()
        
    def _default_config(self) -> Dict:
        """Конфигурация по умолчанию"""
        return {
            'dashboard': {'width': 1200, 'height': 800, 'refresh_rate': 0.1},
            'sounds': {'enabled': True},
            'animations': {'enabled': True},
        }
        
    def create_dashboard_window(self):
        """Создать главное окно дашборда"""
        width = self.config.get('dashboard', {}).get('width', 1200)
        height = self.config.get('dashboard', {}).get('height', 800)
        
        with dpg.window(label="🎣 Fisherman Dashboard", 
                       width=width, height=height, 
                       tag="dashboard_window", no_close=True):
            
            # Заголовок с логотипом
            self._create_header()
            
            dpg.add_separator()
            
            # Табы
            with dpg.tab_bar(tag="tab_bar"):
                with dpg.tab(label=f"{EMOJI['chart']} Main Dashboard", tag=self.ui_tags['main_tab']):
                    self._create_main_tab()
                    
                with dpg.tab(label=f"{EMOJI['up']} Statistics", tag=self.ui_tags['stats_tab']):
                    self._create_stats_tab()
                    
                with dpg.tab(label=f"{EMOJI['trophy']} Achievements", tag=self.ui_tags['achievements_tab']):
                    self._create_achievements_tab()
                    
    def _create_header(self):
        """Создать заголовок дашборда"""
        with dpg.group(horizontal=True):
            # Логотип и название
            with dpg.child_window(width=400, height=70, no_scrollbar=True):
                dpg.add_text(f"{EMOJI['hook']} FISHERMAN PRO", 
                           tag="header_title")
                dpg.add_text("Professional Fishing Dashboard v2.0", 
                           tag="header_subtitle")
                           
            dpg.add_spacer(width=20)
            
            # Быстрые метрики (маленькие виджеты справа)
            with dpg.group(horizontal=True):
                self._create_quick_stat(f"{EMOJI['fish']} Caught", 
                                       self.ui_tags['fish_count'], "0")
                self._create_quick_stat(f"{EMOJI['clock']} Uptime", 
                                       self.ui_tags['uptime'], "0:00:00")
                self._create_quick_stat(f"{EMOJI['coin']} Value", 
                                       self.ui_tags['estimated_value'], "0")
                                       
    def _create_quick_stat(self, label: str, tag: str, default: str):
        """Создать быстрый виджет статистики"""
        with dpg.child_window(width=150, height=70, no_scrollbar=True):
            dpg.add_text(label, color=COLORS['text_secondary'])
            dpg.add_text(default, tag=tag, color=COLORS['accent'])
            
    def _create_main_tab(self):
        """Создать главную вкладку с основными метриками"""
        with dpg.group():
            # Первая строка: Основные метрики
            with dpg.group(horizontal=True):
                self._create_metric_panel("Fish per Hour", 
                                         f"{EMOJI['fire']} 0.0", 
                                         self.ui_tags['fish_per_hour'],
                                         COLORS['primary'])
                                         
                self._create_metric_panel("Success Rate", 
                                         f"{EMOJI['star']} 0%", 
                                         self.ui_tags['success_rate'],
                                         COLORS['success'])
                                         
                self._create_metric_panel("Avg Catch Time", 
                                         f"{EMOJI['clock']} 0s", 
                                         self.ui_tags['avg_catch_time'],
                                         COLORS['info'])
                                         
            dpg.add_spacer(height=10)
            
            # Вторая строка: Uptime/Downtime и Volume
            with dpg.group(horizontal=True):
                # Uptime/Downtime панель
                with dpg.child_window(width=550, height=150):
                    dpg.add_text("⏱️ Session Time", color=COLORS['accent'])
                    dpg.add_separator()
                    
                    with dpg.group(horizontal=True):
                        with dpg.group():
                            dpg.add_text("Uptime:", color=COLORS['text_secondary'])
                            dpg.add_text("0:00:00", tag=self.ui_tags['uptime'], 
                                       color=COLORS['success'])
                        
                        dpg.add_spacer(width=50)
                        
                        with dpg.group():
                            dpg.add_text("Downtime:", color=COLORS['text_secondary'])
                            dpg.add_text("0:00:00", tag=self.ui_tags['downtime'], 
                                       color=COLORS['warning'])
                                       
                # Volume индикатор
                with dpg.child_window(width=550, height=150):
                    dpg.add_text(f"{EMOJI['volume']} Audio Level", color=COLORS['accent'])
                    dpg.add_separator()
                    dpg.add_text("Current: 0", tag=self.ui_tags['volume'], 
                               color=COLORS['primary'])
                    
            dpg.add_spacer(height=10)
            
            # Аудио спектр
            with dpg.child_window(height=220):
                dpg.add_text(f"{EMOJI['wave']} Audio Spectrum Visualization", 
                           color=COLORS['accent'])
                dpg.add_separator()
                
                # Создаем простой бар-график для спектра
                with dpg.plot(label="", height=160, width=-1, 
                            tag=self.ui_tags['spectrum_plot']):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Amplitude", tag="spectrum_y_axis")
                    
                    # Инициализируем данные спектра
                    x_data = list(range(32))
                    y_data = [0] * 32
                    dpg.add_bar_series(x_data, y_data, 
                                      label="Spectrum", 
                                      parent="spectrum_y_axis",
                                      tag="spectrum_series")
                                      
            dpg.add_spacer(height=10)
            
            # Прогресс мастерства
            self._create_mastery_panel()
            
    def _create_metric_panel(self, title: str, value: str, tag: str, color: tuple):
        """Создать панель метрики"""
        with dpg.child_window(width=360, height=120):
            dpg.add_text(title, color=COLORS['text_secondary'])
            dpg.add_separator()
            dpg.add_text(value, tag=tag, color=color)
            
    def _create_mastery_panel(self):
        """Создать панель прогресса мастерства"""
        with dpg.child_window(height=150):
            dpg.add_text(f"{EMOJI['crown']} Mastery Level", color=COLORS['accent'])
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_text("Новичок", tag=self.ui_tags['mastery_text'], 
                           color=COLORS['mastery_novice'])
                dpg.add_text("(0 / 100 EXP)", tag=self.ui_tags['mastery_exp'],
                           color=COLORS['text_secondary'])
                           
            dpg.add_spacer(height=5)
            
            # Progress bar
            dpg.add_progress_bar(default_value=0.0, 
                               tag=self.ui_tags['mastery_bar'],
                               width=-1, height=30)
                               
            dpg.add_spacer(height=5)
            dpg.add_text("Keep fishing to level up!", 
                       color=COLORS['text_secondary'])
                       
    def _create_stats_tab(self):
        """Создать вкладку со статистикой"""
        with dpg.child_window():
            dpg.add_text(f"{EMOJI['chart']} Detailed Statistics", 
                       color=COLORS['accent'])
            dpg.add_separator()
            
            # Таблица статистики
            with dpg.table(header_row=True, borders_innerH=True, 
                          borders_outerH=True, borders_innerV=True,
                          borders_outerV=True):
                dpg.add_table_column(label="Metric")
                dpg.add_table_column(label="Value")
                dpg.add_table_column(label="Description")
                
                # Строки статистики
                stats_rows = [
                    ("Total Catches", "total_catches_stat", "Total fish caught"),
                    ("Total Attempts", "total_attempts_stat", "Total fishing attempts"),
                    ("Total Failures", "total_failures_stat", "Failed attempts"),
                    ("Fish per Hour", "fph_stat", "Current catch rate"),
                    ("Success Rate", "success_stat", "Percentage of successful catches"),
                    ("Average Catch Time", "avg_time_stat", "Average time to catch"),
                    ("Total Uptime", "total_uptime_stat", "Total active fishing time"),
                    ("Total Downtime", "total_downtime_stat", "Total idle time"),
                    ("Estimated Value", "total_value_stat", "Total accumulated value"),
                    ("Mastery Level", "mastery_level_stat", "Current fishing mastery"),
                    ("Mastery EXP", "mastery_exp_stat", "Experience points"),
                ]
                
                for label, tag, desc in stats_rows:
                    with dpg.table_row():
                        dpg.add_text(label)
                        dpg.add_text("0", tag=tag, color=COLORS['primary'])
                        dpg.add_text(desc, color=COLORS['text_secondary'])
                        
    def _create_achievements_tab(self):
        """Создать вкладку с достижениями"""
        with dpg.child_window():
            dpg.add_text(f"{EMOJI['trophy']} Achievements & Badges", 
                       color=COLORS['accent'])
            dpg.add_separator()
            
            # Сетка достижений (3 в ряд)
            achievements_per_row = 3
            for i in range(0, len(ACHIEVEMENTS), achievements_per_row):
                with dpg.group(horizontal=True):
                    for j in range(achievements_per_row):
                        if i + j < len(ACHIEVEMENTS):
                            achievement = ACHIEVEMENTS[i + j]
                            self._create_achievement_badge(achievement)
                            
    def _create_achievement_badge(self, achievement: Dict):
        """Создать значок достижения"""
        is_unlocked = achievement['id'] in self.unlocked_achievements
        bg_color = COLORS['bg_light'] if is_unlocked else COLORS['bg_dark']
        text_color = COLORS['text_primary'] if is_unlocked else COLORS['text_disabled']
        
        with dpg.child_window(width=360, height=120):
            with dpg.group(horizontal=True):
                # Иконка
                dpg.add_text(achievement['icon'], color=text_color)
                
                dpg.add_spacer(width=10)
                
                # Название и описание
                with dpg.group():
                    dpg.add_text(achievement['name'], color=text_color)
                    dpg.add_text(achievement['description'], 
                               color=COLORS['text_secondary'])
                    
                    # Статус
                    if is_unlocked:
                        dpg.add_text(f"{EMOJI['check']} Unlocked!", 
                                   color=COLORS['success'])
                    else:
                        dpg.add_text(f"Progress: {achievement['requirement']}", 
                                   color=COLORS['text_disabled'])
                                   
    def update_dashboard(self):
        """Обновить все метрики дашборда"""
        if not dpg.is_dearpygui_running():
            return
            
        stats = self.metrics.get_stats_dict()
        
        # Обновляем анимацию
        self.animation_time += 0.016  # ~60 FPS
        self.pulse_phase = (math.sin(self.animation_time * 2) + 1) / 2
        
        # Обновляем быстрые метрики в заголовке
        self._update_text_safe(self.ui_tags['fish_count'], 
                              f"{stats['total_catches']}")
        self._update_text_safe(self.ui_tags['estimated_value'], 
                              f"{stats['estimated_value']}")
        
        # Обновляем основные метрики
        self._update_text_safe(self.ui_tags['fish_per_hour'], 
                              f"{EMOJI['fire']} {stats['fish_per_hour']:.1f}")
        self._update_text_safe(self.ui_tags['success_rate'], 
                              f"{EMOJI['star']} {stats['success_rate']:.1f}%")
        self._update_text_safe(self.ui_tags['avg_catch_time'], 
                              f"{EMOJI['clock']} {stats['average_catch_time']:.1f}s")
        
        # Обновляем uptime/downtime
        self._update_text_safe(self.ui_tags['uptime'], 
                              self._format_time(stats['uptime']))
        self._update_text_safe(self.ui_tags['downtime'], 
                              self._format_time(stats['downtime']))
        
        # Обновляем громкость
        self._update_text_safe(self.ui_tags['volume'], 
                              f"Current: {stats['current_volume']}")
        
        # Обновляем спектр
        self._update_spectrum(stats['audio_spectrum'])
        
        # Обновляем мастерство
        self._update_mastery(stats)
        
        # Обновляем статистику на вкладке Stats
        self._update_stats_tab(stats)
        
        # Проверяем достижения
        self._check_achievements(stats)
        
    def _update_text_safe(self, tag: str, value: str):
        """Безопасно обновить текст элемента"""
        try:
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, value)
        except Exception:
            pass
            
    def _update_spectrum(self, spectrum: List[float]):
        """Обновить визуализацию спектра"""
        try:
            if dpg.does_item_exist("spectrum_series"):
                x_data = list(range(len(spectrum)))
                dpg.set_value("spectrum_series", [x_data, spectrum])
        except Exception:
            pass
            
    def _update_mastery(self, stats: Dict):
        """Обновить панель мастерства"""
        level = stats['mastery_level']
        title = stats['mastery_title']
        progress = stats['mastery_progress']
        exp = stats['mastery_exp']
        
        # Получаем информацию о текущем и следующем уровне
        mastery_info = MASTERY_LEVELS.get(level, MASTERY_LEVELS[0])
        next_level_info = MASTERY_LEVELS.get(level + 1, MASTERY_LEVELS[3])
        
        # Обновляем текст
        self._update_text_safe(self.ui_tags['mastery_text'], 
                              f"{mastery_info['icon']} {title}")
        self._update_text_safe(self.ui_tags['mastery_exp'],
                              f"({exp} / {next_level_info['exp_required']} EXP)")
        
        # Обновляем прогресс бар
        try:
            if dpg.does_item_exist(self.ui_tags['mastery_bar']):
                dpg.set_value(self.ui_tags['mastery_bar'], progress)
        except Exception:
            pass
            
        # Проверяем повышение уровня
        if level > self.last_mastery_level:
            self.last_mastery_level = level
            sound_manager.play_level_up_sound()
            
    def _update_stats_tab(self, stats: Dict):
        """Обновить вкладку статистики"""
        updates = {
            'total_catches_stat': str(stats['total_catches']),
            'total_attempts_stat': str(stats['total_attempts']),
            'total_failures_stat': str(stats['total_failures']),
            'fph_stat': f"{stats['fish_per_hour']:.2f}",
            'success_stat': f"{stats['success_rate']:.2f}%",
            'avg_time_stat': f"{stats['average_catch_time']:.2f}s",
            'total_uptime_stat': self._format_time(stats['uptime']),
            'total_downtime_stat': self._format_time(stats['downtime']),
            'total_value_stat': str(stats['estimated_value']),
            'mastery_level_stat': stats['mastery_title'],
            'mastery_exp_stat': str(stats['mastery_exp']),
        }
        
        for tag, value in updates.items():
            self._update_text_safe(tag, value)
            
    def _check_achievements(self, stats: Dict):
        """Проверить и разблокировать достижения"""
        for achievement in ACHIEVEMENTS:
            if achievement['id'] in self.unlocked_achievements:
                continue
                
            unlocked = False
            
            if achievement['type'] == 'catches':
                unlocked = stats['total_catches'] >= achievement['requirement']
            elif achievement['type'] == 'uptime':
                unlocked = stats['uptime'] >= achievement['requirement']
            elif achievement['type'] == 'value':
                unlocked = stats['estimated_value'] >= achievement['requirement']
            elif achievement['type'] == 'success_rate':
                unlocked = stats['success_rate'] >= achievement['requirement']
            elif achievement['type'] == 'speed':
                unlocked = (stats['average_catch_time'] > 0 and 
                          stats['average_catch_time'] <= achievement['requirement'])
                          
            if unlocked:
                self.unlocked_achievements.add(achievement['id'])
                sound_manager.play_achievement_sound()
                print(f"🏆 Achievement Unlocked: {achievement['name']}")
                
    def _format_time(self, seconds: float) -> str:
        """Форматировать время в читаемый вид"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"


def create_dashboard(metrics: FishingMetrics) -> GameDashboard:
    """Создать и инициализировать дашборд"""
    dashboard = GameDashboard(metrics)
    
    # Применяем тему
    apply_theme_to_dpg(dpg)
    
    # Создаем окно
    dashboard.create_dashboard_window()
    
    return dashboard
