"""
CapCut Auto - Python Edition v2
Requires: pip install pyautogui opencv-python pillow requests pyperclip keyboard
Fixes:
  - Chọn file: paste full path vào ô File name (không dùng Alt+N không đáng tin)
  - Resume: nhớ vị trí lỗi, nút F3 chạy lại từ video bị dừng
  - Thứ tự video: sort theo tên file (001, 002, ...)
"""

import threading
import time
import os
import glob
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import pyautogui
import pyperclip
import requests
import keyboard

# ─────────────────────────────────────────────
# CẤU HÌNH
# ─────────────────────────────────────────────
KILL_SWITCH_URL = "https://gist.githubusercontent.com/tranducanh18/19faff47fe5f7193177e7ceee951a5ea/raw/noHandEdit.txt"
CONFIDENCE    = 0.80
POLL_INTERVAL = 0.3

pyautogui.PAUSE    = 0.05
pyautogui.FAILSAFE = True   # Di chuột góc trên-trái để dừng khẩn cấp

# ─────────────────────────────────────────────
# TÊN FILE ẢNH (đặt cùng thư mục script)
# ─────────────────────────────────────────────
IMG = {
    "audio_tab"         : "audio_tab.png",
    "noi_dung_lon_tieng": "noi_dung_lon_tieng.png",
    "xuat_video"        : "xuat_video.png",
    "xuat_video_loi"    : "xuat_video_loi.png",
    "file_btn"          : "file.png",
    "hoan_tat"          : "hoan_tat.png",
    "xoa"               : "xoa.png",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# KILL SWITCH
# ─────────────────────────────────────────────
def check_kill_switch():
    try:
        r = requests.get(KILL_SWITCH_URL + f"?t={int(time.time())}", timeout=5)
        if r.status_code == 200 and r.text.strip() == "off":
            messagebox.showwarning("Thông báo",
                "Script đã bị tạm dừng bởi tác giả. Vui lòng thử lại sau.")
            return False
    except Exception:
        pass
    return True


# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CapCut Auto — Python v2")
        self.root.resizable(True, True)

        self._running        = False
        self._thread         = None
        # Resume state
        self._resume_index   = None   # None = chưa có gì để resume
        self._saved_prompts  = []
        self._saved_videos   = []
        self._saved_folder   = ""

        self._build_ui()
        self._bind_hotkeys()

    # ── UI ───────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 8, "pady": 3}

        tk.Label(self.root,
                 text="Nhập các prompt (cách nhau bằng 1 dòng trống = 1 video):") \
            .pack(anchor="w", **pad)
        self.prompt_box = scrolledtext.ScrolledText(
            self.root, width=72, height=16, font=("Segoe UI", 10))
        self.prompt_box.pack(fill="both", expand=True, **pad)

        # Thư mục
        fr_folder = tk.Frame(self.root)
        fr_folder.pack(fill="x", **pad)
        tk.Label(fr_folder, text="Thư mục video:").pack(side="left")
        self.folder_var = tk.StringVar(value=r"D:\python\hotkry")
        tk.Entry(fr_folder, textvariable=self.folder_var, width=52) \
            .pack(side="left", padx=4)
        tk.Button(fr_folder, text="Browse", command=self._browse).pack(side="left")

        # Confidence
        fr_conf = tk.Frame(self.root)
        fr_conf.pack(fill="x", **pad)
        tk.Label(fr_conf, text="Confidence:").pack(side="left")
        self.conf_var = tk.DoubleVar(value=CONFIDENCE)
        tk.Scale(fr_conf, variable=self.conf_var, from_=0.5, to=1.0,
                 resolution=0.01, orient="horizontal", length=180,
                 showvalue=True).pack(side="left")

        # Buttons
        fr_btn = tk.Frame(self.root)
        fr_btn.pack(**pad)

        self.btn_start = tk.Button(
            fr_btn, text="▶ Bắt đầu (F1)", width=17, height=2,
            bg="#4CAF50", fg="white", command=self._start)
        self.btn_start.pack(side="left", padx=3)

        self.btn_stop = tk.Button(
            fr_btn, text="■ Dừng (F2)", width=14, height=2,
            bg="#f44336", fg="white", command=self._stop)
        self.btn_stop.pack(side="left", padx=3)

        self.btn_resume = tk.Button(
            fr_btn, text="↺ Làm lại từ lỗi (F3)", width=20, height=2,
            bg="#FF9800", fg="white", command=self._resume,
            state="disabled")
        self.btn_resume.pack(side="left", padx=3)

        # Resume info label
        self.resume_info_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.resume_info_var,
                 fg="#FF6600", font=("Segoe UI", 9, "italic")) \
            .pack(anchor="w", padx=8)

        # Status
        self.status_var = tk.StringVar(value="Trạng thái: Chờ...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)

        # Log
        tk.Label(self.root, text="Log:").pack(anchor="w", padx=8)
        self.log_box = scrolledtext.ScrolledText(
            self.root, width=72, height=9, state="disabled",
            font=("Consolas", 9))
        self.log_box.pack(fill="both", **pad)

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def _bind_hotkeys(self):
        keyboard.add_hotkey("F1", self._start)
        keyboard.add_hotkey("F2", self._stop)
        keyboard.add_hotkey("F3", self._resume)

    # ── Log / Status ─────────────────────────
    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_box.config(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        print(line, end="")

    def set_status(self, msg: str):
        self.status_var.set(f"Trạng thái: {msg}")

    def _set_resume_available(self, index: int, video_name: str):
        """Kích hoạt nút Resume và hiển thị thông tin."""
        self._resume_index = index
        self.btn_resume.config(state="normal")
        self.resume_info_var.set(
            f"⚠️ Bị dừng tại video #{index+1}: {video_name}  — nhấn F3 để tiếp tục")

    def _clear_resume(self):
        self._resume_index  = None
        self.btn_resume.config(state="disabled")
        self.resume_info_var.set("")

    # ── Start / Stop / Resume ─────────────────
    def _start(self):
        if self._running:
            messagebox.showinfo("Đang chạy", "Nhấn F2 để dừng trước.")
            return
        if not check_kill_switch():
            return
        self._clear_resume()
        self._running = True
        self._thread  = threading.Thread(
            target=self._run, kwargs={"start_index": 0}, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self.set_status("Đã dừng.")
        self.log("⛔ Người dùng dừng script.")

    def _resume(self):
        if self._running:
            messagebox.showinfo("Đang chạy", "Nhấn F2 để dừng trước.")
            return
        if self._resume_index is None:
            messagebox.showinfo("Thông báo", "Chưa có lỗi nào để làm lại.")
            return
        if not check_kill_switch():
            return
        idx = self._resume_index
        self._clear_resume()
        self._running = True
        self.log(f"↺ Resume từ video #{idx+1}...")
        self._thread  = threading.Thread(
            target=self._run, kwargs={"start_index": idx}, daemon=True)
        self._thread.start()

    # ── Core helper ──────────────────────────
    def _ci(self, img_key: str, conf: float,
            timeout: int = 10000, ox: int = 0, oy: int = 0,
            action: str = "click"):
        """
        Chờ ảnh xuất hiện rồi click (hoặc chỉ trả về loc nếu action='none').
        Trả về loc nếu tìm thấy, False nếu timeout / bị dừng.
        """
        path     = os.path.join(SCRIPT_DIR, IMG[img_key])
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            if not self._running:
                return False
            try:
                loc = pyautogui.locateOnScreen(path, confidence=conf)
                if loc:
                    if action == "click":
                        cx, cy = pyautogui.center(loc)
                        pyautogui.click(cx + ox, cy + oy)
                    return loc
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)
        self.log(f"❌ Timeout: {IMG[img_key]}")
        return False

    def _wait_done(self, conf: float, timeout: int = 600) -> bool:
        """Chờ hoan_tat.png trong timeout giây."""
        deadline = time.time() + timeout
        path     = os.path.join(SCRIPT_DIR, IMG["hoan_tat"])
        while time.time() < deadline:
            if not self._running:
                return False
            try:
                if pyautogui.locateOnScreen(path, confidence=conf):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    # ─────────────────────────────────────────
    # HÀM CHỌN FILE — paste full path vào ô File name
    # Logic: hộp thoại đang mở → click vào ô "File name" → xóa → paste → Enter
    # ─────────────────────────────────────────
    def _select_file_in_dialog(self, full_path: str):
        """
        Sau khi hộp thoại Open đã hiện, paste đường dẫn đầy đủ vào ô File name.
        Cách đáng tin nhất: click thẳng vào ô File name (dưới cùng hộp thoại),
        sau đó Ctrl+A → paste → Enter.
        """
        # Chờ hộp thoại xuất hiện (1.2s là đủ với máy bình thường)
        time.sleep(1.2)

        # Copy path vào clipboard
        pyperclip.copy(full_path)

        # Click vào ô "File name:" — dùng keyboard shortcut Windows chuẩn:
        # Alt+D focus thanh địa chỉ, nhưng với Save/Open dialog thì dùng:
        # Tab liên tục để đến ô File name KHÔNG ổn định.
        # Cách chắc nhất: gõ thẳng vào — khi hộp thoại mới mở,
        # Windows tự focus vào ô File name sẵn.
        pyautogui.hotkey("ctrl", "a")   # chọn hết text cũ trong ô
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "v")   # paste đường dẫn
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.5)

    # ─────────────────────────────────────────
    # VÒNG LẶP CHÍNH
    # ─────────────────────────────────────────
    def _run(self, start_index: int = 0):
        # --- Lấy prompt ---
        raw     = self.prompt_box.get("1.0", "end")
        blocks  = [b.strip() for b in raw.split("\n\n")]
        prompts = [b for b in blocks if b]

        if not prompts:
            messagebox.showerror("Lỗi", "Vui lòng nhập ít nhất 1 prompt!")
            self._running = False
            return

        # --- Lấy và sort video theo tên (001, 002, ...) ---
        folder = self.folder_var.get().strip()
        if not os.path.isdir(folder):
            messagebox.showerror("Lỗi", f"Thư mục không tồn tại:\n{folder}")
            self._running = False
            return

        videos = []
        for ext in ("*.mp4", "*.avi", "*.mov"):
            videos.extend(glob.glob(os.path.join(folder, ext)))
        videos = sorted(videos, key=lambda p: os.path.basename(p).lower())
        video_names = [os.path.basename(v) for v in videos]

        if not videos:
            messagebox.showerror("Lỗi", "Không tìm thấy video trong thư mục!")
            self._running = False
            return

        # Lưu lại để resume sau
        self._saved_prompts = prompts
        self._saved_videos  = videos
        self._saved_folder  = folder

        total = min(len(prompts), len(videos))
        conf  = self.conf_var.get()

        self.log(f"{'↺ Resume' if start_index > 0 else '▶ Bắt đầu'} từ #{start_index+1} "
                 f"— {len(videos)} video, {len(prompts)} prompt → {total} vòng.")

        # ── VÒNG LẶP ─────────────────────────
        for i in range(start_index, total):
            if not self._running:
                break

            prompt    = prompts[i]
            full_path = videos[i]
            video     = video_names[i]

            self.set_status(f"Vòng {i+1}/{total} — {video}")
            self.log(f"=== Vòng {i+1}/{total}: {video} ===")

            # ── Bước 1: Vòng 2+: xóa video cũ ──
            if i > 0:
                self.log("Tìm nút xóa...")
                if not self._ci("xoa", conf, timeout=10000):
                    self._set_resume_available(i, video)
                    self._running = False
                    break
                time.sleep(0.3)
                pyautogui.press("enter")
                time.sleep(0.8)
                self.log("✓ Đã xóa video cũ.")

            # ── Bước 2: Click nút mở file ────────
            self.log("Tìm nút file...")
            if not self._ci("file_btn", conf, timeout=10000):
                self._set_resume_available(i, video)
                self._running = False
                break

            # ── Bước 3: Paste path vào hộp thoại ──
            # Hộp thoại Open vừa bật lên, focus mặc định vào ô File name
            self._select_file_in_dialog(full_path)
            self.log(f"✓ Đã chọn file: {video}")

            # ── Bước 4: Vòng 1 click tab Audio ─────
            if i == 0:
                self.log("Tìm audio_tab...")
                if not self._ci("audio_tab", conf, timeout=8000):
                    self._set_resume_available(i, video)
                    self._running = False
                    break
                time.sleep(0.5)
                self.log("✓ Đã click audio_tab.")

            # ── Bước 5: Xóa text cũ (phòng thủ) ───
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.15)

            # ── Bước 6: Tìm label → click vùng text ─
            self.log("Tìm noi_dung_lon_tieng...")
            loc = self._ci("noi_dung_lon_tieng", conf, timeout=8000, action="none")
            if not loc:
                self._set_resume_available(i, video)
                self._running = False
                break
            cx, cy = pyautogui.center(loc)
            pyautogui.click(cx + 30, cy + 50)
            time.sleep(0.5)

            # ── Bước 7: Xóa rồi paste prompt ────────
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.15)
            pyperclip.copy(prompt)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.4)
            short = prompt[:55] + ("..." if len(prompt) > 55 else "")
            self.log(f"✓ Prompt: {short}")

            # ── Bước 8: Click xuất video ─────────────
            self.log("Tìm nút xuất video...")
            loc_xuat = None
            for key in ("xuat_video", "xuat_video_loi"):
                try:
                    p = os.path.join(SCRIPT_DIR, IMG[key])
                    loc_xuat = pyautogui.locateOnScreen(p, confidence=conf)
                except Exception:
                    pass
                if loc_xuat:
                    self.log(f"✓ Tìm thấy {key}.")
                    break

            if not loc_xuat:
                self.log("❌ Không tìm thấy nút xuất video!")
                self._set_resume_available(i, video)
                self._running = False
                break

            ex, ey = pyautogui.center(loc_xuat)
            pyautogui.click(ex + 30, ey + 15)
            time.sleep(1.0)
            self.log("✓ Đã click xuất video.")

            # ── Bước 9: Chờ Hoàn tất (10 phút) ──────
            self.set_status(f"Vòng {i+1} — Đang xuất, chờ hoàn tất...")
            self.log("Chờ hoàn tất...")
            if not self._wait_done(conf, timeout=600):
                self.log(f"⚠️ Timeout hoàn tất ở vòng {i+1}")
                self._set_resume_available(i, video)
                self._running = False
                break

            time.sleep(0.5)
            self.log("✓ Hoàn tất! Nhấn Enter.")
            pyautogui.press("enter")
            time.sleep(0.8)

        # ── KẾT THÚC ─────────────────────────────
        if self._running:
            msg = f"✅ Hoàn thành {total} video!"
            self.set_status(msg)
            self.log(msg)
            messagebox.showinfo("Xong!", msg)
            self._clear_resume()
        self._running = False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = App(root)
    root.mainloop()