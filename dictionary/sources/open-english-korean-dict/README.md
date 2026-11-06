# Open English-Korean Dictionary

A community-driven, open-source English-Korean dictionary with IPA pronunciations, CEFR levels, and frequency rankings.

## Stats

| Metric | Value |
|--------|-------|
| Total words | 48,037 |
| Korean meanings | 100% |
| IPA pronunciations | 59.1% |
| CEFR levels | 100% (17.8% empirical) |
| License | CC-BY-SA 4.0 |

## Data Format

### SQLite Database

The primary distribution format is SQLite (`dict/word_dictionary.sqlite`):

```sql
CREATE TABLE words (
    word TEXT PRIMARY KEY,
    meaning_ko TEXT NOT NULL,
    meaning_ja TEXT,
    meaning_zh TEXT,
    meaning_en TEXT,
    meaning_secondary TEXT,
    ipa TEXT,
    pos TEXT,
    cefr TEXT DEFAULT 'A1',
    freq_rank INTEGER
);
```

### JSON Export

For easier programmatic access, the dictionary is also available as JSON (`dict/words.json`):

```json
{
  "abandon": {
    "meaning_ko": "버리다, 포기하다",
    "ipa": "/əˈbændən/",
    "pos": "verb",
    "cefr": "B1",
    "freq_rank": 1234
  }
}
```

## Data Sources

This dictionary was built by merging and curating data from the following open-source sources:

| Source | Entries | License | URL |
|--------|---------|---------|-----|
| kengdic | 40,362 | CC-BY-SA 3.0 | [GitHub](https://github.com/garfieldnate/kengdic) |
| cc-kedict | 8,270 | CC-BY-SA 3.0 | [GitHub](https://github.com/mhagiwara/cc-kedict) |
| ipa-dict | 125,927 | MIT | [GitHub](https://github.com/open-dict-data/ipa-dict) |
| CMU Pronouncing Dictionary | 126,052 | BSD | [CMU](http://www.speech.cs.cmu.edu/cgi-bin/cmudict) |
| CEFR-J Wordlist | 8,653 | CC-BY-SA 4.0 | [GitHub](https://github.com/openlanguageprofiles/olp-en-cefrj) |
| NGSL | 2,801 | CC-BY-SA | [newgeneralservicelist.org](http://www.newgeneralservicelist.org) |
| NAWL | 963 | CC-BY-SA | [newacademicwordlist.org](http://www.newacademicwordlist.org) |

Hand-curated translations and LLM-assisted translations are original works by the LexiSnap project team.

## Contributing

We welcome contributions! Here's how you can help:

### Adding or improving translations

1. Fork this repository
2. Edit `contributions/` JSON files or submit new ones
3. Open a Pull Request with a description of your changes

### Contribution format

Create a JSON file in `contributions/` with your additions:

```json
{
  "metadata": {
    "contributor": "your-github-username",
    "description": "Added slang/neologisms for 2026",
    "date": "2026-03-16"
  },
  "words": {
    "doomscroll": {
      "meaning_ko": "끝없이 스크롤하며 부정적 뉴스 보기",
      "pos": "verb",
      "cefr": "C1"
    },
    "situationship": {
      "meaning_ko": "정의되지 않은 연애 관계",
      "pos": "noun",
      "cefr": "C2"
    }
  }
}
```

### Types of contributions we're looking for

- New words (especially neologisms, slang, technical terms)
- Improved Korean translations (more natural, more accurate)
- Missing IPA pronunciations
- Corrected CEFR levels
- Additional parts of speech
- Japanese (meaning_ja) and Chinese (meaning_zh) translations

## Usage

### Python

```python
import sqlite3

db = sqlite3.connect("dict/word_dictionary.sqlite")
db.row_factory = sqlite3.Row

# Look up a word
row = db.execute("SELECT * FROM words WHERE word = ?", ("hello",)).fetchone()
print(dict(row))

# Find all B1 words
b1_words = db.execute("SELECT word, meaning_ko FROM words WHERE cefr = 'B1'").fetchall()
```

### Swift (iOS/macOS)

```swift
import SQLite3

let db = try SQLiteDatabase(path: "word_dictionary.sqlite")
let word = try db.query("SELECT * FROM words WHERE word = ?", ["hello"])
```

## Build from Source

```bash
cd scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python expand_dictionary.py --target 50000
```

## License

This work is licensed under [Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

This means you are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material for any purpose, including commercially

Under the following terms:
- **Attribution** — You must give appropriate credit and link to this repository
- **ShareAlike** — If you remix or build upon this material, you must distribute your contributions under the same license

## Related Projects

- [LexiSnap](https://github.com/jhseo1211/LexiSnap) — iOS vocabulary learning app using this dictionary
- [kengdic](https://github.com/garfieldnate/kengdic) — Korean-English dictionary (upstream source)
- [cc-kedict](https://github.com/mhagiwara/cc-kedict) — Creative Commons Korean-English dictionary (upstream source)
