import os
import sys
import threading
import json
import re
import io
import base64
import ctypes
import hashlib
import difflib
import webbrowser
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, font, colorchooser
from PIL import Image, ImageGrab, ImageDraw, ImageEnhance, ImageTk, ImageFilter, ImageOps
import keyboard
import pystray
import pyperclip
import requests
import urllib3
import certifi
import charset_normalizer
import idna
import cryptography
from cryptography.fernet import Fernet

from gemini_engine import GeminiVisionEngine
from usage_tracker import DailyUsageTracker
from overlay_snipper import OverlaySnipper
from popup_editor import PopupEditor
from batch_processor import BatchProcessorWindow
from text_cleaner import TextCleaner
from auth_manager import AuthManager
from dpi_helper import DPIHelper
from auto_updater import AutoUpdater, CURRENT_VERSION
import spell_checker
from spell_checker import DiffCompareDialog, SpellCorrector


class BookEditorOCRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BookEditor OCR")

        try:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
            with open(os.path.join(exe_dir, "startup_check.log"), "w", encoding="utf-8") as f:
                f.write("GUI_LOOP_ENTERED_SUCCESS\n")
            self._apply_native_taskbar_icon(exe_dir)
        except Exception:
            pass

        self.font_family = "Malgun Gothic"
        self.root.configure(bg="#f8f9fa")
        self._apply_window_size()

        # 1. 소나무디자인 사내 1회 인증 체크
        if not AuthManager.check_auth_or_prompt(self.root):
            self.root.destroy()
            sys.exit(0)

        # 2. 100% Gemini Flash 비전 AI 엔진 탑재 (5개 키 라운드로빈 풀)
        self.ai_engine = GeminiVisionEngine()
        self.history_items: list[str] = []
        self.hotkey = "F4"
        self.tray_icon = None
        self._is_capturing = False

        self._build_ui()
        self._register_hotkey()
        self._init_tray_icon()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)
        # 상단 메뉴바 구성 (보기, 도움말)
        self._init_menu_bar()
        self._bind_font_shortcuts()

        # 프로그램 시작 시 자동 업데이트 확인
        AutoUpdater.check_on_startup(self.root)

    def _apply_window_size(self):
        font_scale = DPIHelper.get_user_font_scale()
        scale_mult = 1.0 + (font_scale - 1.0) * 0.45
        win_w = int(DPIHelper.scale(680) * scale_mult)
        win_h = int(DPIHelper.scale(620) * scale_mult)
        min_w = int(DPIHelper.scale(580) * scale_mult)
        min_h = int(DPIHelper.scale(520) * scale_mult)
        self.root.minsize(min_w, min_h)
        cur_w = self.root.winfo_width()
        cur_h = self.root.winfo_height()
        if cur_w < win_w or cur_h < win_h:
            self.root.geometry(f"{win_w}x{win_h}")

    def _apply_native_taskbar_icon(self, exe_dir: str):
        bundle_dir = getattr(sys, "_MEIPASS", exe_dir)
        search_dirs = [bundle_dir, exe_dir, os.getcwd()]

        icon_ico = None
        icon_png = None
        for d in search_dirs:
            cand_ico = os.path.join(d, "app_icon.ico")
            if not icon_ico and os.path.exists(cand_ico):
                icon_ico = cand_ico
            cand_png = os.path.join(d, "app_icon.png")
            if not icon_png and os.path.exists(cand_png):
                icon_png = cand_png

        # 1. Tkinter iconbitmap (.ico) & iconphoto (.png)
        if icon_ico:
            try:
                self.root.iconbitmap(default=icon_ico)
            except Exception:
                try:
                    self.root.iconbitmap(icon_ico)
                except Exception:
                    pass

        if icon_png:
            try:
                self._icon_img = tk.PhotoImage(file=icon_png)
                self.root.iconphoto(True, self._icon_img)
            except Exception:
                pass

        # 2. Windows 11 Native Win32 WM_SETICON (작업표시줄 및 창 핸들 직접 주입)
        if icon_ico:
            try:
                user32 = ctypes.windll.user32
                LR_LOADFROMFILE = 0x00000010
                IMAGE_ICON = 1
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                self.root.update_idletasks()
                hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                hicon_big = user32.LoadImageW(None, icon_ico, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                hicon_small = user32.LoadImageW(None, icon_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if hicon_big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                if hicon_small:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            except Exception:
                pass

    def _init_menu_bar(self):
        menubar = tk.Menu(self.root)

        # 1. 보기(View) 메뉴
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="글자 크기 크게  (+)", command=self._on_font_larger, accelerator="Ctrl++")
        view_menu.add_command(label="글자 크기 작게  (-)", command=self._on_font_smaller, accelerator="Ctrl+-")
        view_menu.add_separator()
        view_menu.add_command(label="글자 크기 기본값", command=self._on_font_reset, accelerator="Ctrl+0")
        menubar.add_cascade(label="보기", menu=view_menu)

        # 2. 도움말(Help) 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=f"업데이트 확인 (v{CURRENT_VERSION})...", command=lambda: AutoUpdater.check_for_updates(self.root, silent=False))
        help_menu.add_separator()
        help_menu.add_command(label="단축키 안내 (F4 화면 캡처)", command=self._show_shortcut_info)
        help_menu.add_command(label="정식 라이선스 상태", command=self._show_license_info)
        help_menu.add_command(label="소나무 BookEditor OCR 정보", command=self._show_about_info)
        menubar.add_cascade(label="도움말", menu=help_menu)

        self.root.config(menu=menubar)

    def _bind_font_shortcuts(self):
        self.root.bind_all("<Control-plus>", lambda e: self._on_font_larger())
        self.root.bind_all("<Control-equal>", lambda e: self._on_font_larger())
        self.root.bind_all("<Control-minus>", lambda e: self._on_font_smaller())
        self.root.bind_all("<Control-0>", lambda e: self._on_font_reset())

    def _show_shortcut_info(self):
        messagebox.showinfo(
            "단축키 안내",
            "• [ F4 ] : 화면 영역 지정 캡처 및 OCR 자동 전사\n• [ Ctrl + + ] : 글자 크기 한 단계 확대\n• [ Ctrl + - ] : 글자 크기 한 단계 축소\n• [ Ctrl + 0 ] : 글자 크기 기본값 복원",
            parent=self.root
        )

    def _show_license_info(self):
        messagebox.showinfo(
            "정식 라이선스 안내",
            "• 상태: 정상 인증 완료 (소나무디자인 정식 라이선스)\n• 인증 저장소: Windows 로컬 시스템 보안 영역 (%LOCALAPPDATA%)\n• 기기 고유 HWID 기반으로 안전하게 보호되고 있습니다.",
            parent=self.root
        )

    def _show_about_info(self):
        messagebox.showinfo(
            "BookEditor OCR 정보",
            f"소나무 BookEditor OCR (v{CURRENT_VERSION})\n\n출판 디자이너를 위한 고정밀 도서 본문 OCR & 교정 프로그램\n• 제조: 소나무디자인 (Sonamu Design)\n• 문의: 032-465-8195",
            parent=self.root
        )

    def _on_font_smaller(self):
        DPIHelper.decrease_font_scale()
        self._refresh_ui_fonts()

    def _on_font_larger(self):
        DPIHelper.increase_font_scale()
        self._refresh_ui_fonts()

    def _on_font_reset(self):
        DPIHelper.reset_font_scale()
        self._refresh_ui_fonts()

    def _refresh_ui_fonts(self):
        for child in self.root.winfo_children():
            child.destroy()
        self._apply_window_size()
        self._init_menu_bar()
        self._build_ui()
        self._refresh_history_listbox()
        self.lbl_status.config(text="글자 크기가 변경되었습니다. (보기 메뉴 또는 Ctrl + / - 로 조절)")

    def _build_ui(self):
        # 상단 헤더
        header = tk.Frame(self.root, bg="#212529", padx=DPIHelper.scale(16), pady=DPIHelper.scale(12))
        header.pack(fill=tk.X)

        # 헤더 좌측: 타이틀 및 단축키 안내
        title_frame = tk.Frame(header, bg="#212529")
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        title_lbl = tk.Label(
            title_frame,
            text="BookEditor OCR",
            font=DPIHelper.font(self.font_family, 13, "bold"),
            bg="#212529",
            fg="#ffffff"
        )
        title_lbl.pack(anchor=tk.W)

        subtitle_lbl = tk.Label(
            title_frame,
            text=f"단축키: [ {self.hotkey} ] (영역 드래그 즉시 추출)",
            font=DPIHelper.font(self.font_family, 9),
            bg="#212529",
            fg="#adb5bd"
        )
        subtitle_lbl.pack(anchor=tk.W, pady=(DPIHelper.scale(3), 0))

        # 헤더 우측: 깔끔한 버전 뱃지
        badge_frame = tk.Frame(header, bg="#212529")
        badge_frame.pack(side=tk.RIGHT, fill=tk.Y)

        lbl_badge = tk.Label(
            badge_frame,
            text=f"v{CURRENT_VERSION}",
            font=DPIHelper.font(self.font_family, 9),
            bg="#212529",
            fg="#6c757d"
        )
        lbl_badge.pack(anchor=tk.E, pady=(DPIHelper.scale(4), 0))

        # 메인 액션 버튼 영역
        action_frame = tk.Frame(self.root, bg="#f8f9fa", padx=DPIHelper.scale(16), pady=DPIHelper.scale(12))
        action_frame.pack(fill=tk.X)

        # 1. 캡처 버튼 (대형 하이라이트)
        btn_capture = tk.Button(
            action_frame,
            text=f"화면 캡처 ({self.hotkey})",
            command=self.trigger_capture,
            bg="#0d6efd",
            fg="#ffffff",
            activebackground="#0b5ed7",
            activeforeground="#ffffff",
            font=DPIHelper.font(self.font_family, 11, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(16),
            pady=DPIHelper.scale(10),
            cursor="hand2"
        )
        btn_capture.pack(fill=tk.X, pady=(0, DPIHelper.scale(8)))

        # 2. 보조 버튼군
        sub_btn_frame = tk.Frame(action_frame, bg="#f8f9fa")
        sub_btn_frame.pack(fill=tk.X)

        btn_clipboard = tk.Button(
            sub_btn_frame,
            text="클립보드 이미지 추출",
            command=self.trigger_clipboard_ocr,
            bg="#198754",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 10, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(12),
            pady=DPIHelper.scale(8),
            cursor="hand2"
        )
        btn_clipboard.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, DPIHelper.scale(4)))

        btn_batch = tk.Button(
            sub_btn_frame,
            text="사진 일괄 변환",
            command=self.open_batch_processor,
            bg="#495057",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 10, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(12),
            pady=DPIHelper.scale(8),
            cursor="hand2"
        )
        btn_batch.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(DPIHelper.scale(4), 0))

        # 최근 캡처 히스토리
        history_frame = tk.LabelFrame(
            self.root,
            text=" 최근 캡처 내역 ",
            bg="#f8f9fa",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            padx=DPIHelper.scale(10),
            pady=DPIHelper.scale(6)
        )
        history_frame.pack(fill=tk.BOTH, expand=True, padx=DPIHelper.scale(16), pady=(0, DPIHelper.scale(8)))

        list_container = tk.Frame(history_frame, bg="#ffffff")
        list_container.pack(fill=tk.BOTH, expand=True)

        self.history_listbox = tk.Listbox(
            list_container,
            font=DPIHelper.font(self.font_family, 9),
            selectmode=tk.SINGLE,
            bd=0,
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=DPIHelper.scale(4), pady=DPIHelper.scale(4))

        self.history_listbox.bind("<Double-Button-1>", lambda e: self._copy_selected_history())

        hist_btn_bar = tk.Frame(history_frame, bg="#f8f9fa")
        hist_btn_bar.pack(fill=tk.X, pady=(DPIHelper.scale(6), 0))

        btn_copy_hist = tk.Button(
            hist_btn_bar,
            text="선택 복사",
            command=self._copy_selected_history,
            bg="#212529",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(10),
            pady=DPIHelper.scale(3),
            cursor="hand2"
        )
        btn_copy_hist.pack(side=tk.LEFT)

        btn_clear_hist = tk.Button(
            hist_btn_bar,
            text="내역 삭제",
            command=self._clear_history,
            bg="#ced4da",
            fg="#212529",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(3),
            cursor="hand2"
        )
        btn_clear_hist.pack(side=tk.RIGHT)

        # 하단 상태표시줄
        statusbar = tk.Frame(self.root, bg="#e9ecef", height=DPIHelper.scale(24))
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            statusbar,
            text="준비",
            font=DPIHelper.font(self.font_family, 8),
            bg="#e9ecef",
            fg="#495057"
        )
        self.lbl_status.pack(side=tk.LEFT, padx=DPIHelper.scale(10), pady=DPIHelper.scale(2))

        # 하단 회사 정보
        company_frame = tk.Frame(self.root, bg="#f8f9fa", bd=1, relief=tk.GROOVE, padx=DPIHelper.scale(12), pady=DPIHelper.scale(5))
        company_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=DPIHelper.scale(16), pady=(0, DPIHelper.scale(4)))

        lbl_comp1 = tk.Label(
            company_frame,
            text="ⓒ 소나무디자인 All Rights Reserved.",
            font=DPIHelper.font(self.font_family, 8, "bold"),
            bg="#f8f9fa",
            fg="#495057"
        )
        lbl_comp1.pack(anchor=tk.W)

        lbl_comp2 = tk.Label(
            company_frame,
            text="문의: 032-465-8195 | 인천광역시 인주대로 304 영인빌딩 4층",
            font=DPIHelper.font(self.font_family, 8),
            bg="#f8f9fa",
            fg="#6c757d"
        )
        lbl_comp2.pack(anchor=tk.W)

    def _register_hotkey(self):
        try:
            keyboard.add_hotkey(self.hotkey, lambda: self.root.after(0, self.trigger_capture))
        except Exception as e:
            print(f"Hotkey registration failed: {e}", file=sys.stderr)

    def trigger_capture(self):
        if self._is_capturing:
            return
        if not DailyUsageTracker.can_request():
            count, limit = DailyUsageTracker.get_usage()
            messagebox.showwarning("안내", f"오늘 사용 한도({limit}회)에 도달했습니다.\n내일 00시에 자동 초기화됩니다.", parent=self.root)
            return

        self._is_capturing = True
        self.lbl_status.config(text="영역 드래그 (ESC: 취소)")

        def _on_snipper_done(cropped_img):
            self._is_capturing = False
            if cropped_img:
                self._on_crop_done(cropped_img)
            else:
                self.lbl_status.config(text="준비")

        OverlaySnipper(self.root, on_crop_complete=_on_snipper_done)

    def _on_crop_done(self, cropped_image: Image.Image):
        self.lbl_status.config(text="분석 중...")
        self.root.update_idletasks()

        def ocr_worker():
            try:
                raw_text, raw_lines = self.ai_engine.extract_from_pil(cropped_image)
            except Exception as e:
                raw_text = f"[오류: {e}]"
                raw_lines = [raw_text]

            self.root.after(0, self._show_popup_editor, raw_text, raw_lines, cropped_image)

        threading.Thread(target=ocr_worker, daemon=True).start()

    def _show_popup_editor(self, raw_text: str, raw_lines: list[str], cropped_image: Image.Image):
        self.lbl_status.config(text=f"추출 완료 ({len(raw_lines)}줄)")
        PopupEditor(self.root, raw_text=raw_text, raw_lines=raw_lines, cropped_image=cropped_image, on_history_add=self.add_to_history, ai_engine=self.ai_engine)

    def trigger_clipboard_ocr(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self._on_crop_done(img)
            else:
                messagebox.showinfo("안내", "클립보드에 이미지가 없습니다.", parent=self.root)
        except Exception as e:
            messagebox.showerror("오류", f"클립보드 읽기 오류: {e}", parent=self.root)

    def open_batch_processor(self):
        BatchProcessorWindow(self.root, self.ai_engine)

    def add_to_history(self, text: str):
        if not text:
            return
        if text in self.history_items:
            self.history_items.remove(text)
        self.history_items.insert(0, text)

        if len(self.history_items) > 50:
            self.history_items.pop()

        self._refresh_history_listbox()

    def _refresh_history_listbox(self):
        self.history_listbox.delete(0, tk.END)
        for idx, item in enumerate(self.history_items):
            first_line = item.strip().splitlines()[0] if item.strip() else "(빈 텍스트)"
            preview = (first_line[:45] + "...") if len(first_line) > 45 else first_line
            self.history_listbox.insert(tk.END, f"[{idx+1}] {preview}")

    def _copy_selected_history(self):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.history_items):
            content = self.history_items[idx]
            try:
                pyperclip.copy(content)
            except Exception:
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
            self.lbl_status.config(text="클립보드에 복사되었습니다.")

    def _clear_history(self):
        self.history_items.clear()
        self.history_listbox.delete(0, tk.END)
        self.lbl_status.config(text="내역이 삭제되었습니다.")

    def _create_tray_image(self):
        try:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
            bundle_dir = getattr(sys, "_MEIPASS", exe_dir)
            for d in [bundle_dir, exe_dir, os.getcwd()]:
                cand = os.path.join(d, "app_icon.png")
                if os.path.exists(cand):
                    return Image.open(cand).resize((64, 64), Image.Resampling.LANCZOS)
        except Exception:
            pass
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (13, 110, 253, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle([12, 12, 52, 52], fill=(255, 255, 255, 255))
        draw.line([18, 22, 46, 22], fill=(13, 110, 253, 255), width=3)
        draw.line([18, 32, 46, 32], fill=(13, 110, 253, 255), width=3)
        draw.line([18, 42, 36, 42], fill=(13, 110, 253, 255), width=3)
        return image

    def _init_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem("열기", self._show_from_tray),
            pystray.MenuItem(f"화면 캡처 ({self.hotkey})", lambda: self.root.after(0, self.trigger_capture)),
            pystray.MenuItem("종료", self._quit_app)
        )
        self.tray_icon = pystray.Icon("BookEditorOCR", self._create_tray_image(), "BookEditor OCR", menu)

    def _on_close_window(self):
        self.root.withdraw()
        if not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_from_tray(self, icon=None, item=None):
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)


def main():
    try:
        myappid = "SonamuDesign.BookEditorOCR.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    root = tk.Tk()
    app = BookEditorOCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
