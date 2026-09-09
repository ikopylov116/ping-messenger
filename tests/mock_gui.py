"""
Вспомогательный модуль для мокания GUI-зависимостей.

Проект (ping.py, games.py) импортирует тяжёлые GUI-библиотеки на верхнем уровне:
  customtkinter, tkinter, PIL (Image, ImageTk, ImageGrab), plyer.

Эти библиотеки создают реальные окна и требуют графического дисплея,
что делает модульное тестирование невозможным в headless-окружении.

Этот модуль подменяет (mock-ает) все GUI-зависимости в sys.modules
до импорта целевых модулей, позволяя тестировать чистую бизнес-логику
(игровая логика, криптография, сетевые функции) без GUI.
"""
import sys
from unittest.mock import MagicMock


def _install_gui_mocks():
    """Устанавливает mock-объекты для всех GUI-библиотек в sys.modules."""
    # --- customtkinter (используется в games.py и ping.py) ---
    ctk = MagicMock()

    # CTkToplevel и другие классы должны быть реальными типами (type),
    # чтобы классы проекта могли от них наследоваться и использовать __new__.
    # Используем type() для создания лёгких классов-заглушек.
    ctk.CTkToplevel = type('CTkToplevel', (), {'__init__': lambda self, *a, **k: None})
    ctk.CTk = type('CTk', (), {'__init__': lambda self, *a, **k: None})
    ctk.CTkFont = type('CTkFont', (), {})
    ctk.CTkLabel = type('CTkLabel', (), {})
    ctk.CTkButton = type('CTkButton', (), {})
    ctk.CTkFrame = type('CTkFrame', (), {})
    ctk.CTkTabview = type('CTkTabview', (), {})
    ctk.CTkEntry = type('CTkEntry', (), {})
    ctk.CTkTextbox = type('CTkTextbox', (), {})
    ctk.CTkScrollableFrame = type('CTkScrollableFrame', (), {})
    ctk.set_appearance_mode = MagicMock()
    ctk.set_default_color_theme = MagicMock()
    sys.modules['customtkinter'] = ctk

    # --- tkinter (импортируется в ping.py) ---
    tk = MagicMock()
    tk.Canvas = MagicMock
    tk.Label = MagicMock
    sys.modules['tkinter'] = tk

    # --- tkinter.messagebox и tkinter.filedialog ---
    sys.modules['tkinter.messagebox'] = MagicMock()
    sys.modules['tkinter.filedialog'] = MagicMock()

    # --- tkinter.font ---
    tk_font = MagicMock()
    tk_font.Font = MagicMock
    sys.modules['tkinter.font'] = tk_font

    # --- PIL / pillow ---
    pil = MagicMock()
    pil.Image = MagicMock()
    pil.Image.Image = object
    pil.Image.Resampling = MagicMock()
    pil.Image.Resampling.LANCZOS = MagicMock()
    sys.modules['PIL'] = pil
    sys.modules['PIL.Image'] = pil.Image
    sys.modules['PIL.ImageTk'] = MagicMock()
    sys.modules['PIL.ImageGrab'] = MagicMock()

    # --- plyer (системные уведомления) ---
    notification = MagicMock()
    notification.notify = MagicMock()
    plyer = MagicMock()
    plyer.notification = notification
    sys.modules['plyer'] = plyer
    sys.modules['plyer.notification'] = notification


def _restore_gui():
    """Удаляет mock-модули из sys.modules (для очистки после тестов)."""
    for name in [
        'customtkinter', 'tkinter', 'tkinter.messagebox',
        'tkinter.filedialog', 'tkinter.font',
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageGrab',
        'plyer', 'plyer.notification',
    ]:
        sys.modules.pop(name, None)

