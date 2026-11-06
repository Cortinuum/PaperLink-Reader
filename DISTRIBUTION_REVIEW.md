# PDF2zh 사용과 PaperLink 배포 점검

검토일: 2026-11-06. 이 문서는 확인한 라이선스와 실제 배포 파일의 구성을 기록합니다.

## 현재 배포에 대한 결론

PaperLink는 영어·한국어 PDF를 불러와 읽는 별도 리더입니다. 공개 소스와 실행 ZIP에는 PDFMathTranslate/PDF2zh, PDFMathTranslate-next, BabelDOC 번역 프로그램·모델·설치 폴더를 포함하지 않습니다. 해당 프로그램을 호출하는 번역 기능도 없습니다. 따라서 현재 배포는 **PDF2zh 자체를 복사해 재배포하는 구성은 아닙니다**.

이 PC에서 별도로 내려받아 사용한 번역기는 pdf2zh-next 2.9.0이며, 이 설치본과 원문·번역 PDF·API 키·로그인 정보는 PaperLink 배포물에 넣지 않았습니다. 실제 ZIP의 파일 목록과 앱의 import/의존성을 점검했습니다. PaperLink의 `requirements.txt`는 PyMuPDF, cryptography, cffi, pycparser입니다.

PyMuPDF는 PDF2zh와 다른 PDF 처리 라이브러리이며 PaperLink에도 포함됩니다. 그 라이선스에 맞춰 앱 코드는 AGPLv3로 공개하고, 소스·설정·빌드 절차와 제3자 고지를 제공합니다. 세부 출처는 [THIRD_PARTY.md](THIRD_PARTY.md)에 있습니다.

## PDF2zh를 사용하는 것과 재배포하는 것

- 공식 PDFMathTranslate와 PDFMathTranslate-next의 확인한 LICENSE는 모두 **GNU AGPL v3.0**입니다. GitHub에서 받을 수 있다는 이유만으로 무조건 자유로운 재배포가 되는 것은 아니며, 해당 라이선스 조건을 따라야 합니다.
- 본인 PC에서 프로그램을 실행하는 사용과 프로그램 사본을 타인에게 전달하는 행위는 구분합니다. AGPL은 원본 프로그램 실행을 허용합니다.
- 향후 번역기 코드나 실행 파일을 배포물에 넣는다면 원저작권·라이선스·무보증 고지를 보존하고, 수정 사항을 표시하며, 해당 배포본의 대응 소스와 필요한 빌드·설치 절차를 제공해야 합니다. 번역기의 모델·폰트·다른 라이브러리는 각각의 조건도 확인해야 합니다.
- 수정한 AGPL 프로그램을 네트워크로 제공할 때는 원격 사용자에게 해당 버전의 대응 소스를 받을 방법을 제공해야 합니다. 현재 로컬 리더의 공개 코드가 있다고 해서 미래에 추가할 번역기의 배포 조건이 자동으로 충족되는 것은 아닙니다.

공식 라이선스 확인 지점:

- [PDFMathTranslate LICENSE](https://github.com/PDFMathTranslate/PDFMathTranslate/blob/1c9ba47e849030ec59c430cd4d5378b2ecb5c58d/LICENSE)
- [PDFMathTranslate-next LICENSE](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next/blob/f8dffcf4c3a33b254391d43514439b975ce8d966/LICENSE)
- 특히 AGPL 제2조(실행과 출력), 제4~6조(사본·수정·실행형 배포), 제13조(수정판의 원격 네트워크 이용)를 확인했습니다.

## 번역된 논문 PDF의 권리

프로그램의 AGPL과 논문·번역물의 저작권은 별개입니다. AGPL이 생성된 출력물에 무조건 적용되는 것은 아니며, 논문을 번역했다고 해서 원논문의 배포 권한을 얻는 것도 아닙니다. 원문과 번역 PDF를 공개하려면 그 논문의 라이선스·번역/변경 허용 범위·권리자 허락을 확인해야 합니다. 오픈 액세스라는 표시만으로 모든 재배포·변경이 허용된다고 가정하지 않습니다.

이 저장소와 실행 ZIP은 사용자 논문·번역 PDF를 배포하지 않습니다. 사용자가 직접 불러온 파일은 자신의 PC에서 보관합니다.

이 결론은 위에 명시한 배포 구성과 자료에 대한 검토입니다. 프로그램·모델·논문을 추가해 배포 범위가 달라지면 다시 확인해야 합니다.
