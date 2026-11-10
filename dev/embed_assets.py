"""Embed the fonts and the image library into template_shell.py, so a wrap loads nothing from the network.

Sources are in dev/vendor/:
- anybody-*.woff2, onest-*.woff2: the latin and latin-ext files Google Fonts serves
  for Anybody (wdth 50-150, wght 400-900) and Onest (wght 400-600). Both SIL OFL 1.1.
- modern-screenshot-4.4.39.mjs: dist/index.mjs from the npm package, unchanged. MIT.

Run this after changing a vendor file, then dev/sync_template.py.
--check: change nothing, exit 1 if template_shell.py is out of date.
"""
import base64
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
vendor = root / 'dev' / 'vendor'
check = '--check' in sys.argv

LATIN = ('U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,'
         'U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD')
LATIN_EXT = ('U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,'
             'U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF')
FONTS = [
    ('Anybody', 'font-weight:400 900;font-stretch:50% 150%', 'anybody-latin-ext.woff2', LATIN_EXT),
    ('Anybody', 'font-weight:400 900;font-stretch:50% 150%', 'anybody-latin.woff2', LATIN),
    ('Onest', 'font-weight:400 600', 'onest-latin-ext.woff2', LATIN_EXT),
    ('Onest', 'font-weight:400 600', 'onest-latin.woff2', LATIN),
]
LIB = 'modern-screenshot-4.4.39.mjs'


def font_css():
    out = []
    for family, axes, name, urange in FONTS:
        b64 = base64.b64encode((vendor / name).read_bytes()).decode()
        # a backslash at the end of a line continues a CSS string, so the data stays in short lines
        lines = '\\\n'.join(b64[i:i + 100] for i in range(0, len(b64), 100))
        out.append(f"/* {name} */\n@font-face{{font-family:'{family}';font-style:normal;{axes};font-display:swap;"
                   f"unicode-range:{urange};src:url(\"data:font/woff2;base64,\\\n{lines}\") format('woff2')}}")
    return '\n'.join(out)


def lib_js():
    src = (vendor / LIB).read_text()
    body, n = re.subn(r'\nexport \{.*?\};\s*$', '\n', src, flags=re.S)
    name = re.search(r'^\s*(\w+) as domToBlob,?$', src, re.M)
    assert n == 1 and name, 'unexpected export block in ' + LIB
    assert "'''" not in body and '</script' not in body and not re.search(r'^import ', body, re.M)
    return f'(function () {{\n{body}window.modernScreenshot = {{ domToBlob: {name.group(1)} }};\n}})();'


def fill(s, begin, end, new):
    i, j = s.index(begin) + len(begin), s.index(end)
    return s[:i] + '\n' + new + '\n' + s[j:]


path = root / 'template_shell.py'
old = path.read_text()
new = fill(old, '/* fonts:begin */', '/* fonts:end */', font_css())
new = fill(new, '/* shot:begin */', '/* shot:end */', lib_js())
if new == old:
    print('template_shell.py assets up to date')
elif check:
    print('template_shell.py assets out of date: python3 dev/embed_assets.py && python3 dev/sync_template.py')
    sys.exit(1)
else:
    path.write_text(new)
    print('template_shell.py assets embedded')
