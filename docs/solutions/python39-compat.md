# Scripts must run on macOS's python3 (3.9)

- Users run `python3 script.py`; on a stock Mac that is Xcode's Python 3.9.6, not Homebrew's 3.12+.
- 3.12 relaxed f-strings (PEP 701). A backslash or a reused quote inside `{...}` compiles on 3.12 and is a SyntaxError on 3.9.
- On 2026-11-05 this broke imessage, whatsapp and combined for every stock-Mac user (emoji slide line in gen_html).
- Guard: `bin/check` compiles every script and renders every fixture with `/usr/bin/python3`, and lints with ruff `--target-version py39`.
- Fix pattern: build the fragment in a variable before the f-string (`emoji_row = ...`), then interpolate `{emoji_row}`.
- Also avoid 3.10+ runtime features: `match`, `X | Y` in evaluated annotations, `zip(strict=)`, parenthesized context managers.

## Details
Run `bin/check` before every PR. It also checks that template_shell.py / template_imessage.py are synced into the scripts
(`python3 dev/sync_template.py` to sync) and that demo.html matches the fixture render.
