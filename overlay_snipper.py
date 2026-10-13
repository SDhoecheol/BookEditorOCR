import tkinter as tk
from PIL import ImageGrab, ImageTk, ImageEnhance
from dpi_helper import DPIHelper


class OverlaySnipper(tk.Toplevel):
    def __init__(self, parent, on_crop_complete):
        super().__init__(parent)
        self.on_crop_complete = on_crop_complete

        # 캡처 창 설정: 프레임 없음, 항상 위, 전체화면
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.99)

        # 1. 전체 화면 캡처
        self.orig_image = ImageGrab.grab(all_screens=True)
        self.screen_width = self.orig_image.width
        self.screen_height = self.orig_image.height

        self.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        # 2. 반투명 배경용 이미지 생성 (1회만 가볍게 생성)
        darkener = ImageEnhance.Brightness(self.orig_image)
        self.dimmed_image = darkener.enhance(0.60)
        self.tk_dimmed = ImageTk.PhotoImage(self.dimmed_image)

        # 3. 캔버스 생성
        self.canvas = tk.Canvas(
            self,
            width=self.screen_width,
            height=self.screen_height,
            cursor="cross",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_dimmed)

        # 상태 변수
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # 테두리 두께 (DPI 비례)
        self.border_width = max(2, DPIHelper.scale(2))

        # 안내 텍스트 (4K 자동 확대)
        self.info_text_id = self.canvas.create_text(
            self.screen_width // 2,
            DPIHelper.scale(40),
            text="텍스트 영역 드래그 (취소: ESC)",
            fill="#ffffff",
            font=DPIHelper.font("Malgun Gothic", 12, "bold")
        )

        # 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.bind("<Escape>", lambda e: self.cancel())
        self.canvas.bind("<Button-3>", lambda e: self.cancel())

        self.focus_force()

    def _on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

        if self.info_text_id:
            self.canvas.delete(self.info_text_id)
            self.info_text_id = None

        if self.rect_id:
            self.canvas.delete(self.rect_id)

        # 파란색/빨간색의 선명한 선택 박스 생성 (가볍고 즉각 반응)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#00a8ff",
            width=self.border_width
        )

    def _on_mouse_drag(self, event):
        """4K 해상도에서도 60FPS로 물 흐르듯 드래그되도록 경량 사각형 좌표만 갱신"""
        cur_x, cur_y = event.x, event.y
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)

        self.canvas.coords(self.rect_id, x1, y1, x2, y2)

    def _on_button_release(self, event):
        cur_x, cur_y = event.x, event.y
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)

        self.destroy()

        if (x2 - x1) > 8 and (y2 - y1) > 8:
            cropped = self.orig_image.crop((x1, y1, x2, y2))
            if self.on_crop_complete:
                self.on_crop_complete(cropped)
        else:
            if self.on_crop_complete:
                self.on_crop_complete(None)

    def cancel(self):
        self.destroy()
        if self.on_crop_complete:
            self.on_crop_complete(None)
