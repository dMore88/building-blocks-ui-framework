#!/usr/bin/env python3
"""Build tokens: reads tokens/*.json, writes dist/tokens.css, dist/figma-variables.json, docs/scales.md.

Python standard library only. Run from the repo root: python3 scripts/build.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "bb"


def load(name):
    return json.loads((ROOT / "tokens" / name).read_text())


# ---------- color (OKLCH <-> sRGB) ----------

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_oklch(h):
    r, g, b = (_lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def to_hex(L, C, h):
    """Reduce chroma until the colour fits in sRGB, then return #rrggbb."""
    lo, hi = 0.0, C
    for _ in range(24):
        mid = (lo + hi) / 2
        if all(-1e-4 <= v <= 1 + 1e-4 for v in oklch_to_rgb(L, mid, h)):
            lo = mid
        else:
            hi = mid
    rgb = oklch_to_rgb(L, lo, h)
    return "#" + "".join(f"{round(min(1, max(0, _gam(max(0, v)))) * 255):02x}" for v in rgb)


def build_ramp(hue, peak_chroma, steps):
    ramp = {}
    for step, L in steps.items():
        falloff = max(0.15, 1 - ((L - 0.62) / 0.5) ** 2)  # most colourful in the middle
        ramp[step] = to_hex(L, peak_chroma * falloff, hue)
    return ramp


def build_colors(cfg):
    out = {}
    brand_hue = None
    for name, hex_ in cfg["ramps"].items():
        _, chroma, hue = hex_to_oklch(hex_)
        if name == "brand":
            brand_hue = hue
        out[name] = build_ramp(hue, chroma, cfg["steps"])
    neutral = build_ramp(brand_hue, cfg["neutral"]["chroma"], cfg["steps"])
    neutral = {"0": "#000000", **neutral, "100": "#ffffff"}
    out = {"brand": out.pop("brand"), "neutral": neutral, **out}
    return out


# ---------- model ----------

COLOR_SCOPES = ["ALL_FILLS", "STROKE_COLOR"]


def build_model():
    color_cfg, found, layout = load("color.json"), load("foundations.json"), load("layout.json")

    colors = build_colors(color_cfg)
    color_vars = [
        {"name": f"{ramp}/{step}", "type": "COLOR", "scopes": COLOR_SCOPES, "values": {"value": hex_}}
        for ramp, steps in colors.items()
        for step, hex_ in steps.items()
    ]

    found_vars = []
    for group, spec in found.items():
        if group.startswith("$"):
            continue
        for key, val in spec["values"].items():
            if group == "font-family":
                t, v = "STRING", val
            elif group == "font-weight":
                t, v = "STRING", val["figma"]
            else:
                t, v = "FLOAT", val
            found_vars.append({"name": f"{group}/{key}", "type": t, "scopes": spec["scope"], "values": {"value": v}})

    modes = layout["modes"]
    layout_vars = []
    for name, spec in layout["variables"].items():
        values = {}
        for mode, val in zip(modes, spec["values"]):
            values[mode] = {"alias": {"collection": "foundations", "name": val}} if isinstance(val, str) else val
        is_float = not any(isinstance(v, str) for v in spec["values"])
        layout_vars.append({"name": name, "type": "FLOAT", "scopes": spec["scope"], "values": values, "_ref": not is_float})

    for v in layout_vars:
        v.pop("_ref")

    known = {v["name"] for v in found_vars}
    for v in layout_vars:
        for val in v["values"].values():
            if isinstance(val, dict) and val["alias"]["name"] not in known:
                raise SystemExit(f"layout/{v['name']} references unknown foundations token {val['alias']['name']}")

    return {
        "collections": [
            {"name": "color", "modes": ["value"], "variables": color_vars},
            {"name": "foundations", "modes": ["value"], "variables": found_vars},
            {"name": "layout", "modes": modes, "variables": layout_vars},
        ]
    }, colors, found, layout


# ---------- outputs ----------

def css_name(*parts):
    return "--" + "-".join([PREFIX, *[p.replace("/", "-") for p in parts]])


def write_css(colors, found, layout):
    lines = ["/* Generated by scripts/build.py. Do not edit. */", ":root {"]
    for ramp, steps in colors.items():
        for step, hex_ in steps.items():
            lines.append(f"  {css_name('color', ramp, step)}: {hex_};")
    for group, spec in found.items():
        if group.startswith("$"):
            continue
        for key, val in spec["values"].items():
            n = css_name(group, key)
            if group == "font-family":
                fallback = "monospace" if key == "mono" else "sans-serif"
                lines.append(f'  {n}: "{val}", {fallback};')
            elif group == "font-weight":
                lines.append(f"  {n}: {val['css']};")
            elif group == "opacity":
                lines.append(f"  {n}: {val / 100:g};")
            else:
                lines.append(f"  {n}: {val}px;")
    lines.append("}")

    modes = layout["modes"]
    bp = layout["variables"]["breakpoint/min-width"]["values"]
    order = sorted(range(len(modes)), key=lambda i: bp[i])  # mobile first

    def decls(i):
        out = []
        for name, spec in layout["variables"].items():
            if name.startswith("breakpoint/"):
                continue
            val = spec["values"][i]
            if isinstance(val, str):
                out.append(f"  {css_name(name)}: var({css_name(val)});")
            elif "FONT_SIZE" in spec["scope"] or name.endswith("max-width"):
                out.append(f"  {css_name(name)}: {val}px;")
            else:
                out.append(f"  {css_name(name)}: {val};")
        return out

    for pos, i in enumerate(order):
        lines.append("")
        if pos == 0:
            lines.append(f"/* {modes[i]} (base) */")
            lines.append(":root {")
        else:
            lines.append(f"/* {modes[i]} */")
            lines.append(f"@media (min-width: {bp[i]}px) {{\n:root {{")
        lines += decls(i)
        lines.append("}" if pos == 0 else "}\n}")
    (ROOT / "dist" / "tokens.css").write_text("\n".join(lines) + "\n")


def write_scales_doc():
    def rnd(x):
        return int(round(x))

    fib = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    scales = {
        "4px grid": [4 * n for n in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24)],
        "8px grid": [8 * n for n in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24)],
        "Fibonacci": fib,
        "Modular 1.25 (base 4)": [rnd(4 * 1.25 ** n) for n in range(12)],
        "Golden ratio 1.618 (base 4)": [rnd(4 * 1.618 ** n) for n in range(10)],
    }
    notes = {
        "4px grid": "Dense and flexible. The de facto default; most values are even and pixel-safe.",
        "8px grid": "Fewer, bolder steps. Fast to decide, less fine control inside small components.",
        "Fibonacci": "Organic rhythm; steps grow faster. Odd values (3, 5, 13, 21) can land on half pixels when centred.",
        "Modular 1.25 (base 4)": "Smooth, predictable growth. Rounded, so some values are odd.",
        "Golden ratio 1.618 (base 4)": "Dramatic jumps; few steps cover a huge range. Good for concept work, risky for dense UI.",
    }
    out = [
        "# Scale examples",
        "",
        "_Generated by `scripts/build.py`. For comparison only: the framework ships with independent `spacing` and `sizing` scales (see `tokens/foundations.json`). Copy any row into those files and rebuild to try it._",
        "",
        "| Scale | Steps (px) | Notes |",
        "|---|---|---|",
    ]
    for name, vals in scales.items():
        out.append(f"| {name} | {', '.join(map(str, vals))} | {notes[name]} |")
    out += ["", "## Current defaults", ""]
    found = load("foundations.json")
    for g in ("spacing", "sizing"):
        out.append(f"- **{g}**: {', '.join(str(v) for v in found[g]['values'].values())}")
    (ROOT / "docs" / "scales.md").write_text("\n".join(out) + "\n")


def write_typography_doc():
    found = load("foundations.json")
    out = [
        "# Typography",
        "",
        "_Generated by `scripts/build.py` from `tokens/foundations.json`._",
        "",
        "## Font families",
        "",
        "| Token | Family |",
        "|---|---|",
    ]
    for key, val in found["font-family"]["values"].items():
        out.append(f"| `font-family/{key}` | {val} |")
    out += [
        "",
        "## Font weights",
        "",
        "Figma binds a text style's `fontStyle` with a string variable, so the Figma value must match the font's style name exactly (for example `Semi Bold`, with a space, not `SemiBold`). CSS uses the numeric weight. Both live in the same token.",
        "",
        "| Token | Figma style name | CSS `font-weight` |",
        "|---|---|---|",
    ]
    for key, val in found["font-weight"]["values"].items():
        out.append(f"| `font-weight/{key}` | `{val['figma']}` | {val['css']} |")
    out += [
        "",
        "Adding a weight: add it to `tokens/foundations.json` with the exact style name the font exposes in Figma, then rebuild. Not every family ships every weight, so check the font before relying on it.",
    ]
    (ROOT / "docs" / "typography.md").write_text("\n".join(out) + "\n")


def main():
    model, colors, found, layout = build_model()
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "dist" / "figma-variables.json").write_text(json.dumps(model, indent=2) + "\n")
    write_css(colors, found, layout)
    write_scales_doc()
    write_typography_doc()
    counts = {c["name"]: len(c["variables"]) for c in model["collections"]}
    print("built:", counts, "total", sum(counts.values()))


if __name__ == "__main__":
    main()
