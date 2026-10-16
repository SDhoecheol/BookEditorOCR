import os
import sys
import json
import uuid
import hashlib
import tempfile
import threading
import subprocess
from urllib.parse import urlparse
import requests
import tkinter as tk
from tkinter import messagebox, ttk
from dpi_helper import DPIHelper
from usage_tracker import APP_DATA_DIR

CURRENT_VERSION = "1.1.5"
DEFAULT_CONFIG_PATH = os.path.join(APP_DATA_DIR, "update_config.json")
LOCAL_CONFIG_PATH = os.path.join(os.getcwd(), "update_config.json")

DEFAULT_UPDATE_URL = "https://raw.githubusercontent.com/SDhoecheol/BookEditorOCR/main/version.json"


def get_app_dir() -> str:
    """실행 중인 애플리케이션의 실제 디렉터리 경로 반환"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


class AutoUpdater:
    @classmethod
    def _is_url_trusted(cls, url: str) -> bool:
        """다운로드 URL이 신뢰할 수 있는 공식 GitHub 릴리즈 도메인인지 엄격 검증"""
        if not url or not url.startswith("https://"):
            return False
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            if host in ("github.com", "www.github.com"):
                return parsed.path.startswith("/SDhoecheol/BookEditorOCR/releases/")
            elif host in ("objects.githubusercontent.com", "release-assets.githubusercontent.com"):
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_config() -> dict:
        for p in [LOCAL_CONFIG_PATH, DEFAULT_CONFIG_PATH]:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {
            "update_check_url": DEFAULT_UPDATE_URL,
            "auto_check_on_startup": True
        }

    @staticmethod
    def save_config(cfg: dict):
        try:
            with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def check_for_updates(cls, parent=None, silent=False):
        """수동 또는 자동 업데이트 확인 실행"""
        threading.Thread(
            target=cls._worker_check,
            args=(parent, silent),
            daemon=True
        ).start()

    @classmethod
    def check_on_startup(cls, parent=None):
        """앱 시작 시 최우선 업데이트 확인 (타임아웃 2초)"""
        cfg = cls.get_config()
        if not cfg.get("auto_check_on_startup", True):
            return

        cls.check_for_updates(parent=parent, silent=True)

    @classmethod
    def _worker_check(cls, parent, silent: bool):
        cfg = cls.get_config()
        url = cfg.get("update_check_url", DEFAULT_UPDATE_URL)

        try:
            resp = requests.get(url, timeout=2.5)
            if resp.status_code != 200:
                if not silent and parent:
                    parent.after(0, lambda: messagebox.showwarning(
                        "업데이트 확인",
                        f"업데이트 서버에 연결할 수 없습니다. (코드: {resp.status_code})\n\n잠시 후 다시 시도해 주세요.",
                        parent=parent
                    ))
                return

            info = resp.json()
            latest_ver = str(info.get("latest_version", CURRENT_VERSION)).strip()
            download_url = info.get("download_url", "")
            changelog = info.get("changelog", "안정성 및 성능 개선 패치")
            release_date = info.get("release_date", "")
            expected_sha256 = str(info.get("sha256", "")).strip().lower()

            if cls._is_newer(latest_ver, CURRENT_VERSION):
                if parent:
                    parent.after(0, lambda: cls._show_update_dialog(parent, latest_ver, release_date, changelog, download_url, expected_sha256))
            else:
                if not silent and parent:
                    parent.after(0, lambda: messagebox.showinfo(
                        "업데이트 확인",
                        f"현재 최신 버전(v{CURRENT_VERSION})을 사용 중입니다.\n\n고정밀 OCR 엔진이 정상 연동되어 있습니다.",
                        parent=parent
                    ))
        except Exception as e:
            if not silent and parent:
                parent.after(0, lambda: messagebox.showerror(
                    "업데이트 오류",
                    f"업데이트 정보를 확인하는 중 오류가 발생했습니다:\n{e}",
                    parent=parent
                ))

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """시맨틱 버전 비교 (예: 1.2.0 > 1.1.0)"""
        try:
            l_parts = [int(p) for p in latest.lstrip("v").split(".")]
            c_parts = [int(p) for p in current.lstrip("v").split(".")]
            return l_parts > c_parts
        except Exception:
            return latest != current

    @classmethod
    def _show_update_dialog(cls, parent, latest_ver, release_date, changelog, download_url, expected_sha256=""):
        dlg = tk.Toplevel(parent)
        dlg.title("소나무 BookEditor OCR - 신규 업데이트")
        w, h = DPIHelper.scale(540), DPIHelper.scale(410)
        dlg.geometry(f"{w}x{h}")
        dlg.minsize(w, h)
        dlg.configure(bg="#f8f9fa")
        dlg.transient(parent)
        dlg.grab_set()

        # 헤더
        header = tk.Frame(dlg, bg="#0d6efd", padx=DPIHelper.scale(16), pady=DPIHelper.scale(12))
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"새로운 버전이 출시되었습니다 (v{latest_ver})",
            font=DPIHelper.font("Malgun Gothic", 12, "bold"),
            bg="#0d6efd",
            fg="#ffffff"
        ).pack(anchor=tk.W)

        sub_info = f"현재 버전: v{CURRENT_VERSION}  →  최신 버전: v{latest_ver}"
        if release_date:
            sub_info += f"  (배포일: {release_date})"
        tk.Label(
            header,
            text=sub_info,
            font=DPIHelper.font("Malgun Gothic", 9),
            bg="#0d6efd",
            fg="#cfe2ff"
        ).pack(anchor=tk.W, pady=(DPIHelper.scale(4), 0))

        # 1. 하단 버튼 바 (하단에 먼저 고정 배치하여 잘림 방지)
        btn_row = tk.Frame(dlg, bg="#f8f9fa", padx=DPIHelper.scale(16), pady=DPIHelper.scale(14))
        btn_row.pack(side=tk.BOTTOM, fill=tk.X)

        def on_start_update():
            if not download_url:
                messagebox.showinfo("안내", "다운로드 링크가 설정되어 있지 않습니다.", parent=dlg)
                return
            dlg.destroy()
            cls._show_download_and_patch_dialog(parent, download_url, latest_ver, expected_sha256)

        dlg.bind("<Return>", lambda e: on_start_update())

        tk.Button(
            btn_row,
            text="지금 자동 업데이트 및 재실행 (Enter)",
            command=on_start_update,
            bg="#0d6efd",
            fg="#ffffff",
            font=DPIHelper.font("Malgun Gothic", 10, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(16),
            pady=DPIHelper.scale(6),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=(DPIHelper.scale(8), 0))

        tk.Button(
            btn_row,
            text="나중에 하기",
            command=dlg.destroy,
            bg="#e9ecef",
            fg="#495057",
            font=DPIHelper.font("Malgun Gothic", 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(12),
            pady=DPIHelper.scale(6),
            cursor="hand2"
        ).pack(side=tk.RIGHT)

        # 2. 본문 패치노트 (남은 중앙 공간 채우기)
        body = tk.Frame(dlg, bg="#f8f9fa", padx=DPIHelper.scale(16), pady=DPIHelper.scale(10))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tk.Label(
            body,
            text="[주요 업데이트 및 패치 내역]",
            font=DPIHelper.font("Malgun Gothic", 10, "bold"),
            bg="#f8f9fa",
            fg="#212529"
        ).pack(anchor=tk.W, pady=(0, DPIHelper.scale(6)))

        txt_frame = tk.Frame(body, bg="#ffffff", relief=tk.SOLID, bd=1)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            txt_frame,
            font=DPIHelper.font("Malgun Gothic", 9),
            bg="#ffffff",
            fg="#333333",
            relief=tk.FLAT,
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(8),
            wrap=tk.WORD,
            height=7
        )
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        txt.insert("1.0", changelog)
        txt.config(state=tk.DISABLED)

        # 하단 안내 라벨
        tk.Label(
            body,
            text="※ 업데이트 시 기존 정식 라이선스는 100% 안전하게 유지됩니다.",
            font=DPIHelper.font("Malgun Gothic", 8),
            bg="#f8f9fa",
            fg="#6c757d"
        ).pack(anchor=tk.W, pady=(DPIHelper.scale(6), 0))

    @classmethod
    def _show_download_and_patch_dialog(cls, parent, download_url: str, latest_ver: str, expected_sha256=""):
        """다운로드 진행률 표시 및 자동 교체 패처 실행 다이얼로그"""
        dl_dlg = tk.Toplevel(parent)
        dl_dlg.title("소나무 BookEditor OCR - 업데이트 다운로드 중")
        w, h = DPIHelper.scale(460), DPIHelper.scale(180)
        dl_dlg.geometry(f"{w}x{h}")
        dl_dlg.resizable(False, False)
        dl_dlg.configure(bg="#f8f9fa", padx=DPIHelper.scale(20), pady=DPIHelper.scale(16))
        dl_dlg.transient(parent)
        dl_dlg.grab_set()

        lbl_title = tk.Label(
            dl_dlg,
            text=f"최신 버전(v{latest_ver}) 패키지를 다운로드하고 있습니다...",
            font=DPIHelper.font("Malgun Gothic", 10, "bold"),
            bg="#f8f9fa",
            fg="#212529"
        )
        lbl_title.pack(anchor=tk.W, pady=(0, DPIHelper.scale(8)))

        prog = ttk.Progressbar(dl_dlg, orient="horizontal", mode="determinate", length=DPIHelper.scale(420))
        prog.pack(fill=tk.X, pady=(0, DPIHelper.scale(8)))

        lbl_status = tk.Label(
            dl_dlg,
            text="다운로드 준비 중...",
            font=DPIHelper.font("Malgun Gothic", 9),
            bg="#f8f9fa",
            fg="#6c757d"
        )
        lbl_status.pack(anchor=tk.W)

        # 백그라운드 다운로드 스레드
        threading.Thread(
            target=cls._download_worker,
            args=(parent, dl_dlg, prog, lbl_status, download_url, expected_sha256),
            daemon=True
        ).start()

    @classmethod
    def _download_worker(cls, parent, dl_dlg, prog, lbl_status, download_url: str, expected_sha256=""):
        target_dir = get_app_dir()
        temp_dir = tempfile.gettempdir()

        # 1. 신뢰할 수 있는 도메인 검증 (SSRF 및 악성 외부 URL 차단)
        if not cls._is_url_trusted(download_url):
            dl_dlg.after(0, lambda: messagebox.showerror(
                "보안 오류",
                "신뢰할 수 없는 다운로드 소스입니다.\n보안 정책에 따라 업데이트가 중단되었습니다.",
                parent=dl_dlg
            ))
            dl_dlg.after(0, dl_dlg.destroy)
            return

        is_exe = download_url.lower().endswith(".exe") or ("/releases/download/" in download_url and download_url.lower().endswith(".exe"))
        unique_token = uuid.uuid4().hex[:8]
        
        target_exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.join(target_dir, "Sonamu_BookEditorOCR.exe")
        temp_file = os.path.join(temp_dir, f"Sonamu_BookEditorOCR_{unique_token}.exe" if is_exe else f"BookEditorOCR_{unique_token}.zip")
        extracted_dir = os.path.join(temp_dir, f"BookEditorOCR_extracted_{unique_token}")
        bat_path = os.path.join(temp_dir, f"patch_and_restart_{unique_token}.bat")

        try:
            resp = requests.get(download_url, stream=True, timeout=30)
            if resp.status_code != 200:
                raise Exception(f"HTTP 오류 {resp.status_code}")

            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(temp_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            mb_cur = downloaded / (1024 * 1024)
                            mb_tot = total_size / (1024 * 1024)
                            status_text = f"다운로드 중: {mb_cur:.1f}MB / {mb_tot:.1f}MB ({pct}%)"
                            dl_dlg.after(0, lambda p=pct, t=status_text: (
                                prog.configure(value=p),
                                lbl_status.configure(text=t)
                            ))

            # 2. SHA-256 무결성 검증 (해시 정보가 제공된 경우)
            if expected_sha256:
                dl_dlg.after(0, lambda: lbl_status.configure(text="파일 무결성 검증 중..."))
                hasher = hashlib.sha256()
                with open(temp_file, "rb") as f:
                    while c := f.read(65536):
                        hasher.update(c)
                actual_sha256 = hasher.hexdigest().lower()
                if actual_sha256 != expected_sha256:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass
                    raise ValueError("다운로드 파일의 SHA-256 무결성 검증에 실패했습니다. (변조 위험)")

            dl_dlg.after(0, lambda: lbl_status.configure(text="다운로드 완료! 최신 파일 교체 후 종료됩니다. 안내창 확인 후 다시 실행해 주십시오."))

            # 안전한 경로 인젝션 방지
            clean_temp_file = temp_file.replace('"', '')
            clean_target_exe = target_exe_path.replace('"', '')
            clean_target_dir = target_dir.replace('"', '')

            if is_exe:
                # 단일 EXE 교체 스크립트 (교체 완료 안내 팝업 후 안전 종료)
                bat_content = f"""@echo off
chcp 65001 > nul
echo 최신 버전 교체 적용 중... 잠시만 기다려 주십시오.
timeout /t 2 /nobreak > nul
copy /y "{clean_temp_file}" "{clean_target_exe}"
del /f /q "{clean_temp_file}"
powershell -NoProfile -Command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; [System.Windows.Forms.MessageBox]::Show('BookEditor OCR 업데이트가 성공적으로 완료되었습니다.`n`n프로그램을 다시 실행해 주십시오.', '업데이트 완료', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
(goto) 2>nul & del "%~f0"
"""
            else:
                # ZIP 패키지 교체 스크립트 (교체 완료 안내 팝업 후 안전 종료)
                ps_extracted = extracted_dir.replace("'", "''")
                ps_temp = clean_temp_file.replace("'", "''")
                ps_target = clean_target_dir.replace("'", "''")
                bat_content = f"""@echo off
chcp 65001 > nul
echo BookEditor OCR 업데이트 적용 중... 잠시만 기다려 주십시오.
timeout /t 2 /nobreak > nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '{ps_extracted}') {{ Remove-Item -Path '{ps_extracted}' -Recurse -Force }}; Expand-Archive -Path '{ps_temp}' -DestinationPath '{ps_extracted}' -Force"

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '{ps_extracted}\\Sonamu_BookEditorOCR.exe') {{ Copy-Item -Path '{ps_extracted}\\*' -Destination '{ps_target}' -Recurse -Force }} elseif (Test-Path '{ps_extracted}\\*\\Sonamu_BookEditorOCR.exe') {{ $sub = (Get-ChildItem -Path '{ps_extracted}' -Directory)[0].FullName; Copy-Item -Path \"$sub\\*\" -Destination '{ps_target}' -Recurse -Force }} else {{ Copy-Item -Path '{ps_extracted}\\*' -Destination '{ps_target}' -Recurse -Force }}"

del /f /q "{clean_temp_file}"
rmdir /s /q "{extracted_dir}"

powershell -NoProfile -Command "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; [System.Windows.Forms.MessageBox]::Show('BookEditor OCR 업데이트가 성공적으로 완료되었습니다.`n`n프로그램을 다시 실행해 주십시오.', '업데이트 완료', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as bf:
                bf.write(bat_content)

            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=CREATE_NO_WINDOW)
            os._exit(0)

        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            dl_dlg.after(0, lambda: messagebox.showerror(
                "업데이트 실패",
                f"최신 버전 패키지를 다운로드하는 중 오류가 발생했습니다:\n{e}",
                parent=dl_dlg
            ))
            dl_dlg.after(0, dl_dlg.destroy)
