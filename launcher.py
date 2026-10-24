import os, sys, subprocess, webbrowser, tkinter as tk
from tkinter import messagebox, ttk, colorchooser
import tkinter.font as tkfont
import threading, time, urllib.request, urllib.parse, random, math, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE_DIR, "modules")
LOG_DIR = os.path.join(BASE_DIR, "_workflow")
os.makedirs(LOG_DIR, exist_ok=True)

# ================= 动态读取插件 =================
MODULES = []
if os.path.exists(MODULES_DIR):
    for folder in os.listdir(MODULES_DIR):
        config_path = os.path.join(MODULES_DIR, folder, "config.json")
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cfg["folder"] = os.path.join(MODULES_DIR, folder)
                    MODULES.append(cfg)
            except Exception as e:
                print(f"读取插件失败 {folder}: {e}")

# ================= 核心逻辑 =================
def start_services():
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = os.path.join(BASE_DIR, "30-models")
    with open(os.path.join(LOG_DIR, "ollama_log.txt"), "w") as f:
        subprocess.Popen(["ollama", "serve"], env=env, stdout=f, stderr=f, creationflags=subprocess.CREATE_NO_WINDOW)

    py_webui = r"C:\open-webui-venv\Scripts\open-webui.exe"
    env_webui = os.environ.copy()
    env_webui["DATA_DIR"] = os.path.join(BASE_DIR, "00-ai-base\\data")
    env_webui["WEBUI_DEVICE"] = "cuda"
    env_webui["WHISPER_DEVICE_TYPE"] = "cuda"
    with open(os.path.join(LOG_DIR, "webui_log.txt"), "w", encoding="utf-8") as f:
        subprocess.Popen([py_webui, "serve"], env=env_webui, stdout=f, stderr=f, creationflags=subprocess.CREATE_NO_WINDOW)

    # 启动插件服务（绝对路径）
    py_venv = os.path.join(BASE_DIR, r"10-doc-tools\inkdoc-src\.venv\Scripts\python.exe")
    for mod in MODULES:
        if mod.get("type") == "service":
            log_name = f"{os.path.basename(mod['folder'])}.txt"
            app_path = os.path.join(mod["folder"], "app.py")
            with open(os.path.join(LOG_DIR, log_name), "w", encoding="utf-8") as f:
                subprocess.Popen([py_venv, app_path], cwd=mod["folder"], stdout=f, stderr=f, creationflags=subprocess.CREATE_NO_WINDOW)

def check_service(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200: return True
        except Exception: time.sleep(1)
    return False

def open_with_progress(url, title_text, timeout=30):
    load_win = tk.Toplevel(root)
    load_win.title("请稍候")
    load_win.geometry("360x160")
    load_win.configure(bg="#FFF0F5")
    load_win.resizable(False, False)
    load_win.grab_set()
    x = root.winfo_x() + (root.winfo_width() - 360) // 2
    y = root.winfo_y() + (root.winfo_height() - 160) // 2
    load_win.geometry(f"+{x}+{y}")
    border = tk.Frame(load_win, bg="#C2185B", bd=0)
    border.place(x=0, y=0, relwidth=1, relheight=1)
    inner = tk.Frame(border, bg="#FFF0F5")
    inner.place(x=4, y=4, relwidth=1, relheight=1, width=-8, height=-8)
    tk.Label(inner, text="🐾 " + title_text, font=PF(12), bg="#FFF0F5", fg="#C2185B", justify="center").pack(pady=(22, 12))
    style = ttk.Style()
    style.theme_use('default')
    style.configure("Pixel.Horizontal.TProgressbar", troughcolor="#FFE4EC", background="#FF8FB1", bordercolor="#C2185B")
    pb = ttk.Progressbar(inner, mode='indeterminate', length=280, style="Pixel.Horizontal.TProgressbar")
    pb.pack(pady=5); pb.start(15)
    def task():
        is_ready = check_service(url, timeout=timeout)
        if is_ready: load_win.after(0, lambda: (load_win.destroy(), webbrowser.open(url)))
        else: load_win.after(0, lambda: (load_win.destroy(), messagebox.showerror("启动失败", "服务响应超时，请检查后台黑框或日志。")))
    threading.Thread(target=task, daemon=True).start()

def plugin_click(mod):
    mtype = mod.get("type")
    if mtype == "service":
        open_with_progress(mod["url"], f"正在连接 {mod['name']}...", timeout=60)
    elif mtype == "obsidian":
        vault_path = os.path.join(BASE_DIR, "_processed")
        encoded_path = urllib.parse.quote(vault_path.replace("\\", "/"))
        os.startfile(f"obsidian://open?path={encoded_path}")
    elif mtype == "action" and "sync" in mod["name"].lower():
        run_sync()

def run_sync():
    if not check_service("http://127.0.0.1:8080", timeout=2):
        messagebox.showwarning("提示", "AI 服务尚未启动！"); return
    def task():
        oikb = os.path.join(BASE_DIR, r"10-doc-tools\inkdoc-src\.venv\Scripts\oikb.exe")
        dir_path = os.path.join(BASE_DIR, "_processed")
        try:
            res = subprocess.run([oikb, "sync", dir_path, "--url", "http://127.0.0.1:8080", "--token", "sk-e5c5eee1eb55429baba3498f5490cca4", "--kb-id", "85139fc7-3b2f-4216-bc14-9aadb34e9d94"], capture_output=True, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
            root.after(0, lambda: messagebox.showinfo("同步完成", res.stdout.strip()))
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("失败", str(e)))
    threading.Thread(target=task, daemon=True).start()

def kill_all():
    for p in ["python.exe", "pythonw.exe", "ollama.exe", "ollama_llama_server.exe", "open-webui.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", p, "/T"], capture_output=True)

def safe_exit():
    status_label.config(text="🌸 正在停止服务...", fg="#E91E63"); root.update()
    kill_all(); time.sleep(2)
    subprocess.run('powershell -Command "$d = New-Object -comObject Shell.Application; $d.Namespace(17).ParseName(\'G:\').InvokeVerb(\'Eject\')"', shell=True)
    time.sleep(1); messagebox.showinfo("安全退出", "🌸 U盘已安全断开！"); root.destroy()

# ================= UI 构建 =================
root = tk.Tk()
root.title("笺启 · 工作站"); root.geometry("560x720")
root.minsize(500, 640); root.configure(bg="#FFF0F5"); root.resizable(True, True)
root.geometry(f"+{(root.winfo_screenwidth()-560)//2}+{(root.winfo_screenheight()-720)//2}")

def get_pixel_font():
    for name in ["Zpix", "Zpix Ex", "SimSun"]:
        if name in set(tkfont.families()): return name
    return "SimSun"
PIXEL_FONT = get_pixel_font()
def PF(size, bold=False): return (PIXEL_FONT, size, "bold") if bold else (PIXEL_FONT, size)

theme = {
    "bg_top": "#FFE4EC", "bg_bottom": "#FFF0F5", "card_bg": "#FFFFFF", "card_border": "#C2185B",
    "title_color": "#C2185B", "subtitle_color": "#F48FB1", "status_color": "#BA68C8",
    "btn1": "#FF8FB1", "btn1_hover": "#FF6F91", "btn2": "#FFA8C5", "btn2_hover": "#FF8FB1",
    "btn3": "#C792EA", "btn3_hover": "#B07CE0", "btn_sync": "#FFB74D", "btn_sync_hover": "#FFA726",
    "btn_cal": "#81C784", "btn_cal_hover": "#66BB6A", "btn4": "#F48FB1", "btn4_hover": "#E91E63", "footer_color": "#F48FB1",
    "particle_type": "sakura", "particle_count": 28,
}

main_frame = tk.Frame(root, bg=theme["bg_bottom"]); main_frame.pack(fill="both", expand=True)
bg_canvas = tk.Canvas(main_frame, highlightthickness=0, bd=0, bg=theme["bg_bottom"]); bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

def draw_pixel_gradient(canvas, w, h, c1, c2):
    canvas.delete("bg_grad")
    r1, g1, b1 = canvas.winfo_rgb(c1); r2, g2, b2 = canvas.winfo_rgb(c2)
    r1, g1, b1 = r1//256, g1//256, b1//256; r2, g2, b2 = r2//256, g2//256, b2//256
    for i in range(0, h, 8):
        t = i/h; r = int(r1+(r2-r1)*t); g = int(g1+(g2-g1)*t); b = int(b1+(b2-b1)*t)
        canvas.create_rectangle(0, i, w, i+8, fill=f"#{r:02x}{g:02x}{b:02x}", outline="", tags="bg_grad")

particle_win=None; particle_canvas=None; particles=[]
def create_particle_overlay():
    global particle_win, particle_canvas
    particle_win = tk.Toplevel(root); particle_win.overrideredirect(True); particle_win.attributes('-topmost', True)
    particle_win.attributes('-transparentcolor', '#010101'); particle_win.configure(bg='#010101')
    particle_canvas = tk.Canvas(particle_win, bg='#010101', highlightthickness=0, bd=0); particle_canvas.pack(fill="both", expand=True)
def sync_particle_overlay():
    if particle_win and particle_win.winfo_exists(): particle_win.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_x()}+{root.winfo_y()}")

# ================= 完整粒子系统 =================
def spawn_particle(w, h):
    ptype = theme["particle_type"]
    if ptype == "none": return None
    x = random.randint(0, w); y = random.randint(-40, -10); speed = random.uniform(0.8, 2.2); size = random.choice([4, 6, 8])
    drift = random.uniform(-0.5, 0.5); rotation = random.uniform(0, 360); rot_speed = random.uniform(-3, 3)
    if ptype == "sakura":
        color = random.choice(["#FFC0CB", "#FFB7C5", "#FFD1DC", "#FF9EB5"]); shape = "petal"
    elif ptype == "snow":
        color = random.choice(["#FFFFFF", "#E3F2FD", "#BBDEFB"]); shape = "square"
    elif ptype == "star":
        color = random.choice(["#FFD54F", "#FFEB3B", "#FFF176"]); shape = "star"
    elif ptype == "heart":
        color = random.choice(["#FF6F91", "#FF8FB1", "#F48FB1"]); shape = "heart"
    elif ptype == "leaf":
        color = random.choice(["#FFB74D", "#FF8A65", "#A5D6A7"]); shape = "petal"
    else: return None
    return {"x": x, "y": y, "speed": speed, "size": size, "drift": drift, "color": color, "shape": shape, "rotation": rotation, "rot_speed": rot_speed}

def draw_particle(p):
    if not particle_canvas or not particle_canvas.winfo_exists(): return
    x, y, s, c, shape = p["x"], p["y"], p["size"], p["color"], p["shape"]
    rot = p["rotation"]
    if shape == "square":
        particle_canvas.create_rectangle(x, y, x + s, y + s, fill=c, outline="", tags="particle")
    elif shape == "petal":
        cx, cy = x + s/2, y + s/2; rad = math.radians(rot); pts = []
        for angle in [0, 90, 180, 270]:
            a = math.radians(angle) + rad; pts.extend([cx + (s/2) * math.cos(a), cy + (s/2) * math.sin(a)])
        particle_canvas.create_polygon(pts, fill=c, outline="", tags="particle")
    elif shape == "star":
        particle_canvas.create_rectangle(x + s//3, y, x + 2*s//3, y + s, fill=c, outline="", tags="particle")
        particle_canvas.create_rectangle(x, y + s//3, x + s, y + 2*s//3, fill=c, outline="", tags="particle")
    elif shape == "heart":
        particle_canvas.create_rectangle(x, y + s//3, x + s//3, y + 2*s//3, fill=c, outline="", tags="particle")
        particle_canvas.create_rectangle(x + 2*s//3, y + s//3, x + s, y + 2*s//3, fill=c, outline="", tags="particle")
        particle_canvas.create_rectangle(x + s//3, y + 2*s//3, x + 2*s//3, y + s, fill=c, outline="", tags="particle")

def particle_loop():
    global particles
    if particle_canvas and particle_canvas.winfo_exists():
        particle_canvas.delete("particle")
        w = particle_canvas.winfo_width() or 560; h = particle_canvas.winfo_height() or 720
        target = theme["particle_count"] if theme["particle_type"] != "none" else 0
        while len(particles) < target:
            p = spawn_particle(w, h)
            if p: particles.append(p)
            else: break
        new_p = []
        for p in particles:
            p["y"] += p["speed"]; p["x"] += p["drift"]; p["rotation"] += p["rot_speed"]
            if p["y"] < h + 20 and -20 < p["x"] < w + 20: draw_particle(p); new_p.append(p)
        particles = new_p
    root.after(40, particle_loop)

# ================= 完整小猫按钮 =================
class PixelCatButton(tk.Canvas):
    def __init__(self, parent, text, bg_key, hover_key, command):
        super().__init__(parent, height=64, bg=theme["bg_top"], highlightthickness=0, bd=0, cursor="hand2")
        self.text = text; self.bg_key = bg_key; self.hover_key = hover_key; self.command = command
        self.hovered = False; self.anim = 0; self.blink = 0; self.bounce = 0
        self.bind("<Enter>", lambda e: (setattr(self, 'hovered', True), self.draw()))
        self.bind("<Leave>", lambda e: (setattr(self, 'hovered', False), self.draw()))
        self.bind("<Button-1>", lambda e: self.command()); self.bind("<Configure>", lambda e: self.draw())
        self.animate()
    def animate(self):
        self.anim = (self.anim + 1) % 60; self.blink = (self.blink + 1) % 120
        if self.hovered: self.bounce = int(math.sin(self.anim * 0.3) * 3)
        self.draw(); self.after(80, self.animate)
    def draw(self):
        self.delete("all"); w = self.winfo_width() or 500; h = 64
        color = theme.get(self.hover_key, "#FF8FB1") if self.hovered else theme.get(self.bg_key, "#FFA8C5")
        border = theme["card_border"]
        self.create_rectangle(4, 4, w - 4, h - 4, fill=border, outline="")
        body_y = 8 + self.bounce; body_h = h - 16
        self.create_rectangle(0, body_y, w - 8, body_y + body_h, fill=color, outline=border, width=3)
        head_size = body_h - 4; head_x = 6; head_y = body_y + 2
        self.create_rectangle(head_x, head_y, head_x + head_size, head_y + head_size, fill=color, outline=border, width=3)
        ear_size = 10
        self.create_polygon(head_x + 4, head_y, head_x + 4 + ear_size, head_y, head_x + 4 + ear_size // 2, head_y - ear_size, fill=color, outline=border, width=2)
        self.create_polygon(head_x + head_size - 4 - ear_size, head_y, head_x + head_size - 4, head_y, head_x + head_size - 4 - ear_size // 2, head_y - ear_size, fill=color, outline=border, width=2)
        eye_y = head_y + head_size // 2 - 4
        if self.hovered:
            self.create_line(head_x + 8, eye_y + 6, head_x + 11, eye_y, head_x + 14, eye_y + 6, fill="#FFFFFF", width=2)
            self.create_line(head_x + head_size - 14, eye_y + 6, head_x + head_size - 11, eye_y, head_x + head_size - 8, eye_y + 6, fill="#FFFFFF", width=2)
        else:
            if 110 <= self.blink <= 116:
                self.create_line(head_x + 8, eye_y + 3, head_x + 14, eye_y + 3, fill="#FFFFFF", width=2)
                self.create_line(head_x + head_size - 14, eye_y + 3, head_x + head_size - 8, eye_y + 3, fill="#FFFFFF", width=2)
            else:
                self.create_rectangle(head_x + 8, eye_y, head_x + 14, eye_y + 6, fill="#FFFFFF", outline="")
                self.create_rectangle(head_x + head_size - 14, eye_y, head_x + head_size - 8, eye_y + 6, fill="#FFFFFF", outline="")
        nose_x = head_x + head_size // 2; nose_y = eye_y + 10
        self.create_polygon(nose_x - 3, nose_y, nose_x + 3, nose_y, nose_x, nose_y + 3, fill="#FFFFFF", outline="")
        tail_base_x = w - 12; tail_base_y = body_y + body_h // 2
        tail_angle = math.sin(self.anim * 0.2) * 15
        tail_end_x = tail_base_x + 20 * math.cos(math.radians(tail_angle - 90))
        tail_end_y = tail_base_y + 20 * math.sin(math.radians(tail_angle - 90))
        self.create_line(tail_base_x, tail_base_y, tail_end_x, tail_end_y, fill=border, width=6, capstyle="round")
        self.create_line(tail_base_x, tail_base_y, tail_end_x, tail_end_y, fill=color, width=3, capstyle="round")
        self.create_text(head_x + head_size + (w - head_size - 20) // 2, body_y + body_h // 2, text=self.text, font=PF(12), fill="#FFFFFF")

header_frame = tk.Frame(main_frame, bg=theme["card_bg"], bd=0, highlightbackground=theme["card_border"], highlightthickness=3)
header_frame.pack(fill="x", padx=20, pady=(20, 10))
title_label = tk.Label(header_frame, text="🌸 笺启 🐱", font=PF(24), bg=theme["card_bg"], fg=theme["title_color"])
title_label.pack(pady=(10, 2))
subtitle_label = tk.Label(header_frame, text="·  工 作 站 ·", font=PF(12), bg=theme["card_bg"], fg=theme["subtitle_color"])
subtitle_label.pack(pady=2)
status_label = tk.Label(header_frame, text="⏳ 正在后台启动服务...", font=PF(12), bg=theme["card_bg"], fg=theme["status_color"])
status_label.pack(pady=(2, 10))

button_container = tk.Frame(main_frame, bg=theme["bg_top"])
button_container.pack(fill="both", expand=True, padx=20, pady=10)
cat_buttons = []
def add_btn(text, b_key, h_key, cmd):
    btn = PixelCatButton(button_container, text, b_key, h_key, cmd)
    btn.pack(fill="x", pady=4); cat_buttons.append(btn)

add_btn("💬  打开 聊天与知识库", "btn1", "btn1_hover", lambda: open_with_progress("http://127.0.0.1:8080", "正在连接 AI 聊天与知识库...", timeout=60))
for mod in MODULES:
    add_btn(mod["name"], mod.get("color", "btn2"), mod.get("hover", "btn2_hover"), lambda m=mod: plugin_click(m))
add_btn("🛑  安全退出并拔出U盘", "btn4", "btn4_hover", safe_exit)

footer_frame = tk.Frame(main_frame, bg=theme["bg_top"])
footer_frame.pack(fill="x", pady=(0, 15))
footer_label = tk.Label(footer_frame, text="🐾 一切就绪，请点击上方按钮 🐾", font=PF(12), bg=theme["bg_top"], fg=theme["footer_color"])
footer_label.pack(pady=2)
paw_label = tk.Label(footer_frame, text="🐱", font=("Segoe UI Emoji", 22), bg=theme["bg_top"], fg=theme["footer_color"])
paw_label.pack()

# ================= 换肤面板 =================
def open_settings():
    win = tk.Toplevel(root)
    win.title("🎨 装扮设置")
    win.geometry("480x700")
    win.minsize(440, 500)
    win.configure(bg="#FFF0F5")
    win.resizable(True, True)
    win.grab_set()
    x = root.winfo_x() + (root.winfo_width() - 480) // 2
    y = root.winfo_y() + (root.winfo_height() - 700) // 2
    win.geometry(f"+{x}+{y}")
    top_bar = tk.Frame(win, bg="#C2185B", height=60)
    top_bar.pack(fill="x")
    top_bar.pack_propagate(False)
    tk.Label(top_bar, text="🎨  装 扮 设 置", font=PF(16), bg="#C2185B", fg="#FFFFFF").pack(pady=15)
    canvas = tk.Canvas(win, bg="#FFF0F5", highlightthickness=0)
    scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#FFF0F5")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=460)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)
    def make_card(title, emoji):
        card = tk.Frame(scroll_frame, bg="#FFFFFF", bd=0, highlightbackground="#C2185B", highlightthickness=2)
        card.pack(fill="x", padx=10, pady=8)
        title_bar = tk.Frame(card, bg="#FFE4EC", height=32)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text=f"{emoji}  {title}", font=PF(12), bg="#FFE4EC", fg="#C2185B").pack(side="left", padx=10, pady=6)
        body = tk.Frame(card, bg="#FFFFFF")
        body.pack(fill="x", padx=10, pady=8)
        return body
    def pixel_btn(parent, text, command, color="#FF8FB1", hover="#FF6F91"):
        btn = tk.Button(parent, text=text, command=command, bg=color, fg="#FFFFFF", bd=0, relief="flat",
                        font=PF(12), padx=12, pady=5, cursor="hand2", activebackground=hover, activeforeground="#FFFFFF")
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn
    body1 = make_card("主题配色", "🎨")
    presets = {
        "🌸 樱花粉": {"bg_top": "#FFE4EC", "bg_bottom": "#FFF0F5", "card_bg": "#FFFFFF", "card_border": "#C2185B", "title_color": "#C2185B", "subtitle_color": "#F48FB1", "status_color": "#BA68C8", "btn1": "#FF8FB1", "btn1_hover": "#FF6F91", "btn2": "#FFA8C5", "btn2_hover": "#FF8FB1", "btn3": "#C792EA", "btn3_hover": "#B07CE0", "btn_sync": "#FFB74D", "btn_sync_hover": "#FFA726", "btn_cal": "#81C784", "btn_cal_hover": "#66BB6A", "btn4": "#F48FB1", "btn4_hover": "#E91E63", "footer_color": "#F48FB1"},
        "🌿 薄荷绿": {"bg_top": "#E0F7FA", "bg_bottom": "#F1F8E9", "card_bg": "#FFFFFF", "card_border": "#00695C", "title_color": "#00695C", "subtitle_color": "#4DB6AC", "status_color": "#26A69A", "btn1": "#4DB6AC", "btn1_hover": "#26A69A", "btn2": "#81C784", "btn2_hover": "#66BB6A", "btn3": "#4DD0E1", "btn3_hover": "#26C6DA", "btn_sync": "#FFB74D", "btn_sync_hover": "#FFA726", "btn_cal": "#81C784", "btn_cal_hover": "#66BB6A", "btn4": "#EF9A9A", "btn4_hover": "#E57373", "footer_color": "#4DB6AC"},
        "🌌 星空紫": {"bg_top": "#E8EAF6", "bg_bottom": "#F3E5F5", "card_bg": "#FFFFFF", "card_border": "#4527A0", "title_color": "#4527A0", "subtitle_color": "#7E57C2", "status_color": "#5E35B1", "btn1": "#7E57C2", "btn1_hover": "#5E35B1", "btn2": "#9575CD", "btn2_hover": "#7E57C2", "btn3": "#BA68C8", "btn3_hover": "#AB47BC", "btn_sync": "#FFB74D", "btn_sync_hover": "#FFA726", "btn_cal": "#64B5F6", "btn_cal_hover": "#42A5F5", "btn4": "#F48FB1", "btn4_hover": "#E91E63", "footer_color": "#7E57C2"},
        "🍦 奶油黄": {"bg_top": "#FFF8E1", "bg_bottom": "#FFFDE7", "card_bg": "#FFFFFF", "card_border": "#E65100", "title_color": "#E65100", "subtitle_color": "#FFB74D", "status_color": "#FFA726", "btn1": "#FFB74D", "btn1_hover": "#FFA726", "btn2": "#FFCC80", "btn2_hover": "#FFB74D", "btn3": "#FF8A65", "btn3_hover": "#FF7043", "btn_sync": "#81C784", "btn_sync_hover": "#66BB6A", "btn_cal": "#BA68C8", "btn_cal_hover": "#AB47BC", "btn4": "#EF9A9A", "btn4_hover": "#E57373", "footer_color": "#FFB74D"},
        "🌙 暗夜黑": {"bg_top": "#263238", "bg_bottom": "#37474F", "card_bg": "#455A64", "card_border": "#FFD54F", "title_color": "#FFD54F", "subtitle_color": "#FFB74D", "status_color": "#4DD0E1", "btn1": "#546E7A", "btn1_hover": "#607D8B", "btn2": "#455A64", "btn2_hover": "#546E7A", "btn3": "#5C6BC0", "btn3_hover": "#3F51B5", "btn_sync": "#FFB74D", "btn_sync_hover": "#FFA726", "btn_cal": "#E57373", "btn_cal_hover": "#EF5350", "btn4": "#E57373", "btn4_hover": "#EF5350", "footer_color": "#FFB74D"},
        "🕹️ 8-bit": {"bg_top": "#1A1A2E", "bg_bottom": "#16213E", "card_bg": "#0F3460", "card_border": "#E94560", "title_color": "#E94560", "subtitle_color": "#F5A623", "status_color": "#00D9FF", "btn1": "#E94560", "btn1_hover": "#FF6B81", "btn2": "#F5A623", "btn2_hover": "#FFC857", "btn3": "#00D9FF", "btn3_hover": "#4DE8FF", "btn_sync": "#9B59B6", "btn_sync_hover": "#B07CE0", "btn_cal": "#2ECC71", "btn_cal_hover": "#27AE60", "btn4": "#9B59B6", "btn4_hover": "#B07CE0", "footer_color": "#F5A623"},
    }
    def apply_preset(name):
        for k, v in presets[name].items(): theme[k] = v
        redraw_all()
    preset_grid = tk.Frame(body1, bg="#FFFFFF")
    preset_grid.pack(fill="x")
    for i, name in enumerate(presets.keys()):
        b = tk.Button(preset_grid, text=name, command=lambda n=name: apply_preset(n), bg="#FFFFFF", fg="#C2185B", bd=2, relief="solid", padx=8, pady=6, font=PF(12), cursor="hand2", activebackground="#FFE4EC")
        b.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="ew")
    for c in range(3): preset_grid.columnconfigure(c, weight=1)
    body2 = make_card("字体颜色", "✍️")
    def make_color_row(parent, label_text, key):
        row = tk.Frame(parent, bg="#FFFFFF"); row.pack(fill="x", pady=4)
        tk.Label(row, text=label_text, font=PF(12), bg="#FFFFFF", fg="#555", width=10, anchor="w").pack(side="left")
        swatch = tk.Label(row, text="  ", bg=theme[key], width=4, relief="solid", bd=2); swatch.pack(side="left", padx=8)
        def pick():
            c = colorchooser.askcolor(color=theme[key], title=f"选择{label_text}")[1]
            if c: theme[key] = c; swatch.config(bg=c); redraw_all()
        pixel_btn(row, "🎨 选择", pick, "#FFA8C5", "#FF8FB1").pack(side="left")
    make_color_row(body2, "标题颜色", "title_color"); make_color_row(body2, "副标题色", "subtitle_color")
    make_color_row(body2, "状态文字", "status_color"); make_color_row(body2, "底部文字", "footer_color")
    body3 = make_card("飘落粒子", "🌸")
    particle_types = [("🌸 樱花", "sakura"), ("❄️ 雪花", "snow"), ("⭐ 星星", "star"), ("💗 爱心", "heart"), ("🍂 落叶", "leaf"), ("🚫 关闭", "none")]
    type_grid = tk.Frame(body3, bg="#FFFFFF"); type_grid.pack(fill="x", pady=4)
    def set_particle_type(ptype):
        theme["particle_type"] = ptype; global particles; particles = []
        if particle_canvas and particle_canvas.winfo_exists(): particle_canvas.delete("particle")
    for i, (label, ptype) in enumerate(particle_types):
        b = tk.Button(type_grid, text=label, command=lambda p=ptype: set_particle_type(p), bg="#FFFFFF", fg="#C2185B", bd=2, relief="solid", padx=8, pady=6, font=PF(12), cursor="hand2", activebackground="#FFE4EC")
        b.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="ew")
    for c in range(3): type_grid.columnconfigure(c, weight=1)
    count_row = tk.Frame(body3, bg="#FFFFFF"); count_row.pack(fill="x", pady=(10, 4))
    tk.Label(count_row, text="粒子数量：", font=PF(12), bg="#FFFFFF", fg="#555").pack(side="left")
    count_val = tk.Label(count_row, text=str(theme["particle_count"]), font=PF(12), bg="#FFFFFF", fg="#C2185B", width=3); count_val.pack(side="left")
    def on_count_change(v): theme["particle_count"] = int(float(v)); count_val.config(text=str(theme["particle_count"]))
    scale = tk.Scale(body3, from_=0, to=80, orient="horizontal", command=on_count_change, bg="#FFFFFF", fg="#C2185B", troughcolor="#FFE4EC", highlightthickness=0, length=380, showvalue=False, sliderrelief="flat", activebackground="#FF8FB1")
    scale.set(theme["particle_count"]); scale.pack(fill="x", pady=4)
    bottom = tk.Frame(win, bg="#FFF0F5"); bottom.pack(side="bottom", fill="x", pady=10)
    done_btn = tk.Button(bottom, text="✨  完 成  ✨", command=win.destroy, bg="#C2185B", fg="#FFFFFF", bd=0, relief="flat", padx=40, pady=8, font=PF(12), cursor="hand2", activebackground="#E91E63")
    done_btn.pack()

def redraw_background():
    bg_canvas.delete("bg_grad")
    w = bg_canvas.winfo_width() or 560; h = bg_canvas.winfo_height() or 720
    draw_pixel_gradient(bg_canvas, w, h, theme["bg_top"], theme["bg_bottom"])

def add_pixel_border(widget, color, thickness=3):
    widget.configure(highlightbackground=color, highlightthickness=thickness, highlightcolor=color, bd=0)

def redraw_all():
    redraw_background()
    root.configure(bg=theme["bg_bottom"]); main_frame.configure(bg=theme["bg_bottom"]); bg_canvas.configure(bg=theme["bg_bottom"])
    header_frame.configure(bg=theme["card_bg"]); add_pixel_border(header_frame, theme["card_border"], 3)
    title_label.configure(bg=theme["card_bg"]); subtitle_label.configure(bg=theme["card_bg"], fg=theme["subtitle_color"]); status_label.configure(bg=theme["card_bg"], fg=theme["status_color"])
    button_container.configure(bg=theme["bg_top"])
    for btn in cat_buttons: btn.configure(bg=theme["bg_top"]); btn.draw()
    footer_frame.configure(bg=theme["bg_top"])
    footer_label.configure(bg=theme["bg_top"], fg=theme["footer_color"])
    paw_label.configure(bg=theme["bg_top"], fg=theme["footer_color"])
    root.update_idletasks() 

settings_btn = tk.Button(main_frame, text="🎨", font=("Segoe UI Emoji", 14), bg="#FFFFFF", fg="#C2185B", bd=2, relief="solid", cursor="hand2", command=open_settings, activebackground="#FFE4EC")
settings_btn.place(relx=1.0, x=-50, y=8, width=40, height=40)

title_breath = [0]
def breathe_title():
    title_breath[0] = (title_breath[0] + 1) % 60
    t = (math.sin(title_breath[0] * 0.1) + 1) / 2
    c1 = theme["title_color"]; c2 = theme["subtitle_color"]
    r1, g1, b1 = root.winfo_rgb(c1); r2, g2, b2 = root.winfo_rgb(c2)
    r = int((r1 + (r2 - r1) * t) // 256); g = int((g1 + (g2 - g1) * t) // 256); b = int((b1 + (b2 - b1) * t) // 256)
    title_label.config(fg=f"#{r:02x}{g:02x}{b:02x}")
    root.after(100, breathe_title)

def on_resize(event):
    if event.widget == root:
        redraw_background(); sync_particle_overlay()
        for btn in cat_buttons: btn.draw()
root.bind("<Configure>", on_resize)

root.after(100, redraw_background); root.after(200, create_particle_overlay); root.after(300, particle_loop); root.after(500, breathe_title)
def sync_loop(): sync_particle_overlay(); root.after(100, sync_loop)
root.after(600, sync_loop)
root.protocol("WM_DELETE_WINDOW", safe_exit)

threading.Thread(target=start_services, daemon=True).start()
def update_status():
    time.sleep(4)
    status_label.config(text="✅ 后台服务已就绪，请点击上方按钮", fg="#66BB6A")
threading.Thread(target=update_status, daemon=True).start()

root.mainloop()