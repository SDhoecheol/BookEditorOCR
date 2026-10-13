# 소나무 BookEditor OCR GitHub 자동 업데이트 연동 가이드

직원들에게 매번 일일이 USB나 메신저로 파일을 보내지 않고, GitHub를 통해 무제한 트래픽(0원)으로 자동 업데이트를 배포하는 방법입니다.

---

### 1단계: GitHub에 공개 저장소(Public Repository) 생성
1. GitHub(github.com)에 로그인 후 새 저장소를 만듭니다. (예: `BookEditorOCR`)
2. 저장소 공개 여부를 **Public**으로 설정합니다. (무료 무제한 CDN 다운로드 지원)

---

### 2단계: 저장소 루트에 `version.json` 파일 업로드
- `github_template/version.json` 파일을 저장소 메인 브랜치(main)의 최상위 경로에 업로드합니다.
- 이 파일의 Raw URL 형태:
  `https://raw.githubusercontent.com/<사용자ID>/<저장소명>/main/version.json`

---

### 3단계: GitHub Releases에 최신 압축 파일 등록
1. 저장소 우측의 **Releases** -> **Create a new release** 클릭
2. Tag version: `v1.1.0` 입력
3. Release title: `Sonamu BookEditor OCR v1.1.0 정식 배포` 입력
4. 바탕화면에 생성된 `Sonamu_BookEditorOCR_배포용.zip` 파일을 드래그하여 첨부
5. **Publish release** 클릭

---

### 4단계: `update_config.json` 주소 맞추기
- 배포 패키지 내 `update_config.json` 파일의 `update_check_url` 값을 사용자의 실제 GitHub Raw URL로 적어두시면 완료됩니다.
- 추후 신규 버전(예: v1.2.0)이 나오면 `version.json`의 숫자와 다운로드 링크만 고치면 전 직원 프로그램에 알림이 즉시 뜹니다.
