"""Merge the parsed TOTEM layers into one Miryoku-style layer for keymap-drawer.

Usage: python merge_layers.py <parsed.yaml> <merged.yaml>

Every key shows the Base legend in the center and the other layers in the corners.
Layers held by a left thumb (Nav, Mouse, Media) are drawn on right-hand keys and
layers held by a right thumb (Num, Sym, Fun) on left-hand keys, like the Miryoku
reference image. Hold legends and legends a layer puts on its own hand
(BOOT, MAC, ACCEL) go to the bottom-left corner. Korean jamo are derived from the
2-set keycodes the KOR layer sends. Colors per slot live in keymap_drawer.config.yaml.
"""

import sys

import yaml

MERGED_LAYER = "TOTEM"

LEFT_HAND = frozenset([*range(0, 5), *range(10, 15), *range(20, 26), 32, 33, 34])

# layer name -> (hand it is drawn on, legend slot)
LAYER_SLOTS = {
    "Nav": ("right", "tr"),
    "Mouse": ("right", "right"),
    "Media": ("right", "br"),
    "Num": ("left", "tr"),
    "Sym": ("left", "right"),
    "Fun": ("left", "br"),
}

# Legends that only repeat the home row modifiers of a layer: not worth drawing
MODIFIER_LEGENDS = frozenset(["ALT", "GUI", "CTRL", "SHIFT"])

# Standard 2-set (두벌식) IME: keycode legend -> jamo
DUBEOLSIK = dict(zip("QWERTYUIOPASDFGHJKLZXCVBNM", "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ"))
DUBEOLSIK_SHIFTED = {"Q": "ㅃ", "W": "ㅉ", "E": "ㄸ", "R": "ㄲ", "T": "ㅆ", "O": "ㅒ", "P": "ㅖ"}
SHIFT_PREFIX = "Sft+"


def tap_legend(key) -> str:
    """Return the tap legend of a parsed key, '' for none, trans and held keys."""
    if isinstance(key, str):
        return key
    if key.get("type") in ("trans", "held"):
        return ""
    return str(key.get("t", ""))


def korean_jamo(legend: str) -> str:
    if legend.startswith(SHIFT_PREFIX):
        return DUBEOLSIK_SHIFTED.get(legend[len(SHIFT_PREFIX):], "")
    return DUBEOLSIK.get(legend, "")


def base_key(key, pos: int) -> dict:
    hand_type = "left-hand" if pos in LEFT_HAND else "right-hand"
    if isinstance(key, str):
        return {"t": key, "type": hand_type}
    # hold legends go bottom-left so they do not collide with the bottom-right layer legend
    return {"t": key.get("t", ""), "bl": key.get("h", ""), "type": hand_type}


def with_legend(key: dict, slot: str, legend: str) -> dict:
    """Return a copy of key with legend added to slot, skipping duplicates."""
    current = key.get(slot, "")
    if not legend or legend in current.split(" "):
        return key
    return {**key, slot: f"{current} {legend}".strip()}


def merge_key(layers: dict, pos: int) -> dict:
    key = base_key(layers["Base"][pos], pos)
    key = with_legend(key, "tl", korean_jamo(tap_legend(layers["Korean"][pos])))
    hand = "left" if pos in LEFT_HAND else "right"
    for name, (layer_hand, slot) in LAYER_SLOTS.items():
        legend = tap_legend(layers[name][pos])
        if legend == key["t"]:
            continue  # same as Base (e.g. ENT on Nav), nothing new to show
        if layer_hand == hand:
            key = with_legend(key, slot, legend)
        elif legend not in MODIFIER_LEGENDS:
            key = with_legend(key, "bl", legend)
    return key


def merge_combos(combos: list) -> list:
    """Draw every combo once on the merged layer, joining OS variants on the same keys."""
    by_positions: dict = {}
    for combo in combos:
        positions = tuple(combo["p"])
        by_positions[positions] = [*by_positions.get(positions, []), str(combo["k"])]
    # keymap-drawer splits legends on spaces, so each OS variant gets its own line
    return [{"p": list(p), "k": " ".join(labels), "l": [MERGED_LAYER]} for p, labels in by_positions.items()]


def merge(parsed: dict) -> dict:
    layers = parsed["layers"]
    missing = [name for name in ("Base", "Korean", *LAYER_SLOTS) if name not in layers]
    if missing:
        raise SystemExit(f"merge_layers: layers not found in parsed keymap: {', '.join(missing)}")
    merged_layer = [merge_key(layers, pos) for pos in range(len(layers["Base"]))]
    return {
        **parsed,
        "layers": {MERGED_LAYER: merged_layer},
        "combos": merge_combos(parsed.get("combos", [])),
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: merge_layers.py <parsed.yaml> <merged.yaml>")
    with open(sys.argv[1], encoding="utf-8") as src:
        parsed = yaml.safe_load(src)
    with open(sys.argv[2], "w", encoding="utf-8") as dst:
        yaml.safe_dump(merge(parsed), dst, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    main()
