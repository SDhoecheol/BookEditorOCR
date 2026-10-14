import os
import json
import ctypes

APP_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SonamuDesign", "BookEditorOCR")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")


class DPIHelper:
    _scale_factor = None
    _user_font_scale = None
    FONT_SCALES = [1.0, 1.15, 1.30, 1.50]

    @classmethod
    def get_scale_factor(cls) -> float:
        """현재 모니터의 DPI 배율을 반환 (예: 100%->1.0, 150%->1.5, 200%->2.0)"""
        if cls._scale_factor is not None:
            return cls._scale_factor

        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            dc = user32.GetDC(0)
            gdi32 = ctypes.windll.gdi32
            # LOGPIXELSX = 88
            dpi_x = gdi32.GetDeviceCaps(dc, 88)
            user32.ReleaseDC(0, dc)
            scale = dpi_x / 96.0
            # 최소 1.0 이상 보장
            cls._scale_factor = max(1.0, scale)
        except Exception:
            cls._scale_factor = 1.0

        return cls._scale_factor

    @classmethod
    def get_user_font_scale(cls) -> float:
        """사용자가 설정한 폰트 배율 반환 (settings.json에서 로드)"""
        if cls._user_font_scale is not None:
            return cls._user_font_scale

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scale = float(data.get("font_scale", 1.0))
                    if scale in cls.FONT_SCALES:
                        cls._user_font_scale = scale
                        return cls._user_font_scale
            except Exception:
                pass

        cls._user_font_scale = 1.0
        return cls._user_font_scale

    @classmethod
    def set_user_font_scale(cls, scale: float):
        """사용자 폰트 배율 설정 및 settings.json에 영구 저장"""
        if scale not in cls.FONT_SCALES:
            # 가장 가까운 허용 배율 선택
            scale = min(cls.FONT_SCALES, key=lambda x: abs(x - scale))

        cls._user_font_scale = scale
        try:
            os.makedirs(APP_DATA_DIR, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"font_scale": scale}, f, indent=2)
        except Exception:
            pass

    @classmethod
    def increase_font_scale(cls) -> float:
        """폰트 배율 1단계 증가"""
        current = cls.get_user_font_scale()
        idx = cls.FONT_SCALES.index(current) if current in cls.FONT_SCALES else 0
        if idx < len(cls.FONT_SCALES) - 1:
            new_scale = cls.FONT_SCALES[idx + 1]
            cls.set_user_font_scale(new_scale)
            return new_scale
        return current

    @classmethod
    def decrease_font_scale(cls) -> float:
        """폰트 배율 1단계 감소"""
        current = cls.get_user_font_scale()
        idx = cls.FONT_SCALES.index(current) if current in cls.FONT_SCALES else 0
        if idx > 0:
            new_scale = cls.FONT_SCALES[idx - 1]
            cls.set_user_font_scale(new_scale)
            return new_scale
    @classmethod
    def reset_font_scale(cls) -> float:
        """폰트 배율 기본값(1.0)으로 초기화"""
        cls.set_user_font_scale(1.0)
        return 1.0

    @classmethod
    def get_font_scale_percent(cls) -> int:
        """현재 폰트 배율 백분율 (100, 115, 130, 150)"""
        return int(round(cls.get_user_font_scale() * 100))

    @classmethod
    def scale(cls, val: int) -> int:
        """픽셀 크기를 모니터 배율에 맞게 비례 확대"""
        return int(val * cls.get_scale_factor())

    @classmethod
    def font(cls, family: str, size: int, weight: str = "normal") -> tuple:
        """폰트 크기를 모니터 배율 및 사용자 설정 배율에 맞게 자동 확대하여 Tkinter 폰트 튜플 반환"""
        total_scale = cls.get_scale_factor() * cls.get_user_font_scale()
        scaled_size = max(8, int(size * total_scale))
        if weight and weight != "normal":
            return (family, scaled_size, weight)
        return (family, scaled_size)
