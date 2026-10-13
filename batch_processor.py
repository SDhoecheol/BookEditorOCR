import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from text_cleaner import TextCleaner
from dpi_helper import DPIHelper


class BatchProcessorWindow(tk.Toplevel):
    def __init__(self, parent, ai_engine):
        super().__init__(parent)
        self.title("BookEditor OCR - 사진 일괄 변환")

        win_w = DPIHelper.scale(700)
        win_h = DPIHelper.scale(580)
        min_w = DPIHelper.scale(560)
        min_h = DPIHelper.scale(460)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(min_w, min_h)

        self.ai_engine = ai_engine
        self.file_list: list[str] = []

        self.font_family = "Malgun Gothic"
        self.configure(bg="#f8f9fa")

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg="#212529", padx=DPIHelper.scale(14), pady=DPIHelper.scale(10))
        header.pack(fill=tk.X)

        lbl_title = tk.Label(
            header,
            text="사진 일괄 변환",
            font=DPIHelper.font(self.font_family, 11, "bold"),
            bg="#212529",
            fg="#ffffff"
        )
        lbl_title.pack(anchor=tk.W)

        lbl_desc = tk.Label(
            header,
            text="변환할 사진 파일을 추가하세요.",
            font=DPIHelper.font(self.font_family, 8),
            bg="#212529",
            fg="#adb5bd"
        )
        lbl_desc.pack(anchor=tk.W, pady=(DPIHelper.scale(2), 0))

        btn_bar = tk.Frame(self, bg="#f8f9fa")
        btn_bar.pack(fill=tk.X, padx=DPIHelper.scale(10), pady=DPIHelper.scale(6))

        btn_add_files = tk.Button(
            btn_bar,
            text="파일 추가",
            command=self._add_files,
            bg="#0d6efd",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(10),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_add_files.pack(side=tk.LEFT, padx=(0, DPIHelper.scale(6)))

        btn_add_folder = tk.Button(
            btn_bar,
            text="폴더 추가",
            command=self._add_folder,
            bg="#6c757d",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_add_folder.pack(side=tk.LEFT, padx=DPIHelper.scale(6))

        btn_remove = tk.Button(
            btn_bar,
            text="선택 삭제",
            command=self._remove_selected_files,
            bg="#ffc107",
            fg="#000000",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_remove.pack(side=tk.RIGHT, padx=(DPIHelper.scale(6), 0))

        btn_clear = tk.Button(
            btn_bar,
            text="전체 비우기",
            command=self._clear_files,
            bg="#dc3545",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 9),
            relief=tk.FLAT,
            padx=DPIHelper.scale(8),
            pady=DPIHelper.scale(4),
            cursor="hand2"
        )
        btn_clear.pack(side=tk.RIGHT)

        list_frame = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=DPIHelper.scale(10), pady=DPIHelper.scale(4))

        self.listbox = tk.Listbox(
            list_frame,
            font=DPIHelper.font(self.font_family, 9),
            selectmode=tk.EXTENDED,
            bd=0,
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=DPIHelper.scale(5), pady=DPIHelper.scale(5))

        opt_frame = tk.LabelFrame(
            self,
            text=" 옵션 ",
            bg="#f8f9fa",
            font=DPIHelper.font(self.font_family, 9, "bold"),
            padx=DPIHelper.scale(10),
            pady=DPIHelper.scale(6)
        )
        opt_frame.pack(fill=tk.X, padx=DPIHelper.scale(10), pady=DPIHelper.scale(4))

        self.var_smart_merge = tk.BooleanVar(value=True)
        chk_smart = tk.Checkbutton(
            opt_frame,
            text="스마트 문장 연결",
            variable=self.var_smart_merge,
            bg="#f8f9fa",
            font=DPIHelper.font(self.font_family, 9)
        )
        chk_smart.pack(anchor=tk.W)

        self.var_export_mode = tk.StringVar(value="single")
        rb_single = tk.Radiobutton(
            opt_frame,
            text="하나의 파일로 통합 저장 (.txt)",
            variable=self.var_export_mode,
            value="single",
            bg="#f8f9fa",
            font=DPIHelper.font(self.font_family, 9)
        )
        rb_single.pack(anchor=tk.W)

        rb_multiple = tk.Radiobutton(
            opt_frame,
            text="개별 파일로 각각 저장 (.txt)",
            variable=self.var_export_mode,
            value="multiple",
            bg="#f8f9fa",
            font=DPIHelper.font(self.font_family, 9)
        )
        rb_multiple.pack(anchor=tk.W)

        bottom_frame = tk.Frame(self, bg="#f8f9fa")
        bottom_frame.pack(fill=tk.X, padx=DPIHelper.scale(10), pady=DPIHelper.scale(8))

        self.progress = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, DPIHelper.scale(6)))

        self.lbl_status = tk.Label(
            bottom_frame,
            text="대기 중",
            font=DPIHelper.font(self.font_family, 9),
            bg="#f8f9fa",
            fg="#495057"
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.btn_run = tk.Button(
            bottom_frame,
            text="변환 시작",
            command=self._start_batch,
            bg="#198754",
            fg="#ffffff",
            font=DPIHelper.font(self.font_family, 10, "bold"),
            relief=tk.FLAT,
            padx=DPIHelper.scale(16),
            pady=DPIHelper.scale(6),
            cursor="hand2"
        )
        self.btn_run.pack(side=tk.RIGHT)

        lbl_footer = tk.Label(
            self,
            text="ⓒ 소나무디자인 All Rights Reserved. | 문의: 032-465-8195",
            font=DPIHelper.font(self.font_family, 8),
            bg="#f8f9fa",
            fg="#888888"
        )
        lbl_footer.pack(side=tk.BOTTOM, pady=(0, DPIHelper.scale(4)))

    def _add_files(self):
        files = filedialog.askopenfilenames(
            parent=self,
            title="사진 파일 선택",
            filetypes=[
                ("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff"),
                ("모든 파일", "*.*")
            ]
        )
        for f in files:
            norm = os.path.normpath(f)
            if norm not in self.file_list:
                self.file_list.append(norm)
                self.listbox.insert(tk.END, f"[{len(self.file_list)}] {os.path.basename(norm)} ({norm})")
        self._update_status_count()

    def _add_folder(self):
        folder = filedialog.askdirectory(parent=self, title="폴더 선택")
        if not folder:
            return

        valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
        added_count = 0
        for root, _, filenames in os.walk(folder):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.normpath(os.path.join(root, fn))
                    if full_path not in self.file_list:
                        self.file_list.append(full_path)
                        self.listbox.insert(tk.END, f"[{len(self.file_list)}] {fn} ({full_path})")
                        added_count += 1
        self._update_status_count()

    def _remove_selected_files(self):
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            return
        for idx in reversed(selected_indices):
            del self.file_list[idx]
            self.listbox.delete(idx)
        self._update_status_count()

    def _clear_files(self):
        self.file_list.clear()
        self.listbox.delete(0, tk.END)
        self._update_status_count()

    def _update_status_count(self):
        self.lbl_status.config(text=f"선택된 파일: {len(self.file_list)}개")

    def _start_batch(self):
        if not self.file_list:
            messagebox.showwarning("안내", "변환할 사진을 추가해 주세요.", parent=self)
            return

        export_mode = self.var_export_mode.get()
        target_file = None

        if export_mode == "single":
            target_file = filedialog.asksaveasfilename(
                parent=self,
                title="통합 파일 저장",
                defaultextension=".txt",
                filetypes=[("텍스트 파일", "*.txt")]
            )
            if not target_file:
                return

        self.btn_run.config(state=tk.DISABLED, bg="#adb5bd")
        threading.Thread(
            target=self._run_worker,
            args=(export_mode, target_file),
            daemon=True
        ).start()

    def _run_worker(self, export_mode: str, target_file: str | None):
        total = len(self.file_list)
        self.progress["maximum"] = total
        self.progress["value"] = 0

        single_content_parts = []
        smart_merge = self.var_smart_merge.get()

        for idx, file_path in enumerate(self.file_list):
            fname = os.path.basename(file_path)
            self._set_status(f"[{idx+1}/{total}] 변환 중: {fname}")

            try:
                raw_text, raw_lines = self.ai_engine.extract_from_file(file_path)
                import re
                cleaned_lines = [re.sub(r"\[\[(.*?)\]\]", r"\1", line) for line in raw_lines]
                if smart_merge:
                    text_res = TextCleaner.smart_merge_lines(cleaned_lines)
                else:
                    text_res = TextCleaner.preserve_lines(cleaned_lines)
            except Exception as e:
                text_res = f"[오류: {e}]"

            if export_mode == "single":
                separator = f"\n{'='*50}\n[ 파일명: {fname} ]\n{'='*50}\n"
                single_content_parts.append(separator + text_res + "\n")
            else:
                base_without_ext = os.path.splitext(file_path)[0]
                out_txt_path = base_without_ext + "_ocr.txt"
                try:
                    with open(out_txt_path, "w", encoding="utf-8") as f:
                        f.write(text_res)
                except Exception as err:
                    print(f"Failed to write {out_txt_path}: {err}")

            self.progress["value"] = idx + 1

        if export_mode == "single" and target_file:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("".join(single_content_parts))

        self._set_status(f"변환 완료 ({total}개)")
        self.after(0, self._on_finish, export_mode, target_file)

    def _set_status(self, text: str):
        self.after(0, lambda: self.lbl_status.config(text=text))

    def _on_finish(self, export_mode: str, target_file: str | None):
        self.btn_run.config(state=tk.NORMAL, bg="#198754")
        msg = f"{len(self.file_list)}개 파일 변환 완료"
        if export_mode == "single" and target_file:
            msg += f"\n\n저장 경로: {target_file}"
        messagebox.showinfo("변환 완료", msg, parent=self)
