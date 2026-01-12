"""
Темы оформления и стили для game-like интерфейса
Cyberpunk/Modern gaming theme with animations
"""

# Цветовая палитра Cyberpunk/Gaming
COLORS = {
    # Основные цвета
    'primary': (0, 255, 255, 255),      # Cyan
    'secondary': (255, 0, 255, 255),    # Magenta
    'accent': (255, 215, 0, 255),       # Gold
    'success': (0, 255, 100, 255),      # Bright Green
    'warning': (255, 165, 0, 255),      # Orange
    'error': (255, 50, 50, 255),        # Red
    'info': (100, 150, 255, 255),       # Blue
    
    # Фоновые цвета
    'bg_dark': (10, 10, 20, 255),       # Very Dark Blue
    'bg_medium': (20, 20, 40, 255),     # Dark Blue
    'bg_light': (30, 30, 60, 255),      # Medium Dark Blue
    'bg_panel': (25, 25, 45, 255),      # Panel Background
    
    # Текстовые цвета
    'text_primary': (255, 255, 255, 255),   # White
    'text_secondary': (180, 180, 200, 255), # Light Gray
    'text_disabled': (100, 100, 120, 255),  # Dark Gray
    
    # Градиенты (для имитации)
    'gradient_start': (0, 255, 255, 255),   # Cyan
    'gradient_end': (255, 0, 255, 255),     # Magenta
    
    # Специальные цвета
    'health_full': (0, 255, 100, 255),
    'health_medium': (255, 215, 0, 255),
    'health_low': (255, 50, 50, 255),
    
    # Уровни мастерства
    'mastery_novice': (150, 150, 150, 255),     # Gray - Новичок
    'mastery_skilled': (100, 150, 255, 255),    # Blue - Опытный
    'mastery_master': (255, 0, 255, 255),       # Magenta - Мастер
    'mastery_legend': (255, 215, 0, 255),       # Gold - Легенда
}

# Размеры и отступы
SIZES = {
    'widget_height': 60,
    'widget_spacing': 10,
    'panel_padding': 15,
    'button_height': 50,
    'button_width': 150,
    'header_height': 80,
    'chart_height': 200,
    'progress_bar_height': 30,
    'badge_size': 64,
}

# Шрифты и размеры текста
FONTS = {
    'title_size': 32,
    'header_size': 24,
    'body_size': 16,
    'small_size': 14,
    'tiny_size': 12,
}

# Анимации и эффекты
ANIMATIONS = {
    'pulse_speed': 2.0,         # Скорость пульсации (секунды)
    'fade_speed': 0.5,          # Скорость затухания
    'slide_speed': 0.3,         # Скорость выезда элементов
    'number_count_speed': 1.0,  # Скорость подсчета чисел
}

# Конфигурация уровней мастерства
MASTERY_LEVELS = {
    0: {
        'name': 'Новичок',
        'color': COLORS['mastery_novice'],
        'icon': '🎣',
        'exp_required': 100,
    },
    1: {
        'name': 'Опытный',
        'color': COLORS['mastery_skilled'],
        'icon': '⚓',
        'exp_required': 300,
    },
    2: {
        'name': 'Мастер',
        'color': COLORS['mastery_master'],
        'icon': '🔱',
        'exp_required': 700,
    },
    3: {
        'name': 'Легенда',
        'color': COLORS['mastery_legend'],
        'icon': '👑',
        'exp_required': 1000,
    },
}

# Достижения (badges)
ACHIEVEMENTS = [
    {
        'id': 'first_catch',
        'name': 'Первый улов',
        'description': 'Поймай свою первую рыбу',
        'icon': '🐟',
        'requirement': 1,
        'type': 'catches',
    },
    {
        'id': 'ten_catches',
        'name': 'Десяточка',
        'description': 'Поймай 10 рыб',
        'icon': '🎯',
        'requirement': 10,
        'type': 'catches',
    },
    {
        'id': 'fifty_catches',
        'name': 'Полсотни',
        'description': 'Поймай 50 рыб',
        'icon': '⭐',
        'requirement': 50,
        'type': 'catches',
    },
    {
        'id': 'hundred_catches',
        'name': 'Центурион',
        'description': 'Поймай 100 рыб',
        'icon': '💯',
        'requirement': 100,
        'type': 'catches',
    },
    {
        'id': 'perfect_ten',
        'name': 'Идеальная десятка',
        'description': '10 успешных уловов подряд',
        'icon': '✨',
        'requirement': 10,
        'type': 'streak',
    },
    {
        'id': 'speed_demon',
        'name': 'Демон скорости',
        'description': 'Поймай рыбу за 5 секунд',
        'icon': '⚡',
        'requirement': 5,
        'type': 'speed',
    },
    {
        'id': 'marathon',
        'name': 'Марафонец',
        'description': '1 час активной рыбалки',
        'icon': '🏃',
        'requirement': 3600,
        'type': 'uptime',
    },
    {
        'id': 'rich_fisher',
        'name': 'Богатый рыбак',
        'description': 'Накопи 10000 ценности',
        'icon': '💰',
        'requirement': 10000,
        'type': 'value',
    },
    {
        'id': 'high_success',
        'name': 'Мастер точности',
        'description': '90% успешных уловов',
        'icon': '🎖️',
        'requirement': 90,
        'type': 'success_rate',
    },
]

def get_mastery_color(level: int) -> tuple:
    """Получить цвет для уровня мастерства"""
    return MASTERY_LEVELS.get(level, MASTERY_LEVELS[0])['color']

def get_mastery_info(level: int) -> dict:
    """Получить информацию об уровне мастерства"""
    return MASTERY_LEVELS.get(level, MASTERY_LEVELS[0])

def interpolate_color(color1: tuple, color2: tuple, factor: float) -> tuple:
    """Интерполировать между двумя цветами"""
    factor = max(0.0, min(1.0, factor))
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    a = int(color1[3] + (color2[3] - color1[3]) * factor)
    return (r, g, b, a)

def get_health_color(percentage: float) -> tuple:
    """Получить цвет в зависимости от процента (как HP bar)"""
    if percentage > 66:
        return COLORS['health_full']
    elif percentage > 33:
        return COLORS['health_medium']
    else:
        return COLORS['health_low']

def apply_theme_to_dpg(dpg):
    """Применить тему к DearPyGui"""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Фоновые цвета
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, COLORS['bg_dark'], category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, COLORS['bg_panel'], category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, COLORS['bg_medium'], category=dpg.mvThemeCat_Core)
            
            # Текстовые цвета
            dpg.add_theme_color(dpg.mvThemeCol_Text, COLORS['text_primary'], category=dpg.mvThemeCat_Core)
            
            # Кнопки
            dpg.add_theme_color(dpg.mvThemeCol_Button, COLORS['bg_light'], category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLORS['primary'], category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, COLORS['secondary'], category=dpg.mvThemeCat_Core)
            
            # Границы
            dpg.add_theme_color(dpg.mvThemeCol_Border, COLORS['primary'], category=dpg.mvThemeCat_Core)
            
            # Стили
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 15, 15, category=dpg.mvThemeCat_Core)
            
    dpg.bind_theme(global_theme)
    return global_theme

# Emoji для различных состояний
EMOJI = {
    'fish': '🐟',
    'hook': '🎣',
    'star': '⭐',
    'fire': '🔥',
    'lightning': '⚡',
    'trophy': '🏆',
    'crown': '👑',
    'gem': '💎',
    'clock': '⏱️',
    'chart': '📊',
    'volume': '🔊',
    'mute': '🔇',
    'check': '✅',
    'cross': '❌',
    'up': '📈',
    'down': '📉',
    'coin': '💰',
    'anchor': '⚓',
    'trident': '🔱',
    'wave': '🌊',
}
