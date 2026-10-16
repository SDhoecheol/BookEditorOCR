import re
import difflib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pyperclip

from text_cleaner import TextCleaner
from spell_checker import SpellCorrector, DiffCompareDialog
from dpi_helper import DPIHelper


class PopupEditor(tk.Toplevel):
    def __init__(self, parent, raw_text: str, raw_lines: list[str], cropped_image: Image.Image = None, on_history_add=None, ai_engine=None):
        super().__init__(parent)
        self.title("BookEditor OCR - 텍스트 확인 및 편집")

        win_w = DPIHelper.scale(920)
        win_h = DPIHelper.scale(620)
        min_w = DPIHelper.scale(700)
        min_h = DPIHelper.scale(480)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(min_w, min_h)
        self.attributes("-topmost", True)

        self.raw_text = raw_text
        self.raw_lines = raw_lines
        self.cropped_image = cropped_image
        self.tk_preview_img = None
        self.on_history_add = on_history_add
        self.ai_engine = ai_engine
        self.is_smart_merge = False
        self.is_large_font = False

        self.font_family = "Malgun Gothic"
        self.configure(bg="#f8f9fa")

        self._build_ui()
        self._render_text_with_highlights()
        self._copy_to_clipboard(show_toast=False)

        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self):
        # 상단 툴바 (2단 레이아웃)
        toolbar_container = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID)
        toolbar_container.pack(fill=tk.X, padx=DPIHelper.scale(10), pady=(DPIHelper.scale(8), DPIHelper.scale(4)))

        pad_x = DPIHelper.scale(8)
        pad_y = DPIHelper.scale(4)
        btn_font = DPIHelper.font(self.font_family, 9, "bold")
        btn_font_normal = DPIHelper.font(self.font_family, 9)

        # 1행: 편집/검증 도구
        row1 = tk.Frame(toolbar_container, bg="#ffffff")
        row1.pack(fill=tk.X, padx=pad_x, pady=(pad_y, 2))

        self.btn_mode = tk.Button(
            row1,
            text="스마트 연결 (OFF)",
            command=self._toggle_mode,
            bg="#6c757d",
            fg="#ffffff",
            font=btn_font,
            relief=tk.FLAT,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        self.btn_mode.pack(side=tk.LEFT, padx=(0, DPIHelper.scale(6)))

        self.btn_font_size = tk.Button(
            row1,
            text="큰 글씨",
            command=self._toggle_font_size,
            bg="#495057",
            fg="#ffffff",
            font=btn_font_normal,
            relief=tk.FLAT,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        self.btn_font_size.pack(side=tk.LEFT, padx=DPIHelper.scale(4))

        btn_spell = tk.Button(
            row1,
            text="오타 교정",
            command=self._run_spell_check,
            bg="#0d6efd",
            fg="#ffffff",
            font=btn_font_normal,
            relief=tk.FLAT,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        btn_spell.pack(side=tk.LEFT, padx=DPIHelper.scale(4))

        btn_nara = tk.Button(
            row1,
            text="맞춤법 검사",
            command=self._open_nara,
            bg="#198754",
            fg="#ffffff",
            font=btn_font_normal,
            relief=tk.FLAT,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        btn_nara.pack(side=tk.LEFT, padx=DPIHelper.scale(4))

        # 2행: 보조 및 복사 도구
        row2 = tk.Frame(toolbar_container, bg="#ffffff")
        row2.pack(fill=tk.X, padx=pad_x, pady=(2, pad_y))

        btn_save = tk.Button(
            row2,
            text="파일 저장",
            command=self._save_as_txt,
            bg="#6c757d",
            fg="#ffffff",
            font=btn_font_normal,
            relief=tk.FLAT,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )
        btn_save.pack(side=tk.LEFT)

        btn_copy = tk.Button(
            row2,
            text="클립보드 복사",
            command=lambda: self._copy_to_clipboard(show_toast=True),
            bg="#212529",
            fg="#ffffff",
            font=btn_font,
            relief=tk.FLAT,
            padx=DPIHelper.scale(16),
            pady=pad_y,
            cursor="hand2"
        )
        btn_copy.pack(side=tk.RIGHT)

        # 메인 콘텐츠 분할 영역 (좌측: 원본 캡처 이미지 / 우측: 텍스트 에디터)
        content_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#dee2e6", sashwidth=DPIHelper.scale(4))
        content_paned.pack(fill=tk.BOTH, expand=True, padx=DPIHelper.scale(10), pady=DPIHelper.scale(4))

        # 1. 좌측: 원본 캡처 이미지 미니 1:1 대조창
        preview_frame = tk.LabelFrame(
            content_paned,
            text=" [원본 이미지] ",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            bg="#ffffff"
        )
        content_paned.add(preview_frame, minsize=DPIHelper.scale(250), width=DPIHelper.scale(360))

        preview_canvas = tk.Canvas(preview_frame, bg="#212529", highlightthickness=0)
        img_scroll_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_canvas.yview)
        img_scroll_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=preview_canvas.xview)
        preview_canvas.configure(xscrollcommand=img_scroll_x.set, yscrollcommand=img_scroll_y.set)

        img_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        img_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        preview_canvas.pack(fill=tk.BOTH, expand=True)

        if self.cropped_image:
            self.tk_preview_img = ImageTk.PhotoImage(self.cropped_image)
            preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_preview_img)
            preview_canvas.config(scrollregion=(0, 0, self.cropped_image.width, self.cropped_image.height))

        # 2. 우측: 텍스트 에디터 (핀셋 하이라이트 적용)
        editor_frame = tk.LabelFrame(
            content_paned,
            text=" [추출 텍스트] ",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            bg="#ffffff"
        )
        content_paned.add(editor_frame, minsize=DPIHelper.scale(320))

        self.text_area = tk.Text(
            editor_frame,
            wrap=tk.WORD,
            font=DPIHelper.font(self.font_family, 11),
            undo=True,
            bd=0,
            padx=DPIHelper.scale(10),
            pady=DPIHelper.scale(10)
        )
        text_scroll = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=text_scroll.set)

        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 핀셋 하이라이트 태그 스타일 설정 (노란색 형광펜 + 굵게 + 밑줄)
        self.text_area.tag_config(
            "pinpoint_highlight",
            background="#fff3cd",
            foreground="#664d03",
            font=DPIHelper.font(self.font_family, 11, "bold"),
            underline=True
        )

        # AI 오타 교정 태그 스타일 설정 (연초록 배경 + 굵게)
        self.text_area.tag_config(
            "corrected_highlight",
            background="#d1e7dd",
            foreground="#0f5132",
            font=DPIHelper.font(self.font_family, 11, "bold")
        )

        self.text_area.bind("<KeyRelease>", lambda e: self._update_stats())

        # 하단 상태바
        statusbar = tk.Frame(self, bg="#f1f3f5")
        statusbar.pack(fill=tk.X, side=tk.BOTTOM, padx=DPIHelper.scale(10), pady=(0, DPIHelper.scale(4)))

        status_line = tk.Frame(statusbar, bg="#f1f3f5")
        status_line.pack(fill=tk.X, pady=(2, 2))

        self.lbl_toast = tk.Label(
            status_line,
            text="클립보드에 복사됨",
            fg="#0d6efd",
            bg="#f1f3f5",
            font=DPIHelper.font(self.font_family, 9, "bold")
        )
        self.lbl_toast.pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(
            status_line,
            text="글자수: 0 (공백제외 0) | 0줄",
            fg="#495057",
            bg="#f1f3f5",
            font=DPIHelper.font(self.font_family, 9)
        )
        self.lbl_stats.pack(side=tk.RIGHT)

        # 하단 소나무디자인 회사 정보 2줄
        company_frame = tk.Frame(self, bg="#f8f9fa", bd=1, relief=tk.GROOVE, padx=DPIHelper.scale(10), pady=DPIHelper.scale(4))
        company_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=DPIHelper.scale(10), pady=(0, DPIHelper.scale(4)))

        lbl_c1 = tk.Label(
            company_frame,
            text="ⓒ 소나무디자인 All Rights Reserved.",
            font=DPIHelper.font(self.font_family, 8, "bold"),
            bg="#f8f9fa",
            fg="#495057"
        )
        lbl_c1.pack(anchor=tk.W)

        lbl_c2 = tk.Label(
            company_frame,
            text="문의: 032-465-8195 | 인천광역시 인주대로 304 영인빌딩 4층",
            font=DPIHelper.font(self.font_family, 8),
            bg="#f8f9fa",
            fg="#6c757d"
        )
        lbl_c2.pack(anchor=tk.W)

    def _render_text_with_highlights(self):
        """Gemini가 반환한 [[단어]] 태그를 파싱하여 노란색 핀셋 하이라이트로 시각화"""
        self.text_area.delete("1.0", tk.END)

        if self.is_smart_merge:
            # [[단어]] 태그를 유지한 채로 스마트 줄바꿈 적용
            text_to_render = TextCleaner.smart_merge_lines(self.raw_text.splitlines())
        else:
            # 원본 줄바꿈과 빈 줄을 100% 온전히 보존
            text_to_render = self.raw_text

        highlight_count = 0
        # [[단어]] 패턴 분할 및 순차 삽입
        pattern = re.compile(r"\[\[(.*?)\]\]")
        last_end = 0

        for match in pattern.finditer(text_to_render):
            # 매칭 앞부분 일반 텍스트 삽입
            plain_part = text_to_render[last_end:match.start()]
            if plain_part:
                self.text_area.insert(tk.END, plain_part)

            # 복원 단어 핀셋 하이라이트 삽입
            restored_word = match.group(1)
            self.text_area.insert(tk.END, restored_word, ("pinpoint_highlight",))
            highlight_count += 1
            last_end = match.end()

        # 남은 뒷부분 삽입
        remaining = text_to_render[last_end:]
        if remaining:
            self.text_area.insert(tk.END, remaining)

        if highlight_count > 0:
            self.lbl_toast.config(
                text=f"복원된 단어 {highlight_count}개 강조 표시됨",
                fg="#b02a37"
            )
        else:
            self.lbl_toast.config(text="추출 완료", fg="#198754")

        self._update_stats()

    def _toggle_mode(self):
        self.is_smart_merge = not self.is_smart_merge
        if self.is_smart_merge:
            self.btn_mode.config(text="스마트 연결 (ON)", bg="#0d6efd")
        else:
            self.btn_mode.config(text="스마트 연결 (OFF)", bg="#6c757d")
        self._render_text_with_highlights()
        self._copy_to_clipboard(show_toast=True)

    def _toggle_font_size(self):
        self.is_large_font = not self.is_large_font
        if self.is_large_font:
            self.text_area.config(font=DPIHelper.font(self.font_family, 15))
            self.text_area.tag_config("pinpoint_highlight", font=DPIHelper.font(self.font_family, 15, "bold"))
            self.text_area.tag_config("corrected_highlight", font=DPIHelper.font(self.font_family, 15, "bold"))
            self.btn_font_size.config(text="보통 글씨", bg="#212529")
        else:
            self.text_area.config(font=DPIHelper.font(self.font_family, 11))
            self.text_area.tag_config("pinpoint_highlight", font=DPIHelper.font(self.font_family, 11, "bold"))
            self.text_area.tag_config("corrected_highlight", font=DPIHelper.font(self.font_family, 11, "bold"))
            self.btn_font_size.config(text="큰 글씨", bg="#495057")

    def _extract_diff_changes(self, orig: str, corr: str) -> list[dict]:
        orig_words = orig.split()
        corr_words = corr.split()
        matcher = difflib.SequenceMatcher(None, orig_words, corr_words)
        changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                changes.append({
                    'before': ' '.join(orig_words[i1:i2]),
                    'after': ' '.join(corr_words[j1:j2]),
                    'reason': 'AI 맞춤법/문맥 교정'
                })
            elif tag == 'delete':
                changes.append({
                    'before': ' '.join(orig_words[i1:i2]),
                    'after': '(삭제)',
                    'reason': '불필요한 단어 제거'
                })
            elif tag == 'insert':
                changes.append({
                    'before': '(추가)',
                    'after': ' '.join(corr_words[j1:j2]),
                    'reason': '누락된 단어 보충'
                })
        return changes

    def _run_spell_check(self):
        current_text = self.text_area.get("1.0", tk.END).strip()
        if not current_text:
            return

        if not self.ai_engine:
            self.lbl_toast.config(text="AI 엔진 연결 오류", fg="#dc3545")
            return

        self.lbl_toast.config(text="AI 교정 분석 중...", fg="#0d6efd")
        self.update_idletasks()

        def worker():
            try:
                clean_input = re.sub(r"\[\[(.*?)\]\]", r"\1", current_text)
                corrected = self.ai_engine.correct_text(clean_input)
                self.after(0, self._on_spell_check_done, clean_input, corrected)
            except Exception as e:
                self.after(0, self._on_spell_check_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_spell_check_done(self, clean_input: str, corrected_text: str):
        changes = self._extract_diff_changes(clean_input, corrected_text)

        if not changes or clean_input.strip() == corrected_text.strip():
            self.lbl_toast.config(text="교정할 항목 없음 (완벽함)", fg="#198754")
            messagebox.showinfo(
                "오타 교정",
                "교정할 오탈자가 없습니다.\n원문이 이미 문맥상 완벽합니다.",
                parent=self
            )
            return

        self.lbl_toast.config(text=f"교정 내역 {len(changes)}건 감지됨", fg="#0d6efd")

        def apply_callback(final_text: str):
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", final_text)

            # 교정된 단어 본문 하이라이트(연초록) 적용
            for item in changes:
                after_val = item.get("after", "").strip()
                if after_val and not after_val.startswith("("):
                    start = "1.0"
                    while True:
                        pos = self.text_area.search(after_val, start, stopindex=tk.END)
                        if not pos:
                            break
                        end_pos = f"{pos}+{len(after_val)}c"
                        self.text_area.tag_add("corrected_highlight", pos, end_pos)
                        start = end_pos

            self._copy_to_clipboard(show_toast=False)
            self._update_stats()
            self.lbl_toast.config(text=f"AI 교정 적용 완료 ({len(changes)}건 강조 표시)", fg="#198754")

        DiffCompareDialog(
            self,
            original_text=clean_input,
            corrected_text=corrected_text,
            changes=changes,
            on_apply=apply_callback
        )

    def _on_spell_check_error(self, err_msg: str):
        self.lbl_toast.config(text="AI 교정 실패", fg="#dc3545")

    def _open_nara(self):
        current_text = self.text_area.get("1.0", tk.END).strip()
        SpellCorrector.open_nara_speller(current_text, parent=self)

    def _get_clean_clipboard_text(self) -> str:
        """대괄호 태그가 없는 순수 클립보드 복사용 텍스트 반환"""
        text = self.text_area.get("1.0", tk.END).strip()
        return re.sub(r"\[\[(.*?)\]\]", r"\1", text)

    def _copy_to_clipboard(self, show_toast=True):
        clean_text = self._get_clean_clipboard_text()
        if not clean_text:
            return

        try:
            pyperclip.copy(clean_text)
        except Exception:
            self.clipboard_clear()
            self.clipboard_append(clean_text)

        if self.on_history_add:
            self.on_history_add(clean_text)

        if show_toast:
            self.lbl_toast.config(text="클립보드에 복사됨", fg="#198754")
            self.after(2500, lambda: self.lbl_toast.config(text=""))

    def _save_as_txt(self):
        content = self._get_clean_clipboard_text()
        if not content:
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="파일 저장",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.lbl_toast.config(text="파일 저장 완료", fg="#198754")

    def _update_stats(self):
        content = self._get_clean_clipboard_text()
        stats = TextCleaner.get_stats(content)
        self.lbl_stats.config(
            text=f"글자수: {stats['chars_with_spaces']} (공백제외 {stats['chars_no_spaces']}) | {stats['lines']}줄"
        )

