import os
import json
from datetime import date

APP_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SonamuDesign", "BookEditorOCR")
USAGE_FILE = os.path.join(APP_DATA_DIR, "daily_usage.json")
TOTAL_DAILY_LIMIT = 5000  # 5개 계정 키 x 1,000회 안전 한도


class DailyUsageTracker:
    @classmethod
    def _load_data(cls) -> dict:
        today_str = date.today().isoformat()
        if not os.path.exists(USAGE_FILE):
            return {"date": today_str, "count": 0, "limit": TOTAL_DAILY_LIMIT}

        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") != today_str:
                    return {"date": today_str, "count": 0, "limit": TOTAL_DAILY_LIMIT}
                data["limit"] = TOTAL_DAILY_LIMIT
                return data
        except Exception:
            return {"date": today_str, "count": 0, "limit": TOTAL_DAILY_LIMIT}

    @classmethod
    def _save_data(cls, data: dict):
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        try:
            with open(USAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    @classmethod
    def get_usage(cls) -> tuple[int, int]:
        """(현재 사용 횟수, 안전 한도) 반환"""
        data = cls._load_data()
        return data.get("count", 0), TOTAL_DAILY_LIMIT

    @classmethod
    def can_request(cls) -> bool:
        """5,000회 미만인지 검사"""
        count, limit = cls.get_usage()
        return count < limit

    @classmethod
    def increment(cls):
        """1회 호출 기록"""
        data = cls._load_data()
        data["count"] = data.get("count", 0) + 1
        cls._save_data(data)

    @classmethod
    def reset(cls):
        """사용량 0회 리셋"""
        today_str = date.today().isoformat()
        cls._save_data({"date": today_str, "count": 0, "limit": TOTAL_DAILY_LIMIT})

