import re
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
from dpi_helper import DPIHelper


class SpellCorrector:
    FIXED_REPLACEMENTS = [
        (r"설\*\|되어", "설치되어", "OCR 특수문자 깨짐 교정"),
        (r"미十홀구", "미추홀구", "한자 오인식 교정"),
        (r"콤역", "광역시", "자모 뭉개짐 교정"),
        (r"가쇠\b", "개소)", "단어 오인식 교정"),
        (r"빠지하킨", "복지회관", "텍스트 뭉개짐 교정"),
        (r"\[([^\]\n]+)[1|lI]$", r"[\1]", "닫는 대괄호 오인식 교정"),
        (r"\(([^\)\n]+)[1|lI]$", r"(\1)", "닫는 소괄호 오인식 교정"),
        (r"(\d{4})\s+(\d{1,2})\s+개소", r"\1. \2. 개소", "날짜 구분점 보정"),
        (r"(\d{4}\.\s*\d{1,2})\.\s*가쇠", r"\1. 개소)", "날짜 및 개소 표기 교정"),
        (r"\b되요\b", "돼요", "한글 맞춤법 교정"),
        (r"\b안되\b", "안돼", "한글 맞춤법 교정"),
        (r"\b몇일\b", "며칠", "한글 맞춤법 교정"),
        (r"\b어의없", "어이없", "한글 맞춤법 교정"),
        (r"\b바램\b", "바람", "한글 맞춤법 교정"),
        (r"\b뵈요\b", "봬요", "한글 맞춤법 교정"),
        (r"\b금새\b", "금세", "한글 맞춤법 교정"),
        (r"\b설레임\b", "설렘", "한글 맞춤법 교정"),
        (r"\b어따 대고\b", "얻다 대고", "한글 맞춤법 교정"),
    ]

    @classmethod
    def check_and_correct(cls, text: str) -> tuple[str, list[dict]]:
        changes = []
        result_text = text

        for pattern, replacement, reason in cls.FIXED_REPLACEMENTS:
            matches = list(re.finditer(pattern, result_text))
            if matches:
                for m in reversed(matches):
                    orig_matched = m.group(0)
                    new_val = re.sub(pattern, replacement, orig_matched)
                    if orig_matched != new_val:
                        changes.append({
                            "before": orig_matched,
                            "after": new_val,
                            "reason": reason
                        })
                result_text = re.sub(pattern, replacement, result_text)

        return result_text, changes

    @classmethod
    def open_nara_speller(cls, text: str, parent=None):
        if not text.strip():
            messagebox.showinfo("안내", "텍스트가 없습니다.", parent=parent)
            return

        try:
            pyperclip.copy(text)
        except Exception:
            pass

        url = "https://nara-speller.co.kr/speller/"
        webbrowser.open(url)

        messagebox.showinfo(
            "맞춤법 검사기",
            "텍스트가 복사되었습니다.\n검사기 화면에 붙여넣기(Ctrl+V)하세요.",
            parent=parent
        )


class DiffCompareDialog(tk.Toplevel):
    def __init__(self, parent, original_text: str, corrected_text: str, changes: list[dict], on_apply):
        super().__init__(parent)
        self.title("오타 교정 내역")
        win_w = DPIHelper.scale(780)
        win_h = DPIHelper.scale(580)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(DPIHelper.scale(620), DPIHelper.scale(460))
        self.attributes("-topmost", True)
        self.font_family = "Malgun Gothic"
        self.configure(bg="#f8f9fa")

        self.original_text = original_text
        self.corrected_text = corrected_text
        self.changes = changes
        self.on_apply = on_apply

        self._build_ui()
        self._apply_diff_highlights()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        header = tk.Frame(self, bg="#212529", padx=DPIHelper.scale(14), pady=DPIHelper.scale(10))
        header.pack(fill=tk.X)

        count_text = f"총 {len(self.changes)}건 교정됨" if self.changes else "교정할 항목 없음"
        lbl_title = tk.Label(
            header,
            text=f"오타 교정 내역 ({count_text})",
            font=DPIHelper.font(self.font_family, 11, "bold"),
            bg="#212529",
            fg="#ffffff"
        )
        lbl_title.pack(anchor=tk.W)

        # 색상 안내 범례 바
        legend_bar = tk.Frame(self, bg="#e9ecef", padx=DPIHelper.scale(12), pady=DPIHelper.scale(4))
        legend_bar.pack(fill=tk.X)

        lbl_leg1 = tk.Label(
            legend_bar,
            text="■ 교정 전 (빨간색)",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            bg="#e9ecef",
            fg="#b02a37"
        )
        lbl_leg1.pack(side=tk.LEFT, padx=(0, DPIHelper.scale(12)))

        lbl_leg2 = tk.Label(
            legend_bar,
            text="■ 교정 후 (초록색)",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            bg="#e9ecef",
            fg="#198754"
        )
        lbl_leg2.pack(side=tk.LEFT, padx=(0, DPIHelper.scale(12)))

        lbl_leg3 = tk.Label(
            legend_bar,
            text="(※ 아래 세부 내역 목록을 클릭하면 해당 단어 위치로 즉시 이동합니다)",
            font=DPIHelper.font(self.font_family, 8),
            bg="#e9ecef",
            fg="#6c757d"
        )
        lbl_leg3.pack(side=tk.LEFT)

        table_frame = tk.LabelFrame(
            self,
            text=" 세부 내역 ",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            bg="#f8f9fa",
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(4)
        )
        table_frame.pack(fill=tk.X, padx=DPIHelper.scale(10), pady=(DPIHelper.scale(6), DPIHelper.scale(4)))

        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(
            table_frame,
            columns=("before", "after", "reason"),
            show="headings",
            height=4,
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("before", text="교정 전")
        self.tree.heading("after", text="교정 후")
        self.tree.heading("reason", text="사유")

        self.tree.column("before", width=DPIHelper.scale(180))
        self.tree.column("after", width=DPIHelper.scale(180))
        self.tree.column("reason", width=DPIHelper.scale(260))

        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for item in self.changes:
            self.tree.insert("", tk.END, values=(item["before"], item["after"], item["reason"]))

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        compare_frame = tk.Frame(self, bg="#f8f9fa")
        compare_frame.pack(fill=tk.BOTH, expand=True, padx=DPIHelper.scale(10), pady=DPIHelper.scale(4))

        left_box = tk.LabelFrame(compare_frame, text=" [교정 전 원문] ", font=DPIHelper.font(self.font_family, 9, "bold"), bg="#ffffff")
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, DPIHelper.scale(4)))

        self.txt_orig = tk.Text(left_box, wrap=tk.WORD, font=DPIHelper.font(self.font_family, 10), bd=0, padx=DPIHelper.scale(6), pady=DPIHelper.scale(6))
        self.txt_orig.insert("1.0", self.original_text)
        self.txt_orig.pack(fill=tk.BOTH, expand=True)

        right_box = tk.LabelFrame(compare_frame, text=" [교정 후 내용] ", font=DPIHelper.font(self.font_family, 9, "bold"), bg="#ffffff")
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(DPIHelper.scale(4), 0))

        self.txt_corr = tk.Text(right_box, wrap=tk.WORD, font=DPIHelper.font(self.font_family, 10), bd=0, padx=DPIHelper.scale(6), pady=DPIHelper.scale(6))
        self.txt_corr.insert("1.0", self.corrected_text)
        self.txt_corr.pack(fill=tk.BOTH, expand=True)

        # 하이라이트 스타일 태그 설정
        self.txt_orig.tag_config(
            "diff_del",
            background="#f8d7da",
            foreground="#842029",
            font=DPIHelper.font(self.font_family, 10, "bold")
        )
        self.txt_orig.tag_config(
            "focus_highlight",
            background="#fff3cd",
            foreground="#000000",
            underline=True
        )

        self.txt_corr.tag_config(
            "diff_add",
            background="#d1e7dd",
            foreground="#0f5132",
            font=DPIHelper.font(self.font_family, 10, "bold")
        )
        self.txt_corr.tag_config(
            "focus_highlight",
            background="#fff3cd",
            foreground="#000000",
            underline=True
        )

        btn_bar = tk.Frame(self, bg="#f8f9fa", pady=DPIHelper.scale(10))
        btn_bar.pack(fill=tk.X, padx=DPIHelper.scale(10))

        btn_apply = tk.Button(
            btn_bar,
            text="적용",
            command=self._on_apply_click,
            bg="#0d6efd",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 10, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(18),
            pady=DPIHelper.scale(6),
            cursor="hand2"
        )
        btn_apply.pack(side=tk.RIGHT, padx=(DPIHelper.scale(6), 0))

        btn_cancel = tk.Button(
            btn_bar,
            text="취소",
            command=self.destroy,
            bg="#6c757d",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 10),
            relief=tk.FLAT,
            padx=DPIHelper.scale(14),
            pady=DPIHelper.scale(6),
            cursor="hand2"
        )
        btn_cancel.pack(side=tk.RIGHT)

    def _apply_diff_highlights(self):
        """교정 전(빨간색) 및 교정 후(초록색) 단어 인라인 하이라이트 적용"""
        for item in self.changes:
            before_val = item.get("before", "").strip()
            if before_val and not before_val.startswith("("):
                start = "1.0"
                while True:
                    pos = self.txt_orig.search(before_val, start, stopindex=tk.END)
                    if not pos:
                        break
                    end_pos = f"{pos}+{len(before_val)}c"
                    self.txt_orig.tag_add("diff_del", pos, end_pos)
                    start = end_pos

            after_val = item.get("after", "").strip()
            if after_val and not after_val.startswith("("):
                start = "1.0"
                while True:
                    pos = self.txt_corr.search(after_val, start, stopindex=tk.END)
                    if not pos:
                        break
                    end_pos = f"{pos}+{len(after_val)}c"
                    self.txt_corr.tag_add("diff_add", pos, end_pos)
                    start = end_pos

        self.txt_orig.config(state=tk.DISABLED, bg="#f8f9fa")

    def _on_tree_select(self, event):
        """세부 내역 표에서 행 클릭 시 좌/우 텍스트 뷰 해당 단어로 자동 스크롤 및 포커스"""
        sel = self.tree.selection()
        if not sel:
            return

        item = self.tree.item(sel[0])
        values = item.get("values", [])
        if len(values) < 2:
            return

        before_val = str(values[0]).strip()
        after_val = str(values[1]).strip()

        # 기존 포커스 태그 제거
        self.txt_orig.tag_remove("focus_highlight", "1.0", tk.END)
        self.txt_corr.tag_remove("focus_highlight", "1.0", tk.END)

        if before_val and not before_val.startswith("("):
            pos = self.txt_orig.search(before_val, "1.0", stopindex=tk.END)
            if pos:
                end_pos = f"{pos}+{len(before_val)}c"
                self.txt_orig.tag_add("focus_highlight", pos, end_pos)
                self.txt_orig.see(pos)

        if after_val and not after_val.startswith("("):
            pos = self.txt_corr.search(after_val, "1.0", stopindex=tk.END)
            if pos:
                end_pos = f"{pos}+{len(after_val)}c"
                self.txt_corr.tag_add("focus_highlight", pos, end_pos)
                self.txt_corr.see(pos)

    def _on_apply_click(self):
        final_text = self.txt_corr.get("1.0", tk.END).strip()
        if self.on_apply:
            self.on_apply(final_text)
        self.destroy()
