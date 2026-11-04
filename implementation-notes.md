# wrap2026 implementation notes

## Plan
1. Copy wrap2025 scripts, shift year window to 2026 (fallback 2025), serve scripts from wrap2026.com.
2. New site (index.html): lilac/plum/cobalt/pink palette, Anybody (variable width) + Onest, live demo wrap in hero.
3. New generated-wrap template, shared shell (template_shell.py -> TEMPLATE) pasted into each script.
4. Port template to whatsapp/combined/call/people scripts.
5. Deploy to Vercel, attach wrap2026.com.

## Layout
- `template_shell.py`: source of truth for the TEMPLATE string (CSS+JS). Each script embeds a copy (scripts must stay single-file for `curl -O`).
- `template_imessage.py`: source of truth for imessage gen_html. Spliced into imessage_wrapped.py.
- `dev/fixture*.py`: render a wrap from made-up data. `dev/shots.sh <html> <outdir>`: contact sheet of all slides, final state (`?still`).
- `demo.html`: fixture render, embedded live in the site hero. `img/slide-*.webp`: exported fixture slides for the site strip.

## Deviations
- Headless Chrome min window width is 500px; mobile checks use 390px iframes.
- Save-as-image switched from html2canvas to modern-screenshot (html2canvas drops variable-font width axes).
- Site privacy copy changed from "zero network" to "script makes no network calls; the wrap page loads fonts + image-save library" (accurate).

## Gotchas
- fit(): a block element's scrollWidth can't report text narrower than itself; measure as inline-block with animations off.
- browser-harness tabs run in background; rAF-based libs (modern-screenshot) stall there. Test captures in headless Chrome instead.
