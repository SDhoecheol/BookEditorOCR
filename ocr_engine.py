import asyncio
import os
import sys
import tempfile
from PIL import Image, ImageEnhance

try:
    import winsdk.windows.graphics.imaging as imaging
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.storage as storage
    HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


class OCREngine:
    def __init__(self):
        self.engine = None
        self._init_engine()

    def _init_engine(self):
        if HAS_WINSDK:
            try:
                # Try user profile language (Korean)
                self.engine = ocr.OcrEngine.try_create_from_user_profile_languages()
                if not self.engine and len(ocr.OcrEngine.available_recognizer_languages) > 0:
                    self.engine = ocr.OcrEngine.try_create_from_language(
                        ocr.OcrEngine.available_recognizer_languages[0]
                    )
            except Exception as e:
                print(f"[OCREngine] WinSDK init error: {e}", file=sys.stderr)

    def preprocess_image(self, pil_img: Image.Image) -> Image.Image:
        """책자 및 캡처 텍스트의 인식률을 극대화하기 위한 이미지 전처리"""
        img = pil_img.convert("RGB")
        
        # 작은 이미지(캡처 영역이 작을 때) 2배 업스케일
        w, h = img.size
        if w < 1200 or h < 1200:
            scale = 2.0
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 선명도(Sharpness) 및 대비(Contrast) 향상
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.8)
        
        contraster = ImageEnhance.Contrast(img)
        img = contraster.enhance(1.2)
        
        return img

    async def _recognize_async(self, file_path: str):
        if not self.engine:
            self._init_engine()
        if not self.engine:
            raise RuntimeError("Windows OCR 엔진을 초기화할 수 없습니다.")

        abs_path = os.path.abspath(file_path)
        storage_file = await storage.StorageFile.get_file_from_path_async(abs_path)
        stream = await storage_file.open_async(storage.FileAccessMode.READ)
        decoder = await imaging.BitmapDecoder.create_async(stream)
        software_bitmap = await decoder.get_software_bitmap_async()

        result = await self.engine.recognize_async(software_bitmap)
        lines = []
        for line in result.lines:
            lines.append(line.text)
        return lines

    def extract_from_pil(self, pil_img: Image.Image) -> list[str]:
        """PIL Image 객체로부터 텍스트 추출"""
        processed = self.preprocess_image(pil_img)
        
        # 임시 파일로 저장하여 고속 전달
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            processed.save(tmp_path, format="PNG")
            lines = asyncio.run(self._recognize_async(tmp_path))
            return lines
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def extract_from_file(self, file_path: str) -> list[str]:
        """이미지 파일 경로로부터 텍스트 추출"""
        with Image.open(file_path) as img:
            return self.extract_from_pil(img)


# 단독 테스트용
if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = r"C:\Users\COM\.gemini\antigravity\brain\8c4d640f-ec97-4499-9b1e-c270279e2f73\.user_uploaded\media_1788755779314.png"
    
    engine = OCREngine()
    res = engine.extract_from_file(test_path)
    print(f"추출된 줄 수: {len(res)}")
    for line in res:
        print(line)
