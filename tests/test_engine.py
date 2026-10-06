"""Headless tests for the vowel-drop, order-sensitive chord model."""
import importlib.util
from types import SimpleNamespace
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "typemax_devowelator.pyw"
spec = importlib.util.spec_from_file_location("typemax_devowelator", APP)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

WRITES = []
mod.keyboard.write = lambda text, **kw: WRITES.append(text)
SENDS = []
mod.keyboard.send = lambda key, **kw: SENDS.append(key)
PRESSED = set()
mod.keyboard.is_pressed = lambda k: k in PRESSED

DOWN, UP = mod.KEY_DOWN, mod.KEY_UP
def ev(name, down=True):
    return SimpleNamespace(name=name, event_type=DOWN if down else UP)
def tap(engine, name):
    engine.on_event(ev(name, True)); engine.on_event(ev(name, False))
def space(engine):
    engine.on_event(ev("space", True)); engine.on_event(ev("space", False))

P = F = 0
def check(cond, msg):
    global P, F
    if cond: P += 1
    else:
        F += 1; print("  FAIL:", msg)


def test_rule():
    check(mod.derive_chord("example", {}) == ("e", "x", "m", "p", "l"), "example -> exmpl")
    check(mod.derive_chord("order", {}) == ("o", "r", "d", "r"), "order -> ordr (dup r kept)")
    check(mod.derive_chord("enough", {}) == ("e", "n", "g", "h"), "enough -> engh")
    check(mod.derive_chord("instead", {}) == ("i", "n", "s", "t", "d"), "instead -> instd")
    check(mod.derive_chord("chording", {}) == ("c", "h", "r", "d", "n", "g"), "chording -> chrdng")
    check(mod.derive_chord("you", {}) == ("y", "o"), "you -> yo")
    check(mod.derive_chord("the", {}) == ("t", "h"), "the -> th")
    check(mod.derive_chord("one", {}) == ("o", "n", "e"), "one avoids 'on'")
    check(mod.derive_chord("use", {}) == ("u", "s", "e"), "use avoids 'us'")
    check(mod.derive_chord("too", {}) == ("t", "o", "o"), "too avoids 'to' -> too")
    check(mod.derive_chord("thee", {("t", "h"): "the"}) == ("t", "h", "e"),
          "collision reveals a vowel")


def test_library():
    by, words, wk = mod.load_library()
    check(len(by) > 1500, f"library size {len(by)}")
    check(wk.get("the") == ("t", "h"), "the -> t,h")
    check(by.get(("t", "h")) == "the", "t,h -> the")
    idx = mod.build_prefix_index(words, wk)
    cands = mod.find_candidates(["t", "h"], idx)
    check(all(k[:2] == ("t", "h") for _, k in cands), "candidates all START WITH t,h")
    check(mod.find_candidates([], idx) == [], "no keys -> no candidates")
    brute = [w for w in words if wk[w][:2] == ("t", "h")][:8]
    check([w for w, _ in cands] == brute, "prefix index matches brute-force scan")
    bad = [w for w, k in wk.items() if mod.spells_two_letter_word(k)]
    check(bad == [], f"no chord spells a 2-letter word ({bad[:5]})")


def test_engine():
    by = {("t", "h"): "the", ("o", "r", "d", "r"): "order"}
    reports, builds = [], []
    eng = mod.ChordEngine(by, lambda k, w: reports.append((list(k), w)),
                          lambda k: builds.append(list(k)))

    WRITES.clear()
    r = eng.on_event(ev("t", True)); check(r is False, "letter down suppressed")
    eng.on_event(ev("t", False)); tap(eng, "h"); space(eng)
    check(WRITES == ["the "], f"th -> 'the ' ({WRITES})")
    check(reports == [(["t", "h"], "the")], f"report ({reports})")
    check(builds[0] == ["t"], "build events fire")

    WRITES.clear()
    for k in ("o", "r", "d", "r"):
        tap(eng, k)
    space(eng)
    check(WRITES == ["order "], f"ordr (dup r) -> 'order ' ({WRITES})")

    # holding a key (auto-repeat) counts once
    WRITES.clear()
    eng.on_event(ev("r", True)); eng.on_event(ev("r", True)); eng.on_event(ev("r", True))
    eng.on_event(ev("r", False)); space(eng)
    check(WRITES == ["r "], f"auto-repeat r -> single 'r ' ({WRITES})")

    # order matters
    WRITES.clear()
    tap(eng, "h"); tap(eng, "t"); space(eng)
    check(WRITES == ["ht "], f"h,t -> literal 'ht ' ({WRITES})")

    # backspace edits the pending stroke
    WRITES.clear()
    tap(eng, "t"); tap(eng, "x")
    eng.on_event(ev("backspace", True))
    tap(eng, "h"); space(eng)
    check(WRITES == ["the "], f"backspace fix -> 'the ' ({WRITES})")

    # modifier bypass
    PRESSED.add("ctrl")
    check(eng.on_event(ev("c", True)) is True, "Ctrl+letter passes through")
    check(eng.order == [], "shortcut not buffered")
    eng.on_event(ev("c", False)); PRESSED.discard("ctrl")

    # practice mode: reports but does not type
    WRITES.clear(); reports.clear(); eng.type_output = False
    tap(eng, "t"); tap(eng, "h"); space(eng)
    check(WRITES == [], "practice mode does not type")
    check(reports == [(["t", "h"], "the")], "practice mode still reports")


def test_rebind():
    import tempfile, json as _json, os
    by = {("t", "h"): "the", ("a", "n", "d"): "and"}
    check(mod.keys_clash(("t", "h"), "other", by) == "the", "clash detected")
    check(mod.keys_clash(("t", "h"), "the", by) is None, "no clash: same word")
    check(mod.keys_clash(("x", "y", "z"), "w", by) is None, "no clash: free keys")

    tmp = Path(tempfile.gettempdir()) / "user_rebind.json"
    if tmp.exists(): os.remove(tmp)
    old = mod.USER_FILE
    try:
        mod.USER_FILE = tmp
        mod.save_chord("cat", ("c", "t"))
        mod.rebind_chord("the", ("t", "h"), ("t", "h", "e"))
        d = _json.loads(tmp.read_text(encoding="utf-8"))
        check(d.get("t,h,e") == "the", "rebind wrote new combo to the user file")
        check(d.get("c,t") == "cat", "user file keeps other additions")
        mod.rebind_chord("the", ("t", "h", "e"), ("t", "h", "x"))
        d = _json.loads(tmp.read_text(encoding="utf-8"))
        check("t,h,e" not in d and d.get("t,h,x") == "the", "re-rebind replaces the prior user entry")
    finally:
        mod.USER_FILE = old
        try: os.remove(tmp)
        except OSError: pass


def test_merge():
    import tempfile, json as _json, os
    g = Path(tempfile.gettempdir()) / "gen_m.json"
    u = Path(tempfile.gettempdir()) / "user_m.json"
    g.write_text(_json.dumps({"t,h": "the", "c,t": "cat"}), encoding="utf-8")
    u.write_text(_json.dumps({"c,t,a": "cat", "z,z,q": "zzq"}), encoding="utf-8")
    og, ou = mod.GEN_FILE, mod.USER_FILE
    try:
        mod.GEN_FILE, mod.USER_FILE = g, u
        by, ordered, wk = mod.load_library()
        check(wk["cat"] == ("c", "t", "a"), "merge: user override wins for 'cat'")
        check(by.get(("c", "t")) is None, "merge: cat's old generated chord is freed")
        check(by.get(("c", "t", "a")) == "cat", "merge: cat's new chord is active")
        check(by.get(("t", "h")) == "the", "merge: untouched generated word intact")
        check(wk.get("zzq") == ("z", "z", "q") and "zzq" in ordered, "merge: new user word added")
    finally:
        mod.GEN_FILE, mod.USER_FILE = og, ou
        for p in (g, u):
            try: os.remove(p)
            except OSError: pass


def test_dictionary():
    reports, dicts = [], []
    eng = mod.ChordEngine({}, lambda k, w: reports.append((list(k), w)), lambda k: None)
    eng.on_dict = lambda action, w, ch: dicts.append((action, w, list(ch) if ch else ch))
    eng.dictionary_mode = True
    eng.known_words = set()
    eng.type_output = True

    WRITES.clear()
    for k in ("c", "a", "t"):
        tap(eng, k)
    space(eng)
    check(WRITES == ["cat "], f"dict: new word typed literally ({WRITES})")
    check(dicts == [("suggest", "cat", ["c", "t"])], f"dict: suggest event ({dicts})")
    check(eng.pending == ("cat", ["c", "t"]), "dict: pending armed")

    r = eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(r is False, "dict: accept space consumed")
    check(dicts[-1] == ("add", "cat", ["c", "t"]), "dict: add event on space")
    check(eng.pending is None, "dict: pending cleared after add")

    dicts.clear()
    for k in ("d", "o", "g"):
        tap(eng, k)
    space(eng)
    check(dicts[-1][0] == "suggest", "dict: suggest for dog")
    eng.on_event(ev("esc", True)); eng.on_event(ev("esc", False))
    check(dicts[-1] == ("cancel", "dog", ["d", "g"]), "dict: esc cancels")

    dicts.clear()
    for k in ("f", "o", "x"):
        tap(eng, k)
    space(eng)
    eng.on_event(ev("h", True)); eng.on_event(ev("h", False))
    check(("dismiss", "fox", ["f", "x"]) in dicts, "dict: other key dismisses")
    check(eng.order == ["h"], "dict: the dismissing key is then buffered")

    dicts.clear(); WRITES.clear(); eng.order = []; eng._down = set()
    eng.known_words = {"cat"}
    for k in ("c", "a", "t"):
        tap(eng, k)
    space(eng)
    check(dicts == [], "dict: known word does not prompt")

    dicts.clear()
    for k in ("b", "c", "d"):
        tap(eng, k)
    space(eng)
    check(dicts == [], "dict: vowel-less string does not prompt")

    dicts.clear(); eng.dictionary_mode = False; eng.known_words = set()
    for k in ("c", "a", "t"):
        tap(eng, k)
    space(eng)
    check(dicts == [], "dict: off -> no prompt")


def test_echo():
    by = {("t", "h"): "the"}
    reports = []
    eng = mod.ChordEngine(by, lambda k, w: reports.append((list(k), w)), lambda k: None)
    eng.echo = True
    eng.type_output = True

    # letters pass through (visible), Space replaces a matched chord with the word
    WRITES.clear(); SENDS.clear()
    check(eng.on_event(ev("t", True)) is True, "echo: letter passes through (visible)")
    eng.on_event(ev("t", False))
    check(eng.on_event(ev("h", True)) is True, "echo: 2nd letter passes through")
    eng.on_event(ev("h", False))
    r = eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(r is False, "echo: matching Space is consumed")
    check(SENDS == ["backspace", "backspace"], f"echo: backspaced the echoed letters ({SENDS})")
    check(WRITES == ["the "], f"echo: wrote the word ({WRITES})")

    # no match -> letters stay, Space passes through untouched
    WRITES.clear(); SENDS.clear(); reports.clear()
    for k in ("x", "y", "z"):
        tap(eng, k)
    r = eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(r is True, "echo: non-matching Space passes through (letters stay)")
    check(SENDS == [] and WRITES == [], "echo: literal left as typed")
    check(reports[-1] == (["x", "y", "z"], None), "echo: literal reported")

    # backspace edits the visible letters and the buffer together
    WRITES.clear(); SENDS.clear()
    tap(eng, "t"); tap(eng, "x")
    check(eng.on_event(ev("backspace", True)) is True, "echo: backspace passes through")
    eng.on_event(ev("backspace", False))
    tap(eng, "h")
    eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(WRITES == ["the "] and SENDS == ["backspace", "backspace"],
          f"echo: backspace-corrected chord still resolves ({WRITES}, {SENDS})")

    # echo defaults off -> suppress path (letters swallowed as before)
    eng2 = mod.ChordEngine(by, lambda k, w: None, lambda k: None)
    check(eng2.on_event(ev("t", True)) is False, "echo off: letters suppressed as before")


def test_echo_dict():
    by = {("t", "h"): "the"}
    dicts = []
    eng = mod.ChordEngine(by, lambda k, w: None, lambda k: None)
    eng.on_dict = lambda a, w, c: dicts.append((a, w, list(c) if c else c))
    eng.echo = True; eng.type_output = True
    eng.dictionary_mode = True; eng.known_words = set()

    WRITES.clear(); SENDS.clear()
    for k in ("c", "a", "t"):            # a new word, echoed visibly
        tap(eng, k)
    r = eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(r is False, "echo+dict: Space consumed to arm the prompt")
    check(SENDS == [], "echo+dict: echoed letters kept (not backspaced)")
    check(WRITES == [" "], "echo+dict: a space added after the new word")
    check(dicts[-1][:2] == ("suggest", "cat"), "echo+dict: suggest fired")
    check(eng.pending == ("cat", ["c", "t"]), "echo+dict: pending armed")
    eng.on_event(ev("space", True)); eng.on_event(ev("space", False))
    check(dicts[-1][:2] == ("add", "cat"), "echo+dict: second Space accepts")


def test_case():
    check(mod.apply_case("the", "th") == "the", "case: lower stays lower")
    check(mod.apply_case("the", "Th") == "The", "case: leading capital carried")
    check(mod.apply_case("the", "TH") == "THE", "case: all caps carried")
    check(mod.apply_case("through", "T") == "Through", "case: single capital")

    by = {("t", "h"): "the"}
    reports = []
    eng = mod.ChordEngine(by, lambda k, w: reports.append((list(k), w)), lambda k: None)

    # Shift+T arrives as "T"; Shift released before the key -> key-up is "t"
    WRITES.clear()
    eng.on_event(ev("T", True)); eng.on_event(ev("t", False))
    tap(eng, "h"); space(eng)
    check(WRITES == ["The "], f"case: Th -> 'The ' ({WRITES})")
    check(reports[-1] == (["t", "h"], "the"), f"case: reported lowercase ({reports[-1]})")
    check(eng._down == set(), f"case: no key stuck as held ({eng._down})")

    WRITES.clear()                      # a second capital T must not be eaten as auto-repeat
    eng.on_event(ev("T", True)); eng.on_event(ev("T", False))
    tap(eng, "h"); space(eng)
    check(WRITES == ["The "], f"case: second capital chord still fires ({WRITES})")

    WRITES.clear()                      # caps lock / all caps
    tap(eng, "T"); tap(eng, "H"); space(eng)
    check(WRITES == ["THE "], f"case: TH -> 'THE ' ({WRITES})")

    WRITES.clear()                      # unmatched literal keeps its case
    tap(eng, "X"); tap(eng, "y"); space(eng)
    check(WRITES == ["Xy "], f"case: literal keeps case ({WRITES})")

    SENDS.clear(); WRITES.clear()       # echo path
    eng.echo = True
    tap(eng, "T"); tap(eng, "h"); space(eng)
    check(WRITES == ["The "] and SENDS == ["backspace"] * 2, f"case: echo Th -> The ({WRITES})")

    dicts = []                          # dictionary learns the lowercase word
    eng2 = mod.ChordEngine({}, lambda k, w: None, lambda k: None)
    eng2.on_dict = lambda a, w, c: dicts.append((a, w))
    eng2.dictionary_mode = True; eng2.type_output = True
    WRITES.clear()
    for k in ("C", "a", "t"):
        tap(eng2, k)
    space(eng2)
    check(WRITES == ["Cat "], f"case: dict types as typed ({WRITES})")
    check(dicts == [("suggest", "cat")], f"case: dict suggests lowercase ({dicts})")


def test_typo_filter():
    by = {tuple("nnklvn"): "nanokelvin", tuple("thrgh"): "through"}
    lc = mod.looks_like_chord
    check(lc("nanklvn", by), "typo: chord-shaped string flagged")
    check(lc("thragh", by), "typo: one edit from a chord + vowel-poor flagged")
    for w in ("cat", "freelance", "zebuq", "banana", "operation"):
        check(not lc(w, by), f"typo: real-looking word '{w}' not flagged")

    dicts = []
    eng = mod.ChordEngine(by, lambda k, w: None, lambda k: None)
    eng.on_dict = lambda a, w, c: dicts.append((a, w))
    eng.dictionary_mode = True; eng.type_output = True
    WRITES.clear()
    for k in "nanklvn":
        tap(eng, k)
    space(eng)
    check(dicts == [] and eng.pending is None, f"typo: mistyped chord not offered ({dicts})")
    check(WRITES == ["nanklvn "], f"typo: still typed literally ({WRITES})")


def main():
    test_rule(); test_library(); test_engine(); test_rebind(); test_merge()
    test_dictionary(); test_echo(); test_echo_dict(); test_case(); test_typo_filter()
    print(f"\n{'ALL PASS' if F == 0 else 'FAILURES'}:  {P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    raise SystemExit(main())
