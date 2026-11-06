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

## Owner fixes pass (2026-11-05): expanded lists, vertical rhythm, who-reaches-out, poster, graph scrub
### Changes
- Layout rule (template_shell `.body`): content is centered between the chrome and the footer by two flex spacers (`.body::before/::after{flex:1 1 0}`); they shrink to 0, so tall content starts under the chrome instead of riding up over it. Top visuals keep a fixed 1.1em gap to the text (one selector list in `.body>:is(...)`). Body padding-bottom 1em + footer padding = about 2em minimum gap above the footer. Intro and poster opt out of the spacers.
- Expanded lists (`.rows.all`): compact rows, stack/spark/bubbles/sticker hidden, body scrolls inside the card only as a last resort.
- iMessage busiest-day shows top 3 (was 5) with "Show all N"; the toggle label is generic now ("Show top N").
- Who reaches out: `MIN_CONVOS = 10` conversations, and rows whose display name is a raw phone number are dropped (imessage, whatsapp, combined). A side with fewer than 2 rows is dropped; no rows at all = no slide (existing behaviour).
- Poster: kicker title, waveform, total, small app split (`.pmeta`), personality as the one loud accent (fitName), #1, three stats (`.stats3`). Palettes `t-poster-a..d` on the summary slide; default is the `POSTER` constant in template_shell JS; `?poster=c` previews.
- Day graphs (`.spark[data-c]`, data-y + data-c counts + data-u unit): hover/drag shows "Mon D · N messages"; at rest the busiest-day label shows the peak, the poster label is hidden. Deck pointerup ignores events on the graph.
### Deviations
- SQL already required 5+ conversations, so the owner's 100% unknown numbers were not 1–2-conversation contacts. They were most likely automated/business senders. A threshold alone would not remove them, so unsaved numbers are also filtered (conservative: these lists are about people you know).
- Poster graph label is hidden at rest (shown only while hovering/scrubbing), unlike busiest-day. A permanent pill on the poster added noise to the calm layout.
- Calls poster gained the daily waveform (it had none) so all posters share one layout. Calls stats: People, Talk time, Missed (Answered dropped).
- Combined platform waffle cells flattened (aspect 1.45 -> 1.7) so the slide fits a 9:16 card with the new footer gap.
- Palette A keeps the pink peak bar on cobalt (1.65:1 non-text contrast, unchanged from before); the peak is also the tallest bar.
### Gotchas
- `margin-bottom:auto` on a top visual no longer does anything (the flex spacers take the free space first). Add new top visuals to the `.body>:is(...)` list.
- A flex child with only percentage-height children (the spark) collapses to 0 when the body overflows; `.body>.spark` is `flex-shrink:0`, only the poster wave may shrink.
- CDP: navigating to the same file with a new #hash fires no load event; go via about:blank.
- Poster color: default cobalt (a); the summary slide shows 4 color dots (.swatches.chrome, injected by JS above the Share CTA). Choice persists in localStorage ('wrap-poster'); ?poster= overrides; export uses the current palette and drops the dots.

## Final pass (2026-11-05)
### Changes
- Python 3.9: a backslash inside an f-string expression (emoji slide) was a SyntaxError on macOS's stock python3; imessage/whatsapp/combined never started. See docs/solutions/python39-compat.md. `bin/check` is the repo gate.
- dev/sync_template.py also splices template_imessage.py (gen_html) into imessage_wrapped.py; `--check` fails on drift.
- dev/test_bugs.py: regression tests on made-up chat.db/AddressBook (dev/synth.py), run in US Pacific time.
- Fixed: year window was UTC while stats use local dates (now `_local_ts`); non-daemon spinner hung the process after any crash; SUM NULL on zero sent messages crashed; busiest-day multiplier divided all messages by 1:1-only messages; last-7-digit name fallback matched other countries' numbers (now only for 7-digit handles); calls dropped FaceTime-by-email and international numbers (toll-free filter now NANP-only); HTML written in the locale encoding (now utf-8); call check_access probed a different WhatsApp table than the analysis reads.
- Wrap page: modern-screenshot pinned with SRI (sha384). DB paths print with ~ instead of the home dir.
- Removed localbrief.py (unrelated private-dashboard script that was committed and served publicly).
### Deviations
- Not fixed (owner call or larger change): people_wrapped tells users to run `claude --dangerously-skip-permissions` over raw message text (prompt-injection risk); WhatsApp names use push names only (no ZPARTNERNAME fallback); iMessage word/emoji counts skip attributedBody-only rows; people lacks is_person/is_own filters; WhatsApp group calls add full duration per participant.
- iMessage real-data run on 3.9 not repeated: this session lost Full Disk Access to Messages/Contacts. WhatsApp, combined (WhatsApp half) and calls ran on real data under 3.9.

## Newcomer slide (2026-11-06): "New phone, who dis?"
### Changes
- New slide `newcomer` right after `inner-circle` in imessage, whatsapp, combined and calls. Hero = new person with the most 1:1 messages (calls: calls) this year; line below: "N new people this year. M from last year are still here."
- Person = existing filters (iMessage `is_person`; WhatsApp `NOT is_own` 1:1 sessions; calls = named contacts), grouped by contact. Bar: 10 messages (calls: 3) this year. New = no 1:1 before Jan 1 of the wrap year (local). Still here = qualifies and had 1+ in the previous calendar year.
- Shown only when the source has 1:1 messages (calls: named calls) in 6+ distinct months of the previous year, and N > 0. Shared helpers `group_people` / `find_newcomer` copied into imessage/whatsapp/combined; calls has `call_newcomer`.
- People count (total slide + poster): same grouping, no bar. iMessage was already right; combined (was COUNT DISTINCT handle_id + sum of both apps) and WhatsApp (was distinct JIDs) fixed.
- calls: name normalization and per-contact grouping moved out of `analyze_calls` into `normalize_call_names` / `group_call_contacts` (code moved as-is, plus a `times` list per contact) so the newcomer uses the same grouping.
- CSS: `.after.rule` (separator line, existing `--soft` token). Tests: dev/test_newcomer.py (in bin/check); synth.py gained `WhatsAppDB` and `CallDB`.
### Deviations / judgment calls
- WhatsApp people are grouped by display name (push name, else formatted number), as combined already does, so a phone JID and a @lid JID of one person count once. Risk: two different people with the same push name merge.
- WhatsApp does not use `is_person`: it returns 0 for every `@lid` JID, so it would drop real people. WhatsApp keeps its existing `NOT is_own` filter.
- Combined: each app adds to the newcomer slide only if that app passes its own 6-month check; if only WhatsApp passes, the slide uses WhatsApp alone. People count uses both apps regardless.
- Calls history check counts months of named calls only (unnamed calls are dropped before analysis). Calls have no `plural()` helper; the slide uses inline conditionals.
- Unsaved numbers that pass `is_person` with 10+ messages can be the hero (same as number-one). Not filtered, per spec.
- Theme: white (calls: ink, since the next calls slide is white).
### Gotchas
- WhatsApp `analyze()` now takes `contacts` (names are needed for grouping).
- dev/test_newcomer.py stubs `load_own_imessage` in whatsapp/combined: whatsapp's version opens the real ~/Library/Messages/chat.db by path.
- Review (2026-11-06): WhatsApp keeps grouping people by display name. On the owner's DB, of 16 names on >1 1:1 chat, 1 was a phone+@lid pair and 15 phone+phone; LID.sqlite's ZWAPHONENUMBERLIDPAIR exists but is empty. Merging by name can only make "you'd never texted before" more cautious (shared name with an old contact => not new); splitting by JID can make it false. Cost: two new people with the same push name count as one.
- Combined: an app that fails the 6-month history check still contributes its before-this-year counts, so older chats there rule people out as new (test in dev/test_merge.py).
- Calls newcomer counts WhatsApp group-call participants like 1:1 calls (existing call-counting behaviour; left as is).
