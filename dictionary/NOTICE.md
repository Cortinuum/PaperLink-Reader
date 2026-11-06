# Local English-Korean dictionary data

The bundled general dictionary is derived from koreader-dicts v1.3.0 en-ko.zip:
https://github.com/DanielGregorini/koreader-dicts/releases/tag/v1.3.0
Author/compiler: Daniel Gregorini and upstream Wiktionary contributors.
Upstream sources: English Wiktionary via Kaikki/wiktextract; Princeton WordNet 3.0.
License of the dictionary compilation and this adapted general dictionary: CC BY-SA 4.0.
https://creativecommons.org/licenses/by-sa/4.0/

Original download, LICENSE, ATTRIBUTION, README.txt and .ifo metadata are retained in sources/.
Full CC BY-SA 4.0 legal text is in sources/CC-BY-SA-4.0.txt.

Adaptation by PaperLink (2026-11-05): Korean bold-text senses and part-of-speech tags
were extracted from the StarDict HTML entries, English explanations and HTML were
omitted, case-insensitive lookup keys and the original synonym/inflection index
were converted to SQLite. No upstream code is executed. 25,974 entries contain
usable Korean senses; 11 of the original 25,985 entries did not and were omitted.
Synonym-index connections can be broader than inflected forms. Exact headwords
are preferred. Coverage and sense ordering do not imply contextual correctness.

engineering_supplement.json contains 22 separately authored PaperLink technical
supplements, offered under CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/ .
These are labeled separately and are not presented as upstream dictionary content.
Personal vocabulary in ../data/vocabulary.sqlite3 is separate and is not included
in this open dictionary data.

Rebuild using the bundled Python: run build_dictionary.py from PaperLink_Reader.
The source archive SHA-256 and imported counts are recorded in manifest.json.


Additional general dictionary (2026-11-06): Open English-Korean Dictionary,
https://github.com/jhseo1211/open-english-korean-dict/tree/92cbfe63deee1ccead2c42677027d8b4a305b2c7
Authors: jhseo1211 / LexiSnap project team and credited upstream contributors.
License: CC BY-SA 4.0. Original words.json, README, CREDITS and revision are
retained in sources/open-english-korean-dict/. See CREDITS for constituent data.
PaperLink imports only English headwords, Korean meanings and part-of-speech
labels; IPA, rankings and other languages are omitted. 48,035 usable Korean
entries were imported; 2 entries without Korean text were omitted. Upstream
includes curated and LLM-assisted translations. Results are labeled community
supplements and may omit senses or give an unsuitable meaning for a paper.
Existing dictionary senses are preserved. Combined unique headwords: 61,710.
Spelling normalization and attested lemma candidates are tried on lookup misses.
Guessed lemmas and compound components are explicitly labeled; a component
meaning is not a translation of the whole compound. No online model is called.

Quick English-Korean is excluded from this repository and its release ZIP.
