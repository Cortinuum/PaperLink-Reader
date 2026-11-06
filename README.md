# PaperLink Reader

영어 원문과 한국어 번역 PDF를 나란히 읽는 **Windows 로컬 브라우저 리더**입니다.

## 다운로드·실행

[최신 실행 ZIP 받기](https://github.com/Cortinuum/PaperLink-Reader/releases/latest)

1. Windows 10/11 x64에서 ZIP 전체를 압축 해제합니다.
2. `Start_PaperLink.cmd`를 실행하면 기본 브라우저에서 열립니다.
3. 영어 원문과 한국어 번역 PDF를 한 쌍으로 불러옵니다.
4. 종료는 `Stop_PaperLink.cmd`입니다.

Python과 패키지를 포함하여 별도 설치·최초 다운로드가 필요하지 않습니다. 시스템 Python과 PATH를 바꾸지 않습니다. 이 프로그램은 **이미 번역된 PDF를 읽는 리더**이며 PDF 번역 엔진을 포함하지 않습니다. 논문·기록·단어장은 각 사용자 PC의 `data/`에 저장하며 배포물에 포함하지 않습니다.

## 기능

- 원문·번역 PDF 나란히 보기, 기본 75% 배율, 페이지 이동 단축키
- 문장 선택과 GPT 옆 패널, 분야를 가정하지 않는 질문과 추가 검토 선택
- 오프라인 영한사전, 대표 결과 한 개와 접을 수 있는 추가 결과, 개인 단어장
- 논문쌍 추가·PDF 변경·제거·휴지통 복원
- 다크 모드, 메모·읽기 기록·단어장 내보내기

대표 사전은 커뮤니티 보충입니다. 테스트 논문 11쪽 전체에서 출현 횟수 기준 적중률은 커뮤니티 보충 **87.13%**, 공개 사전 **75.61%**였습니다. 비교 방법은 [dictionary/comparison.json](dictionary/comparison.json)에 있습니다. 단어 조회율이며 문맥상 뜻의 정확도가 아닙니다. Quick 사전은 제외했습니다.

## 개인정보·GPT 연결

PDF 보기·사전 조회는 로컬 처리합니다. 원본 PDF를 수정하지 않습니다. 용례 검색을 누르면 표제어를 외부 검색 서비스로 보냅니다.

GPT 질문은 사용자가 로그인과 전송 동의를 한 경우 선택 문장·대응 번역·문맥과 최근 대화를 첨부합니다. ChatGPT 연결의 실제 이용 가능 여부와 한도는 계정·공식 서비스 정책에 따릅니다. 유료 API 키로 자동 전환하지 않습니다. 로그인 연결 정보는 해당 Windows 사용자 보호 기능으로 저장하며 저장소·ZIP에는 포함하지 않습니다. 보관한 대화가 ChatGPT 웹 목록에 동기화되지는 않습니다.

## 개발 환경

`Setup_PaperLink.cmd`를 실행하면 앱 폴더 안에 전용 Python 환경을 구성합니다. 이후 `Start_PaperLink.cmd`로 실행합니다. 의존성은 `requirements.txt`에 고정했습니다.

```powershell
.\.venv\Scripts\python.exe -m unittest test_review_options test_chatgpt_account test_pdf_import test_library_management test_local_dictionary
node --test test_markdown.cjs test_question_prompt.cjs
```

실행 ZIP은 `build_release.py`로 생성합니다. 사전 재구축은 `build_dictionary.py`를 사용합니다. 사전 원자료와 출처 고지는 `dictionary/sources/`에 있습니다.

## 한계

자동 문장 연결은 의미 검증된 번역 정렬이 아닙니다. 복잡한 단·수식·약어·그림 안의 문장은 잘못 추출될 수 있습니다. PDF 보기로 확인하세요. 스캔 PDF는 단어·문장 선택에 OCR이 필요합니다. 공개 사전과 커뮤니티 사전에도 오역·누락이 남을 수 있습니다.

## 라이선스

앱 코드: GNU AGPL v3.0. 사전과 외부 라이브러리에는 각각의 별도 라이선스가 적용됩니다. [THIRD_PARTY.md](THIRD_PARTY.md), [dictionary/NOTICE.md](dictionary/NOTICE.md)를 확인하세요.
