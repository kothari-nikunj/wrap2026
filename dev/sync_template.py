"""Copy shared sources into the single-file scripts.

- template_shell.py (TEMPLATE) -> every *_wrapped.py that embeds it
- template_imessage.py (gen_html) -> imessage_wrapped.py

--check: change nothing, exit 1 if any script is out of date.
"""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
check = '--check' in sys.argv
shell = (root / 'template_shell.py').read_text().strip()
gen_html = (root / 'template_imessage.py').read_text().strip()
stale = []


def sync(path, pattern, new):
    s = path.read_text()
    m = re.search(pattern, s, re.S | re.M)
    if not m:
        sys.exit(f'{path.name}: pattern not found: {pattern}')
    if m.group(0) == new:
        return
    stale.append(path.name)
    if not check:
        path.write_text(s[:m.start()] + new + s[m.end():])


for f in sorted(root.glob('*_wrapped.py')):
    sync(f, r"^TEMPLATE = r'''.*?'''$", shell)
sync(root / 'imessage_wrapped.py', r'^def gen_html\(.*?(?=\n+def main\(\):)', gen_html)

for name in sorted(set(stale)):
    print(f'{name}: {"out of date" if check else "synced"}')
if not stale:
    print('all scripts up to date')
sys.exit(1 if check and stale else 0)
