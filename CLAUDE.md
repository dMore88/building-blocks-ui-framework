# Building Blocks UI Framework

Personal, brand-agnostic framework: a Figma components library (file `Building-Blocks3`, key `w5qhBlhUU8wkVq6anEGNiR`) plus this repo as the token source of truth.

## Principles (decided with the owner)

- Less is better. Prefer fewer variables, fewer collections, fewer layers.
- Colors are primitives only (no semantic layer), one brand color, ramps by luminosity: 10 dark to 90 light.
- `spacing` and `sizing` are independent scales. No shared "scale-progression" collection. Alternative scales (Fibonacci, golden, 8px) live only as examples in `docs/scales.md`.
- Anything that changes per breakpoint lives in `layout` (modes desktop / tablet / phone), including `font-size`. Do not duplicate it elsewhere.
- Figma binds `fontStyle` with a string, so weights keep the exact Figma style name (e.g. "Semi Bold").

## Figma file state

- The Figma variables were migrated to this structure (collections `primitives` (colors), `foundations`, `layout`); old `semantic` and the original `foundations` were removed.
- Old color steps map step-for-step (10 to 10 ... 90 to 90; old 99 merged into 90). Old `spacing`/`sizing`/radius/border values were remapped to the nearest new step (more than 25% off was unbound and kept as a fixed value).
- Known leftovers: ~200 widths/heights on icon instances nested in instances and 34 text `minWidth/maxWidth` kept as fixed values (the API cannot rebind them). Legacy orphan bindings (`border-radius/*`, `bbs-*`, `typography/color/*`, `typography/weight/*`) were later remapped: colors to the `primitives` ramps (n-default/soft/subtle/inverted to neutral 10/30/40/90, p-default/soft/subtle to brand 50/70/80), radii to the nearest `radius/*`, fonts to `font-family/body` + `font-size/*`, `bbs-spacing/0` and unmatched values unbound (kept as fixed numbers). Remaining dead links: ~100 widths on nested icon instances and text `minWidth/maxWidth` (the API cannot rebind them). No unbound fills use the old palette hex values.
- Documentation frames in Figma were updated to the new structure: spacing (12 steps), sizing (16), radius (1-4, full), border-weight (1-3), color ramps (9 swatches, bound to the `primitives` collection), layout text. The `scale progression` frame was removed. Semantic frames (Backgrounds, Interactive states, Icon fill, Border color, Opacity, Text color variables) are kept only as usage references, labeled with the primitive each swatch uses; their role names are not variables.
- Doc rows for sizing bind only one dimension (height) because the sample components lock proportions.

- Elevations (shadows) are Figma effect styles, not variables. Their source of truth is `tokens/elevation.json`, extracted from Figma; they build to CSS as `--bb-elevation-*` and to `dist/figma-effect-styles.json`. Shadow color is `neutral/10` (a reference resolved at build). In Figma it is a plain value (not bound): binding a variable to a shadow color forces the variable's alpha and loses each layer's opacity.

- Icons: Lucide (ISC) curated set in `icons/lucide/` + `icons/icons.json`; Figma components `lucide:*` replaced the old Heroicons-style set and `icon-placeholder` (removed). Slots default to `lucide:star`. See `docs/icons.md`. Remix icons are not used.

## Workflow

- Edit `tokens/*.json`, then run `python3 scripts/build.py`. Never hand-edit `dist/` or `docs/scales.md`.
- Node is not installed on this machine; scripts use Python 3 stdlib.
- Do not write to the Figma file without the owner's go-ahead; show the plan first.
