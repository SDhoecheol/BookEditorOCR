import base64
import io
import json
import os
import requests
from PIL import Image
from usage_tracker import DailyUsageTracker, APP_DATA_DIR


_K1 = bytes([0x53, 0x6f, 0x6e, 0x61, 0x6d, 0x75, 0x4f, 0x43])
_K2 = bytes([0x52, 0x5f, 0x53, 0x65, 0x63, 0x72, 0x65, 0x74])
_K3 = bytes([0x32, 0x30, 0x32, 0x36, 0x5f, 0x47, 0x65, 0x6d])
_K4 = bytes([0x69, 0x6e, 0x69, 0x5f, 0x41, 0x45, 0x53, 0x21])
_SEED = _K1 + _K2 + _K3 + _K4

_ENC_KEYS = [
    "gAAAAABqn3eYLfOV7S2CKGfoAzq--X3AK8z3knYEea97gGXr2amcHb3BDEV0xV4vrdTvhDUO0xNdIkfoaVm-Tln-wULBKysITcG3MlznuYTqBKbh_ZJ0rMjjITfU2dIWf2P81RN_5D86xNEpFuX_AIXdBBEEBFgL6Q==",
    "gAAAAABqn3eYKad1UhrcCbya_dDJ8RpjCEUaUA4rLTy7fKrWBTq8Q4tYXj9thZ6y5bi7vQ3vGkXFtJ4STqraTafMxdQMOfh516O-ognXmT0BbLGUVGaQTkO_ihuRqFRoalfge-P43qcw3iUsQNjJnagMhYRtAStJhg==",
    "gAAAAABqn3eY8d6AZQNZGq455vemDTbDBh77fge_gykX7hGxnqCnRabR6o-jrpnrbvNfi5QIDTA5iM-W-gSe4gZ6ywVsRjKoFq3iwQFPfQVeDTiyWpa4_kxnfJMgM2xzPFaSpjlsZAab5NapxPi2n49fCxTgtNO7AA==",
    "gAAAAABqn3eYnS8gwFpz81Nywjtax1U-kg6ecj0sCBwKZY2-x0Ev-8_jmqKOWFDR2PmBaewlWrcw3OXakpyMphD-HftFJb0yf1RjV-ddns_tKvbdq8cfqmkgrxdSN0jeL1CwMS4yo7DmPjhVSmUeVyRyUg5rX2Sizw==",
    "gAAAAABqn3eYEZuzhSGRKr8-zjPLPDE_E7yBRhg1jg91zLEC2WLJCFhH35CRIQK4L9sv2fGkrnmnFuooDPyhc2-D_9I_Pvk3mxPP0vURmfZ_QIgLIsOxlMTMXemtCX_4bv-2lzPwqWHNpCixBR-2xXbEdDcbaJZdOA=="
]

def _decrypt_keys() -> list[str]:
    try:
        from cryptography.fernet import Fernet
        k = base64.urlsafe_b64encode(_SEED)
        f = Fernet(k)
        return [f.decrypt(enc.encode("utf-8")).decode("utf-8") for enc in _ENC_KEYS]
    except Exception:
        return []

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent"
API_URL_FALLBACK = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"

def _get_api_urls() -> tuple[str, str]:
    """외부 model_config.json 파일이 있으면 해당 모델 우선 사용, 없으면 최신 안정화 모델 사용"""
    candidates = [
        os.path.join(os.getcwd(), "model_config.json"),
        os.path.join(APP_DATA_DIR, "model_config.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    m = cfg.get("model", "").strip()
                    if m:
                        return f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", API_URL_FALLBACK
            except Exception:
                pass
    return API_URL, API_URL_FALLBACK

PROMPT_OCR = """당신은 전문 출판 디자이너를 위한 고정밀 OCR 전사 엔진입니다.
제공된 이미지에 포함된 모든 텍스트를 위에서 아래로, 원래 문맥과 레이아웃에 맞게 한국어로 정확하게 전사하세요.

[규칙]
1. 해상도가 낮거나 글자가 뭉개져 손상된 글자는 한국어 문맥 지식을 동원하여 가장 자연스럽고 온전한 본래 단어로 스마트하게 복원하십시오.
2. 단, 화질이 흐리거나 뭉개져서 문맥으로 유추하여 복원한 단어가 있다면 그 단어만 [[단어]] 형태로 이중 대괄호로 감싸서 표시하십시오. 확실하게 잘 보이는 정상 글자는 대괄호 없이 출력하십시오.
3. 화살표, 사칙연산, 불릿 등 모든 특수기호는 LaTeX나 영문 명령어 형태(예: \\rightarrow, \\times, $ 등)로 영문 표기하지 말고, 실제 눈에 보이는 유니코드 특수문자 기호(→, ←, ×, ÷, • 등) 그대로 사용해 출력하십시오.
4. 원문에 없는 내용을 임의로 창작하거나 문장을 요약·생략하지 마십시오.
5. 불릿 기호(•, ▶, -, 1., 2. 등)와 제목, 주소, 표 목록은 원래의 형태를 온전히 유지하십시오.
6. 오직 추출된 본문 텍스트만 출력하고, 불필요한 서두나 해설 문장은 절대 출력하지 마십시오."""


class GeminiVisionEngine:
    _key_index = 0

    def __init__(self, api_keys: list[str] | None = None):
        self.api_keys = api_keys or self._load_keys()

    @classmethod
    def _load_keys(cls) -> list[str]:
        """외부 api_keys.json 파일이 있으면 불러오고, 없으면 내부 암호화 키 복호화 사용"""
        candidates = [
            os.path.join(os.getcwd(), "api_keys.json"),
            os.path.join(APP_DATA_DIR, "api_keys.json"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list) and data:
                            return [k.strip() for k in data if isinstance(k, str) and k.strip()]
                        elif isinstance(data, dict) and "keys" in data:
                            return [k.strip() for k in data["keys"] if isinstance(k, str) and k.strip()]
                except Exception:
                    pass
        return _decrypt_keys()

    def _get_next_key(self) -> str:
        """라운드로빈 방식으로 다음 키 선택"""
        if not self.api_keys:
            self.api_keys = _decrypt_keys()
        key = self.api_keys[GeminiVisionEngine._key_index % len(self.api_keys)]
        GeminiVisionEngine._key_index += 1
        return key

    def extract_from_pil(self, pil_img: Image.Image) -> tuple[str, list[str]]:
        """PIL Image 객체로부터 텍스트 추출 (결과 텍스트와 라인 리스트 반환)"""
        if not DailyUsageTracker.can_request():
            count, limit = DailyUsageTracker.get_usage()
            raise RuntimeError(
                f"오늘 사용 한도({limit}회)에 도달했습니다.\n"
                f"내일 00시에 자동 초기화됩니다."
            )

        # 이미지 base64 인코딩 (메모리 고속 처리)
        img_rgb = pil_img.convert("RGB")
        buf = io.BytesIO()
        img_rgb.save(buf, format="JPEG", quality=92)
        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {"text": PROMPT_OCR},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_data}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 3000
            }
        }

        main_url, fallback_url = _get_api_urls()
        target_urls = [main_url, fallback_url]
        last_error = "API 호출 실패"

        for url in target_urls:
            for _ in range(len(self.api_keys)):
                api_key = self._get_next_key()
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }

                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=25)
                    if resp.status_code == 200:
                        DailyUsageTracker.increment()
                        res_json = resp.json()
                        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        lines = [line for line in text.splitlines() if line.strip()]
                        return text, lines
                    elif resp.status_code in (429, 503):
                        last_error = f"요청 한도 또는 서버 일시 지연 ({resp.status_code})"
                        import time
                        time.sleep(2.0)
                        continue
                    else:
                        last_error = f"API 오류 ({resp.status_code}): {resp.text[:100]}"
                        continue
                except requests.exceptions.RequestException as e:
                    last_error = f"네트워크 오류: {e}"
                    continue

        raise RuntimeError(last_error)

    def correct_text(self, text: str) -> str:
        """AI 기반 문맥 오탈자 및 띄어쓰기 교정"""
        if not text or not text.strip():
            return text

        prompt = (
            "당신은 출판 교정교열 전문가입니다.\n"
            "제공된 텍스트의 오탈자, 잘못된 띄어쓰기, OCR 오인식 글자를 문맥에 맞게 정확히 교정하세요.\n"
            "화살표나 연산자 등 특수기호는 LaTeX나 영문 명령어 형태(예: \\rightarrow, \\times, $ 등)를 절대 쓰지 말고 실제 유니코드 특수문자(→, ←, ×, ÷, • 등)를 그대로 유지하세요.\n"
            "원문의 서식과 줄바꿈은 유지하고, 설명 없이 교정된 본문 텍스트만 출력하세요.\n\n"
            f"[원문]\n{text}"
        )
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4000
            }
        }

        main_url, fallback_url = _get_api_urls()
        target_urls = [main_url, fallback_url]
        last_error = "API 호출 실패"

        for url in target_urls:
            for _ in range(len(self.api_keys)):
                api_key = self._get_next_key()
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }

                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=20)
                    if resp.status_code == 200:
                        DailyUsageTracker.increment()
                        res_json = resp.json()
                        return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    elif resp.status_code in (429, 503):
                        last_error = "요청 한도에 일시 도달했습니다."
                        import time
                        time.sleep(2.0)
                        continue
                    else:
                        last_error = f"API 오류 ({resp.status_code})"
                        continue
                except Exception as e:
                    last_error = f"네트워크 오류: {e}"
                    continue

        raise RuntimeError(last_error)

    def extract_from_file(self, file_path: str) -> tuple[str, list[str]]:
        with Image.open(file_path) as img:
            return self.extract_from_pil(img)

