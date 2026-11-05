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

- Sound feature removed (owner request); top bar is brand + one action pill. Action is "Share" where navigator.canShare({files}) is true, else "Save image"; summary slide repeats it as a full-width CTA.
- Share text uses `My ${document.title} — wrap2026.com` (e.g. "My iMessage Wrapped 2026 — wrap2026.com") instead of a hard-coded year, so 2025-fallback wraps stay correct.
- who-reaches-out: first 5 qualifying rows in data order, then sorted by % desc (not top-5 by %), so high-volume people aren't displaced by 1-message 100% contacts. Bubbles drop when >6 rows.
- Combined summary lost its iMessage/WhatsApp share bars (pbar) to make room for the poster; the psum line keeps the split.
- Muted text opacity raised to the existing .85 (.after) value everywhere it failed 4.5:1; unvisited progress bars (.25) still fail 3:1 non-text — left as is (raising them erases the done/undone distinction).

## Gotchas
- fit(): a block element's scrollWidth can't report text narrower than itself; measure as inline-block with animations off.
- browser-harness tabs run in background; rAF-based libs (modern-screenshot) stall there. Test captures in headless Chrome instead.
- Save/share renders an offscreen clone with --cw:360px/--ch:640px at scale 3, so every device yields exactly 1080x1920 (live card is 100dvh tall on phones, and fractional widths gave 1079x1918).
- fit() must freeze descendant animations too (.fitting *): the stretch keyframe narrows the 2026 span mid-animation and the title overflowed after it finished.
- .spark with 1px gaps and ~306 bars leaves sub-pixel bars at 360px; modern-screenshot drops them. gap:0.
- gen_html has a local `pl = d['priority_list']`; the plural helper is named `plural`.
- people_wrapped.py splices PEOPLE_JS/PEOPLE_TAP_GUARD after exact TEMPLATE lines (PEOPLE_JS_ANCHOR, PEOPLE_TAP_ANCHOR); editing the tap comment or tap-guard line in template_shell.py must update both anchors.
- Under reduced motion, keep the slide visibility transition at 0s or focus() lands on a still-hidden slide.
- Reply time is now a median (SQLite `median` aggregate registered in `_connect`). Combined pools raw gaps from both apps; `merge_data` still needs `im_weight/wa_weight/total_weight` for starter %. `dev/test_merge.py` covers merge_data (fixtures skip it).
- A crash in combined `main()` hangs instead of exiting: the spinner thread is non-daemon. Look in stderr, not at the exit code.

## Animation pass (Emil skills, 2026-11-04)
### Deviations
- Did not use clip-path for the versus-bar reveal (Emil allows it). The bar fill moved to `.vs div::before` with scaleX, so only transform/opacity animate and the label text no longer squashes.
- Kept these non-transform animations on purpose: `heroIn` 6px blur (masks the entrance), and the `stretch` font-width keyframes on the intro and poster titles (the brand moment; it runs twice per wrap).
- Slide navigation keeps its transition when you use the keyboard. In a deck, the motion shows direction; it is short (≤350ms) and can be interrupted.
- iOS `touchstart` no-op listener (for `:active` press feedback) and per-slide `theme-color` are not verified on a real phone.
### Gotchas
- An entrance `animation` with fill `both` keeps its final transform and overrides `:active{transform}`. Pressable elements use fill `backwards` (`.cta`).
- people: a horizontal swipe that starts on the scrollable `.story` becomes a scroll (pointercancel), so it does not change slides. This existed before this pass.
- Landing: main action is "Copy prompt" (Claude + Codex icons, simple-icons 15.0.0 paths inlined); prompt text lives in hidden <p> elements, Terminal command is a <details> fallback. Phones/tablets ((hover:none) and (pointer:coarse)) get "runs on a Mac" + send-link instead. Slides strip moved directly under the hero.
- Agent prompt tells the agent not to open messages or the wrap; script stdout is counts only, so nothing personal reaches the model.
- Headless Chrome clamps --window-size width to 500px, so it can't emulate a 360px phone. Card text scales with --cw (font-size cw/22), so dev/shots.sh sheets already show 360px proportions.
- Parallel dev/shots.sh runs share Chrome's default profile and silently drop sheets. Run them one at a time.
