"""Real launch test: start the app with real keyboard hooks, run mainloop, shut down."""
import importlib.util, traceback
from pathlib import Path
import tkinter as tk

APP = Path(__file__).resolve().parent.parent / "typemax_devowelator.pyw"
spec = importlib.util.spec_from_file_location("typemax_devowelator", APP)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

try:
    root = tk.Tk()
    root.withdraw()                       # don't flash a window during the test
    app = mod.DevowelatorApp(root)            # installs REAL keyboard hook + hotkey
    # capture stays disabled (enabled=False), so nothing is suppressed
    assert app.enabled is False
    root.after(1200, app._on_close)       # real unhook_all + clear_all_hotkeys + destroy
    root.mainloop()
    print("LAUNCH OK: app started, installed hooks, ran mainloop, shut down cleanly")
except Exception:
    print("LAUNCH FAILED:")
    traceback.print_exc()
    raise SystemExit(1)
