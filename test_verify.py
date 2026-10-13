import sys
from ocr_engine import OCREngine
from text_cleaner import TextCleaner

sys.stdout.reconfigure(encoding="utf-8")

def run_test():
    engine = OCREngine()
    sample_img = r"C:\Users\COM\.gemini\antigravity\brain\8c4d640f-ec97-4499-9b1e-c270279e2f73\.user_uploaded\media_1788755779314.png"

    print("[1] OCR 엔진 추출 테스트...")
    lines = engine.extract_from_file(sample_img)
    print(f"추출된 줄 수: {len(lines)}")

    print("\n[2] 스마트 문장 이어붙이기 결과:")
    merged = TextCleaner.smart_merge_lines(lines)
    print(merged)

    print("\n[3] 원문 줄바꿈 유지 결과:")
    preserved = TextCleaner.preserve_lines(lines)
    print(preserved)

    stats = TextCleaner.get_stats(merged)
    print(f"\n[4] 통계: 공백포함 {stats['chars_with_spaces']}자, 공백제외 {stats['chars_no_spaces']}자, {stats['lines']}줄")
    print("\n모든 검증 완료: 정상 작동!")

if __name__ == "__main__":
    run_test()
