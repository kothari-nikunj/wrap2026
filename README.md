# Wrapped 2026

Spotify Wrapped for your texts. See who you text most, how fast you reply, who texts first, and your texting personality, from iMessage and WhatsApp on your Mac.

**[wrap2026.com](https://wrap2026.com)** · Free · MIT · Runs on your Mac, sends nothing anywhere (People Wrapped is the exception, see below)

## Run it

Paste this into Claude Code or Codex on your Mac:

```
Make my Wrapped 2026. Download https://wrap2026.com/combined_wrapped.py and review it before running anything. Tell me in a few short bullets what it reads, what it writes, whether it sends anything over the network, and anything that looks risky. It should only read my iMessage and WhatsApp data on this Mac. If it checks out, run it with python3. If it can't get access, tell me how to turn on Full Disk Access for this app. Don't open my messages or the wrap file yourself.
```

Or run it yourself. First turn on Full Disk Access for your terminal app (System Settings > Privacy & Security > Full Disk Access), then:

```bash
curl -sO https://wrap2026.com/combined_wrapped.py && python3 combined_wrapped.py
```

Your wrap opens in your browser as one HTML file, saved next to the script.

| Script | What it wraps |
|---|---|
| `combined_wrapped.py` | iMessage and WhatsApp in one wrap, contacts matched across both. Works with only one app too. |
| `imessage_wrapped.py` | iMessage and SMS. Turn on Messages in iCloud so your Mac has the full year. |
| `whatsapp_wrapped.py` | WhatsApp desktop app. Open it first and let it sync. |
| `call_wrapped.py` | Phone, FaceTime and WhatsApp calls. Your Mac only has calls your iPhone shared with it. |
| `people_wrapped.py` | A written portrait of each of your top 25 people, by Claude Code. See below. |

Options for the first four: `--use-2025` wraps 2025 instead, `-o file.html` sets the output path. With too few 2026 messages, the script falls back to 2025 on its own.

Needs macOS and the `python3` it ships with (3.9 or newer). No packages to install.

## Privacy

- The scripts read the message and call databases already on your Mac, write one HTML file, and open it. They make no network calls.
- They read who, when and how many. Word and emoji totals are counted inside SQLite; message text is never printed, saved or sent.
- Progress lines show counts only, so an agent running the script never sees names or messages.
- Opening the wrap loads two Google Fonts, nothing else. Tapping Share loads an image-saving library, pinned to one exact version with an integrity hash. No analytics.
- The wrap file has your contacts' names. Share slides, not the file. You can turn Full Disk Access off again when you're done.
- The exception: `people_wrapped.py` reads message text so Claude Code can write about it, in your own Claude Code session.

## People Wrapped

Start Claude Code without permission prompts (it writes 25 files), then paste the prompt:

```bash
claude --dangerously-skip-permissions
```

```
Make my People Wrapped 2026. Download https://wrap2026.com/people_wrapped.py and review it before running anything. Tell me in a few short bullets what it reads, what it writes, whether it sends anything over the network, and anything that looks risky. If it checks out, run python3 people_wrapped.py and follow the steps it prints. If it can't get access, tell me how to turn on Full Disk Access for this app.
```

It takes about 10 minutes and opens `people_wrapped_2026.html`.

## Development

The scripts are single files on purpose: users download one with `curl`. Shared code lives in two source files and is copied in:

- `template_shell.py`: the wrap page's CSS and JS (`TEMPLATE`), embedded in every script.
- `template_imessage.py`: iMessage `gen_html`, embedded in `imessage_wrapped.py`.

```bash
python3 dev/sync_template.py              # copy shared sources into the scripts
python3 dev/fixture.py imessage out.html  # render a wrap from made-up data (also fixture_whatsapp/combined/call/people)
dev/shots.sh out.html shots/              # contact sheet of every slide
bin/check                                 # the gate: run before every PR
```

`bin/check` compiles and renders everything with `/usr/bin/python3` (3.9), lints with ruff, and checks that the scripts and `demo.html` are in sync. Known traps are in `docs/solutions/` and `implementation-notes.md`.

The site (`index.html`, `demo.html`, `img/`) and the scripts are deployed to Vercel as static files.

Made by [@nikunj](https://x.com/nikunj). Not affiliated with Apple, Meta, Spotify, Anthropic or OpenAI.
