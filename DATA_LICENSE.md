# Data license

The source code in this repository is licensed under the MIT License (see `LICENSE`).

The generated word data files

- `chords.json`
- `cheatsheet.md`

are **derived from the word-frequency data in
[wordfreq](https://github.com/rspeer/wordfreq)** by Robyn Speer, which is
distributed under the
[Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).
wordfreq is itself built from several upstream corpora; see the wordfreq README
for the full list of sources and their attributions.

**Changes made:** `generate_chords.py` took the most frequent English words from
wordfreq, kept only alphabetic words of three or more letters, cut the list to
about 50,000 words, and turned each word into a vowel-dropped key sequence
("chord"). The ordering of the files reflects wordfreq's frequency ranking.

Accordingly, `chords.json` and `cheatsheet.md` are licensed under **CC BY-SA 4.0**.
If you redistribute them or works adapted from them, you must give appropriate
credit and share your adaptations under the same license.

`words.txt` (a short fallback list of common English words) is not derived from
wordfreq and is covered by the MIT License with the rest of the repository.
