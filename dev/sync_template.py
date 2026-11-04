"""Copy TEMPLATE from template_shell.py into every script that embeds it."""
import re, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
shell = (root / 'template_shell.py').read_text().strip()
for f in sorted(root.glob('*_wrapped.py')):
    s = f.read_text()
    m = re.search(r"^TEMPLATE = r'''.*?'''$", s, re.S | re.M)
    if not m:
        print(f'{f.name}: no TEMPLATE, skipped'); continue
    if m.group(0) == shell:
        print(f'{f.name}: up to date'); continue
    f.write_text(s[:m.start()] + shell + s[m.end():])
    print(f'{f.name}: synced')
