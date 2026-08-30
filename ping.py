import socket, threading, json, os, tkinter as tk, customtkinter as ctk
from tkinter import messagebox, filedialog, font as tkfont
import base64, hashlib, secrets, struct, io, urllib.request
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet
from PIL import Image, ImageTk, ImageGrab

# Импорт игры (только крестики-нолики)
from games import TicTacToeWindow

# Для уведомлений
from plyer import notification

# ---------- Константы ----------
CONFIG = {"host":"0.0.0.0","data_file":"user_data.json","theme":"blue","appearance":"dark"}
START_PORT, PORT_RANGE, MAX_IMG_W = 55555, 20, 300

# ---------- Вспомогательные функции ----------
def find_free_port(start=START_PORT, max_attempts=PORT_RANGE):
    for port in range(start, start+max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError: continue
    raise RuntimeError("Нет свободного порта")

def get_public_ip():
    try:
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as r:
            return r.read().decode()
    except: return None

def get_all_ips():
    ips = []
    try:
        for addr in socket.getaddrinfo(socket.gethostname(), None):
            ip = addr[4][0]
            if ip not in ips and ip != '127.0.0.1' and not ip.startswith('127.'):
                ips.append(ip)
    except: pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8',80))
            ip = s.getsockname()[0]; s.close()
            if ip != '127.0.0.1': ips.append(ip)
        except: pass
    if not ips: ips.append('127.0.0.1')
    return ips

# ---------- Палитра эмодзи ----------
class EmojiPicker(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Палитра эмодзи")
        self.geometry("700x550")
        self.minsize(600,400)
        self.transient(parent); self.grab_set()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        main = ctk.CTkFrame(self); main.pack(fill="both", expand=True, padx=10, pady=10)
        tabs = ctk.CTkTabview(main, width=660, height=450)
        tabs.pack(fill="both", expand=True)
        categories = {
            "Смайлы": [
                "😀","😁","😂","🤣","😃","😄","😅","😆","😉","😊",
                "😋","😎","😍","🥰","😘","😗","😙","😚","☺️","🙂",
                "🤗","🤩","🤔","🤨","😐","😑","😶","🙄","😏","😣",
                "😥","😮","🤐","😯","😪","😫","😴","😌","😛","😜",
                "😝","🤤","😒","😓","😔","😕","🙃","🤑","😲","☹️",
                "🙁","😖","😞","😟","😤","😢","😭","😦","😧","😨",
                "😩","🤯","😬","😰","😱","🥵","🥶","😳","🤪","😵",
                "😡","😠","🤬","😷","🤒","🤕","🤢","🤮","🥴","😇",
                "🤠","🤡","🥳","🥺","🤥","🤫","🤭","🧐","🤓","😈"
            ],
            "Жесты": [
                "👋","🤚","🖐️","✋","🖖","👌","🤌","🤞","🤟","🤘",
                "🤙","👈","👉","👆","🖕","👇","☝️","👍","👎","✊",
                "👊","🤛","🤜","👏","🙌","👐","🤲","🤝","🙏","✍️",
                "💅","🤳","💪","🦾","🦵","🦶","👂","🦻","👃","🧠",
                "🦷","🦴","👀","👁️","👅","👄","💋","🩸"
            ],
            "Еда": [
                "🍏","🍎","🍐","🍊","🍋","🍌","🍉","🍇","🍓","🫐",
                "🍈","🍒","🍑","🥭","🍍","🥥","🥝","🍅","🍆","🥑",
                "🫑","🌽","🥕","🥒","🥬","🥦","🧄","🧅","🍄","🥜",
                "🌰","🍞","🥐","🥖","🫓","🥨","🥯","🥞","🧇","🧀",
                "🍖","🍗","🥩","🥓","🍔","🍟","🍕","🌭","🥪","🌮",
                "🌯","🫔","🥙","🧆","🥚","🍳","🥘","🍲","🫕","🥣",
                "🥗","🍿","🧈","🧂","🥫","🍱","🍘","🍙","🍚","🍛",
                "🍜","🍝","🍠","🍢","🍣","🍤","🍥","🥮","🍡","🥠",
                "🥟","🥤","🧋","🧃","🧉","🧊","🍦","🍧","🍨","🍩",
                "🍪","🎂","🍰","🧁","🥧","🍫","🍬","🍭","🍮","🍯",
                "☕","🍵","🥤","🧃","🧉","🧊","🍶","🍾","🍷","🍸",
                "🍹","🍺","🍻","🥂","🥃","🥤"
            ],
            "Транспорт": [
                "🚗","🚕","🚙","🚌","🚎","🏎️","🚓","🚑","🚒","🚐",
                "🛻","🚚","🚛","🚜","🏍️","🛵","🚲","🦽","🦼","🛹",
                "🛼","🚘","🚖","🚔","🚍","🚀","🛸","✈️","🛩️","🛫",
                "🛬","🪂","💺","🚁","🚂","🚃","🚄","🚅","🚆","🚇",
                "🚈","🚉","🚊","🚝","🚞","🚋","🚌","🚍","🚎","🚐",
                "🚑","🚒","🚓","🚔","🚕","🚖","🚗","🚘","🚙","🚚",
                "🚛","🚜","🚝","🚞","🚟","🚠","🚡","🚢","🛳️","⛵",
                "🛶","🚤","🛥️","🛰️","🛩️","🛫","🛬","🪂"
            ],
            "Символы": [
                "❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔",
                "❣️","💕","💞","💓","💗","💖","💘","💝","💟","☮️",
                "✝️","☪️","🕉️","☸️","✡️","🔯","🕎","☯️","☦️","🛐",
                "⛎","♈","♉","♊","♋","♌","♍","♎","♏","♐",
                "♑","♒","♓","🆔","⚛️","🉑","☢️","☣️","📛","🔰",
                "⭕","✅","☑️","✔️","❌","❎","➖","➕","➗","✖️",
                "🟢","🟣","🟤","⚪","⚫","🔴","🟠","🟡","🟢","🔵",
                "🟣","🟤"
            ]
        }
        for cat, emojis in categories.items():
            tabs.add(cat)
            frame = ctk.CTkScrollableFrame(tabs.tab(cat), width=640, height=400)
            frame.pack(fill="both", expand=True, padx=5, pady=5)
            r=c=0
            for em in emojis:
                btn = ctk.CTkButton(frame, text=em, width=45, height=45,
                                    font=("Segoe UI Emoji",18),
                                    command=lambda e=em: self._insert(e))
                btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                c += 1
                if c >= 10: c=0; r+=1
            for i in range(10): frame.grid_columnconfigure(i, weight=1)
            for i in range(r+1): frame.grid_rowconfigure(i, weight=1)
        ctk.CTkButton(main, text="Закрыть", command=self.destroy, width=100).pack(pady=10)

    def _insert(self, emoji):
        self.callback(emoji)

# ---------- Просмотр изображений ----------
class ImageViewer(ctk.CTkToplevel):
    def __init__(self, parent, pil_img):
        super().__init__(parent)
        self.original = pil_img.copy()
        self.scale = 1.0
        self.full = False
        self.photo = None
        self.transient(parent); self.grab_set()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        max_w, max_h = int(sw*0.8), int(sh*0.8)
        w, h = self.original.size
        self.scale = min(max_w/w, max_h/h, 1.0)
        win_w, win_h = max(400, int(w*self.scale)), max(300, int(h*self.scale))
        self.geometry(f"{min(win_w,max_w)}x{min(win_h,max_h)}")
        self._build_ui()
        self._redraw()
        self._bind_events()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        main = ctk.CTkFrame(self); main.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(main, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="🔍+", width=60, command=lambda: self.zoom(0.1)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔍-", width=60, command=lambda: self.zoom(-0.1)).pack(side="left", padx=5)
        self.fs_btn = ctk.CTkButton(btn_frame, text="⛶ На весь экран", width=120, command=self.toggle_fullscreen)
        self.fs_btn.pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Сохранить", width=80, command=self.save).pack(side="left", padx=5)
        self.scale_label = ctk.CTkLabel(main, text="Масштаб: 100%", font=("Inter",10))
        self.scale_label.pack(pady=(0,5))
        ctk.CTkLabel(main, text="Колесо – масштаб, ЛКМ – перемещение, F/А – полноэкранный", font=("Inter",10), text_color="gray").pack()

    def _bind_events(self):
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel); self.canvas.bind("<Button-5>", self._on_wheel)
        self.bind("<Escape>", lambda e: self.toggle_fullscreen(force_off=True))
        self.bind("f", lambda e: self.toggle_fullscreen())
        self.bind("F", lambda e: self.toggle_fullscreen())
        self.bind("а", lambda e: self.toggle_fullscreen())
        self.bind("А", lambda e: self.toggle_fullscreen())
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

    def _on_wheel(self, e):
        delta = 0.1 if (e.num == 4 or (hasattr(e,'delta') and e.delta>0)) else -0.1
        self.zoom(delta)

    def zoom(self, delta):
        new = self.scale + delta
        if new < 0.1: new = 0.1
        elif new > 5.0: new = 5.0
        if new == self.scale: return
        self.scale = new
        self._redraw()
        self.scale_label.configure(text=f"Масштаб: {int(self.scale*100)}%")

    def _redraw(self):
        self.canvas.delete("all")
        w, h = self.original.size
        nw, nh = max(1, int(w*self.scale)), max(1, int(h*self.scale))
        img = self.original.resize((nw, nh), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0,0, anchor="nw", image=self.photo)
        self.canvas.config(scrollregion=(0,0,nw,nh))

    def toggle_fullscreen(self, force_off=False):
        if force_off and not self.full: return
        self.full = not self.full if not force_off else False
        self.attributes('-fullscreen', self.full)
        self.fs_btn.configure(text="⛶ Выйти из полноэкранного" if self.full else "⛶ На весь экран")
        self.update_idletasks()

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=[("PNG Image","*.png"),("JPEG","*.jpg"),("All","*.*")])
        if path:
            try:
                self.original.save(path)
                messagebox.showinfo("Успех", f"Сохранено:\n{path}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

# ---------- Основной класс мессенджера ----------
class PingMessenger:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PING! — Secure P2P Messenger")
        self.root.geometry("920x720")
        ctk.set_appearance_mode(CONFIG["appearance"])
        ctk.set_default_color_theme(CONFIG["theme"])

        self.username = self.password = self.salt = ""
        self.conn = self.cipher = None
        self.running = True
        self.server_sock = None
        self.image_refs = []
        self.typing_timer = None
        self.is_typing = False

        # Игра (только крестики-нолики)
        self.game_window = None
        self.game_opponent = None
        self.game_type = None   # всегда 'ttt'

        self._setup_styles()
        self._load_user()
        self._show_welcome()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Стили и данные ----------
    def _setup_styles(self):
        self.main_font = ctk.CTkFont(family="Inter", size=16)
        self.header_font = ctk.CTkFont(family="Inter", size=28, weight="bold")
        self.chat_font = ("Segoe UI Emoji", 13) if os.name == 'nt' else ("Noto Color Emoji", 13)
        self.chat_font_obj = tkfont.Font(family=self.chat_font[0], size=self.chat_font[1])
        self.timestamp_width = self.chat_font_obj.measure("[00:00:00] ")

    def _load_user(self):
        if os.path.exists(CONFIG["data_file"]):
            try:
                with open(CONFIG["data_file"], "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.username = d.get("username","")
                    self.password = d.get("password","")
                    self.salt = d.get("salt","")
            except: pass

    def _save_user(self):
        try:
            if not self.salt: self.salt = secrets.token_hex(16)
            pwd_hash = hashlib.pbkdf2_hmac('sha256', self.password.encode(), self.salt.encode(), 100000).hex()
            with open(CONFIG["data_file"], "w", encoding="utf-8") as f:
                json.dump({"username":self.username,"password":pwd_hash,"salt":self.salt}, f)
        except: pass

    def _clear(self):
        for w in self.root.winfo_children(): w.destroy()

    def _show_welcome(self):
        self._clear()
        ctk.CTkLabel(self.root, text="PING!", font=self.header_font, text_color="#00ff88").pack(pady=(50,10))
        ctk.CTkLabel(self.root, text="Мессенджер для своих", font=("Inter",14)).pack(pady=(0,30))
        btn = {"width":300,"height":50,"font":self.main_font}
        ctk.CTkButton(self.root, text="РЕГИСТРАЦИЯ", command=lambda: self._show_auth(True), **btn).pack(pady=10)
        ctk.CTkButton(self.root, text="ВОЙТИ", command=lambda: self._show_auth(False), **btn).pack(pady=10)
        canvas = tk.Canvas(self.root, width=300, height=100, bg="#2b2b2b", highlightthickness=0)
        canvas.pack(pady=30)
        colors = ["#ff4444","#ffaa00","#ffff00","#00ff44"]
        for i,c in enumerate(colors):
            h=(i+1)*20
            canvas.create_rectangle(20+i*60, 100-h, 60+i*60, 100, fill=c, outline="")

    def _show_auth(self, reg):
        self._clear()
        ctk.CTkLabel(self.root, text="Регистрация" if reg else "Вход", font=self.header_font).pack(pady=30)
        self.u_entry = ctk.CTkEntry(self.root, placeholder_text="Имя", width=300, height=45)
        self.u_entry.insert(0, self.username); self.u_entry.pack(pady=10)
        self.p_entry = ctk.CTkEntry(self.root, placeholder_text="Пароль", show="•", width=300, height=45)
        if len(self.password) < 50: self.p_entry.insert(0, self.password)
        self.p_entry.pack(pady=10)
        ctk.CTkButton(self.root, text="ПРОДОЛЖИТЬ", command=self._handle_auth).pack(pady=20)
        ctk.CTkButton(self.root, text="Назад", fg_color="transparent", command=self._show_welcome).pack()

    def _handle_auth(self):
        u, p = self.u_entry.get().strip(), self.p_entry.get().strip()
        if len(u) < 2 or len(p) < 3:
            messagebox.showwarning("Внимание", "Слишком короткий логин или пароль")
            return
        self.username, self.password = u, p
        self._save_user()
        self._show_main()

    def _show_main(self):
        self._clear()
        nav = ctk.CTkFrame(self.root, height=60); nav.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(nav, text=f"Аккаунт: @{self.username}", font=("Inter",14,"bold")).pack(side="left", padx=15)
        ctk.CTkButton(nav, text="Создать чат", width=140, command=self._start_server).pack(side="right", padx=5)
        ctk.CTkButton(nav, text="Подключиться", width=140, command=self._start_client).pack(side="right", padx=5)

        container = ctk.CTkFrame(self.root, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=5)

        self.chat = tk.Text(container, font=self.chat_font, bg="#1e1e1e", fg="#ffffff",
                            wrap=tk.WORD, padx=10, pady=10, spacing1=0, spacing2=0, spacing3=0,
                            relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("system", foreground="#888888", font=(self.chat_font[0], 11, "italic"))
        self.chat.tag_config("my_msg", foreground="#00ff88", font=(self.chat_font[0], 13, "bold"))
        self.chat.tag_config("other_msg", foreground="#ffffff", font=(self.chat_font[0], 13))
        self.chat.tag_config("msg_indent", lmargin1=self.timestamp_width, lmargin2=self.timestamp_width)
        self.chat.config(state="disabled")

        self.typing_label = ctk.CTkLabel(container, text="", font=("Inter",11,"italic"), text_color="#ffaa00")
        self.typing_label.pack(side="top", fill="x", pady=(2,0))

        input_frame = ctk.CTkFrame(container, fg_color="transparent", height=90)
        input_frame.pack(side="bottom", fill="x", pady=(5,0))
        input_frame.pack_propagate(False)

        self.msg_input = ctk.CTkTextbox(input_frame, height=70, wrap="word", font=("Inter",14))
        self.msg_input.pack(side="left", fill="both", expand=True, padx=(0,10))

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(side="right", fill="y")
        ctk.CTkButton(btn_frame, text="😊", width=50, height=40,
                      font=("Segoe UI Emoji",18), command=self._open_emoji).pack(side="left", padx=(0,5))
        ctk.CTkButton(btn_frame, text="📎", width=50, height=40,
                      font=("Segoe UI Emoji",16), command=self._send_image).pack(side="left", padx=(0,5))
        ctk.CTkButton(btn_frame, text="ОТПРАВИТЬ", width=90, height=40,
                      command=self._send_msg).pack(side="left")

        self.msg_input.bind("<Return>", self._send_msg)
        self.msg_input.bind("<Shift-Return>", lambda e: self.msg_input.insert("insert", "\n"))
        self.msg_input.bind("<Control-Return>", lambda e: self.msg_input.insert("insert", "\n"))
        self.msg_input.bind("<Key>", self._on_typing)
        self.msg_input.bind("<FocusOut>", self._on_typing_stop)
        self.msg_input.bind("<<Paste>>", self._paste)

    def _open_emoji(self):
        EmojiPicker(self.root, self._insert_emoji)

    def _insert_emoji(self, em):
        self.msg_input.insert("insert", em)
        self.msg_input.focus()

    # ---------- Вставка из буфера ----------
    def _paste(self, event=None):
        try:
            img = ImageGrab.grabclipboard()
            if img and isinstance(img, Image.Image):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                if self._send_image_data(b64, own=True):
                    self._log("Вы вставили изображение из буфера", "my_msg")
                    self._display_image(b64, own=True)
                return "break"
        except: pass
        try:
            text = self.root.clipboard_get()
            if text:
                self.msg_input.insert("insert", text)
                return "break"
        except: pass

    # ---------- Отправка изображений ----------
    def _send_image_data(self, b64, own=False):
        if not self.conn or not self.cipher: return False
        try:
            payload = json.dumps({"type":"image","sender":self.username,"data":b64}).encode()
            return self._send_data(payload)
        except Exception as e:
            self._log(f"Ошибка отправки изображения: {e}", "system")
            return False

    def _send_image(self):
        if not self.conn or not self.cipher:
            messagebox.showwarning("Внимание", "Нет активного соединения.")
            return
        path = filedialog.askopenfilename(title="Выберите изображение",
                                          filetypes=[("Изображения","*.png *.jpg *.jpeg *.gif *.bmp")])
        if not path: return
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            if self._send_image_data(b64, own=True):
                self._log("Вы отправили изображение", "my_msg")
                self._display_image(b64, own=True)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ---------- Отправка данных ----------
    def _send_data(self, data):
        if not self.conn or not self.cipher: return False
        try:
            enc = self.cipher.encrypt(data)
            self.conn.sendall(struct.pack('>I', len(enc)) + enc)
            return True
        except Exception as e:
            self._log(f"Ошибка отправки: {e}", "system")
            return False

    def _send_msg(self, event=None):
        msg = self.msg_input.get("1.0", "end").strip()
        if not msg or not self.conn or not self.cipher: return
        lower = msg.lower()
        # Команды игр (только крестики-нолики)
        if lower in ("крестики нолики", "крестики-нолики", "tic tac toe", "ttt"):
            self._send_game_invite("ttt")
            self.msg_input.delete("1.0", "end")
            self._on_typing_stop()
            return
        # Обычное сообщение
        payload = json.dumps({"type":"text","sender":self.username,"data":msg}).encode()
        if self._send_data(payload):
            self._log(f"Вы: {msg}", "my_msg")
            self.msg_input.delete("1.0", "end")
            self._on_typing_stop()

    # ---------- Отображение в чате и уведомления ----------
    def _log(self, text, tag=None, widget=None, ts=None, sender=None):
        """Передаёт сообщение в UI и при необходимости показывает уведомление."""
        self.root.after(0, self._log_ui, text, tag, widget, ts)
        # Если сообщение от другого пользователя (sender != self.username) и окно не активно – уведомление
        if sender and sender != self.username:
            self._notify_if_needed("Новое сообщение", text)

    def _log_ui(self, text, tag, widget, ts):
        self.chat.config(state="normal")
        ts = ts or datetime.now().strftime("%H:%M:%S")
        if widget:
            self.chat.insert("end", f"[{ts}] ", "system")
            self.chat.window_create("end", window=widget)
            self.chat.insert("end", "\n")
        else:
            tag = tag or "other_msg"
            lines = text.split('\n')
            for i,line in enumerate(lines):
                if i == 0:
                    self.chat.insert("end", f"[{ts}] {line}\n", tag)
                else:
                    self.chat.insert("end", f"{line}\n", ("msg_indent", tag))
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _notify_if_needed(self, title, message):
        """Показывает системное уведомление, если окно свёрнуто или не в фокусе."""
        try:
            # Проверяем, активно ли окно
            if self.root.state() == 'iconic' or not self.root.focus_displayof():
                notification.notify(
                    title=title,
                    message=message[:100],  # обрезаем длинные сообщения
                    app_name="PING!",
                    timeout=5
                )
        except:
            pass

    def _display_image(self, b64, own=False, sender=None):
        try:
            img_data = base64.b64decode(b64)
            pil = Image.open(io.BytesIO(img_data))
            orig = pil.copy()
            w,h = pil.size
            if w > MAX_IMG_W:
                r = MAX_IMG_W / w
                pil = pil.resize((MAX_IMG_W, int(h*r)), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil)
            lbl = tk.Label(self.chat, image=photo, bg="#1e1e1e", cursor="hand2")
            lbl.image = photo
            lbl.bind("<Button-1>", lambda e, img=orig: ImageViewer(self.root, img))
            self.image_refs.append((photo, lbl, orig))
            self._log("📷 Изображение" + (" (вы)" if own else ""), widget=lbl, sender=sender)
            if not own and sender and sender != self.username:
                self._notify_if_needed("Новое изображение", f"От {sender}")
        except Exception as e:
            self._log(f"Ошибка отображения изображения: {e}", "system")

    # ---------- Статус печати ----------
    def _on_typing(self, e):
        if e.keysym in ('Shift_L','Shift_R','Control_L','Control_R','Alt_L','Alt_R'): return
        if not self.is_typing and self.conn and self.cipher:
            self.is_typing = True
            self._send_typing(True)
        if self.typing_timer:
            self.root.after_cancel(self.typing_timer)
        self.typing_timer = self.root.after(2000, self._on_typing_stop)

    def _on_typing_stop(self, e=None):
        if self.is_typing:
            self.is_typing = False
            if self.conn and self.cipher: self._send_typing(False)
        if self.typing_timer:
            self.root.after_cancel(self.typing_timer); self.typing_timer = None

    def _send_typing(self, state):
        try:
            payload = json.dumps({"type":"typing","sender":self.username,"data":state}).encode()
            enc = self.cipher.encrypt(payload)
            self.conn.sendall(struct.pack('>I', len(enc)) + enc)
        except: pass

    def _show_typing(self, sender, state):
        if state:
            self.typing_label.configure(text=f"✍️ {sender} печатает...")
            if hasattr(self, '_typing_hide'):
                self.root.after_cancel(self._typing_hide)
            self._typing_hide = self.root.after(3000, lambda: self.typing_label.configure(text=""))
        else:
            self.typing_label.configure(text="")
            if hasattr(self, '_typing_hide'):
                self.root.after_cancel(self._typing_hide)

    # ---------- Игра (только крестики-нолики) ----------
    def _send_game_invite(self, game_type):
        if not self.conn or not self.cipher:
            messagebox.showwarning("Нет соединения", "Подключитесь к собеседнику")
            return
        payload = json.dumps({"type":"game_invite","sender":self.username,"game":"ttt"}).encode()
        if self._send_data(payload):
            self._log("Вы отправили приглашение сыграть в крестики-нолики", "system")

    def _handle_game_invite(self, sender):
        accept_btn = ctk.CTkButton(self.chat, text="Принять", width=80, height=30,
                                   command=lambda: self._accept_game(sender))
        self._log(f"{sender} предлагает сыграть в крестики-нолики", widget=accept_btn)

    def _accept_game(self, sender):
        payload = json.dumps({"type":"game_accept","sender":self.username,"game":"ttt"}).encode()
        if self._send_data(payload):
            self._log("Вы приняли приглашение. Игра начинается!", "system")
            self._start_game(sender, is_initiator=False)

    def _handle_game_accept(self, sender):
        self._log(f"{sender} принял приглашение. Игра начинается!", "system")
        self._start_game(sender, is_initiator=True)

    def _start_game(self, opponent, is_initiator):
        if self.game_window and self.game_window.winfo_exists():
            self.game_window.destroy()
        my_symbol = 'X' if is_initiator else 'O'
        self.game_window = TicTacToeWindow(
            self.root, my_symbol, opponent,
            self._send_game_move,
            self._on_game_close
        )
        self.game_opponent = opponent
        self.game_type = "ttt"

    def _send_game_move(self, *args, surrender=False):
        if surrender:
            payload = json.dumps({"type":"game_move","sender":self.username,
                                  "game":"ttt",
                                  "data":{"surrender":True}}).encode()
        else:
            row, col = args[0], args[1]
            data = {"row":row, "col":col, "surrender":False}
            payload = json.dumps({"type":"game_move","sender":self.username,
                                  "game":"ttt",
                                  "data":data}).encode()
        self._send_data(payload)

    def _handle_game_move(self, sender, data):
        if self.game_window is None or not self.game_window.winfo_exists():
            return
        if sender == self.username:
            return
        if data.get("surrender", False):
            self.game_window._end_game(f"{sender} сдался. Вы выиграли!")
            return
        row, col = data.get("row"), data.get("col")
        if row is not None and col is not None:
            symbol = 'O' if self.game_window.my_symbol == 'X' else 'X'
            self.game_window.opponent_move(row, col, symbol)

    def _on_game_close(self):
        self.game_window = None
        self.game_opponent = None
        self.game_type = None

    # ---------- Криптография ----------
    def _exchange_keys(self, is_server):
        try:
            self._log("⏳ Генерация ключей шифрования...", "system")
            priv = ec.generate_private_key(ec.SECP384R1())
            pub = priv.public_key()
            pub_bytes = pub.public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo)
            if is_server:
                self.conn.sendall(pub_bytes)
                peer = self.conn.recv(2048)
            else:
                peer = self.conn.recv(2048)
                self.conn.sendall(pub_bytes)
            peer_key = serialization.load_pem_public_key(peer)
            secret = priv.exchange(ec.ECDH(), peer_key)
            key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                       info=b'ping_messenger_e2ee').derive(secret)
            self.cipher = Fernet(base64.urlsafe_b64encode(key))
            self._log("🔒 Сквозное шифрование AES-256 установлено!", "my_msg")
            return True
        except Exception as e:
            self._log(f"❌ Ошибка обмена ключами: {e}", "system")
            return False

    def _send_handshake(self):
        try:
            payload = json.dumps({"type":"handshake","sender":self.username,"data":"join"}).encode()
            enc = self.cipher.encrypt(payload)
            self.conn.sendall(struct.pack('>I', len(enc)) + enc)
        except: pass

    # ---------- Сеть ----------
    def _start_server(self):
        def server_thread():
            try:
                port = find_free_port()
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind((CONFIG["host"], port))
                self.server_sock.listen(1)
                ips = get_all_ips()
                pub = get_public_ip()
                self._log(f"✅ Сервер запущен на порту {port}", "system")
                if pub: self._log(f"🌍 Публичный IP (для интернета): {pub}", "system")
                self._log("📶 Доступные IP-адреса для подключения:", "system")
                for ip in ips: self._log(f"   {ip}:{port}", "system")
                self._log(f"📌 Сообщите другу IP и порт {port}.", "system")
                self._log("   (Radmin VPN: выберите IP, начинающийся с 26.x.x.x)", "system")
                client, addr = self.server_sock.accept()
                self.conn = client
                self._log(f"✅ Соединение с {addr[0]}!", "system")
                if self._exchange_keys(True):
                    self._send_handshake()
                    self._listen()
                else:
                    self.conn.close()
            except OSError as e:
                if e.winerror == 10048:
                    self._log("❌ Порт занят. Попробуйте снова.", "system")
                else:
                    self._log(f"❌ Ошибка сервера: {e}", "system")
            except Exception as e:
                self._log(f"❌ Ошибка сервера: {e}", "system")
            finally:
                if self.server_sock: self.server_sock.close()
        threading.Thread(target=server_thread, daemon=True).start()

    def _start_client(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Подключение")
        dialog.geometry("340x280")
        dialog.transient(self.root); dialog.grab_set()
        ctk.CTkLabel(dialog, text="IP-адрес друга:").pack(pady=(10,0))
        ip_e = ctk.CTkEntry(dialog, width=250); ip_e.pack(pady=5)
        ctk.CTkLabel(dialog, text="Порт:").pack(pady=(10,0))
        port_e = ctk.CTkEntry(dialog, width=250); port_e.pack(pady=5)
        ctk.CTkLabel(dialog, text="Если друг за пределами вашей сети,\nнужен публичный IP и проброс порта.",
                     font=("Inter",10), text_color="gray").pack(pady=5)
        def connect():
            ip = ip_e.get().strip()
            try:
                port = int(port_e.get().strip())
            except:
                messagebox.showerror("Ошибка", "Порт должен быть числом"); return
            if not ip or port <= 0:
                messagebox.showerror("Ошибка", "Введите корректные данные"); return
            dialog.destroy()
            def client_thread():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10)
                    s.connect((ip, port))
                    s.settimeout(None)
                    self.conn = s
                    self._log(f"✅ Подключено к {ip}:{port}", "system")
                    if self._exchange_keys(False):
                        self._send_handshake()
                        self._listen()
                    else:
                        self.conn.close()
                except socket.timeout:
                    messagebox.showerror("Ошибка", "Время ожидания истекло.\nПроверьте, запущен ли сервер.")
                except socket.error as e:
                    if e.winerror == 10051:
                        messagebox.showerror("Ошибка сети", "Сеть недоступна.\nПроверьте соединение и правильность IP.")
                    else:
                        messagebox.showerror("Ошибка", f"Код: {e}")
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
            threading.Thread(target=client_thread, daemon=True).start()
        ctk.CTkButton(dialog, text="Подключиться", command=connect).pack(pady=15)
        ctk.CTkButton(dialog, text="Отмена", command=dialog.destroy, fg_color="transparent").pack()

    def _listen(self):
        while self.running and self.conn:
            try:
                raw = self.conn.recv(4)
                if not raw: break
                length = struct.unpack('>I', raw)[0]
                data = b''
                while len(data) < length:
                    chunk = self.conn.recv(min(length - len(data), 4096))
                    if not chunk: break
                    data += chunk
                if len(data) < length: break
                dec = self.cipher.decrypt(data)
                msg = json.loads(dec.decode())
                typ = msg.get("type")
                sender = msg.get("sender", "Неизвестный")
                if typ == "text":
                    if sender != self.username:
                        self._log(f"{sender}: {msg['data']}", "other_msg", sender=sender)
                elif typ == "image":
                    if sender != self.username:
                        self._log(f"📷 {sender} отправил изображение", "system")
                        self.root.after(0, self._display_image, msg["data"], False, sender)
                elif typ == "game_invite":
                    if sender != self.username:
                        self.root.after(0, self._handle_game_invite, sender)
                elif typ == "game_accept":
                    if sender != self.username:
                        self.root.after(0, self._handle_game_accept, sender)
                elif typ == "game_move":
                    if sender != self.username:
                        self.root.after(0, self._handle_game_move, sender, msg.get("data", {}))
                elif typ == "typing":
                    if sender != self.username:
                        self.root.after(0, self._show_typing, sender, msg.get("data", False))
                elif typ == "handshake":
                    if sender != self.username:
                        self._log(f"✅ {sender} присоединился к чату", "system")
                        # Уведомление о подключении
                        self.root.after(0, self._notify_if_needed, "Новый пользователь", f"{sender} присоединился к чату")
            except socket.error:
                break
            except Exception as e:
                self._log(f"Ошибка приёма: {e}", "system")
                break
        self._log("🔌 Соединение разорвано.", "system")
        if self.conn:
            try: self.conn.close()
            except: pass
            self.conn = None; self.cipher = None

    def _on_close(self):
        self.running = False
        if self.conn: self.conn.close()
        if self.server_sock: self.server_sock.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    PingMessenger().run()