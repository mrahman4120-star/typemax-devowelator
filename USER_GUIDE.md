# Typemax Devowelator — User Guide

Typemax Devowelator turns your keyboard into a chording keyboard. You type a word **without
its vowels**, in order, then press **Space**, and the whole word appears:

```
thrgh  + Space  ->  through
exmpl  + Space  ->  example
ppl    + Space  ->  people
```

There is one input method (no chords held simultaneously) — you just skip the
vowel keys.

---

## 1. Quick start

1. Launch the app: double-click `typemax_devowelator.pyw`, or run
   `pythonw typemax_devowelator.pyw` (see the README for setup and an optional
   Start Menu shortcut).
2. Click **Enable**. The status bar turns green: *chording is live*.
3. In Notepad, type a word's letters **without the vowels**, then **Space**:
   - `t` `h` Space → `the`
   - `o` `r` `d` `r` Space → `order`
   - `t` `h` `r` `g` `h` Space → `through`
4. Click **Disable** (or close the window) to type normally again.

The app starts **disabled** on purpose, so it never captures your keyboard until
you ask it to.

---

## 2. How the chord for a word is built

**Drop the vowels. Keep the first letter, the order, and any doubled letters.**

| word | chord | | word | chord |
|------|-------|-|------|-------|
| the | th | | order | ordr |
| example | exmpl | | letter | lttr |
| instead | instd | | people | ppl |
| enough | engh | | through | thrgh |

Typemax Devowelator ships with about **49,000 words**. The most common word owns each chord
(`thn → then`, `frlnc → freelance`); rarer words that would collide are reached
by typing more of their letters. Anything not covered still types literally, and
Dictionary mode learns it.

Two small rules make it practical:
- If dropping vowels makes two words identical, the rarer one gets a vowel added
  back (in its natural place) until it's unique — so a few words keep a vowel.
- A word isn't given a chord that spells a common two-letter word, so you can
  still type `to`, `on`, `of`, `go`, etc. literally. That's why `one → one` and
  `use → use` keep a vowel.

Unknown words are typed **literally** (whatever letters you pressed + Space).

**Capitals work.** Hold Shift on the first letter (`Th` → `The`), or type the whole
chord in capitals / with Caps Lock (`TH` → `THE`).

---

## 3. Live suggestions (great for learning)

As you type a chord, the app shows every word whose chord **starts with** the
keys so far, so you see the word coming:

```
thr →  through (thrgh)   three (thr)   throw (thrw)   ...
```

Shown under the paper tape (Type tab) and in the Practice tab.

---

## 4. Practice tab

1. Open the **Practice** tab, pick a **Word set**:
   - **All** (default) — random words from the whole ~49,000-word library.
   - **My words** — only the words you added or re-bound (great for drilling your
     own custom vocabulary).
   - **Top 100 / 500 / 2000** — just the most common words, for starting out.
2. Click **Start**. A target word appears with its chord.
3. Type the chord. Correct → it advances; wrong → it shows the right chord.
4. Watch **accuracy**, **streak**, and **words-per-minute**.

Tips: keep **Show the chord hint** on at first, use **Top 100** while learning and
**My words** to drill your own additions, and note that nothing is typed into
other apps while practicing — it's a safe sandbox.

---

## 5. Impulse — add chords on the fly

- Click **＋ Add chord**, or press **Ctrl + Alt + I** anywhere.
- Type the word. Leave **Keys** blank to auto-generate (drop the vowels), or type
  your own letters (spaces between them; duplicates allowed).
- **Add** saves it and makes it usable immediately.

---

## 6. Dictionary mode — learn new words as you type

**Dictionary mode is on by default** (untick it on the Type tab to turn it off).
Whenever you type a word the app doesn't know, it types the word normally and
offers a chord for it:

```
you type:   freelance + Space
banner:     ➕ new word “freelance” → frlnc   [ Space = add · Esc = skip ]
```

- Press **Space** again to add it — the chord is saved and usable immediately.
- Press **Esc** to skip it.
- Press any other key to dismiss and keep typing.

Only genuinely new words trigger the offer: they need a vowel, must not already
be in the library, and must not look like a **mistyped chord** (for example
`nanklvn`, which has almost no vowels). Mistyped chords are skipped so typos don't
pile up in your library. If a real word is skipped this way, add it with
**Ctrl + Alt + I**. It's the easy way to grow your
library while you work.

---

## 7. View / edit every chord

- Click **View / edit chords**.
- **Search** to filter, click a word to select it.
- Edit its **Keys** (in order, duplicates allowed) and **Save**.
- If your keys already type another word, you get a live **⚠ warning** and the
  save is blocked — no two words can share a chord.

---

## 8. Growing / rebuilding the library

- Your own additions (Dictionary mode, Add chord, re-bindings) are saved to
  **`user_chords.json`** and are **kept when you regenerate** — the generator only
  rewrites `chords.json`. Delete a line in `user_chords.json` to undo an edit.
- `cheatsheet.md` — the most common words and their chords (top 3000).
- `generate_chords.py` — rebuilds `chords.json` from the most-common English words.
  Edit the top (`TARGET_WORDS`, or `KEEP_LEADING_VOWEL = False` for `xmpl`-style
  pure-consonant chords) and run:
  ```
  python generate_chords.py
  ```
  Then restart the app. Your `user_chords.json` is untouched.

---

## 9. Turning it off / safety

- **Disable** (or closing the window) stops capture instantly.
- **Show keys as you type** is **on by default**: the letters appear as you type
  and are swapped for the word on Space. It's made Word-safe by suppressing the
  commit space, so autocorrect can't mangle the raw letters; if some app with heavy
  autocomplete misbehaves, untick it there.
- Untick it and your letters become **invisible until you press Space** instead —
  that's the suppression working, not a freeze.
- Ctrl/Alt shortcuts (copy, paste, …) keep working while chording.

---

## 10. Troubleshooting

| Problem | Fix |
|--------|-----|
| Nothing happens when I chord | Make sure the status bar is green (**Enable**). |
| Letters don't show as I type | Normal — they appear when you press Space. Disable for normal typing. |
| Chords don't reach an admin app | Close the app and relaunch it as administrator. |
| A chord types the wrong word | Look it up / change it in **View / edit chords**. |

---

## 11. Files

```
typemax_devowelator.pyw  the app
chords.json              generated chord library (rebuilt by generate_chords.py)
user_chords.json         your added/edited chords (created on first edit; safe from regeneration)
cheatsheet.md            printable word -> chord list (top 3000)
generate_chords.py       rebuilds chords.json
words.txt                fallback word list
USER_GUIDE.md            this file
tools/rollover_test.py   keyboard rollover checker (optional)
```

To uninstall: delete this folder (and any shortcut you made to it).
