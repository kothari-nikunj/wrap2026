""""New phone, who dis?" slide and the People count, on made-up databases. python3 dev/test_newcomer.py

Wrap year 2026, previous year 2025. Never touches real data (see test_bugs.load).
"""
import re
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synth import CallDB, ChatDB, WhatsAppDB, address_book, at  # noqa: E402
from test_bugs import load, tmp  # noqa: E402  (sets TZ to US Pacific)

BOOK = [('Nina', 'New', ['(415) 555-0102'], ['nina@example.com']), ('Second', 'Newbie', ['415-555-0106'], []),
        ('Old', 'Friend', ['4155550103'], []), ('Returning', 'Ray', ['+1 415 555 0104'], []),
        ('Nine', 'Msgs', ['4155550105'], [])]


def burst(add, start, n):
    for k in range(n):
        add(k % 2, start + timedelta(hours=k))


def chat_db(name, ray_months=12):
    """Nina (phone 15 + email 15, new), Second Newbie (12, new), Old Friend (2023, then 20), Ray (2025 + 2026),
    Nine Msgs (9), a short code, an alphanumeric sender, a group-only person."""
    d = tmp / name
    d.mkdir()
    db = ChatDB(str(d / 'chat.db'))
    for rowid, h in enumerate(['+14155550102', 'nina@example.com', '+14155550106', '+14155550103', '+14155550104',
                               '+14155550105', '12345', 'AMZN', '+14155550107', '+14155550108'], 1):
        db.handle(rowid, h)
    for c in range(1, 9):
        db.chat(c, [c])
    db.chat(9, [9, 10], group=True, name='Crew')

    def one(c):
        return lambda me, when: db.message(c, c, me, when)
    burst(one(1), at(2026, 3, 1), 15)
    burst(one(2), at(2026, 4, 1), 15)
    burst(one(3), at(2026, 5, 1), 12)
    burst(one(4), at(2023, 6, 1), 5)
    burst(one(4), at(2026, 2, 1), 20)
    for m in range(1, ray_months + 1):
        db.message(5, 5, 1, at(2025, m, 10))
    burst(one(5), at(2026, 6, 1), 20)
    burst(one(6), at(2026, 7, 1), 9)
    burst(one(7), at(2026, 3, 5), 50)
    burst(one(8), at(2026, 3, 9), 50)
    burst(lambda me, when: db.message(9, 9, me, when), at(2026, 8, 1), 60)
    db.close()
    address_book(str(d / 'ab'), BOOK)
    return d


def wa_db(name, ray_months=12):
    """Wanda (14 on her number + 3 on a @lid id, new), Ray (2025 + 2026), Nine Wa (9), a group."""
    path = tmp / f'{name}.sqlite'
    db = WhatsAppDB(str(path))
    db.session(1, '14155550199@s.whatsapp.net', 'Wanda Wave')
    db.session(2, '14155550104@s.whatsapp.net', 'Returning Ray')
    db.session(3, '14155550198@s.whatsapp.net', 'Nine Wa')
    db.session(4, '120363-1@g.us', 'Group', group=True)
    db.session(5, '88812345@lid', 'Wanda Wave')

    def one(s):
        return lambda me, when: db.message(s, me, when)
    burst(one(1), at(2026, 3, 1), 14)
    burst(one(5), at(2026, 9, 1), 3)
    for m in range(1, ray_months + 1):
        db.message(2, 1, at(2025, m, 10))
    burst(one(2), at(2026, 6, 1), 11)
    burst(one(3), at(2026, 6, 1), 9)
    burst(one(4), at(2026, 6, 1), 40)
    db.close()
    return path


def imessage_run(d):
    w = load('imessage')
    w.IMESSAGE_DB, w.ADDRESSBOOK_DIR = str(d / 'chat.db'), str(d / 'ab')
    contacts = w.extract_contacts()
    data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, contacts)
    data['year'] = 2026
    return w, data, contacts


def combined_run(d, wa_path):
    w = load('combined')
    w.load_own_imessage = lambda: None
    w.IMESSAGE_DB, w.ADDRESSBOOK_DIR, w.WHATSAPP_DB = str(d / 'chat.db'), str(d / 'ab'), str(wa_path)
    im = w.analyze_imessage(w.TS_2026_IMESSAGE, w.TS_2026_END_IMESSAGE, w.TS_JUN_2026_IMESSAGE)
    wa = w.analyze_whatsapp(w.TS_2026_WHATSAPP, w.TS_2026_END_WHATSAPP, w.TS_JUN_2026_WHATSAPP)
    return w.merge_data(im, wa, w.extract_imessage_contacts(), w.extract_whatsapp_contacts(), True, True)


def slide_names(html):
    return re.findall(r'data-name="([^"]+)"', html)


def test_imessage_newcomer():
    _, data, _ = imessage_run(chat_db('im'))
    nc = data['newcomer']
    assert nc, 'no newcomer found'
    # Nina's phone + email are one person (30), ranked above Second Newbie (12).
    # Old Friend texted in 2023 so is not new; Nine Msgs is under the bar; short code, AMZN and the group don't count.
    assert (nc['name'], nc['count']) == ('Nina New', 30), nc
    assert nc['new'] == 2, f"new people: {nc['new']} (want Nina + Second Newbie)"
    assert nc['kept'] == 1, f"still here: {nc['kept']} (want Ray only)"


def test_imessage_people_count():
    _, data, _ = imessage_run(chat_db('im_people'))
    # Nina (phone + email once), Second, Old Friend, Ray, Nine. Not the short code, AMZN or the group-only person.
    assert data['stats'][3] == 5, f"people: {data['stats'][3]}"


def test_imessage_short_history_skips_slide():
    w, data, contacts = imessage_run(chat_db('im_short', ray_months=3))
    assert data['newcomer'] is None, f"3 months of 2025 history, slide should be skipped: {data['newcomer']}"
    out = tmp / 'im_short.html'
    w.gen_html(data, contacts, str(out))
    assert 'newcomer' not in slide_names(out.read_text(encoding='utf-8'))


def test_imessage_slide_renders_after_inner_circle():
    w, data, contacts = imessage_run(chat_db('im_html'))
    out = tmp / 'im.html'
    w.gen_html(data, contacts, str(out))
    html = out.read_text(encoding='utf-8')
    names = slide_names(html)
    assert 'newcomer' in names and names.index('newcomer') == names.index('inner-circle') + 1, names
    assert 'New phone, who dis?' in html
    assert '2 new people this year. 1 from last year is still here.' in html
    assert 'hi there' not in html, 'message text leaked into the page'


def test_whatsapp_newcomer_and_people():
    w = load('whatsapp')
    w.load_own_imessage = lambda: None
    w.WHATSAPP_DB = str(wa_db('wa'))
    data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, w.extract_contacts())
    nc = data['newcomer']
    assert nc and (nc['name'], nc['count'], nc['new'], nc['kept']) == ('Wanda Wave', 17, 1, 1), nc
    assert data['stats'][3] == 3, f"people: {data['stats'][3]} (want Wanda once, Ray, Nine Wa)"


def test_whatsapp_short_history_skips_slide():
    w = load('whatsapp')
    w.load_own_imessage = lambda: None
    w.WHATSAPP_DB = str(wa_db('wa_short', ray_months=2))
    data = w.analyze(w.TS_2026, w.TS_2026_END, w.TS_JUN_2026, w.extract_contacts())
    assert data['newcomer'] is None, data['newcomer']


def test_combined_merges_both_apps():
    d = combined_run(chat_db('co'), wa_db('co_wa'))
    nc = d['newcomer']
    assert nc and (nc['name'], nc['count']) == ('Nina New', 30), nc
    assert (nc['new'], nc['kept']) == (3, 1), f"new {nc['new']} (want Nina, Second, Wanda), kept {nc['kept']} (Ray)"
    # Nina, Second, Old Friend, Ray (both apps, once), Nine Msgs, Wanda, Nine Wa
    assert d['stats'][3] == 7, f"people: {d['stats'][3]}"


def test_combined_skips_whatsapp_without_history():
    d = combined_run(chat_db('co2'), wa_db('co2_wa', ray_months=2))
    nc = d['newcomer']
    assert nc and (nc['new'], nc['kept']) == (2, 1), f'WhatsApp side should drop out: {nc}'
    assert d['stats'][3] == 7, f"people: {d['stats'][3]}"


def call_db(name, ray_months=12):
    path = tmp / f'{name}.storedata'
    db = CallDB(str(path))

    def calls(addr, start, n, **kw):
        for k in range(n):
            db.call(addr, start + timedelta(days=k), **kw)
    calls('+14155550102', at(2026, 3, 1), 5)
    calls('nina@example.com', at(2026, 4, 1), 2, call_type=8)
    calls('+14155550106', at(2026, 5, 1), 3)
    calls('+14155550105', at(2026, 5, 1), 2)
    calls('+14155550103', at(2023, 5, 1), 2)
    calls('+14155550103', at(2026, 2, 1), 4)
    for m in range(1, ray_months + 1):
        db.call('+14155550104', at(2025, m, 10))
    calls('+14155550104', at(2026, 6, 1), 5)
    calls('+18005551234', at(2026, 6, 1), 10)
    calls('12345', at(2026, 6, 1), 10)
    db.close()
    return path


def call_run(path):
    w = load('call')
    w.CALL_HISTORY_DB = str(path)
    d = tmp / f'{path.stem}_ab'
    address_book(str(d), BOOK)
    w.ADDRESSBOOK_DIR = str(d)
    return w.call_newcomer(w.TS_2026_START, w.TS_2026_END, w.extract_contacts(), True, False)


def test_call_newcomer():
    nc = call_run(call_db('calls'))
    # Nina: 5 phone + 2 FaceTime-by-email = 7. Second: 3 (at the bar). Two-call person, toll-free and short code out.
    assert nc and (nc['name'], nc['count'], nc['new'], nc['kept']) == ('Nina New', 7, 2, 1), nc


def test_call_short_history_skips_slide():
    assert call_run(call_db('calls_short', ray_months=3)) is None


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
