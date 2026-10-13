# Building Blocks UI Framework

A minimal, brand-agnostic base for design systems, web pages, wireframes and concepts. Designed in Figma, with this repo as the source of truth for the tokens.

**Philosophy: less is better.** Primitives only, a handful of editable values, no theme layers until they are needed.

## Tokens

| Collection | Contents |
|---|---|
| `primitives` | `brand`, `neutral`, `success`, `warning`, `danger`, `info`. Steps 10 (darkest) to 90 (lightest); `neutral` also has 0 (black) and 100 (white). Generated from one hex per ramp. |
| `foundations` | `spacing`, `sizing` (independent scales), `radius`, `border-weight`, `opacity`, `font-family`, `font-weight`. |
| *(styles)* | `elevation/1x` to `5x`: drop shadows, kept in `tokens/elevation.json` (Figma holds them as effect styles, not variables). |
| `layout` | Everything that changes by breakpoint (modes desktop / tablet / phone): grid, margins, container, `font-size`. |

Source files are in `tokens/`. To retheme, change `brand` in `tokens/color.json`.

## Build

```bash
python3 scripts/build.py
```

Writes `dist/tokens.css`, `dist/figma-variables.json`, `docs/scales.md` and `docs/typography.md` (scale comparison: 4px, 8px, Fibonacci, modular, golden). Python 3 standard library only.
