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


def load_words():
    words = []
    try:
        from wordfreq import top_n_list
        words = top_n_list("en", TARGET_WORDS * 3)
        print(f"Harvested {len(words)} words from wordfreq frequency list.")
    except Exception:
        print("wordfreq not available; falling back to words.txt.")
        if WORDS_FILE.exists():
            words = WORDS_FILE.read_text(encoding="utf-8").split()
        else:
            words = list(DEFAULT_WORDS)

    seen, out = set(), []
    for w in words:
        w = w.split("#", 1)[0].strip().lower()
        if w.isalpha() and len(w) >= 3 and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= TARGET_WORDS:
            break
    return out


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
    assigned = {}     # tuple(keys) -> word
    result = []
    for word in words:
        if len(word) < 3:
            continue
        chosen = None
        for variant in chord_variants(word):
            if len(variant) < 2 or variant in assigned or spells_two_letter_word(variant):
                continue
            chosen = variant
            break
        if chosen is None:
            continue
        assigned[chosen] = word
        result.append((word, chosen))
    return result


def main():
    words = load_words()
    result = build(words)

    chords_json = {",".join(ch): w for w, ch in result}
    (HERE / "chords.json").write_text(json.dumps(chords_json, indent=2), encoding="utf-8")

    lines = ["# Chord cheat sheet", "",
             f"{len(result)} chords. Type the letters in order, then SPACE."]
    if len(result) > CHEAT_CAP:
        lines.append(f"(showing the {CHEAT_CAP} most common; the rest follow the same rule)")
    lines += ["", "| word | chord |", "|------|-------|"]
    for w, ch in result[:CHEAT_CAP]:
        lines.append(f"| {w} | {''.join(ch)} |")
    (HERE / "cheatsheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    sizes = {}
    for _, ch in result:
        sizes[len(ch)] = sizes.get(len(ch), 0) + 1
    print(f"Wrote {len(result)} chords to chords.json and cheatsheet.md")
    print("Chord sizes:", ", ".join(f"{n}:{c}" for n, c in sorted(sizes.items())))


if __name__ == "__main__":
    main()
