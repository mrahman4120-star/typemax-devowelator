# Typemax Devowelator

Type words **without their vowels** and get the whole word. Press Space and
`thrgh` becomes `through`, `exmpl` becomes `example`, `ppl` becomes `people`.

Typemax Devowelator is a small Windows app that turns any keyboard into a
chording keyboard. You don't need special hardware or a chord table to memorise:
the chord for a word is the word with its vowels left out.

```
the      -> th        order    -> ordr       through  -> thrgh
example  -> exmpl     people   -> ppl        letter   -> lttr
```

## Features

- **~49,000-word library** built from English word-frequency data. When two words
  reduce to the same letters, the more common one gets the short chord and the
  rarer one keeps a vowel until its chord is unique, so every word is reachable.
- **Works in any app.** It uses a system-wide keyboard hook, so it works in
  Notepad, Word, browsers and so on. Ctrl/Alt shortcuts still work.
- **Capitals:** `Th` → `The`, `TH` → `THE`.
- **Live suggestions** show which words start with the keys typed so far.
- **Practice tab** with accuracy, streak and words-per-minute. Nothing you type
  there reaches other apps.
- **Dictionary mode** offers to learn new words as you type them. Strings that
  look like mistyped chords are skipped so typos don't pile up in the library.
- **Add a chord anywhere** with Ctrl+Alt+I, plus a searchable editor for
  rebinding any word. It blocks a new binding that would clash with another word.
- Your own words live in `user_chords.json` and survive regenerating the library.

## Requirements

- **Windows** (10 or 11). The keyboard hook and the guide launcher are Windows-specific.
- **Python 3.9+** with Tkinter (included in the standard python.org installer).
- The [`keyboard`](https://github.com/boppreh/keyboard) package.

## Install and run

```bash
git clone https://github.com/mrahman4120-star/typemax-devowelator.git
cd typemax-devowelator
pip install -r requirements.txt
pythonw typemax_devowelator.pyw
```

Then click **Enable**. The app always starts **disabled**, so it never captures your
keyboard until you ask it to. See [USER_GUIDE.md](USER_GUIDE.md) for the full guide.

**Optional Start Menu shortcut** (PowerShell, run from the project folder):

```powershell
$s = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Typemax Devowelator.lnk")
$s.TargetPath = (Get-Command pythonw).Source
$s.Arguments = "`"$PWD\typemax_devowelator.pyw`""
$s.WorkingDirectory = "$PWD"
$s.Save()
```

## Privacy and safety

The app installs a **global keyboard hook**, which is the same mechanism a
keylogger uses. Here is exactly what it does with your keys:

- **Nothing is sent over the network.** The app makes no network connections.
- **Nothing you type is written to disk**, except words you explicitly add or
  accept in Dictionary mode, which go into `user_chords.json` in the app folder.
- The on-screen "paper tape" history exists only in memory and is gone when you close the app.
- **Fails open:** if the engine hits an error, the key passes through untouched,
  so a bug can't lock your keyboard. Disable it or close the window to return to
  normal typing instantly.

Some antivirus tools flag keyboard-hook programs on principle. The source is a
single readable Python file, so you can check it yourself.

## Rebuilding the word library

`chords.json` is generated. To rebuild it (for example with more words, or
pure-consonant chords like `xmpl`), edit the settings at the top of
`generate_chords.py` and run:

```bash
pip install -r requirements-dev.txt
python generate_chords.py
```

Your `user_chords.json` is never touched by regeneration.

## Tests

```bash
python tests/test_engine.py    # chord rule, engine, dictionary, capitals, typo filter
python tests/test_gui.py       # headless GUI wiring
python tests/test_launch.py    # real launch with live hooks (local only)
```

## Known limitations

- Windows only.
- To type into an app running as administrator, run Typemax Devowelator as administrator too.
- If two words share a vowel-less form, the more common word always wins the short
  chord. There is no pick-list yet.
- The `keyboard` package has not had a release since 2020. It works, but it is unmaintained.

## License

- **Code:** [MIT](LICENSE).
- **Word data** (`chords.json`, `cheatsheet.md`): derived from
  [wordfreq](https://github.com/rspeer/wordfreq) by Robyn Speer and licensed
  under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). See
  [DATA_LICENSE.md](DATA_LICENSE.md).
