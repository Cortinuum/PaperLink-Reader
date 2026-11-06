# Third-party components and data

Application source is prepared for GNU AGPL v3.0 distribution. Third-party components and dictionary datasets retain their own licences and copyright notices; this is not a relicensing of their data.

| Component | Version | Licence / notices | Corresponding source |
|---|---|---|---|
| PyMuPDF / MuPDF | 1.28.0 | AGPL v3.0 (Artifex dual licence; no commercial licence is included) | https://pypi.org/project/PyMuPDF/1.28.0/#files ; https://github.com/pymupdf/PyMuPDF/tree/1.28.0 ; https://mupdf.com/releases |
| CPython standalone runtime | 3.13.16 | PSF and bundled third-party notices in the runtime | https://www.python.org/downloads/ ; https://github.com/astral-sh/python-build-standalone |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause; included package notices | https://pypi.org/project/cryptography/49.0.0/#files |
| cffi | 2.1.0 | MIT; included package notices | https://pypi.org/project/cffi/2.1.0/#files |
| pycparser | 3.0 | BSD-3-Clause; included package notices | https://pypi.org/project/pycparser/3.0/#files |
| markdown-it | 15.0.3 | MIT; vendor/markdown-it.LICENSE | https://github.com/markdown-it/markdown-it/tree/15.0.3 |
| Wiktionary / koreader-dicts general dictionary | v1.3.0 | CC BY-SA 4.0; dictionary/NOTICE.md and dictionary/sources | https://github.com/DanielGregorini/koreader-dicts/releases/tag/v1.3.0 |
| Open English-Korean Dictionary | pinned revision in dictionary/sources/open-english-korean-dict/REVISION.txt | CC BY-SA 4.0 with constituent-source credits | https://github.com/jhseo1211/open-english-korean-dict |
| PaperLink authored technical supplements | 22 entries | CC0 1.0; dictionary/NOTICE.md | dictionary/engineering_supplement.json |

The release ZIP includes the app's Python/JavaScript source and the component notice files in its runtime/package directories. The complete app source and build/setup scripts are available at the matching GitHub release tag. Upstream component source archives are available through the version-pinned links above; use the versions in requirements.txt and runtime notices to reproduce the distribution.

The private Quick supplement, personal PDFs, reading records, vocabulary and account credentials are not published. PDFs used by users are not covered by this repository's application licence. No claim of third-party affiliation or endorsement is made.

PDF2zh / PDFMathTranslate-next is not bundled or invoked. See [DISTRIBUTION_REVIEW.md](DISTRIBUTION_REVIEW.md) for the software-versus-paper distribution distinction and the checked licence references.
