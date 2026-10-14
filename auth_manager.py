import hashlib
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox
from dpi_helper import DPIHelper

MASTER_PW_HASH = "dc73e38c49cff72b85b6c5142b0d9fb0cea4397dcd6691f9ebe4677904b93823"

APP_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SonamuDesign", "BookEditorOCR")
LICENSE_FILE = os.path.join(APP_DATA_DIR, "license.dat")


class AuthManager:
    @classmethod
    def _get_machine_hwid(cls) -> str:
        """기기 고유 식별자 (HWID) 해시 생성 - 순수 os.environ과 hashlib 사용 (누락 위험 0%)"""
        comp = os.environ.get("COMPUTERNAME", "UNKNOWN_PC")
        user = os.environ.get("USERNAME", "USER")
        cpu = os.environ.get("PROCESSOR_IDENTIFIER", "CPU")
        domain = os.environ.get("USERDOMAIN", "DOMAIN")
        raw = f"SONAMU_HWID_{comp}_{user}_{cpu}_{domain}_2026"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _generate_license_token(cls) -> str:
        """기기 고유값과 마스터 해시를 결합한 인증 토큰 생성"""
        hwid = cls._get_machine_hwid()
        return hashlib.sha256(f"{hwid}_{MASTER_PW_HASH}".encode("utf-8")).hexdigest()

    @classmethod
    def is_authenticated(cls) -> bool:
        if not os.path.exists(LICENSE_FILE):
            return False
        try:
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("token")
                expected = cls._generate_license_token()
                return token == expected
        except Exception:
            return False

    @classmethod
    def save_license(cls):
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        try:
            token = cls._generate_license_token()
            hwid_tag = cls._get_machine_hwid()[:16]
            with open(LICENSE_FILE, "w", encoding="utf-8") as f:
                json.dump({"token": token, "device_id": hwid_tag, "auth_by": "SonamuDesign"}, f)
        except Exception as e:
            print(f"Failed to save license: {e}", file=sys.stderr)

    @classmethod
    def check_auth_or_prompt(cls, parent=None) -> bool:
        if cls.is_authenticated():
            return True

        dialog = PasswordDialog(parent)
        return dialog.is_valid


class PasswordDialog(tk.Toplevel):
    def __init__(self, parent=None):
        if parent is None:
            self.temp_root = tk.Tk()
            self.temp_root.withdraw()
            super().__init__(self.temp_root)
        else:
            self.temp_root = None
            super().__init__(parent)

        self.title("소나무디자인 인증")
        win_w = DPIHelper.scale(420)
        win_h = DPIHelper.scale(260)
        self.geometry(f"{win_w}x{win_h}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg="#f8f9fa")
        self.font_family = "Malgun Gothic"

        self.is_valid = False
        self.attempts = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()
        self.focus_force()
        self.wait_window()

    def _build_ui(self):
        header = tk.Frame(self, bg="#212529", padx=DPIHelper.scale(15), pady=DPIHelper.scale(12))
        header.pack(fill=tk.X)

        lbl_title = tk.Label(
            header,
            text="소나무디자인 인증",
            font=DPIHelper.font(self.font_family, 11, "bold"),
            bg="#212529",
            fg="#ffffff"
        )
        lbl_title.pack(anchor=tk.W)

        lbl_desc = tk.Label(
            header,
            text="비밀번호를 입력하세요. (최초 1회)",
            font=DPIHelper.font(self.font_family, 8),
            bg="#212529",
            fg="#adb5bd"
        )
        lbl_desc.pack(anchor=tk.W, pady=(DPIHelper.scale(2), 0))

        body = tk.Frame(self, bg="#f8f9fa", padx=DPIHelper.scale(20), pady=DPIHelper.scale(15))
        body.pack(fill=tk.BOTH, expand=True)

        lbl_guide = tk.Label(
            body,
            text="인증 비밀번호:",
            font=DPIHelper.font(self.font_family, 9),
            bg="#f8f9fa",
            fg="#333333"
        )
        lbl_guide.pack(anchor=tk.W, pady=(0, DPIHelper.scale(6)))

        self.entry_pw = tk.Entry(
            body,
            show="*",
            font=DPIHelper.font(self.font_family, 11),
            bd=1,
            relief=tk.SOLID
        )
        self.entry_pw.pack(fill=tk.X, pady=(0, DPIHelper.scale(10)))
        self.entry_pw.focus_set()
        self.entry_pw.bind("<Return>", lambda e: self._on_confirm())

        btn_box = tk.Frame(body, bg="#f8f9fa")
        btn_box.pack(fill=tk.X)

        btn_confirm = tk.Button(
            btn_box,
            text="확인",
            command=self._on_confirm,
            bg="#0d6efd",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(16),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_confirm.pack(side=tk.RIGHT, padx=(DPIHelper.scale(6), 0))

        btn_cancel = tk.Button(
            btn_box,
            text="취소",
            command=self._on_cancel,
            bg="#6c757d",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(12),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_cancel.pack(side=tk.RIGHT)

        lbl_footer = tk.Label(
            self,
            text="ⓒ 소나무디자인 All Rights Reserved.",
            font=DPIHelper.font(self.font_family, 8),
            bg="#f8f9fa",
            fg="#888888"
        )
        lbl_footer.pack(side=tk.BOTTOM, pady=(0, DPIHelper.scale(6)))

    def _on_confirm(self):
        import hmac
        entered = self.entry_pw.get().strip()
        entered_hash = hashlib.sha256(entered.encode("utf-8")).hexdigest()

        if hmac.compare_digest(entered_hash, MASTER_PW_HASH):
            self.is_valid = True
            AuthManager.save_license()
            messagebox.showinfo("인증 성공", "인증이 완료되었습니다.", parent=self)
            self.destroy()
            if self.temp_root:
                self.temp_root.destroy()
        else:
            self.attempts += 1
            if self.attempts >= 3:
                messagebox.showerror("인증 실패", "비밀번호 3회 오류로 프로그램을 종료합니다.", parent=self)
                self._on_cancel()
            else:
                messagebox.showwarning("오류", f"비밀번호가 일치하지 않습니다. (남은 횟수: {3 - self.attempts})", parent=self)
                self.entry_pw.delete(0, tk.END)

    def _on_cancel(self):
        self.is_valid = False
        self.destroy()
        if self.temp_root:
            self.temp_root.destroy()
