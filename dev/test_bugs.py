"""Regression tests on made-up databases. python3 dev/test_bugs.py

Runs in US Pacific time so local-vs-UTC bugs show up. Never touches real data:
every script's database and AddressBook paths point at a temp dir, and
load_own_whatsapp (which reads the real WhatsApp DB) is stubbed out.
"""
import contextlib
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

os.environ['TZ'] = 'America/Los_Angeles'
time.tzset()

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from synth import COCOA, ChatDB, address_book, at  # noqa: E402

SCRIPTS = ['imessage', 'whatsapp', 'combined', 'call', 'people']
tmp = Path(tempfile.mkdtemp())


def load(name):
    spec = importlib.util.spec_from_file_location(f'{name}_t', root / f'{name}_wrapped.py')
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    for attr in ('IMESSAGE_DB', 'WHATSAPP_DB'):
        if hasattr(w, attr):
            setattr(w, attr, str(tmp / 'none.db'))
    w.ADDRESSBOOK_DIR = str(tmp / 'none-ab')
    if hasattr(w, 'load_own_whatsapp'):
        w.load_own_whatsapp = lambda: None
    return w


def imessage_env(name, build):
    """Load a script against a fresh made-up chat.db built by build(db)."""
    d = tmp / name
    d.mkdir()
    db = ChatDB(str(d / 'chat.db'))
    build(db)
    db.close()
    address_book(str(d / 'ab'), [('Alex', 'Chen', ['(415) 555-0101'], []),
                                 ('Email', 'Pal', [], ['Friend@Example.com'])])
    return d


def local_ts(y, m, d):
    return int(datetime(y, m, d).timestamp())


def test_spinner_does_not_hang_on_crash():
    for name in SCRIPTS:
        s = load(name).Spinner()
        with contextlib.redirect_stdout(io.StringIO()):
            s.start('x')
            daemon = s.thread.daemon
            s.stop()
        assert daemon, f'{name}: spinner thread must be a daemon, or a crash hangs the process'


def test_year_window_is_local_time():
    im, wa, co = load('imessage'), load('whatsapp'), load('combined')
    assert im.TS_2026 == local_ts(2026, 1, 1), 'imessage TS_2026 is not local midnight'
    assert im.TS_2026_END == local_ts(2027, 1, 1) - 1
    assert im.TS_JUN_2026 == local_ts(2026, 6, 1)
    assert im.TS_2025 == local_ts(2025, 1, 1)
    assert wa.TS_2026 == local_ts(2026, 1, 1) - COCOA, 'whatsapp TS_2026 is not local midnight'
    assert wa.TS_2025_END == local_ts(2026, 1, 1) - 1 - COCOA
    assert co.TS_2026_IMESSAGE == im.TS_2026 and co.TS_2026_WHATSAPP == wa.TS_2026
    assert co.TS_JUN_2025_WHATSAPP == local_ts(2025, 6, 1) - COCOA


def test_new_years_eve_stays_in_2025():
    def build(db):
        db.handle(1, '+14155550101')
        db.chat(1, [1])
        db.daily(1, 1, at(2026, 2, 1, 18), 120, 6)
        for k in range(900):  # Dec 31, 6pm Pacific = Jan 1, 2am UTC
            db.message(1, 1, k % 2, at(2026, 1, 1, 2), 'happy new year')
    d = imessage_env('nye', build)
    w = load('imessage')
    w.IMESSAGE_DB, w.ADDRESSBOOK_DIR = str(d / 'chat.db'), str(d / 'ab')
    data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, w.extract_contacts())
    assert min(data['daily_counts']) >= '2026-01-01', f"daily counts start {min(data['daily_counts'])}"
    assert data['busiest_day'][0] != '2025-12-31', 'a 2025 evening became the busiest day of 2026'


def test_no_sent_messages():
    def build(db):
        db.handle(1, '+14155550101')
        db.chat(1, [1])
        db.daily(1, 1, at(2026, 2, 1, 18), 60, 4, from_me=lambda k: 0)
    d = imessage_env('nosent', build)
    for name in ('imessage', 'combined'):
        w = load(name)
        w.IMESSAGE_DB, w.ADDRESSBOOK_DIR = str(d / 'chat.db'), str(d / 'ab')
        if name == 'imessage':
            data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, w.extract_contacts())
        else:
            data = w.analyze_imessage(w.TS_2026_IMESSAGE, w.TS_2026_END_IMESSAGE, w.TS_JUN_2026_IMESSAGE)
        emoji = dict(data['emoji'])
        assert all(isinstance(c, int) for c in emoji.values()), f'{name}: emoji counts {emoji}'


def test_busiest_day_multiplier_counts_group_chats():
    def build(db):
        for h in (1, 2, 3):
            db.handle(h, f'+1415555010{h}')
        db.chat(1, [1, 3], group=True, name='Fam')
        db.chat(2, [2, 3], group=True, name='Work')
        db.daily(1, 1, at(2026, 3, 1, 18), 150, 5, from_me=lambda k: k % 3 == 0)
        db.daily(2, 2, at(2026, 3, 1, 19), 150, 5, from_me=lambda k: 0)
        for k in range(60):
            db.message(1, 3, 0, at(2026, 4, 10, 18, k % 60))
    d = imessage_env('groups', build)
    w = load('imessage')
    w.IMESSAGE_DB, w.ADDRESSBOOK_DIR = str(d / 'chat.db'), str(d / 'ab')
    contacts = w.extract_contacts()
    data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, contacts)
    data['year'] = 2026
    out = tmp / 'groups.html'
    w.gen_html(data, contacts, str(out))
    m = re.search(r', ([\d,.]+)× a normal day', out.read_text(encoding='utf-8'))
    assert m and float(m.group(1).replace(',', '')) < 20, f'multiplier: {m and m.group(1)}'


def test_seven_digit_match_needs_a_seven_digit_handle():
    contacts = {'4155550101': 'Alex Chen', '5550101': 'Alex Chen', '14155550101': 'Alex Chen'}
    for name, fn in (('imessage', 'get_name'), ('combined', 'get_name_imessage'), ('call', 'get_name'),
                     ('people', 'get_name_imessage')):
        get = getattr(load(name), fn)
        assert get('+14155550101', contacts) == 'Alex Chen', f'{name}: lost an exact match'
        for other in ('+12125550101', '+442075550101'):
            assert get(other, contacts) != 'Alex Chen', f'{name}: {other} matched Alex Chen by its last 7 digits'


def test_call_contacts_include_email_and_international():
    d = imessage_env('callab', lambda db: None)
    address_book(str(d / 'ab2'), [('Email', 'Pal', [], ['Friend@Example.com']),
                                  ('Ravi', 'K', ['+91 88812 34567'], [])])
    w = load('call')
    w.ADDRESSBOOK_DIR = str(d / 'ab2')
    contacts = w.extract_contacts()
    assert w.get_name('friend@example.com', contacts) == 'Email Pal', 'FaceTime-by-email call lost its name'
    assert w.get_name('+918881234567', contacts) == 'Ravi K', 'international number dropped as toll-free'
    assert w.get_name('+18005551234', contacts) is None, 'US toll-free should still be skipped'


def test_call_emails_are_not_phone_numbers():
    w = load('call')
    for email in ('alice1234567@example.com', 'bob1234567@example.com'):
        assert w.normalize_phone(email) is None, f'{email} was turned into a phone number and could merge people'


def test_output_is_utf8_under_any_locale():
    out = tmp / 'latin1.html'
    env = dict(os.environ, LC_ALL='en_US.ISO8859-1')
    r = subprocess.run([sys.executable, str(root / 'dev/fixture.py'), 'imessage', str(out)],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr.strip().splitlines()[-1]


if __name__ == '__main__':
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'ok    {name}')
        except Exception as e:
            failed += 1
            print(f'FAIL  {name}: {type(e).__name__}: {e}')
    print(f'{len(tests) - failed}/{len(tests)} passed')
    sys.exit(1 if failed else 0)
