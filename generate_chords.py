"""
generate_chords.py -- build the chord library from a word list.

Chord rule: a word's chord is the word typed WITHOUT its vowels, in natural
order, with the first letter always kept and duplicate letters preserved:

    example -> exmpl     chording -> chrdng     order -> ordr
    instead -> instd     enough   -> engh

(Set KEEP_LEADING_VOWEL = False for pure consonants: example -> xmpl.)

When two words reduce to the same chord, the MORE FREQUENT word keeps the short
form; the rarer one has its vowels revealed one at a time, in natural position,
until its chord is unique. Every word therefore gets a chord.

Contractions (don't, I'm, you're, ...) are included at their real frequency. Their
chord is built from the letters alone, so the apostrophe is never typed but is
always written: don't -> dnt, can't -> cnt. Each one also answers to its spelling
without the apostrophe (dont, cant) unless that spelling is a real word (its, were).
Possessives (world's, people's) are left out.

Run:  python generate_chords.py   -> writes chords.json and cheatsheet.md
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
WORDS_FILE = HERE / "words.txt"
VOWELS = set("aeiou")
TARGET_WORDS = 50000          # maximal coverage: the most-common word owns each skeleton
CHEAT_CAP = 3000              # cheatsheet lists only the most common (the rest follow the rule)
KEEP_LEADING_VOWEL = True     # keep a first-letter vowel (example -> exmpl, not xmpl)

# 2-key chords whose letters spell one of these common words are avoided, so the
# short word stays typeable literally (e.g. "to", "on", "of", "go").
TWO_LETTER_WORDS = {
    "am", "an", "as", "at", "be", "by", "do", "go", "he", "hi", "if", "in", "is",
    "it", "me", "my", "no", "of", "oh", "ok", "on", "or", "ox", "so", "to", "up",
    "us", "we", "ax", "ex",
}

DEFAULT_WORDS = (
    "the and that have for not with you this but his from they say her she will "
    "one all would there their what about which people because example order enough"
).split()

# Contractions kept from the word list: n't 're 've 'll 'm 'd, plus the 's forms
# that really are contractions (it's = it is). Other 's tokens are possessives.
CONTRACTION_SUFFIXES = {"re", "ve", "ll", "m", "d"}
S_CONTRACTIONS = {"it's", "that's", "he's", "she's", "there's", "here's", "what's",
                  "who's", "where's", "let's", "how's", "when's", "why's"}
EXTRA_APOSTROPHE_WORDS = {"y'all", "ma'am", "o'clock"}
BLOCKED = {"ya'll", "who're"}
MISSPELLING_RATIO = 10        # "dont" is a missed apostrophe if "don't" is 10x as common


def is_contraction(w):
    if w in BLOCKED:
        return False
    if w in EXTRA_APOSTROPHE_WORDS or w in S_CONTRACTIONS:
        return True
    if w.count("'") != 1:
        return False
    head, tail = w.split("'")
    if not head.isalpha() or not tail.isalpha():
        return False
    if tail == "t":
        return len(head) >= 2 and head.endswith("n")
    return tail in CONTRACTION_SUFFIXES


def letters(w):
    return w.replace("'", "")


def display(w):
    """How a word is written out: i'm -> I'm."""
    return "I" + w[1:] if w.startswith("i'") else w


def load_words():
    """Return (words, misspellings), words in frequency order with contractions.

    `misspellings` maps an apostrophe-less token that is really a missed
    apostrophe ("dont" 55/M vs "don't" 1580/M) to its contraction. Those tokens
    are dropped as words and become aliases of the contraction instead.
    """
    word_frequency = None
    try:
        from wordfreq import top_n_list, word_frequency
        raw = top_n_list("en", TARGET_WORDS * 3)
        print(f"Harvested {len(raw)} words from wordfreq frequency list.")
    except Exception:
        print("wordfreq not available; falling back to words.txt.")
        if WORDS_FILE.exists():
            raw = WORDS_FILE.read_text(encoding="utf-8").split()
        else:
            raw = list(DEFAULT_WORDS)

    misspellings = {}
    if word_frequency:
        for w in raw:
            if is_contraction(w):
                s = letters(w)
                if word_frequency(s, "en") * MISSPELLING_RATIO < word_frequency(w, "en"):
                    misspellings.setdefault(s, w)

    seen, out = set(), []
    for w in raw:
        w = w.split("#", 1)[0].strip().lower()
        if w in seen or w in misspellings:
            continue
        if (w.isalpha() and len(w) >= 3) or is_contraction(w):
            seen.add(w)
            out.append(w)
        if len(out) >= TARGET_WORDS:
            break
    return out, misspellings


def spells_two_letter_word(chord):
    return len(chord) == 2 and (
        "".join(chord) in TWO_LETTER_WORDS or "".join(reversed(chord)) in TWO_LETTER_WORDS)


def base_indices(word):
    keep = [i for i, c in enumerate(word) if i == 0 or c not in VOWELS]
    if not KEEP_LEADING_VOWEL and word and word[0] in VOWELS and len(keep) > 1:
        keep = keep[1:]                      # drop the leading vowel too
    return keep


def chord_variants(word):
    """Skeleton (consonants), then the same with 1, 2, ... vowels revealed, then full word."""
    base = set(base_indices(word))
    interior = [i for i, c in enumerate(word) if c in VOWELS and i not in base]
    for k in range(len(interior) + 1):
        kept = sorted(base | set(interior[:k]))
        yield tuple(word[i] for i in kept)


def build(words):
    """Return [(word as written, chord, is_alias)] in frequency order."""
    plain = {w for w in words if "'" not in w}
    twin_letters = {letters(w) for w in words if "'" in w}
    seen_plain = set()   # plain words already placed, i.e. more frequent than the current one
    assigned = {}        # tuple(keys) -> word
    result = []
    for word in words:
        if len(word) < 3:
            continue
        s = letters(word)
        is_c = "'" in word
        if not is_c:
            seen_plain.add(s)
        chosen = None
        for variant in chord_variants(s):
            if len(variant) < 2 or variant in assigned or spells_two_letter_word(variant):
                continue
            if is_c and "".join(variant) in seen_plain:
                continue      # never spell a more common word: we're must not become "were"
            chosen = variant
            break
        if chosen is None and (is_c or s in twin_letters):
            twin = tuple(s) + (s[-1],)    # its / it's share every letter: double the last one
            if twin not in assigned:
                chosen = twin
        if chosen is None:
            continue
        assigned[chosen] = word
        result.append((display(word), chosen, False))
        full = tuple(s)
        if is_c and s not in plain and full not in assigned and not spells_two_letter_word(full):
            assigned[full] = word          # alias: the same contraction spelled without the '
            result.append((display(word), full, True))
    return result


def main():
    words, misspellings = load_words()
    result = build(words)

    chords_json = {",".join(ch): w for w, ch, _ in result}
    (HERE / "chords.json").write_text(json.dumps(chords_json, indent=2), encoding="utf-8")

    rows = {}                       # word -> [chord, alias...], first-seen (frequency) order
    for w, ch, _ in result:
        rows.setdefault(w, []).append("".join(ch))
    lines = ["# Chord cheat sheet", "",
             f"{len(rows)} words. Type the letters in order, then SPACE."]
    if len(rows) > CHEAT_CAP:
        lines.append(f"(showing the {CHEAT_CAP} most common; the rest follow the same rule)")
    lines += ["", "| word | chord |", "|------|-------|"]
    for w, chords in list(rows.items())[:CHEAT_CAP]:
        alt = f" (or {', '.join(chords[1:])})" if len(chords) > 1 else ""
        lines.append(f"| {w} | {chords[0]}{alt} |")
    (HERE / "cheatsheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    sizes = {}
    for _, ch, alias in result:
        if not alias:
            sizes[len(ch)] = sizes.get(len(ch), 0) + 1
    contractions = sum(1 for w in rows if "'" in w)
    aliases = sum(1 for *_, alias in result if alias)
    print(f"Wrote {len(rows)} words ({contractions} contractions, {aliases} apostrophe-free "
          f"aliases, {len(misspellings)} misspelled tokens folded in) to chords.json and cheatsheet.md")
    print("Chord sizes:", ", ".join(f"{n}:{c}" for n, c in sorted(sizes.items())))


if __name__ == "__main__":
    main()
