"""
Typemax Devowelator -- type words without their vowels (a chording keyboard for Windows).

You type a word WITHOUT its vowels, in order, then press Space, and the whole
word appears:  exmpl -> example,  ordr -> order,  thrgh -> through.
The first letter is always kept and duplicate letters count (ppl -> people).

Features: live word suggestions, on-the-fly chord creation ("impulse"), a
practice trainer, and a browser to view / re-bind every chord.

Run with:  pythonw typemax_devowelator.pyw
"""

import json
import os
import queue
import random
import sys
import time
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import keyboard
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Typemax Devowelator", "The 'keyboard' library is missing.\n\n"
                         "Open a terminal and run:\n    pip install keyboard")
    sys.exit(1)

if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
GEN_FILE = HERE / "chords.json"          # generated bulk; overwritten by generate_chords.py
USER_FILE = HERE / "user_chords.json"    # your added/edited chords; never touched by regeneration
GUIDE_FILE = HERE / "USER_GUIDE.md"
VOWELS = set("aeiou")
KEEP_LEADING_VOWEL = True
KEY_DOWN, KEY_UP = keyboard.KEY_DOWN, keyboard.KEY_UP

TWO_LETTER_WORDS = {
    "am", "an", "as", "at", "be", "by", "do", "go", "he", "hi", "if", "in", "is",
    "it", "me", "my", "no", "of", "oh", "ok", "on", "or", "ox", "so", "to", "up",
    "us", "we", "ax", "ex",
}


# --------------------------------------------------------------------------- #
#  chord rule + library helpers  (pure functions, unit tested)
# --------------------------------------------------------------------------- #

def spells_two_letter_word(chord):
    return len(chord) == 2 and (
        "".join(chord) in TWO_LETTER_WORDS or "".join(reversed(chord)) in TWO_LETTER_WORDS)


def base_indices(word):
    keep = [i for i, c in enumerate(word) if i == 0 or c not in VOWELS]
    if not KEEP_LEADING_VOWEL and word and word[0] in VOWELS and len(keep) > 1:
        keep = keep[1:]
    return keep


def chord_variants(word):
    """Consonant skeleton, then the same with 1, 2, ... vowels revealed, then full word."""
    base = set(base_indices(word))
    interior = [i for i, c in enumerate(word) if c in VOWELS and i not in base]
    for k in range(len(interior) + 1):
        kept = sorted(base | set(interior[:k]))
        yield tuple(word[i] for i in kept)


def derive_chord(word, taken):
    """Shortest vowel-dropped chord for a word that is free in `taken` (seq -> word)."""
    word = "".join(c for c in word.lower() if c.isalpha())
    if len(word) < 2:
        return None
    for variant in chord_variants(word):
        if len(variant) < 2 or spells_two_letter_word(variant):
            continue
        occ = taken.get(variant)
        if occ is None or occ == word:
            return variant
    return tuple(word)


def _read_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _parse_combo(combo):
    return tuple(k.strip().lower() for k in combo.split(",") if k.strip())


def load_library():
    """Merge the generated bulk (chords.json) with your edits (user_chords.json)."""
    by_seq, ordered, word_keys = {}, [], {}
    for combo, word in _read_json(GEN_FILE).items():
        keys = _parse_combo(combo)
        if len(keys) >= 2:
            by_seq[keys] = word
            if word not in word_keys:
                word_keys[word] = keys
                ordered.append(word)
    for combo, word in _read_json(USER_FILE).items():        # your edits win
        keys = _parse_combo(combo)
        if len(keys) < 2:
            continue
        old = word_keys.get(word)
        if old and old != keys and by_seq.get(old) == word:
            del by_seq[old]                                  # free the word's previous chord
        by_seq[keys] = word
        if word not in word_keys:
            ordered.append(word)
        word_keys[word] = keys
    return by_seq, ordered, word_keys


def build_prefix_index(words, word_keys):
    """Bucket words by their chord's first key, preserving frequency order."""
    idx = {}
    for w in words:
        seq = word_keys.get(w)
        if seq:
            idx.setdefault(seq[0], []).append((seq, w))
    return idx


def find_candidates(prefix, prefix_index, limit=8):
    """Words whose chord STARTS WITH the keys pressed so far (frequency order)."""
    if not prefix:
        return []
    p = tuple(prefix); n = len(p); out = []
    for seq, w in prefix_index.get(prefix[0], ()):
        if seq[:n] == p:
            out.append((w, seq))
            if len(out) >= limit:
                break
    return out


def keys_clash(new_keys, word, by_seq):
    """Return the OTHER word this exact key sequence is bound to, or None."""
    other = by_seq.get(tuple(new_keys))
    return other if (other and other != word) else None


def save_chord(word, keys):
    data = _read_json(USER_FILE)
    data[",".join(keys)] = word
    USER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def rebind_chord(word, old_keys, new_keys):
    data = _read_json(USER_FILE)
    for combo in [c for c, w in list(data.items()) if w == word]:
        del data[combo]                       # drop any earlier user binding for this word
    data[",".join(new_keys)] = word
    USER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def apply_case(word, typed):
    """Carry the typed capitalisation onto the word: Th -> The, TH -> THE."""
    if not word or not typed or not typed[0].isupper():
        return word
    if len(typed) > 1 and all(c.isupper() for c in typed):
        return word.upper()
    return word[0].upper() + word[1:]


def _edits1(s):
    """Every string one insert / delete / substitute / adjacent swap away from s."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    splits = [(s[:i], s[i:]) for i in range(len(s) + 1)]
    out = {a + b[1:] for a, b in splits if b}
    out |= {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
    out |= {a + c + b[1:] for a, b in splits if b for c in letters}
    out |= {a + c + b for a, b in splits for c in letters}
    out.discard(s)
    return out


def looks_like_chord(literal, by_seq):
    """True if an unmatched string is probably a mistyped chord, not a new word.

    Real words carry their vowels; chords mostly don't. So we flag strings with
    almost no interior vowels, and vowel-poor strings one edit away from a chord.
    (Measured on wordfreq: catches ~80% of mistyped chords, skips ~13% of rare
    real words -- those can still be added with Ctrl+Alt+I.)
    """
    interior = sum(c in VOWELS for c in literal[1:])
    if len(literal) >= 5 and interior <= 1:
        return True
    if sum(c in VOWELS for c in literal) / len(literal) < 0.3:
        return any(len(e) >= 4 and tuple(e) in by_seq for e in _edits1(literal))
    return False


def mod_held():
    try:
        return (keyboard.is_pressed("ctrl") or keyboard.is_pressed("alt")
                or keyboard.is_pressed("windows"))
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  engine -- blocking hook: return False to swallow, True to pass through
# --------------------------------------------------------------------------- #

class ChordEngine:
    hint = "Type the word's letters without vowels, in order, then Space."

    def __init__(self, by_seq, report, on_build=None):
        self.by_seq = by_seq
        self.report = report
        self.on_build = on_build or (lambda k: None)
        self.type_output = True
        self.order = []
        self._down = set()
        self.dictionary_mode = False
        self.known_words = set()
        self.on_dict = lambda *a: None
        self.pending = None
        self.echo = False

    def on_event(self, e):
        if self.echo and self.type_output:
            return self._on_echo(e)
        return self._on_suppress(e)

    def _on_suppress(self, e):
        try:
            n = e.name
            is_letter = bool(n) and len(n) == 1 and n.isalpha()
            held = n.lower() if is_letter else n     # Shift-up may arrive before T-up as 't'

            if e.event_type == KEY_UP:
                if held in self._down:
                    self._down.discard(held)
                    return False
                return True

            # ---- key down ----
            if self.pending is not None:
                w, ch = self.pending
                if n == "space":
                    self.pending = None
                    self._down.add("space")
                    self.on_dict("add", w, ch)
                    return False
                if n == "esc":
                    self.pending = None
                    self._down.add("esc")
                    self.on_dict("cancel", w, ch)
                    return False
                self.pending = None
                self.on_dict("dismiss", w, ch)
                # fall through and handle this key normally

            if n == "space":
                if mod_held():
                    return True
                self._commit(" ")
                self._down.add("space")
                return False
            if is_letter:
                if mod_held():
                    return True                     # let Ctrl/Alt shortcuts pass
                if held in self._down:
                    return False                    # auto-repeat while held -> ignore
                self._down.add(held)
                self.order.append(n)                # keep duplicates and case (fresh presses)
                self.on_build(self._keys())
                return False
            if n == "backspace":
                if self.order:
                    self.order.pop()
                    self.on_build(self._keys())
                    return False
                return True
            if self.order:
                self._commit("")
            return True
        except Exception as ex:
            self.report([], f"[err] {ex}")
            return True

    def _commit(self, trailing):
        if not self.order:
            if trailing and self.type_output:
                keyboard.write(trailing, restore_state_after=False)
            return
        keys = self._keys()
        word = self.by_seq.get(tuple(keys))
        typed = "".join(self.order)                 # as typed, case kept
        literal = typed.lower()
        if (word is None and self.dictionary_mode and self.type_output
                and self._is_new_word(literal)):
            chord = derive_chord(literal, self.by_seq)
            if chord and self.by_seq.get(tuple(chord)) in (None, literal):
                keyboard.write(typed + trailing, restore_state_after=False)
                self.report(keys, None)
                self.on_build([])
                self.order = []
                self.pending = (literal, list(chord))
                self.on_dict("suggest", literal, list(chord))
                return
        if self.type_output:
            keyboard.write((apply_case(word, typed) if word else typed) + trailing,
                           restore_state_after=False)
        self.report(keys, word)
        self.on_build([])
        self.order = []

    def _keys(self):
        return [k.lower() for k in self.order]

    def _is_new_word(self, literal):
        return (len(literal) >= 3 and literal.isalpha()
                and any(c in VOWELS for c in literal)
                and literal not in self.known_words
                and not looks_like_chord(literal, self.by_seq))

    # ----- echo path: letters are visible in the document, replaced on Space -----
    def _on_echo(self, e):
        try:
            n = e.name
            is_letter = bool(n) and len(n) == 1 and n.isalpha()
            held = n.lower() if is_letter else n     # Shift-up may arrive before T-up as 't'

            if e.event_type == KEY_UP:
                if held in self._down:
                    self._down.discard(held)
                    return False
                return True

            # ---- key down ----
            if self.pending is not None:
                w, ch = self.pending
                if n == "space":
                    self.pending = None
                    self._down.add("space")
                    self.on_dict("add", w, ch)
                    return False
                if n == "esc":
                    self.pending = None
                    self._down.add("esc")
                    self.on_dict("cancel", w, ch)
                    return False
                self.pending = None
                self.on_dict("dismiss", w, ch)
                # fall through

            if n == "space":
                if mod_held():
                    return True
                return self._commit_echo()
            if is_letter:
                if mod_held():
                    return True
                self.order.append(n)            # counts duplicates and repeats
                self.on_build(self._keys())
                return True                     # let the key type (visible)
            if n == "backspace":
                if self.order:
                    self.order.pop()
                    self.on_build(self._keys())
                return True                     # also delete the visible character
            if self.order:                      # any other key ends the stroke
                self.report(self._keys(), None)
                self.on_build([])
                self.order = []
            return True
        except Exception as ex:
            self.report([], f"[err] {ex}")
            return True

    def _commit_echo(self):
        if not self.order:
            return True                          # nothing pending -> a normal space
        keys = self._keys()
        word = self.by_seq.get(tuple(keys))
        typed = "".join(self.order)
        literal = typed.lower()
        if word:
            for _ in range(len(self.order)):     # erase the echoed letters
                keyboard.send("backspace")
            keyboard.write(apply_case(word, typed) + " ", restore_state_after=False)
            self.report(keys, word)
            self.on_build([]); self.order = []
            self._down.add("space")
            return False                         # we supplied the space
        if self.dictionary_mode and self._is_new_word(literal):
            chord = derive_chord(literal, self.by_seq)
            if chord and self.by_seq.get(tuple(chord)) in (None, literal):
                keyboard.write(" ", restore_state_after=False)
                self.report(keys, None)
                self.on_build([]); self.order = []
                self.pending = (literal, list(chord))
                self.on_dict("suggest", literal, list(chord))
                self._down.add("space")
                return False
        # plain literal: leave the letters, let the space through
        self.report(keys, None)
        self.on_build([]); self.order = []
        return True


# --------------------------------------------------------------------------- #
#  application
# --------------------------------------------------------------------------- #

class DevowelatorApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.by_seq, self.words, self.word_keys = load_library()
        self.prefix_index = build_prefix_index(self.words, self.word_keys)

        self.enabled = False
        self.practice_active = False
        self.dictionary_mode = True
        self.echo_keys = True
        self.engine = self._make_engine()

        self._build_ui()
        self._sync_status()

        keyboard.hook(self._master_hook, suppress=True)
        try:
            keyboard.add_hotkey("ctrl+alt+i", lambda: self.q.put(("impulse",)),
                                suppress=True)
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(60, self._poll)

    def _make_engine(self):
        eng = ChordEngine(self.by_seq,
                          lambda keys, word: self.q.put(("chord", list(keys), word)),
                          lambda keys: self.q.put(("build", list(keys))))
        eng.type_output = not self.practice_active
        eng.dictionary_mode = self.dictionary_mode
        eng.known_words = set(self.word_keys)
        eng.on_dict = lambda action, word, chord: self.q.put(("dict", action, word, chord))
        eng.echo = self.echo_keys
        return eng

    def _master_hook(self, e):
        if not self.enabled:
            return True
        return self.engine.on_event(e)

    # ---- UI --------------------------------------------------------------- #
    def _build_ui(self):
        self.root.title("Typemax Devowelator")
        self.root.geometry("480x560")
        self.root.minsize(440, 520)

        top = ttk.Frame(self.root, padding=(10, 8)); top.pack(fill="x")
        ttk.Label(top, text="⌨  Typemax Devowelator", font=("Segoe UI", 16, "bold")).pack(side="left")
        self.count_lbl = ttk.Label(top, text="", foreground="#666"); self.count_lbl.pack(side="right")

        self.status = tk.Label(self.root, font=("Segoe UI", 10, "bold"), pady=6)
        self.status.pack(fill="x")

        nb = ttk.Notebook(self.root); nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tab_type = ttk.Frame(nb, padding=10)
        self.tab_practice = ttk.Frame(nb, padding=10)
        nb.add(self.tab_type, text="  Type  ")
        nb.add(self.tab_practice, text="  Practice  ")
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.nb = nb
        self._build_type_tab()
        self._build_practice_tab()

    def _build_type_tab(self):
        t = self.tab_type
        self.enable_btn = tk.Button(t, text="Enable  (start chording)",
                                    font=("Segoe UI", 11, "bold"), height=2,
                                    command=self._toggle_enabled)
        self.enable_btn.pack(fill="x")

        info = ttk.Label(t, foreground="#555", justify="left", wraplength=430,
                         text="Type a word without its vowels, in order, then Space.\n"
                              "Examples:  exmpl → example    ordr → order    thrgh → through")
        info.pack(anchor="w", pady=8)

        self.echo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(t, text="Show keys as you type (echo, then swap in the word on Space)",
                        variable=self.echo_var, command=self._toggle_echo).pack(anchor="w")
        self.dict_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(t, text="Dictionary mode — offer to add new words you type",
                        variable=self.dict_var, command=self._toggle_dict).pack(anchor="w")
        self.dict_lbl = tk.Label(t, text="", font=("Segoe UI", 10, "bold"), anchor="w",
                                 fg="#0a6a2a", wraplength=450, justify="left")
        self.dict_lbl.pack(fill="x", pady=(2, 4))

        ttk.Label(t, text="Paper tape").pack(anchor="w")
        self.tape = tk.Text(t, height=8, state="disabled", font=("Consolas", 10),
                            background="#101418", foreground="#7fd88f")
        self.tape.pack(fill="both", expand=True)
        self.cand_type = ttk.Label(t, text="", foreground="#0a7", wraplength=440)
        self.cand_type.pack(anchor="w", pady=(4, 0))

        row = ttk.Frame(t); row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="＋ Add chord", command=self.open_impulse).pack(side="left")
        ttk.Button(row, text="View / edit chords", command=self.open_library).pack(side="left", padx=6)
        ttk.Button(row, text="Guide", command=self._open_guide).pack(side="left")
        self.topmost = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="On top", variable=self.topmost,
                        command=lambda: self.root.attributes("-topmost", self.topmost.get())
                        ).pack(side="right")
        self.root.attributes("-topmost", False)

    def _build_practice_tab(self):
        p = self.tab_practice
        row = ttk.Frame(p); row.pack(fill="x")
        ttk.Label(row, text="Word set:").pack(side="left")
        self.set_var = tk.StringVar(value="All")
        ttk.OptionMenu(row, self.set_var, "All", "All", "My words",
                       "Top 100", "Top 500", "Top 2000").pack(side="left", padx=6)
        self.practice_btn = tk.Button(row, text="Start", width=10,
                                      font=("Segoe UI", 10, "bold"), command=self._toggle_practice)
        self.practice_btn.pack(side="right")

        self.target_lbl = tk.Label(p, text="press Start", font=("Segoe UI", 30, "bold"), pady=10)
        self.target_lbl.pack()
        self.hint_lbl = tk.Label(p, text="", font=("Consolas", 15), foreground="#0a7")
        self.hint_lbl.pack()
        self.show_hint = tk.BooleanVar(value=True)
        ttk.Checkbutton(p, text="Show the chord hint", variable=self.show_hint,
                        command=self._refresh_target).pack(pady=2)

        ttk.Label(p, text="You are typing:", foreground="#555").pack()
        self.cand_prac = tk.Label(p, text="", font=("Segoe UI", 11), fg="#0a7",
                                  wraplength=440, height=3, justify="center")
        self.cand_prac.pack()

        self.feedback_lbl = tk.Label(p, text="", font=("Segoe UI", 12)); self.feedback_lbl.pack(pady=2)
        self.stat_lbl = ttk.Label(p, text="", font=("Segoe UI", 10)); self.stat_lbl.pack(pady=4)

    # ---- status ----------------------------------------------------------- #
    def _sync_status(self):
        self.count_lbl.config(text=f"{len(self.by_seq)} chords")
        if self.practice_active:
            self.status.config(text="● PRACTICE  (typing goes nowhere)", bg="#243b55", fg="#cfe6ff")
        elif self.enabled:
            self.status.config(text="● ON  —  chording is live", bg="#1e3a24", fg="#9be7a6")
        else:
            self.status.config(text="○ OFF  —  normal typing", bg="#3a1e1e", fg="#e79b9b")
        self.enable_btn.config(text="Disable  (stop chording)" if self.enabled and not self.practice_active
                               else "Enable  (start chording)")

    def _toggle_enabled(self):
        if self.practice_active:
            return
        self.enabled = not self.enabled
        self.engine.type_output = True
        self._sync_status()

    def _on_tab_changed(self, _evt):
        if self.nb.index(self.nb.select()) == 0 and self.practice_active:
            self._toggle_practice()

    # ---- paper tape + candidates ----------------------------------------- #
    def _tape(self, text):
        self.tape.config(state="normal")
        self.tape.insert("end", text + "\n")
        self.tape.see("end")
        if int(self.tape.index("end-1c").split(".")[0]) > 200:
            self.tape.delete("1.0", "50.0")
        self.tape.config(state="disabled")

    def _show_candidates(self, keys):
        if not keys:
            self.cand_type.config(text=""); self.cand_prac.config(text=""); return
        cands = find_candidates(keys, self.prefix_index)
        typed = "".join(keys)
        if cands:
            txt = "   ".join(f"{w} ({''.join(k)})" for w, k in cands)
        else:
            txt = "(no word starts with those keys)"
        self.cand_type.config(text=f"{typed} →  {txt}")
        self.cand_prac.config(text=f"[{typed}]\n{txt}")

    # ---- impulse ---------------------------------------------------------- #
    def open_impulse(self):
        was = self.enabled
        self.enabled = False
        self._sync_status()

        dlg = tk.Toplevel(self.root); dlg.title("Add chord")
        dlg.geometry("330x220"); dlg.transient(self.root); dlg.grab_set()
        dlg.attributes("-topmost", True)

        ttk.Label(dlg, text="Word:").pack(anchor="w", padx=12, pady=(12, 0))
        word_e = ttk.Entry(dlg); word_e.pack(fill="x", padx=12); word_e.focus_set()
        ttk.Label(dlg, text="Keys (blank = auto):").pack(anchor="w", padx=12, pady=(8, 0))
        keys_e = ttk.Entry(dlg); keys_e.pack(fill="x", padx=12)
        sugg = ttk.Label(dlg, text="", foreground="#0a7"); sugg.pack(anchor="w", padx=12)

        def update_sugg(*_):
            w = word_e.get().strip().lower()
            c = derive_chord(w, self.by_seq) if w.isalpha() and w else None
            sugg.config(text=("suggested: " + "".join(c)) if c else "")
        word_e.bind("<KeyRelease>", update_sugg)

        def finish(save):
            if save:
                w = word_e.get().strip().lower()
                if not w or not w.isalpha():
                    messagebox.showerror("Add chord", "Enter a single word (letters only).", parent=dlg)
                    return
                raw = keys_e.get().strip().lower()
                keys = tuple(k for k in raw.replace(",", " ").split()) if raw \
                    else derive_chord(w, self.by_seq)
                if not keys or len(keys) < 2 or not all(len(k) == 1 and k.isalpha() for k in keys):
                    messagebox.showerror("Add chord", "Need at least 2 single-letter keys.", parent=dlg)
                    return
                clash = keys_clash(keys, w, self.by_seq)
                if clash:
                    messagebox.showerror("Add chord", f"Those keys already type '{clash}'.", parent=dlg)
                    return
                save_chord(w, keys)
                self._reload_library()
                self._tape(f"+ added  {''.join(keys)} -> {w}")
            dlg.destroy()
            self.enabled = was
            self.engine.type_output = not self.practice_active
            self._sync_status()

        br = ttk.Frame(dlg); br.pack(side="bottom", fill="x", pady=10, padx=12)
        ttk.Button(br, text="Add", command=lambda: finish(True)).pack(side="right")
        ttk.Button(br, text="Cancel", command=lambda: finish(False)).pack(side="right", padx=6)
        dlg.bind("<Return>", lambda _e: finish(True))
        dlg.protocol("WM_DELETE_WINDOW", lambda: finish(False))

    def _reload_library(self):
        self.by_seq, self.words, self.word_keys = load_library()
        self.prefix_index = build_prefix_index(self.words, self.word_keys)
        self.engine.by_seq = self.by_seq
        self.engine.known_words = set(self.word_keys)
        self._sync_status()

    def _toggle_echo(self):
        self.echo_keys = self.echo_var.get()
        self.engine.echo = self.echo_keys

    def _toggle_dict(self):
        self.dictionary_mode = self.dict_var.get()
        self.engine.dictionary_mode = self.dictionary_mode
        if self.dictionary_mode and not self.practice_active and not self.enabled:
            self.enabled = True
            self.engine.type_output = True
        if not self.dictionary_mode:
            self.engine.pending = None
            self.dict_lbl.config(text="")
        self._sync_status()

    def _dict_event(self, action, word, chord):
        keys = "".join(chord) if chord else ""
        if action == "suggest":
            self.dict_lbl.config(
                text=f"➕ new word  “{word}”  →  {keys}"
                     f"      [ Space = add · Esc = skip ]", fg="#0a6a2a")
        elif action == "add":
            save_chord(word, chord)
            self._reload_library()
            self._tape(f"+ learned  {keys} -> {word}")
            self.dict_lbl.config(text=f"✓ added  “{word}”  →  {keys}", fg="#0a0")
            self._clear_dict_later()
        elif action == "cancel":
            self.dict_lbl.config(text=f"skipped  “{word}”", fg="#777")
            self._clear_dict_later()
        else:  # dismiss
            self.dict_lbl.config(text="")

    def _clear_dict_later(self):
        self._dict_gen = getattr(self, "_dict_gen", 0) + 1
        g = self._dict_gen
        self.root.after(2500, lambda: (getattr(self, "_dict_gen", 0) == g)
                        and self.dict_lbl.config(text=""))

    # ---- view / edit the whole library ----------------------------------- #
    def _validate_rebind(self, word, keys):
        keys = tuple(keys)
        if len(keys) < 2 or not all(len(k) == 1 and k.isalpha() for k in keys):
            return "invalid", "enter at least 2 single-letter keys"
        clash = keys_clash(keys, word, self.by_seq)
        if clash:
            return "clash", f"those keys already type '{clash}'"
        if keys == self.word_keys.get(word, ()):
            return "unchanged", "unchanged"
        return "ok", "available"

    def _apply_rebind(self, word, keys):
        status, msg = self._validate_rebind(word, keys)
        if status in ("invalid", "clash"):
            return False, msg
        if status == "unchanged":
            return True, "unchanged"
        rebind_chord(word, self.word_keys[word], tuple(keys))
        self._reload_library()
        return True, f"saved: {word} = {''.join(keys)}"

    def open_library(self):
        was = self.enabled
        self.enabled = False
        self._sync_status()

        win = tk.Toplevel(self.root)
        win.title("Chord library"); win.geometry("560x600")
        win.transient(self.root); win.attributes("-topmost", self.topmost.get())

        top = ttk.Frame(win, padding=8); top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        ttk.Entry(top, textvariable=search_var).pack(side="left", fill="x", expand=True, padx=6)
        count = ttk.Label(top, text=""); count.pack(side="right")

        mid = ttk.Frame(win); mid.pack(fill="both", expand=True, padx=8)
        tree = ttk.Treeview(mid, columns=("word", "keys"), show="headings", height=15)
        tree.heading("word", text="Word"); tree.heading("keys", text="Chord")
        tree.column("word", width=230); tree.column("keys", width=280)
        sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")

        ed = ttk.LabelFrame(win, text="Edit binding", padding=8)
        ed.pack(fill="x", padx=8, pady=8)
        selv = tk.StringVar(value="(select a word above)")
        ttk.Label(ed, textvariable=selv, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        krow = ttk.Frame(ed); krow.pack(fill="x", pady=4)
        ttk.Label(krow, text="Keys (in order):").pack(side="left")
        keys_var = tk.StringVar()
        keys_e = ttk.Entry(krow, textvariable=keys_var)
        keys_e.pack(side="left", fill="x", expand=True, padx=6)
        save_btn = ttk.Button(krow, text="Save"); save_btn.pack(side="left")
        warn = tk.Label(ed, text="select a word, edit its keys, then Save", anchor="w", fg="#777")
        warn.pack(fill="x", pady=(4, 0))

        state = {"word": None}
        COLORS = {"invalid": "#b30000", "clash": "#c05500",
                  "unchanged": "#777777", "ok": "#0a7a0a", "saved": "#0a7a0a"}

        def parse():
            return tuple(k for k in keys_var.get().strip().lower().replace(",", " ").split())

        def populate(*_):
            flt = search_var.get().strip().lower()
            tree.delete(*tree.get_children())
            n = 0
            truncated = False
            for w in self.words:
                if flt and flt not in w:
                    continue
                tree.insert("", "end", iid=w, values=(w, "".join(self.word_keys[w])))
                n += 1
                if n >= 800:
                    truncated = True
                    break
            count.config(text=(f"first {n} of {len(self.words)} — type to search"
                               if truncated else f"{n} shown"))

        def on_sel(_e=None):
            s = tree.selection()
            if not s:
                return
            w = s[0]; state["word"] = w
            selv.set(w); keys_var.set(" ".join(self.word_keys[w]))
            live()

        def live(*_):
            w = state["word"]
            if not w:
                return
            status, msg = self._validate_rebind(w, parse())
            warn.config(text=("✓ available" if status == "ok" else msg),
                        fg=COLORS.get(status, "#777777"))

        def save():
            w = state["word"]
            if not w:
                return
            ok, msg = self._apply_rebind(w, parse())
            warn.config(text=("✓ " + msg) if ok else ("⚠ " + msg),
                        fg=COLORS["saved"] if ok else COLORS["clash"])
            if ok and w in self.words:
                self._tape(f"rebound  {w} -> {''.join(parse())}")
                populate()
                tree.selection_set(w); tree.see(w)
                keys_var.set(" ".join(self.word_keys[w]))

        save_btn.config(command=save)
        keys_e.bind("<KeyRelease>", live)
        keys_e.bind("<Return>", lambda _e: save())
        tree.bind("<<TreeviewSelect>>", on_sel)
        search_var.trace_add("write", populate)
        populate()

        def on_close():
            win.destroy()
            self.enabled = was
            self.engine.type_output = not self.practice_active
            self._sync_status()
        win.protocol("WM_DELETE_WINDOW", on_close)
        return win

    # ---- practice --------------------------------------------------------- #
    def _toggle_practice(self):
        if self.practice_active:
            self.practice_active = False
            self.enabled = False
            self.engine.type_output = True
            self.practice_btn.config(text="Start")
            self.target_lbl.config(text="press Start")
            self.hint_lbl.config(text=""); self.feedback_lbl.config(text="")
            self.cand_prac.config(text="")
        else:
            pool = self._practice_pool()
            if not pool:
                messagebox.showinfo("Practice", "No words in that set."); return
            self.p_pool = pool
            self.p_correct = self.p_wrong = self.p_streak = 0
            self.p_start = None
            self.practice_active = True
            self.enabled = True
            self.engine.type_output = False
            self.engine.pending = None
            self.practice_btn.config(text="Stop")
            self._next_target()
        self._sync_status(); self._update_stats()

    def _practice_pool(self):
        choice = self.set_var.get()
        if choice == "My words":                       # words you added / re-bound
            mine = list(dict.fromkeys(_read_json(USER_FILE).values()))
            return [w for w in mine if w in self.word_keys]
        n = {"Top 100": 100, "Top 500": 500, "Top 2000": 2000,
             "All": len(self.words)}.get(choice, len(self.words))
        return self.words[:n]

    def _next_target(self):
        self.target = random.choice(self.p_pool)
        self._refresh_target()

    def _refresh_target(self):
        if not self.practice_active:
            return
        self.target_lbl.config(text=self.target)
        keys = self.word_keys.get(self.target, ())
        self.hint_lbl.config(text=("type:  " + "".join(keys)) if self.show_hint.get() else "• • •")

    def _practice_check(self, word):
        if word == self.target:
            if self.p_start is None:
                self.p_start = time.time()
            self.p_correct += 1; self.p_streak += 1
            self.feedback_lbl.config(text="✓ correct!", fg="#0a0")
            self._next_target()
        else:
            self.p_wrong += 1; self.p_streak = 0
            keys = self.word_keys.get(self.target, ())
            got = word if word else "(no match)"
            self.feedback_lbl.config(text=f"✗ got {got}   —   {self.target} = {''.join(keys)}", fg="#c00")
        self._update_stats()

    def _update_stats(self):
        done = getattr(self, "p_correct", 0) + getattr(self, "p_wrong", 0)
        acc = (self.p_correct / done * 100) if done else 0
        wpm = 0
        if getattr(self, "p_start", None) and self.p_correct > 1:
            mins = (time.time() - self.p_start) / 60
            # the clock starts when the first word lands, so that word isn't timed
            wpm = (self.p_correct - 1) / mins if mins > 0 else 0
        self.stat_lbl.config(text=f"correct {getattr(self,'p_correct',0)}    "
                             f"wrong {getattr(self,'p_wrong',0)}    accuracy {acc:.0f}%    "
                             f"streak {getattr(self,'p_streak',0)}    {wpm:.0f} wpm")

    # ---- misc ------------------------------------------------------------- #
    def _open_guide(self):
        try:
            os.startfile(str(GUIDE_FILE))
        except Exception:
            messagebox.showinfo("Guide", f"Open the guide here:\n{GUIDE_FILE}")

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "chord":
                    _, keys, word = item
                    self._tape(f"{''.join(keys):16} -> {word if word else '(no match)'}")
                    if self.practice_active:
                        self._practice_check(word)
                elif item[0] == "build":
                    self._show_candidates(item[1])
                elif item[0] == "dict":
                    self._dict_event(item[1], item[2], item[3])
                elif item[0] == "impulse":
                    self.open_impulse()
        except queue.Empty:
            pass
        self.root.after(60, self._poll)

    def _on_close(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    DevowelatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
