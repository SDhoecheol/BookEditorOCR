import re


class TextCleaner:
    # 불릿/항목 기호 패턴 (새 줄로 유지해야 하는 항목들: 특수 불릿 기호, 숫자 번호, 괄호 번호 등 뒤에 공백이 따르는 경우)
    BULLET_PATTERN = re.compile(
        r"^([•\-\*▶▷◆◇■□○●※\u2022\u25b6\u25c0\u25cf\u25cb]\s*|"
        r"\d+[\.\)]\s+|"
        r"\(\d+\)\s*|"
        r"\([a-zA-Z가-힣]\)\s*|"
        r"\[\d+\]\s*|"
        r"[가-힣a-zA-Z][\.\)]\s+)"
    )

    @classmethod
    def clean_spaces(cls, text: str) -> str:
        """연속 공백 정돈 및 문장 부호 주변 공백 보정"""
        if not text:
            return ""

        # 탭이나 여러 개의 연속 공백을 단일 공백으로 치환
        text = re.sub(r"[ \t]+", " ", text)
        
        # 쉼표 앞 공백 제거 및 뒤 공백 확보: "인천 , 남동구" -> "인천, 남동구"
        text = re.sub(r"\s*,\s*", ", ", text)
        
        # 괄호 안쪽 불필요한 공백 제거
        text = re.sub(r"\(\s+", "(", text)
        text = re.sub(r"\s+\)", ")", text)
        text = re.sub(r"\[\s+", "[", text)
        text = re.sub(r"\s+\]", "]", text)
        
        # 한국어 괄호 닫힘 오타 흔한 케이스 교정 (예: "[...강화군1" -> "[...강화군]")
        text = re.sub(r"\[([^\]\n]+)[1|lI]$", r"[\1]", text)

        return text.strip()

    @classmethod
    def fix_spaced_letters(cls, text: str) -> str:
        """디자인용 넓은 자간 보정: '인 천 광 역 시' -> '인천광역시'"""
        # 한 글자씩 띄어쓰기 된 패턴 (2글자 이상 연속)
        pattern = re.compile(r"(?:^|(?<=\s))([가-힣])\s+([가-힣])(?:\s+([가-힣]))+(?=\s|$)")
        def repl(match):
            return match.group(0).replace(" ", "")
        return pattern.sub(repl, text)

    @classmethod
    def smart_merge_lines(cls, lines: list[str]) -> str:
        """책자 편집을 위한 스마트 문장 이어붙이기.
        
        - 빈 줄은 단락 구분(엔터 2개)으로 보존
        - 불릿 항목은 새 줄 유지
        - 마침표나 물음표/느낌표로 끝난 줄은 문단 구분
        - 문장 중간에 줄바꿈된 행들은 하나로 자연스럽게 이어붙임
        """
        if not lines:
            return ""

        paragraphs = []
        current_lines = []

        # 1차: 빈 줄 기준으로 문단 블록 분리
        for line in lines:
            cleaned = cls.clean_spaces(line)
            if not cleaned:
                if current_lines:
                    paragraphs.append(current_lines)
                    current_lines = []
            else:
                current_lines.append(cleaned)
        if current_lines:
            paragraphs.append(current_lines)

        merged_paragraphs = []
        for p_lines in paragraphs:
            if not p_lines:
                continue

            merged_blocks = []
            current_block = p_lines[0]

            for next_line in p_lines[1:]:
                # 다음 줄이 불릿이나 번호 항목으로 시작하면 무조건 새 줄로 분리
                is_next_bullet = bool(cls.BULLET_PATTERN.match(next_line))
                
                # 현재 줄이 문장의 끝(마침표, 물음표, 느낌표, 콜론 등)으로 끝났는지 확인
                ends_with_sentence_punct = bool(re.search(r"[\.!?:\"]$", current_block))

                # 짧은 소제목(예: [공지사항], (참고사항) 등 단독 줄인 경우)
                is_short_title = len(current_block) <= 15 and bool(re.search(r"[\)\]]$", current_block))
                
                if is_next_bullet or ends_with_sentence_punct or is_short_title:
                    # 새 줄 시작
                    merged_blocks.append(current_block)
                    current_block = next_line
                else:
                    # 문장 중간에 줄바꿈된 경우 -> 띄어쓰기 하나로 연결
                    current_block += " " + next_line

            if current_block:
                merged_blocks.append(current_block)

            merged_paragraphs.append("\n".join(merged_blocks))

        return "\n\n".join(merged_paragraphs)

    @classmethod
    def preserve_lines(cls, lines: list[str]) -> str:
        """원문 줄바꿈을 그대로 유지하면서 줄별 공백만 정돈"""
        cleaned_lines = [cls.clean_spaces(line) for line in lines if line.strip()]
        return "\n".join(cleaned_lines)

    @classmethod
    def get_stats(cls, text: str) -> dict:
        """텍스트 글자 수 및 라인 수 통계 반환"""
        lines = text.splitlines()
        char_count_with_spaces = len(text)
        char_count_no_spaces = len(re.sub(r"\s", "", text))
        word_count = len(text.split())
        return {
            "lines": len(lines),
            "chars_with_spaces": char_count_with_spaces,
            "chars_no_spaces": char_count_no_spaces,
            "words": word_count,
        }
