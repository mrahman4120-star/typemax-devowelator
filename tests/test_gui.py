"""GUI smoke test for the single-mode, order-sensitive app."""
import importlib.util, shutil, tempfile, os
from types import SimpleNamespace
from pathlib import Path
import tkinter as tk

APP = Path(__file__).resolve().parent.parent / "typemax_devowelator.pyw"
spec = importlib.util.spec_from_file_location("typemax_devowelator", APP)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.keyboard.hook = lambda *a, **k: None
mod.keyboard.add_hotkey = lambda *a, **k: None
mod.keyboard.unhook_all = lambda *a, **k: None
mod.keyboard.clear_all_hotkeys = lambda *a, **k: None
WRITES = []
mod.keyboard.write = lambda t, **k: WRITES.append(t)
mod.keyboard.is_pressed = lambda k: False
SENDS = []
mod.keyboard.send = lambda k, **kw: SENDS.append(k)
DOWN, UP = mod.KEY_DOWN, mod.KEY_UP
def ev(n, d=True): return SimpleNamespace(name=n, event_type=DOWN if d else UP)

P = F = 0
def check(c, m):
    global P, F
    if c: P += 1
    else:
        F += 1; print("  FAIL:", m)

def feed(app, keys):
    for k in keys:
        app._master_hook(ev(k, True)); app._master_hook(ev(k, False))
    app._master_hook(ev("space", True)); app._master_hook(ev("space", False))
    app._poll()

def main():
    global F
    root = tk.Tk(); root.withdraw()
    app = mod.DevowelatorApp(root); root.update()
    check(app.enabled is False, "starts disabled")
    check(app.echo_var.get() is True and app.engine.echo is True, "echo ON by default")
    check(app.dict_var.get() is True and app.engine.dictionary_mode is True, "dictionary mode ON by default")
    check(app.topmost.get() is False, "on-top OFF by default")
    check(len(app.words) > 1500, "library loaded")
    check("chords" in app.count_lbl.cget("text"), "count label set")

    # practice
    app.set_var.set("Top 50"); app._toggle_practice(); root.update()
    check(app.practice_active and app.enabled, "practice starts + enables")
    check(app.engine.type_output is False, "practice suppresses typing")
    tgt = app.target
    feed(app, app.word_keys[tgt]); root.update()
    check(app.p_correct == 1, f"correct chord scored ({tgt})")
    check(WRITES == [], "no real keystrokes during practice")
    pw = app.p_wrong
    feed(app, ("z", "q", "z")); root.update()
    check(app.p_wrong == pw + 1, "wrong chord counted")

    # candidate prefix suggestions
    app._master_hook(ev("t", True)); app._poll(); root.update()
    ct = app.cand_prac.cget("text")
    check("t" in ct and len(ct) > 3, f"prefix suggestions show ({ct[:30]})")
    app._master_hook(ev("t", False))
    app._master_hook(ev("space", True)); app._master_hook(ev("space", False)); app._poll()
    import time as _time
    app.p_correct, app.p_wrong = 6, 0
    app.p_start = _time.time() - 60          # first word landed a minute ago
    app._update_stats()
    check(app.stat_lbl.cget("text").endswith(" 5 wpm"),
          f"wpm excludes the untimed first word ({app.stat_lbl.cget('text')})")
    app.p_correct = 1; app._update_stats()
    check(app.stat_lbl.cget("text").endswith(" 0 wpm"), "wpm is 0 after a single word")
    app._toggle_practice(); root.update()
    check(not app.practice_active and not app.enabled, "practice stops")

    # impulse (dup letters) + rebind + collision, writing to an ISOLATED user file
    import json as _json
    real_user = mod.USER_FILE
    tmp = Path(tempfile.gettempdir()) / "user_gui.json"
    if tmp.exists(): os.remove(tmp)
    gen_before = mod.GEN_FILE.read_text(encoding="utf-8")
    try:
        mod.USER_FILE = tmp
        app._reload_library()
        before = len(app.words)
        mod.save_chord("zzq", ("z", "z", "q"))
        app._reload_library(); root.update()
        check("zzq" in app.words, "impulse adds a word")
        check(app.by_seq.get(("z", "z", "q")) == "zzq", "duplicate-letter chord stored in order")
        check(len(app.words) == before + 1, "library grew by one")

        word = "the"
        other = next(w for w in app.words if w != word)
        st, _ = app._validate_rebind(word, app.word_keys[other])
        check(st == "clash", f"collision flagged with '{other}'")
        ok, _ = app._apply_rebind(word, app.word_keys[other])
        check(ok is False, "colliding rebind blocked")
        st2, _ = app._validate_rebind(word, ("z", "q", "j"))
        check(st2 == "ok", "free keys accepted")
        ok2, _ = app._apply_rebind(word, ("z", "q", "j"))
        check(ok2 and app.word_keys[word] == ("z", "q", "j"), "rebind applied")
        check(app.by_seq.get(("z", "q", "j")) == word, "by_seq has new binding")
        check(_json.loads(mod.GEN_FILE.read_text(encoding="utf-8")).get("t,h") == "the",
              "generated chords.json is NOT modified by user edits")

        win = app.open_library(); root.update()
        check(win.winfo_class() == "Toplevel", "library window opens")
        check(app.enabled is False, "library open disables capture")
        win.destroy(); app.enabled = False
    finally:
        mod.USER_FILE = real_user
        app._reload_library()
        try: os.remove(tmp)
        except OSError: pass
    check(mod.GEN_FILE.read_text(encoding="utf-8") == gen_before, "generated file byte-identical after edits")

    # ---- dictionary mode (persists to the isolated user file) ----
    real_user3 = mod.USER_FILE
    tmp3 = Path(tempfile.gettempdir()) / "user_dict.json"
    if tmp3.exists(): os.remove(tmp3)
    try:
        mod.USER_FILE = tmp3
        app._reload_library()
        app.dict_var.set(True); app._toggle_dict(); root.update()
        check(app.dictionary_mode and app.enabled, "dict mode on + capture auto-enabled")
        neww = "zebuq"
        check(neww not in app.word_keys, "test word is genuinely new")
        for k in neww:
            app._master_hook(ev(k, True)); app._master_hook(ev(k, False))
        app._master_hook(ev("space", True)); app._master_hook(ev("space", False))
        app._poll(); root.update()
        check("new word" in app.dict_lbl.cget("text"), f"dict banner shows ({app.dict_lbl.cget('text')[:25]})")
        check(app.engine.pending is not None, "pending armed")
        app._master_hook(ev("space", True)); app._master_hook(ev("space", False))
        app._poll(); root.update()
        check(neww in app.words, "accepted new word added to library")
        check(app.engine.pending is None, "pending cleared after accept")
        check(neww in _json.loads(tmp3.read_text(encoding="utf-8")).values(),
              "dictionary add persisted to the user file")
    finally:
        mod.USER_FILE = real_user3
        app.dict_var.set(False); app._toggle_dict()
        app._reload_library()
        try: os.remove(tmp3)
        except OSError: pass

    # ---- practice draws from the ENTIRE library, including user words ----
    real_user4 = mod.USER_FILE
    tmp4 = Path(tempfile.gettempdir()) / "user_practice.json"
    tmp4.write_text(_json.dumps({"z,b,q,x": "zbqx"}), encoding="utf-8")
    try:
        mod.USER_FILE = tmp4
        app._reload_library()
        app.set_var.set("All")
        pool = app._practice_pool()
        check(len(pool) == len(app.words), "practice 'All' pool == whole library")
        check("zbqx" in pool, "practice 'All' includes a user-added word")
        app.set_var.set("My words")
        check(app._practice_pool() == ["zbqx"], "practice 'My words' = user additions")
        app.set_var.set("Top 100")
        check(len(app._practice_pool()) == 100, "practice 'Top 100' still works")
        app.set_var.set("All")
    finally:
        mod.USER_FILE = real_user4
        app._reload_library()
        try: os.remove(tmp4)
        except OSError: pass

    # ---- echo mode: keys visible, replaced with the word on Space ----
    SENDS.clear(); WRITES.clear()
    app.echo_var.set(True); app._toggle_echo()
    check(app.engine.echo is True, "echo toggle wires to the engine")
    app.enabled = True; app.engine.type_output = True
    tgt = app.words[0]; keys = app.word_keys[tgt]
    for k in keys:
        app._master_hook(ev(k, True)); app._master_hook(ev(k, False))
    app._master_hook(ev("space", True)); app._master_hook(ev("space", False)); app._poll()
    check(WRITES and WRITES[-1] == tgt + " ", f"echo GUI: word written ({WRITES[-1:]})")
    check(SENDS == ["backspace"] * len(keys), f"echo GUI: backspaced {len(keys)} echoed letters")
    app.enabled = False; app.echo_var.set(False); app._toggle_echo()

    root.destroy()
    print(f"\n{'ALL PASS' if F == 0 else 'FAILURES'}:  {P} passed, {F} failed")
    return 1 if F else 0

if __name__ == "__main__":
    raise SystemExit(main())
