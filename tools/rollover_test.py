"""
rollover_test.py -- measure how many keys your keyboard registers at once.

This is the hardware go/no-go test for chording. Membrane and laptop keyboards
often "ghost": press 3+ keys and some silently don't register. A chord only
works if EVERY key in it registers at the same time.

Run it, watch the live count, and try these in order:
  1. Hold  F + J            -> count should read 2
  2. Hold  F + J + K        -> count should read 3
  3. Hold  S D F J K L      -> how high does the count actually go?
  4. Hold each 2-key pair you plan to chord with and confirm it reads 2.

If the count stalls BELOW the number of keys you are actually holding down,
those keys are ghosting on this keyboard.

Requires:  pip install keyboard
Quit:      Esc
"""

import sys

try:
    import keyboard
except ImportError:
    sys.exit("Missing dependency. Install it with:  pip install keyboard")

held = set()
prev = set()
max_seen = 0


def on_event(e):
    global max_seen, prev
    if e.name is None:
        return
    if e.event_type == keyboard.KEY_DOWN:
        held.add(e.name)
    elif e.event_type == keyboard.KEY_UP:
        held.discard(e.name)

    if held == prev:
        return  # auto-repeat while holding -- nothing changed
    prev = set(held)

    max_seen = max(max_seen, len(held))
    shown = " + ".join(sorted(held)) if held else "(none)"
    print(f"held now: {len(held):2d}   max so far: {max_seen:2d}   [{shown}]")


def main():
    print("Rollover test -- hold key combos and watch the count. Press Esc to quit.\n")
    keyboard.hook(on_event)
    keyboard.wait("esc")
    keyboard.unhook_all()
    print(f"\nHighest number of keys registered at once: {max_seen}")
    if max_seen >= 3:
        print("-> 3+ keys work: this keyboard can do multi-key chords.")
    elif max_seen == 2:
        print("-> only 2 keys at once: stick to 2-key chords on this keyboard.")
    else:
        print("-> could not confirm 2+ keys. Try again, holding keys firmly together.")


if __name__ == "__main__":
    main()
