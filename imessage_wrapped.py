#!/usr/bin/env python3
"""
iMessage Wrapped 2026 - Your texting habits, exposed.
Usage: python3 imessage_wrapped.py
"""

import argparse, glob, os, plistlib, re, sqlite3, subprocess, sys, threading, time
from datetime import datetime

IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESSBOOK_DIR = os.path.expanduser("~/Library/Application Support/AddressBook")

class Spinner:
    """Animated terminal spinner for long operations"""
    def __init__(self, message=""):
        self.message = message
        self.spinning = False
        self.thread = None
        self.frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']

    def spin(self):
        i = 0
        while self.spinning:
            frame = self.frames[i % len(self.frames)]
            print(f"\r    {frame} {self.message}", end='', flush=True)
            time.sleep(0.1)
            i += 1

    def start(self, message=None):
        if message:
            self.message = message
        self.spinning = True
        self.thread = threading.Thread(target=self.spin, daemon=True)
        self.thread.start()

    def stop(self, final_message=None):
        self.spinning = False
        if self.thread:
            self.thread.join()
        if final_message:
            print(f"\r    ✓ {final_message}".ljust(60))
        else:
            print()

def _local_ts(y, m=1, d=1):
    """Unix time of local midnight. The stats bucket days and hours in local time, so the year must too."""
    return int(datetime(y, m, d).timestamp())

TS_2026, TS_JUN_2026, TS_2026_END = _local_ts(2026), _local_ts(2026, 6), _local_ts(2027) - 1
TS_2025, TS_JUN_2025, TS_2025_END = _local_ts(2025), _local_ts(2025, 6), _local_ts(2026) - 1

def normalize_phone(phone):
    if not phone: return None
    digits = re.sub(r'\D', '', str(phone))
    # Handle common international prefixes
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]  # US/Canada +1
    elif len(digits) > 10:
        # For international numbers, store full digits for exact matching
        # but also try common formats
        return digits
    return digits[-10:] if len(digits) >= 10 else (digits if len(digits) >= 7 else None)

def extract_contacts():
    contacts = {}
    db_paths = glob.glob(os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "AddressBook-v22.abcddb"))
    main_db = os.path.join(ADDRESSBOOK_DIR, "AddressBook-v22.abcddb")
    if os.path.exists(main_db): db_paths.append(main_db)
    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            people = {}
            for row in conn.execute("SELECT ROWID, ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL"):
                name = f"{row[1] or ''} {row[2] or ''}".strip()
                if name: people[row[0]] = name
            for owner, phone in conn.execute("SELECT ZOWNER, ZFULLNUMBER FROM ZABCDPHONENUMBER WHERE ZFULLNUMBER IS NOT NULL"):
                if owner in people:
                    name = people[owner]
                    digits = re.sub(r'\D', '', str(phone))
                    # Store multiple formats for better matching
                    if digits:
                        contacts[digits] = name  # Full international
                        if len(digits) >= 10:
                            contacts[digits[-10:]] = name  # Last 10
                        if len(digits) >= 7:
                            contacts[digits[-7:]] = name  # Last 7 (local)
                        if len(digits) == 11 and digits.startswith('1'):
                            contacts[digits[1:]] = name  # Without US prefix
            for owner, email in conn.execute("SELECT ZOWNER, ZADDRESS FROM ZABCDEMAILADDRESS WHERE ZADDRESS IS NOT NULL"):
                if owner in people: contacts[email.lower().strip()] = people[owner]
            conn.close()
        except: pass
    return contacts

def get_name(handle, contacts):
    if '@' in handle:
        lookup = handle.lower().strip()
        if lookup in contacts: return contacts[lookup]
        return handle.split('@')[0]
    # Try multiple phone formats for matching
    digits = re.sub(r'\D', '', str(handle))
    # Try full digits first (international)
    if digits in contacts: return contacts[digits]
    # Try without leading 1 (US/Canada)
    if len(digits) == 11 and digits.startswith('1'):
        if digits[1:] in contacts: return contacts[digits[1:]]
    # Try last 10 digits
    if len(digits) >= 10 and digits[-10:] in contacts:
        return contacts[digits[-10:]]
    # A 7-digit local number (no area code)
    if len(digits) == 7 and digits in contacts:
        return contacts[digits]
    return handle

def contact_key_and_label(handle, contacts):
    """
    Build a stable key for a contact so phone + email from the same person merge.
    Priority:
      1) Address book name
      2) Normalized phone number
      3) Normalized email
      4) Raw handle
    """
    name = get_name(handle, contacts)
    clean_name = re.sub(r'\s+', ' ', name).strip() if name else ''
    lower_handle = handle.lower().strip()

    if clean_name and clean_name.lower() != lower_handle:
        return f"name:{clean_name.lower()}", clean_name

    digits = normalize_phone(handle)
    if digits:
        return f"phone:{digits}", clean_name or digits

    if '@' in handle:
        return f"email:{lower_handle}", clean_name or lower_handle

    return f"raw:{lower_handle}", clean_name or handle

def aggregate_contacts(rows, contacts):
    """
    Merge message counts for multiple handles that belong to the same contact.
    Returns a sorted list of dicts with name/count/sent/recv/handles.
    """
    aggregated = {}
    for handle, total, sent, recv in rows:
        key, label = contact_key_and_label(handle, contacts)
        if key not in aggregated:
            aggregated[key] = {
                'name': label,
                'count': 0,
                'sent': 0,
                'recv': 0,
                'handles': set()
            }
        aggregated[key]['count'] += total or 0
        aggregated[key]['sent'] += sent or 0
        aggregated[key]['recv'] += recv or 0
        aggregated[key]['handles'].add(handle)

        # Prefer a real contact name over raw handles when available
        current_label = aggregated[key]['name']
        if label and (current_label == handle or current_label == label.lower()):
            aggregated[key]['name'] = label

    return sorted(aggregated.values(), key=lambda x: x['count'], reverse=True)

def check_access():
    if not os.path.exists(IMESSAGE_DB):
        print("\n[FATAL] Not macOS.")
        sys.exit(1)
    try:
        conn = sqlite3.connect(IMESSAGE_DB)
        conn.execute("SELECT 1 FROM message LIMIT 1")
        conn.close()
    except:
        print("\n⚠️  ACCESS DENIED")
        print("   System Settings → Privacy & Security → Full Disk Access → turn on the app running this (Terminal, iTerm, Ghostty, Codex), then reopen it")
        subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles'])
        sys.exit(1)

class _Median:
    def __init__(self): self.v = []
    def step(self, x):
        if x is not None: self.v.append(x)
    def finalize(self):
        if not self.v: return None
        s = sorted(self.v); n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

OWN_IDS, OWN_DIGITS = set(), set()

def _add_own(i):
    i = re.sub(r'^[EePp]:', '', (i or '').strip()).lower()
    if not i: return
    if '@' in i and not i.endswith('@s.whatsapp.net'): OWN_IDS.add(i); return
    dg = re.sub(r'\D', '', i.split('@')[0])
    if len(dg) >= 7: OWN_DIGITS.add(dg[-10:])

def is_person(h):
    """A real person: an email or a phone number. Not a short code, business sender ID, bot or yourself."""
    if not h: return 0
    l = h.strip().lower()
    if l.startswith('urn:') or l in OWN_IDS: return 0
    if '@' in l:
        dom = l.rsplit('@', 1)[1]
        return int('.' in dom and not dom.endswith('rbm.goog'))
    num = re.sub(r'\([^)]*\)$', '', l)
    if re.search(r'[a-z]', num): return 0
    dg = re.sub(r'\D', '', num)
    return int(len(dg) >= 7 and dg[-10:] not in OWN_DIGITS)

def is_own(jid):
    dg = re.sub(r'\D', '', (jid or '').split('@')[0])
    return int(len(dg) >= 7 and dg[-10:] in OWN_DIGITS)

def _connect(path):
    conn = sqlite3.connect(path)
    conn.create_aggregate('median', 1, _Median)
    conn.create_function('is_person', 1, is_person, deterministic=True)
    conn.create_function('is_own', 1, is_own, deterministic=True)
    return conn

def load_own_imessage():
    try:
        conn = sqlite3.connect(IMESSAGE_DB)
        for (i,) in conn.execute("SELECT DISTINCT destination_caller_id FROM message WHERE destination_caller_id IS NOT NULL UNION SELECT DISTINCT account_login FROM chat WHERE account_login IS NOT NULL"):
            _add_own(i)
        conn.close()
    except sqlite3.Error:
        pass

def load_own_whatsapp():
    p = os.path.expanduser('~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Library/Preferences/group.net.whatsapp.WhatsApp.shared.plist')
    try:
        with open(p, 'rb') as f:
            _add_own(plistlib.load(f).get('OwnJabberID'))
    except (OSError, plistlib.InvalidFileException):
        pass

def q(sql):
    conn = _connect(IMESSAGE_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def analyze(ts_start, ts_end, ts_jun, contacts):
    d = {}
    load_own_imessage(); load_own_whatsapp()

    # === IDENTIFY 1:1 vs GROUP CHATS ===
    # 1:1 chats have exactly 1 participant in chat_handle_join
    # Group chats have 2+ participants
    # We'll use this CTE pattern to filter queries

    # Common table expression for 1:1 chat filtering
    one_on_one_cte = """
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        )
    """

    # Stats: handle NULL from SUM when 0 messages (1:1 only)
    raw_stats = q(f"""{one_on_one_cte}
        SELECT COUNT(*), SUM(CASE WHEN is_from_me=1 THEN 1 ELSE 0 END), SUM(CASE WHEN is_from_me=0 THEN 1 ELSE 0 END), COUNT(DISTINCT handle_id)
        FROM message m
        WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
    """)[0]
    stats = [raw_stats[0] or 0, raw_stats[1] or 0, raw_stats[2] or 0, raw_stats[3] or 0]

    # Top contacts (1:1 only, excluding 5-6 digit shortcodes like 12345, 123456)
    top_handles = q(f"""{one_on_one_cte}
        SELECT h.id, COUNT(*) t, SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.is_from_me=0 THEN 1 ELSE 0 END)
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id ORDER BY t DESC LIMIT 20
    """)
    d['top'] = aggregate_contacts(top_handles, contacts)

    # Unique people count (merge phone/email for same contact)
    all_handles = q(f"""{one_on_one_cte}
        SELECT DISTINCT h.id
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
    """)
    unique_contact_keys = {contact_key_and_label(row[0], contacts)[0] for row in all_handles}
    stats[3] = len(unique_contact_keys)
    d['stats'] = tuple(stats)

    # Late night texters (1:1 only, excluding shortcodes)
    d['late'] = q(f"""{one_on_one_cte}
        SELECT h.id, COUNT(*) n FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND CAST(strftime('%H',datetime((m.date/1000000000+978307200),'unixepoch','localtime')) AS INT)<5
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id HAVING n>5 ORDER BY n DESC LIMIT 5
    """)
    
    r = q(f"SELECT CAST(strftime('%H',datetime((date/1000000000+978307200),'unixepoch','localtime')) AS INT) h, COUNT(*) c FROM message WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end} GROUP BY h ORDER BY c DESC LIMIT 1")
    d['hour'] = r[0][0] if r else 12
    days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    r = q(f"SELECT CAST(strftime('%w',datetime((date/1000000000+978307200),'unixepoch','localtime')) AS INT) d, COUNT(*) FROM message WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end} GROUP BY d ORDER BY 2 DESC LIMIT 1")
    d['day'] = days[r[0][0]] if r else '???'
    
    # Ghosted (1:1 only, excluding shortcodes)
    d['ghosted'] = q(f"""{one_on_one_cte}
        SELECT h.id, SUM(CASE WHEN m.is_from_me=0 AND (m.date/1000000000+978307200)<{ts_jun} THEN 1 ELSE 0 END) b, SUM(CASE WHEN m.is_from_me=0 AND (m.date/1000000000+978307200)>={ts_jun} THEN 1 ELSE 0 END) a
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id HAVING b>10 AND a<3 ORDER BY b DESC LIMIT 5
    """)

    # Heating up (1:1 only, excluding shortcodes)
    d['heating'] = q(f"""{one_on_one_cte}
        SELECT h.id, SUM(CASE WHEN (m.date/1000000000+978307200)<{ts_jun} THEN 1 ELSE 0 END) h1, SUM(CASE WHEN (m.date/1000000000+978307200)>={ts_jun} THEN 1 ELSE 0 END) h2
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id HAVING h1>20 AND h2>h1*1.5 ORDER BY (h2-h1) DESC LIMIT 5
    """)

    # Biggest fan (1:1 only, excluding shortcodes)
    d['fan'] = q(f"""{one_on_one_cte}
        SELECT h.id, SUM(CASE WHEN m.is_from_me=0 THEN 1 ELSE 0 END) t, SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END) y
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id HAVING t>y*2 AND y>0 AND (t+y)>100 ORDER BY (t*1.0/NULLIF(y,0)) DESC LIMIT 5
    """)

    # Simp (1:1 only, excluding shortcodes)
    d['simp'] = q(f"""{one_on_one_cte}
        SELECT h.id, SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END) y, SUM(CASE WHEN m.is_from_me=0 THEN 1 ELSE 0 END) t
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id HAVING y>t*2 AND t>0 AND (t+y)>100 ORDER BY (y*1.0/NULLIF(t,0)) DESC LIMIT 5
    """)
    
    # Response time: partition by handle_id so we measure per-conversation (1:1 only)
    r = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        ),
        g AS (
            SELECT (m.date/1000000000+978307200) ts, m.is_from_me, m.handle_id,
                   LAG(m.date/1000000000+978307200) OVER (PARTITION BY m.handle_id ORDER BY m.date) pt,
                   LAG(m.is_from_me) OVER (PARTITION BY m.handle_id ORDER BY m.date) pf
            FROM message m
            WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        )
        SELECT MEDIAN(ts-pt)/60.0 FROM g
        WHERE is_from_me=1 AND pf=0 AND (ts-pt)<86400 AND (ts-pt)>10
    """)
    d['resp'] = round(r[0][0], 1) if r[0][0] is not None else 30

    # Per-person response time: who you reply to fastest (YOUR PRIORITY LIST)
    d['priority_list'] = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        ),
        response_pairs AS (
            SELECT m.handle_id,
                   (m.date/1000000000+978307200) ts,
                   m.is_from_me,
                   LAG(m.date/1000000000+978307200) OVER (PARTITION BY m.handle_id ORDER BY m.date) pt,
                   LAG(m.is_from_me) OVER (PARTITION BY m.handle_id ORDER BY m.date) pf
            FROM message m
            WHERE (m.date/1000000000+978307200) > {ts_start} AND (m.date/1000000000+978307200) < {ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        )
        SELECT h.id, MEDIAN(rp.ts - rp.pt)/60.0 as avg_resp_min, COUNT(*) as reply_count
        FROM response_pairs rp
        JOIN handle h ON rp.handle_id = h.ROWID
        WHERE rp.is_from_me = 1 AND rp.pf = 0
        AND (rp.ts - rp.pt) BETWEEN 10 AND 86400
        AND is_person(h.id)
        GROUP BY h.id
        HAVING reply_count >= 50
        ORDER BY avg_resp_min ASC
        LIMIT 5
    """)

    # Per-person response time: who replies to YOU fastest (WHO DROPS EVERYTHING)
    d['fast_responders'] = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        ),
        response_pairs AS (
            SELECT m.handle_id,
                   (m.date/1000000000+978307200) ts,
                   m.is_from_me,
                   LAG(m.date/1000000000+978307200) OVER (PARTITION BY m.handle_id ORDER BY m.date) pt,
                   LAG(m.is_from_me) OVER (PARTITION BY m.handle_id ORDER BY m.date) pf
            FROM message m
            WHERE (m.date/1000000000+978307200) > {ts_start} AND (m.date/1000000000+978307200) < {ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        )
        SELECT h.id, MEDIAN(rp.ts - rp.pt)/60.0 as avg_resp_min, COUNT(*) as reply_count
        FROM response_pairs rp
        JOIN handle h ON rp.handle_id = h.ROWID
        WHERE rp.is_from_me = 0 AND rp.pf = 1
        AND (rp.ts - rp.pt) BETWEEN 10 AND 86400
        AND is_person(h.id)
        GROUP BY h.id
        HAVING reply_count >= 50
        ORDER BY avg_resp_min ASC
        LIMIT 5
    """)

    # Per-person initiation breakdown (WHO TEXTS FIRST per person)
    d['initiation_breakdown'] = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        ),
        conversation_starts AS (
            SELECT m.handle_id, m.is_from_me,
                   (m.date/1000000000+978307200) ts,
                   LAG(m.date/1000000000+978307200) OVER (PARTITION BY m.handle_id ORDER BY m.date) prev_ts
            FROM message m
            WHERE (m.date/1000000000+978307200) > {ts_start} AND (m.date/1000000000+978307200) < {ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        )
        SELECT h.id,
               SUM(CASE WHEN cs.is_from_me = 1 THEN 1 ELSE 0 END) as you_started,
               SUM(CASE WHEN cs.is_from_me = 0 THEN 1 ELSE 0 END) as they_started,
               COUNT(*) as total_convos
        FROM conversation_starts cs
        JOIN handle h ON cs.handle_id = h.ROWID
        WHERE (cs.prev_ts IS NULL OR (cs.ts - cs.prev_ts) > 14400)
        AND is_person(h.id)
        GROUP BY h.id
        HAVING total_convos >= 5
        ORDER BY total_convos DESC
        LIMIT 60
    """)

    emojis = ['😂','❤️','😭','🔥','💀','✨','🙏','👀','💯','😈']
    emoji_cases = ', '.join([f"SUM(CASE WHEN text LIKE '%{e}%' THEN 1 ELSE 0 END)" for e in emojis])
    r = q(f"SELECT {emoji_cases} FROM message WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end} AND is_from_me=1")
    counts = {e: c or 0 for e, c in zip(emojis, r[0])} if r else {e: 0 for e in emojis}
    d['emoji'] = sorted(counts.items(), key=lambda x:-x[1])[:5]

    # Total words sent (excluding reactions, empty messages, and attachments-only)
    # Simple approach: count messages with text as minimum, then add extra for spaces
    # This ensures we get at least 1 word per text message
    r = q(f"""
        SELECT
            COUNT(*) as msg_count,
            COALESCE(SUM(LENGTH(text) - LENGTH(REPLACE(text, ' ', ''))), 0) as extra_words
        FROM message
        WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end}
        AND is_from_me=1
        AND text IS NOT NULL
        AND LENGTH(text) > 0
        AND text NOT LIKE 'Loved "%'
        AND text NOT LIKE 'Liked "%'
        AND text NOT LIKE 'Disliked "%'
        AND text NOT LIKE 'Laughed at "%'
        AND text NOT LIKE 'Emphasized "%'
        AND text NOT LIKE 'Questioned "%'
        AND text NOT LIKE '%￼%'
    """)
    # Words = number of messages with text + number of spaces (each space = 1 extra word)
    msg_count = r[0][0] or 0
    extra_words = r[0][1] or 0
    d['words'] = msg_count + extra_words
    
    # NEW: Busiest day
    r = q(f"SELECT DATE(datetime((date/1000000000+978307200),'unixepoch','localtime')) d, COUNT(*) c FROM message WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end} GROUP BY d ORDER BY c DESC LIMIT 1")
    if r:
        busiest_date = r[0][0]
        d['busiest_day'] = (busiest_date, r[0][1])  # ('2026-03-15', 523)

        # Top 10 people you messaged on that busiest day (1:1 chats only, exclude shortcodes)
        d['busiest_day_top'] = q(f"""{one_on_one_cte}
            SELECT h.id, COUNT(*) t
            FROM message m
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE DATE(datetime((m.date/1000000000+978307200),'unixepoch','localtime')) = '{busiest_date}'
            AND (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
            AND is_person(h.id)
            GROUP BY h.id
            ORDER BY t DESC
            LIMIT 10
        """)
    else:
        d['busiest_day'] = None
        d['busiest_day_top'] = []
    
    # NEW: Conversation starter % (who texts first after 4+ hour gap) - 1:1 only
    r = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        ),
        convos AS (
            SELECT m.is_from_me,
                   (m.date/1000000000+978307200) as ts,
                   LAG(m.date/1000000000+978307200) OVER (PARTITION BY m.handle_id ORDER BY m.date) as prev_ts
            FROM message m
            WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        )
        SELECT
            SUM(CASE WHEN is_from_me=1 THEN 1 ELSE 0 END) as you_started,
            COUNT(*) as total
        FROM convos
        WHERE prev_ts IS NULL OR (ts - prev_ts) > 14400
    """)
    if r and r[0][1] and r[0][1] > 0:
        you_started = r[0][0] or 0
        d['starter_pct'] = round((you_started / r[0][1]) * 100)
    else:
        d['starter_pct'] = 50

    # Longest streak: consecutive days with a single person (1:1 only)
    streak_rows = q(f"""{one_on_one_cte}
        SELECT h.id, DATE(datetime((m.date/1000000000+978307200),'unixepoch','localtime')) d
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id, d
        ORDER BY h.id, d
    """)
    best_streak = None
    from datetime import datetime as dt2, timedelta
    streaks = {}
    for handle, dstr in streak_rows:
        if handle not in streaks:
            streaks[handle] = {'last': None, 'current_len': 0, 'start': None, 'end': None, 'best': (0, None, None)}
        cur = streaks[handle]
        cur_day = dt2.strptime(dstr, '%Y-%m-%d').date()
        if cur['last'] and cur_day == cur['last'] + timedelta(days=1):
            cur['current_len'] += 1
            cur['end'] = cur_day
        else:
            cur['current_len'] = 1
            cur['start'] = cur_day
            cur['end'] = cur_day
        cur['last'] = cur_day
        if cur['current_len'] > cur['best'][0]:
            cur['best'] = (cur['current_len'], cur['start'], cur['end'])
    for handle, info in streaks.items():
        length, start_d, end_d = info['best']
        if length and (best_streak is None or length > best_streak['length']):
            best_streak = {'handle': handle, 'length': length, 'start': start_d, 'end': end_d}
    d['streak'] = best_streak

    # Message marathon: single-day convo with most messages (1:1 only)
    r = q(f"""{one_on_one_cte}
        SELECT h.id,
               DATE(datetime((m.date/1000000000+978307200),'unixepoch','localtime')) d,
               COUNT(*) c,
               MIN(m.date/1000000000+978307200) min_ts,
               MAX(m.date/1000000000+978307200) max_ts
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND is_person(h.id)
        GROUP BY h.id, d
        ORDER BY c DESC
        LIMIT 1
    """)
    if r:
        h_id, d_str, cnt, min_ts, max_ts = r[0]
        duration_hours = round(max((max_ts - min_ts) / 3600.0, 0), 1)
        d['marathon'] = {'handle': h_id, 'date': d_str, 'count': cnt, 'hours': duration_hours}
    else:
        d['marathon'] = None
    
    # Personality
    s = d['stats']
    ratio = s[1] / (s[2] + 1)
    if d['hour'] < 5 or d['hour'] > 22: d['personality'] = ("NOCTURNAL MENACE", "terrorizes people at ungodly hours")
    elif d['resp'] < 1: d['personality'] = ("TERMINALLY ONLINE", "has never touched grass")
    elif d['resp'] > 30: d['personality'] = ("TOO COOL TO REPLY", "leaves everyone on read")
    elif ratio < 0.5: d['personality'] = ("POPULAR (ALLEGEDLY)", "everyone wants a piece")
    elif ratio > 2: d['personality'] = ("THE YAPPER", "carries every conversation alone")
    elif d['starter_pct'] > 65: d['personality'] = ("CONVERSATION STARTER", "always making the first move")
    elif d['starter_pct'] < 35: d['personality'] = ("THE WAITER", "never texts first, ever")
    else: d['personality'] = ("SUSPICIOUSLY NORMAL", "no notes, boring but stable")

    # === CONTRIBUTION GRAPH DATA ===
    # Get daily message counts for the year
    daily_counts = q(f"""
        SELECT DATE(datetime((date/1000000000+978307200),'unixepoch','localtime')) as d, COUNT(*) as c
        FROM message
        WHERE (date/1000000000+978307200)>{ts_start} AND (date/1000000000+978307200)<{ts_end}
        GROUP BY d
        ORDER BY d
    """)
    d['daily_counts'] = {row[0]: row[1] for row in daily_counts}

    # Calculate streaks and stats
    from datetime import datetime as dt, timedelta
    if d['daily_counts']:
        all_counts = list(d['daily_counts'].values())
        d['max_daily'] = max(all_counts) if all_counts else 0
        d['active_days'] = len([c for c in all_counts if c > 0])

        # Top 5 most active days
        sorted_days = sorted(d['daily_counts'].items(), key=lambda x: -x[1])[:5]
        d['top_days'] = sorted_days

        # Average messages per active day
        d['avg_daily'] = round(sum(all_counts) / max(len(all_counts), 1))

        # Find busiest month
        monthly_counts = {}
        for date_str, count in d['daily_counts'].items():
            month_key = date_str[:7]  # "2026-03" format
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + count
        if monthly_counts:
            busiest_month_key = max(monthly_counts, key=monthly_counts.get)
            d['busiest_month'] = dt.strptime(busiest_month_key, '%Y-%m').strftime('%b')
            d['busiest_month_count'] = monthly_counts[busiest_month_key]
        else:
            d['busiest_month'] = 'N/A'
            d['busiest_month_count'] = 0

        # Calculate quiet days (days with 0 messages in the year so far)
        first_data_date = min(d['daily_counts'].keys())
        last_data_date = max(d['daily_counts'].keys())
        first_dt = dt.strptime(first_data_date, '%Y-%m-%d').date()
        last_dt = dt.strptime(last_data_date, '%Y-%m-%d').date()
        total_days_in_range = (last_dt - first_dt).days + 1
        d['quiet_days'] = total_days_in_range - d['active_days']
    else:
        d['daily_counts'] = {}
        d['max_daily'] = 0
        d['active_days'] = 0
        d['top_days'] = []
        d['avg_daily'] = 0
        d['busiest_month'] = 'N/A'
        d['busiest_month_count'] = 0
        d['quiet_days'] = 0

    # === GROUP CHAT STATS ===
    # Group chats have 2+ participants in chat_handle_join
    group_chat_cte = """
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        group_chats AS (
            SELECT chat_id FROM chat_participants WHERE participant_count >= 2
        ),
        group_messages AS (
            SELECT m.ROWID as msg_id, cmj.chat_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE cmj.chat_id IN (SELECT chat_id FROM group_chats)
        )
    """

    # Group chat overview: count of groups, total messages, sent by you
    r = q(f"""{group_chat_cte}
        SELECT
            (SELECT COUNT(DISTINCT chat_id) FROM group_messages gm
             JOIN message m ON gm.msg_id = m.ROWID
             WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}) as group_count,
            COUNT(*) as total_msgs,
            SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END) as sent
        FROM message m
        WHERE (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        AND m.ROWID IN (SELECT msg_id FROM group_messages)
    """)
    if r and r[0][0]:
        d['group_stats'] = {
            'count': r[0][0] or 0,
            'total': r[0][1] or 0,
            'sent': r[0][2] or 0
        }
    else:
        d['group_stats'] = {'count': 0, 'total': 0, 'sent': 0}

    # Group chat leaderboard: top 5 most active group chats
    # Get chat_id, display_name, message count, and participant handles for name fallback
    r = q(f"""
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        group_chats AS (
            SELECT chat_id FROM chat_participants WHERE participant_count >= 2
        ),
        group_messages AS (
            SELECT m.ROWID as msg_id, cmj.chat_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE cmj.chat_id IN (SELECT chat_id FROM group_chats)
            AND (m.date/1000000000+978307200)>{ts_start} AND (m.date/1000000000+978307200)<{ts_end}
        )
        SELECT
            c.ROWID as chat_id,
            c.display_name,
            COUNT(*) as msg_count,
            (SELECT COUNT(*) FROM chat_handle_join WHERE chat_id = c.ROWID) as participant_count
        FROM chat c
        JOIN group_messages gm ON c.ROWID = gm.chat_id
        GROUP BY c.ROWID
        ORDER BY msg_count DESC
        LIMIT 10
    """)
    d['group_leaderboard'] = []
    for row in r:
        chat_id, display_name, msg_count, participant_count = row
        if display_name:
            name = display_name
        else:
            # Get first 2 participant names for fallback
            handles = q(f"""
                SELECT h.id FROM chat_handle_join chj
                JOIN handle h ON chj.handle_id = h.ROWID
                WHERE chj.chat_id = {chat_id}
                LIMIT 2
            """)
            name = handles  # Will be resolved to names in gen_html
        d['group_leaderboard'].append({
            'chat_id': chat_id,
            'name': name,
            'msg_count': msg_count,
            'participant_count': participant_count
        })

    return d

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="theme-color" content="#160A26">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect x='4' y='10' width='56' height='40' rx='20' fill='%232F4BFF'/><path d='M14 44 L8 58 L26 48Z' fill='%232F4BFF'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link crossorigin="anonymous" href="https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,400..900&family=Onest:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#241038; --night:#160A26; --lilac:#EEE8FF; --lav:#DCD3F5;
  --cobalt:#2F4BFF; --pink:#FF5FA2; --white:#FFFFFF;
  --cw:min(100vw, calc(92dvh * 9 / 16));
  --ch:calc(var(--cw) * 16 / 9);
  --display:'Anybody',system-ui,sans-serif;
  --body:'Onest',system-ui,sans-serif;
  --ease:cubic-bezier(.23,1,.32,1);
  --spring:cubic-bezier(.3,1.4,.5,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overscroll-behavior:none}
html{-webkit-text-size-adjust:100%}
body{background:var(--night);color:var(--white);font-family:var(--body);-webkit-font-smoothing:antialiased;overflow:hidden;user-select:none;-webkit-user-select:none;-webkit-tap-highlight-color:transparent;touch-action:pan-y;transition:background .6s var(--ease)}
button{font:inherit;color:inherit;cursor:pointer}
:focus-visible{outline:2px solid currentColor;outline-offset:3px}

/* themes */
.t-cobalt{--bg:var(--cobalt);--fg:var(--white);--soft:rgba(255,255,255,.14);--tint:#9FB0FF}
.t-lilac{--bg:var(--lilac);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt)}
.t-white{--bg:var(--white);--fg:var(--ink);--soft:rgba(36,16,56,.07);--tint:var(--cobalt)}
.t-ink{--bg:var(--ink);--fg:var(--lilac);--soft:rgba(238,232,255,.1);--tint:var(--pink)}
.t-night{--bg:var(--night);--fg:var(--lilac);--soft:rgba(238,232,255,.09);--tint:var(--pink)}
.t-pink{--bg:var(--pink);--fg:var(--ink);--soft:rgba(36,16,56,.1);--tint:var(--white)}
.t-lav{--bg:var(--lav);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt)}
.t-stage{--bg:var(--cobalt);--fg:var(--white);--soft:rgba(255,255,255,.14);--tint:#9FB0FF}

/* deck */
.deck{position:fixed;inset:0}
.slide{position:absolute;inset:0;display:grid;place-items:center;opacity:0;visibility:hidden;transform:translateX(5%) scale(.97);transition:opacity .2s var(--ease),transform .3s var(--ease),visibility 0s .3s}
.slide.past{transform:translateX(-5%) scale(.97)}
.slide.on{opacity:1;visibility:visible;transform:none;transition:opacity .3s var(--ease),transform .35s var(--ease),visibility 0s}
.card{position:relative;width:var(--cw);height:var(--ch);border-radius:calc(var(--cw) * .075);background:var(--bg);color:var(--fg);font-size:calc(var(--cw) / 22);padding:5.2em 1.6em 1.3em;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.5)}
.body{flex:1;display:flex;flex-direction:column;gap:.2em;min-height:0;padding-bottom:1em}
/* vertical rhythm: one rule for every slide. The content block (top visual + text) is centered between the
   chrome and the footer. The spacers shrink to 0 when content is tall, so it never rides up under the chrome. */
.body::before,.body::after{content:"";flex:1 1 0}
.body:has(>.intro)::before,.body:has(>.intro)::after{content:none}
.body>:is(.pile,.redact,.chain,.spark,.sticker,.stack,.av.xl,.thread,.clock,.wave,.share,.tiles,.ringing,.waffle,.pies,.notes,.cal,.cols,.lag,.who){margin-bottom:1.1em}
.body>.spark{padding-bottom:0;flex-shrink:0}
.body:has(>.rows)>.spark{height:5em}
.mark{display:flex;justify-content:space-between;font-family:var(--display);font-weight:700;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:.62em;opacity:.85;padding-top:1.6em;letter-spacing:.01em}

/* type */
.lead{font-size:1.15em;font-weight:500;line-height:1.3;text-wrap:balance;max-width:20ch}
.lead.gap{margin-top:1.2em}
.hero.fit{white-space:nowrap;overflow-wrap:normal}
.hero{font-family:var(--display);font-weight:900;font-stretch:125%;font-variation-settings:"wdth" 125;font-size:4.6em;line-height:.86;letter-spacing:-.045em;font-variant-numeric:tabular-nums;margin:.12em 0 .08em -.04em;overflow-wrap:anywhere}
.hero small{font-size:.32em;font-stretch:100%;font-variation-settings:"wdth" 100;font-weight:700;letter-spacing:0;margin-left:.15em}
.hero.name{font-weight:800;font-stretch:62%;font-variation-settings:"wdth" 62;font-size:4.4em;line-height:.88;letter-spacing:-.03em;text-wrap:balance;overflow-wrap:normal}
.hero.diag{font-weight:800;font-stretch:62%;font-variation-settings:"wdth" 62;font-size:4.6em;line-height:.86;letter-spacing:-.015em;color:var(--tint);text-wrap:balance;overflow-wrap:normal}
.hero.sm{font-size:3.4em}
.after{font-size:1em;line-height:1.4;opacity:.85;max-width:26ch;text-wrap:pretty;overflow-wrap:break-word}
.after b{font-weight:600;opacity:1}
.after .count{font-weight:600;font-variant-numeric:tabular-nums}

/* stat split */
.split{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8em;margin-top:1.4em;padding-top:1em;border-top:1.5px solid var(--soft)}
.split b{display:block;font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.35em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.split span{font-size:.72em;opacity:.7;line-height:1.2;display:block;margin-top:.2em}

/* ranked rows */
.rows{list-style:none;display:flex;flex-direction:column;gap:.32em;margin-top:.9em}
.row{position:relative;display:grid;grid-template-columns:1.5em minmax(0,1fr) auto;align-items:baseline;gap:.4em;padding:.55em .75em;border-radius:.7em;overflow:hidden;font-size:.95em}
.row{border-bottom:1.5px solid var(--soft);border-radius:0;padding:.6em 0}
.row::before{content:"";position:absolute;left:0;bottom:-1.5px;height:2.5px;width:calc(var(--w) * 100%);background:var(--tint);border-radius:2px;transform-origin:left;z-index:0}
.row>*{position:relative;z-index:1}
.row .rk{font-family:var(--display);font-weight:700;font-stretch:110%;font-variation-settings:"wdth" 110;opacity:.85;font-size:.85em}
.row .nm{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .vl{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-variant-numeric:tabular-nums}
.row .vl i{font-style:normal;font-family:var(--body);font-weight:400;opacity:.85;font-size:.85em}
.row:first-child{font-size:1.15em}
.row:last-child{border-bottom-color:transparent}
.row.extra{display:none}
.rows.all .row.extra{display:grid}
/* expanded to 10: compact rows, decoration steps aside, and the body scrolls inside the card as a last resort */
.rows.all{gap:0;margin-top:.6em}
.rows.all .row{padding:.34em 0;font-size:.85em}
.rows.all .row:first-child{padding:.45em 0;font-size:1em}
.body:has(.rows.all)>:is(.stack,.spark,.thread,.sticker,.pile,.av.xl){display:none}
.body:has(.rows.all){overflow-y:auto;overscroll-behavior:contain;scrollbar-width:none;margin:0 -.3em;padding-left:.3em;padding-right:.3em}
.body:has(.rows.all)::-webkit-scrollbar{display:none}
.rows.tight{margin-top:.5em;gap:.1em}
.rows.tight .row{padding:.4em 0}
.rows.tight .row:first-child{font-size:1em}
.more{align-self:flex-start;background:none;border:0;font-size:.75em;font-weight:600;opacity:.85;padding:.6em 0;text-decoration:underline;text-underline-offset:.25em}
@media (hover:hover) and (pointer:fine){.more:hover{opacity:1}}

/* avatars: five colorways, swapped where one would vanish into the slide */
.a0{--ab:var(--cobalt);--af:var(--white)}.a1{--ab:var(--pink);--af:var(--ink)}.a2{--ab:var(--ink);--af:var(--lilac)}.a3{--ab:var(--lav);--af:var(--ink)}.a4{--ab:var(--white);--af:var(--cobalt)}
.t-cobalt .a0,.t-stage .a0{--ab:var(--white);--af:var(--cobalt)}.t-cobalt .a4{--ab:var(--lilac);--af:var(--ink)}
.t-pink .a1{--ab:var(--white);--af:var(--ink)}
.t-ink .a2,.t-night .a2{--ab:var(--lilac);--af:var(--ink)}
.t-lav .a3,.t-lilac .a3{--ab:var(--white);--af:var(--ink)}.t-lilac .a4,.t-white .a4{--ab:var(--cobalt);--af:var(--white)}
/* avatars */
.av{display:inline-grid;place-items:center;width:2.6em;height:2.6em;border-radius:50%;background:var(--ab);color:var(--af);font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1em;letter-spacing:-.02em;box-shadow:0 0 0 .18em var(--bg);flex:none}
.av .ae{font-size:1.15em;letter-spacing:0}
.av .ag{width:1.15em;height:1.15em}
.av.xl{width:5.2em;height:5.2em;font-size:1.5em;margin-bottom:auto;box-shadow:0 1em 2.4em -1em rgba(36,16,56,.45)}
.stack{display:flex;margin-bottom:auto;padding-left:.7em}
.stack .av{width:3.6em;height:3.6em;margin-left:-.7em;font-size:1.05em}
.stack .av:nth-child(1){width:4.6em;height:4.6em;z-index:5}
.stack .av:nth-child(2){z-index:4}.stack .av:nth-child(3){z-index:3}.stack .av:nth-child(4){z-index:2}.stack .av:nth-child(5){z-index:1}

/* message pile */
.pile{display:flex;flex-wrap:wrap;gap:.3em;margin-bottom:auto;align-content:flex-start;max-height:46%;overflow:hidden}
.pile i{width:1.05em;height:.75em;border-radius:.4em .4em .4em .12em;background:var(--soft);background:color-mix(in srgb,var(--fg) 16%,transparent)}
.pile i.s{background:var(--cobalt);border-radius:.4em .4em .12em .4em}

/* redacted text */
.redact{display:flex;flex-direction:column;gap:.55em;margin-bottom:auto}
.redact i{height:.8em;width:var(--w);border-radius:.4em;background:var(--soft);background:color-mix(in srgb,var(--fg) 12%,transparent)}
.redact i:nth-child(4n){background:var(--cobalt);opacity:.85}

/* streak chain */
.chain{display:grid;grid-template-columns:repeat(15,1fr);gap:.3em;margin-bottom:auto}
.chain i{aspect-ratio:1;border-radius:.25em;background:var(--cobalt)}

/* stars */
.stars{position:absolute;inset:4em 0 50% 0;pointer-events:none}
.stars i{position:absolute;width:.25em;height:.25em;border-radius:50%;background:var(--lilac);box-shadow:0 0 .6em var(--lilac);animation:twinkle 3s infinite;animation-delay:calc(var(--d) * -.4s)}
@keyframes twinkle{0%,100%{opacity:.25}50%{opacity:1}}

/* year sparkline */
.spark{display:flex;align-items:flex-end;gap:0;height:9em;margin-bottom:auto;padding-bottom:1.4em}
.spark i{flex:1;height:var(--h);background:var(--ink);opacity:.28;border-radius:1px 1px 0 0}
.spark i.pk{opacity:1;background:var(--white);box-shadow:0 0 0 2px var(--ink)}
/* day graph: hover or drag reads a day; the label sits above the bars */
.spark[data-c]{position:relative;touch-action:none;cursor:crosshair;margin-top:2.2em}
.spark .sl{position:absolute;left:0;top:-.5em;translate:0 -100%;padding:.3em .7em;border-radius:999px;background:var(--fg);color:var(--bg);font-size:.72em;font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums;pointer-events:none;transition:opacity .15s var(--ease)}
.spark i.cur{opacity:1}

/* sticker */
.sticker.big{font-size:6em}
.sticker{margin-bottom:auto;align-self:flex-start;font-size:4.2em;line-height:1;width:1.7em;height:1.7em;display:grid;place-items:center;border-radius:50%;background:var(--soft);transform:rotate(-8deg)}

/* typing */
.typing{display:flex;gap:.3em;padding:.85em 1em;font-size:1.6em}
.typing i{width:.42em;height:.42em;border-radius:50%;background:currentColor;opacity:.35;animation:blink 1.2s infinite}
.typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,60%,100%{opacity:.3;transform:none}30%{opacity:1;transform:translateY(-.12em)}}

/* clock */
.clock{position:relative;width:11em;height:11em;border-radius:50%;margin-bottom:auto;background:var(--soft)}
.clock i{position:absolute;left:50%;top:50%;width:.22em;height:.9em;margin:-.45em 0 0 -.11em;background:currentColor;opacity:.4;border-radius:.2em;transform:rotate(var(--t)) translateY(-4.6em)}
.clock b{position:absolute;left:50%;top:50%;width:.36em;height:4.2em;margin-left:-.18em;background:var(--pink);border-radius:.3em;transform-origin:50% 0;transform:rotate(calc(var(--a) + 180deg));box-shadow:0 0 1.2em var(--pink)}
.clock u{position:absolute;left:50%;top:50%;width:.9em;height:.9em;margin:-.45em;border-radius:50%;background:var(--pink)}

/* versus */
.vs{display:flex;flex-direction:column;gap:.5em;margin-top:1.2em}
.vs div{position:relative;isolation:isolate;display:flex;justify-content:space-between;align-items:center;font-weight:500;padding:.55em .8em;border-radius:.9em;color:var(--bg);width:max(11em, calc(var(--w) * 100%));max-width:100%}
.vs div::before{content:"";position:absolute;inset:0;z-index:-1;border-radius:inherit;background:var(--fg);transform-origin:left}
.vs span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vs div:last-child{color:var(--fg)}
.vs div:last-child::before{background:var(--soft)}
.vs b{flex:none;font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-variant-numeric:tabular-nums;margin-left:1em}

/* bubbles */
.thread{display:flex;flex-direction:column;gap:.3em;margin-bottom:auto}
.bub{max-width:80%;padding:.5em .8em;border-radius:1.1em;font-size:1em;line-height:1.3;width:fit-content}
.bub.r{background:var(--soft);border-bottom-left-radius:.3em}
.bub.s{align-self:flex-end;background:var(--fg);color:var(--bg);border-bottom-right-radius:.3em}
.thread.big .bub{font-size:1.4em}

/* intro */
.intro{display:flex;flex-direction:column;flex:1}
.stretch{font-family:var(--display);line-height:.82;letter-spacing:-.04em;margin-bottom:auto}
.stretch span{display:block}
.stretch span:first-child{font-weight:800;font-stretch:58%;font-variation-settings:"wdth" 58;font-size:3.6em;white-space:nowrap}
.stretch span:last-child{font-weight:900;font-stretch:150%;font-variation-settings:"wdth" 150;font-size:3.4em;margin-left:-.05em;white-space:nowrap}
.intro .thread{margin:0 0 1.2em}
.hint{font-size:.85em;opacity:.85;font-weight:500}

/* year dots */
.year{display:flex;flex-direction:column;gap:.34em;margin:1em 0 .2em}
.mrow{display:grid;grid-template-columns:2em minmax(0,1fr);align-items:center}
.mrow span{font-size:.6em;opacity:.6;font-weight:500}
.dots{display:grid;grid-template-columns:repeat(31,1fr);gap:.14em}
.dots i{aspect-ratio:1;border-radius:50%;background:currentColor;opacity:.12}
.dots i.na{opacity:0}
.dots i.fut{opacity:.04}
.dots i.l1{opacity:.3}.dots i.l2{opacity:.55}.dots i.l3{opacity:.85}
.dots i.l4{opacity:1;background:var(--pink);box-shadow:0 0 .5em var(--pink)}
.tip{position:fixed;pointer-events:none;background:var(--white);color:var(--ink);font:500 13px var(--body);padding:6px 10px;border-radius:999px;transform:translate(-50%,-140%);opacity:0;transition:opacity .15s;z-index:20;white-space:nowrap;box-shadow:0 6px 20px rgba(0,0,0,.25)}

/* moon */
.moon{position:absolute;top:4.6em;right:1.6em;width:4.5em;height:4.5em;border-radius:50%;box-shadow:inset -1.1em .5em 0 0 var(--pink);filter:drop-shadow(0 0 1.4em rgba(255,95,162,.45));transform:rotate(-20deg)}

/* emoji */
.emoji{display:flex;flex-wrap:wrap;gap:.1em .25em;font-size:3.2em;line-height:1.15;margin:.2em 0 .3em}
.emoji span{display:inline-block}

/* duo */
.duo{margin-top:1.1em}
.duo+.duo{padding-top:1.1em;border-top:1.5px solid var(--soft)}

/* summary */
.t-stage .tilt{perspective:1200px}
.summary{transform-style:preserve-3d;transition:transform .5s var(--ease);background:var(--pbg)}
/* poster palettes: t-poster-a (cobalt, default) to d; JS picks POSTER (or ?poster=b) */
.t-stage,.t-poster-a{--pbg:linear-gradient(160deg,#4A62FF 0%,var(--cobalt) 45%,#2236D9 100%);--acc:#FFC2DC;--bar:var(--white);--bo:.4;--pk:var(--pink);--cbg:var(--white);--cfg:var(--cobalt)}
.t-poster-b{--bg:var(--ink);--fg:var(--lilac);--soft:rgba(238,232,255,.1);--tint:var(--pink);--pbg:linear-gradient(160deg,var(--ink) 0%,var(--night) 100%);--acc:var(--pink);--bar:var(--lilac);--bo:.35;--pk:var(--pink);--cbg:var(--pink);--cfg:var(--ink)}
.t-poster-c{--bg:var(--lilac);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt);--pbg:var(--lilac);--acc:var(--cobalt);--bar:var(--ink);--bo:.25;--pk:var(--cobalt);--cbg:var(--cobalt);--cfg:var(--white)}
.t-poster-d{--bg:var(--pink);--fg:var(--ink);--soft:rgba(36,16,56,.1);--tint:var(--white);--pbg:var(--pink);--acc:var(--ink);--bar:var(--ink);--bo:.25;--pk:var(--ink);--cbg:var(--ink);--cfg:var(--pink)}
.summary .sheen{position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at var(--mx,30%) var(--my,20%),rgba(255,255,255,.28),transparent 45%);mix-blend-mode:soft-light;z-index:2}
.summary .hero{font-size:4.2em}
.grid4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.9em 1em;margin-top:1.3em;padding-top:1.1em;border-top:1.5px solid var(--soft)}
.grid4 dt{font-size:.7em;opacity:.85}
.grid4 dd{font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1.5em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.diag-sm{font-family:var(--display);font-weight:900;font-stretch:55%;font-variation-settings:"wdth" 55;font-size:2.4em;line-height:.9;margin-top:.7em;color:#FFC2DC}
.top3{font-size:.85em;opacity:.85;margin-top:.5em}
/* summary poster: the slide people post */
.ptitle{font-family:var(--display);font-weight:800;line-height:.9;letter-spacing:-.03em;white-space:nowrap;font-size:2.4em}
.ptitle span:first-child{font-stretch:58%;font-variation-settings:"wdth" 58}
.ptitle span:last-child{font-weight:900;font-stretch:150%;font-variation-settings:"wdth" 150;margin-left:.12em}
/* poster layout: title, graph and total on top; personality, #1 and three stats at the bottom */
.poster .body::before,.poster .body::after{content:none}
.poster .body{padding-bottom:1em}
.poster .hero small{opacity:.85}
.pwave{height:5em;padding:0;margin:1.6em 0 .5em}
.poster .pwave{flex-shrink:1;min-height:2.6em;margin-top:1.2em}
.pwave i{background:var(--bar);opacity:var(--bo)}
.pwave i.pk{background:var(--pk);opacity:1;box-shadow:none}
.pwave .sl{opacity:0}.pwave.hot .sl{opacity:1}
.pmeta{font-size:.78em;font-weight:500;opacity:.85;margin-top:.15em}
.poster .ptitle{font-size:1.9em;margin-bottom:auto}
/* white at .85 on the light end of the cobalt gradient is 3.8:1; full white is 4.7:1 */
.t-poster-a .poster :is(.pmeta,.one span,.stats3 dt,.hero small){opacity:1}
.poster .diag-sm{margin-top:auto;padding-top:.15em;font-size:3.3em;line-height:.88;letter-spacing:-.01em;color:var(--acc);text-wrap:balance}
.one{display:flex;align-items:center;gap:.6em;margin-top:.9em}
.one .av{--ab:var(--fg);--af:var(--bg);width:2.3em;height:2.3em;font-size:.9em;flex:none;box-shadow:none}
.one b{display:block;font-family:var(--display);font-weight:800;font-stretch:75%;font-variation-settings:"wdth" 75;font-size:1.3em;line-height:1.05;letter-spacing:-.01em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.one div{min-width:0}
.one span{font-size:.72em;opacity:.85}
.stats3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8em;margin-top:1.1em}
.stats3 dt{font-size:.68em;opacity:.85}
.stats3 dd{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.15em;font-variant-numeric:tabular-nums;letter-spacing:-.01em;white-space:nowrap}
.poster .mark{opacity:1;gap:1em}
.cta{display:flex;justify-content:center;align-items:center;gap:.5em;margin-top:1.2em;border:0;border-radius:999px;padding:.85em 1em;background:var(--cbg,var(--white));color:var(--cfg,var(--cobalt));font-weight:600;font-size:.9em;transition:transform .15s var(--ease)}
.cta:not(:disabled):active{transform:scale(.96)}
.cta:focus-visible{outline-color:var(--fg)}
.cta svg{width:1.1em;height:1.1em}
/* poster color picker: never in the exported image (.chrome) */
.swatches{display:flex;justify-content:center;gap:.7em;margin-top:1em}
.swatches button{width:1.6em;height:1.6em;border-radius:50%;border:0;padding:0;background:var(--sw);box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--fg) 35%,transparent);position:relative;transition:transform .16s var(--ease)}
.swatches button::after{content:"";position:absolute;inset:-.7em}
.swatches button[aria-pressed=true]{box-shadow:0 0 0 2px var(--fg),inset 0 0 0 1.5px color-mix(in srgb,var(--fg) 35%,transparent)}
.swatches button:active{transform:scale(.9)}
.on .swatches{animation:rise .5s var(--ease) backwards;animation-delay:.58s}

/* chrome: progress + controls, sized to the card */
.top{position:fixed;left:50%;transform:translateX(-50%);width:var(--cw);top:calc((100dvh - var(--ch)) / 2);padding:calc(var(--cw)*.035) calc(var(--cw)*.07) 0;z-index:10;color:var(--chrome,#fff);transition:color .3s ease}
.bars{display:flex;gap:4px}
.bars button{flex:1;height:3px;border:0;border-radius:3px;background:currentColor;opacity:.25;padding:0;position:relative}
.bars button::after{content:"";position:absolute;inset:-10px 0}
.bars button.done{opacity:.9}
/* stories-style autoplay (site demo only, ?autoplay): the current bar fills, then the deck moves on */
.auto .bars button.now{opacity:1;background:color-mix(in srgb,currentColor 25%,transparent);overflow:hidden}
.auto .bars button.now::before{content:"";position:absolute;inset:0;border-radius:inherit;background:currentColor;opacity:.9;transform-origin:left;transform:scaleX(0);animation:fill var(--dwell,5s) linear forwards}
.auto.held .bars button.now::before{animation-play-state:paused}
@keyframes fill{to{transform:scaleX(1)}}
.ctl{display:flex;justify-content:space-between;align-items:center;margin-top:12px;font-size:13px;font-weight:500}
.ctl .brand{font-family:var(--display);font-weight:800;font-stretch:120%;font-variation-settings:"wdth" 120;font-size:14px;opacity:.85}
.pills{display:flex;gap:6px}
.pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border:0;border-radius:999px;padding:7px 12px;background:color-mix(in srgb,currentColor 14%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .15s var(--ease),background .2s ease}
@media (hover:hover) and (pointer:fine){.pill:hover{background:color-mix(in srgb,currentColor 22%,transparent)}}
.pill:not(:disabled):active{transform:scale(.96)}
.pill svg{width:14px;height:14px}

/* entrance choreography, replayed on each slide */
.on .lead,.on .after,.on .split,.on .more{animation:rise .5s var(--ease) both}
.on .hero{animation:heroIn .6s var(--spring) both;animation-delay:.08s}
.on .after{animation-delay:.3s}
.on .split,.on .grid4,.on .more{animation:rise .5s var(--ease) both;animation-delay:.38s}
.on .row{animation:rowIn .45s var(--ease) both;animation-delay:calc(.12s + var(--d) * 50ms)}
.on .row::before{animation:grow .6s var(--ease) both;animation-delay:calc(.25s + var(--d) * 50ms)}
.on .bub{animation:pop .45s var(--spring) both}
.on .bub:nth-child(2){animation-delay:.55s}.on .bub:nth-child(3){animation-delay:1.1s}
.on .intro .a1{animation-delay:.9s}.on .intro .a2{animation-delay:1.6s}.on .intro .a3{animation-delay:2.3s}
.on .intro .a4{animation:rise .6s var(--ease) both;animation-delay:2.9s}
.on .stretch span:last-child{animation:stretch 1.4s var(--ease) both}
.on .stretch span:first-child{animation:rise .8s var(--ease) both}
.on .emoji span{animation:pop .5s var(--spring) both;animation-delay:calc(.15s + var(--d) * 60ms)}
.on .dots i{animation:dot .5s var(--ease) both;animation-delay:calc(var(--r, 0) * 45ms)}
.on .moon{animation:moon 1.4s var(--ease) both}
.on .redact i{animation:grow .8s var(--ease) both;transform-origin:left;animation-delay:calc(var(--k, 0) * 60ms)}
.on .chain i{animation:pop .3s var(--spring) both;animation-delay:calc(var(--k, 0) * 12ms)}
.on .spark i{animation:barUp .7s var(--ease) both;transform-origin:bottom;animation-delay:calc(var(--k, 0) * 2ms)}
@keyframes barUp{from{transform:scaleY(0)}}
.on .pile i{animation:pop .35s var(--spring) both;animation-delay:calc(var(--d, 0) * 1ms)}
.on .av{animation:pop .5s var(--spring) both;animation-delay:calc(.08s + var(--i, 0) * 60ms)}
.on .sticker{animation:sticker .8s var(--spring) both}
.on .clock b{animation:hand 1.6s var(--spring) both}
.on .vs div::before{animation:grow .6s var(--ease) both;animation-delay:.3s}
.on .vs div:last-child::before{animation-delay:.38s}
.on .vs div>*{animation:fade .3s var(--ease) both;animation-delay:.5s}
.on .ptitle span:first-child{animation:rise .8s var(--ease) both}
.on .ptitle span:last-child{animation:stretch 1.4s var(--ease) both}
.on .one,.on .stats3,.on .pmeta{animation:rise .5s var(--ease) both;animation-delay:.4s}
.on .cta{animation:rise .5s var(--ease) backwards;animation-delay:.5s}
@keyframes sticker{from{opacity:0;transform:rotate(-40deg) scale(.4)}to{opacity:1;transform:rotate(-8deg)}}
@keyframes hand{from{transform:rotate(180deg)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:var(--o,1);transform:none}}
@keyframes heroIn{from{opacity:0;transform:translateY(24px) scale(.94);filter:blur(6px)}to{opacity:1;transform:none;filter:none}}
@keyframes rowIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.9)}to{opacity:1;transform:none}}
@keyframes stretch{from{font-stretch:50%;font-variation-settings:"wdth" 50;opacity:0}30%{opacity:1}to{font-stretch:150%;font-variation-settings:"wdth" 150}}
@keyframes dot{from{opacity:0;transform:scale(.5)}}
@keyframes fade{from{opacity:0}}
@keyframes moon{from{opacity:0;transform:rotate(-60deg) translateY(1em)}to{opacity:1;transform:rotate(-20deg)}}
.after{--o:.85}

/* saving: freeze everything at its final frame */
.capturing *, .capturing *::before{animation:none !important;transition:none !important}
.card.saving{border-radius:0;box-shadow:none}
.fitting *{animation:none !important}

@media (max-width:540px){
  :root{--cw:100vw;--ch:100dvh}
  .card{border-radius:0;box-shadow:none;padding-top:max(5.4em, calc(env(safe-area-inset-top) + 4.6em));padding-bottom:max(1.3em, env(safe-area-inset-bottom))}
  .top{padding-top:max(10px, env(safe-area-inset-top))}
}
@media (prefers-reduced-motion:reduce){
  *,*::before{animation:none !important;transition-duration:.01s !important}
  .slide,.slide.past{transform:none}
  .slide,.slide.on{transition-duration:.3s,.3s,0s !important}
}
.slide:focus{outline:none}
</style>
</head>
<body>
<div class="top" id="top">
  <nav class="bars" id="bars" aria-label="Slides"></nav>
  <div class="ctl">
    <span class="brand">wrap2026</span>
    <div class="pills">
      <button class="pill" id="save" data-act><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span class="lbl">Save image</span></button>
    </div>
  </div>
</div>
<main class="deck" id="deck">__SLIDES__</main>
<div class="tip" id="tip"></div>
<label id="hapticLbl" style="position:fixed;left:-99px;top:-99px;opacity:0" aria-hidden="true"><input type="checkbox" switch tabindex="-1"></label>

<script>
(() => {
const FILE = '__FILE__';
const deck = document.getElementById('deck');
const slides = [...deck.querySelectorAll('.slide')];
const bars = document.getElementById('bars');
const top = document.getElementById('top');
const dark = new Set(['t-cobalt','t-ink','t-night','t-stage','t-poster-a','t-poster-b']);
// poster palette: a cobalt (default), b ink, c lilac, d pink; ?poster=c previews another
let saved = null; try { saved = localStorage.getItem('wrap-poster'); } catch (_) {}
const POSTER = (location.search.match(/[?&]poster=([a-d])\b/) || [, /^[a-d]$/.test(saved || '') ? saved : 'a'])[1];
const posterSlide = slides.find(s => s.dataset.name === 'summary');
const POSTERS = [['a', 'Cobalt', '#2F4BFF'], ['b', 'Night', '#241038'], ['c', 'Lilac', '#EEE8FF'], ['d', 'Pink', '#FF5FA2']];
function setPoster(p) {
  if (!posterSlide) return;
  POSTERS.forEach(([k]) => posterSlide.classList.toggle('t-poster-' + k, k === p));
  posterSlide.querySelectorAll('.swatches button').forEach(b => b.setAttribute('aria-pressed', b.dataset.p === p));
  if (slides[cur] === posterSlide) {
    top.style.setProperty('--chrome', dark.has('t-poster-' + p) ? '#fff' : '#241038');
    if (phone.matches) themeMeta.content = getComputedStyle(posterSlide).getPropertyValue('--bg').trim();
  }
}
if (posterSlide) {
  posterSlide.classList.add('t-poster-' + POSTER);
  const cta = posterSlide.querySelector('.cta');
  if (cta) {
    const sw = document.createElement('div');
    sw.className = 'swatches chrome'; sw.setAttribute('role', 'group'); sw.setAttribute('aria-label', 'Poster color');
    sw.innerHTML = POSTERS.map(([k, name, c]) => `<button type="button" data-p="${k}" aria-label="${name}" aria-pressed="${k === POSTER}" style="--sw:${c}"></button>`).join('');
    sw.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; e.stopPropagation(); setPoster(b.dataset.p); buzz(); try { localStorage.setItem('wrap-poster', b.dataset.p); } catch (_) {} });
    cta.before(sw);
  }
}
const themeOf = s => [...s.classList].filter(c => c.startsWith('t-'));
let cur = -1;
const themeMeta = document.querySelector('meta[name="theme-color"]'), phone = matchMedia('(max-width:540px)');
// iOS Safari only applies :active (press feedback) on touch when a touchstart listener exists
document.addEventListener('touchstart', () => {}, { passive: true });

// fit text to the card width (numbers and the intro title)
// measures a hidden copy of the parent, so siblings keep their styles and the real element's entrance animation never restarts
function fit(el, max) {
  el.style.fontSize = '';
  const p = el.parentElement, i = [...p.children].indexOf(el), pc = p.cloneNode(true);
  pc.classList.add('fitting'); pc.setAttribute('aria-hidden', 'true'); pc.removeAttribute('id');
  pc.style.cssText += ';position:absolute;visibility:hidden;left:0;top:0;animation:none;width:' + p.clientWidth + 'px';
  p.after(pc);
  const c = pc.children[i];
  c.style.cssText += ';animation:none;display:inline-block;width:max-content';
  const base = parseFloat(getComputedStyle(c).fontSize), w = p.clientWidth * .97;
  const ratio = w / c.getBoundingClientRect().width;
  pc.remove();
  el.style.fontSize = (max ? Math.min(base * ratio, base * max) : Math.min(base, base * ratio)) + 'px';
}
// long names shrink until every word fits and they take at most three lines; they never split mid-word
function fitName(el) {
  el.style.fontSize = '';
  if (/\p{Extended_Pictographic}/u.test(el.textContent)) el.style.lineHeight = '1.08';
  const cs = () => getComputedStyle(el);
  for (let k = 0; k < 16 && (el.scrollWidth > el.clientWidth + 1 || el.offsetHeight > parseFloat(cs().lineHeight) * 3.2); k++)
    el.style.fontSize = parseFloat(cs().fontSize) * .9 + 'px';
}
function fitAll() {
  document.querySelectorAll('.stretch span').forEach(e => fit(e, 3));
  document.querySelectorAll('.hero.fit').forEach(e => fit(e));
  document.querySelectorAll('.ptitle:not(.poster .ptitle)').forEach(e => fit(e, 3));
  document.querySelectorAll('.split b, .grid4 dd, .stats3 dd').forEach(e => fit(e));
  document.querySelectorAll('.hero.name, .hero.diag, .poster .diag-sm').forEach(fitName);
}
document.querySelectorAll('.hero').forEach(h => { if (!h.classList.contains('name') && !h.classList.contains('diag')) h.classList.add('fit'); });
document.querySelectorAll('.redact, .chain, .spark').forEach(p => [...p.children].forEach((c, k) => c.style.setProperty('--k', k)));
document.querySelectorAll('.pile i').forEach(i => i.style.setProperty('--d', Math.round(Math.random() * 900)));
document.querySelectorAll('.stack, .slide .body').forEach(p => p.querySelectorAll(':scope > .av, :scope > .stack > .av').forEach((a, k) => a.style.setProperty('--i', k)));
(document.fonts ? document.fonts.ready : Promise.resolve()).then(fitAll);
if (document.fonts) document.fonts.addEventListener('loadingdone', fitAll);
addEventListener('resize', fitAll);

// dot rows stagger by month
document.querySelectorAll('.mrow').forEach((r, i) => r.querySelectorAll('i').forEach(d => d.style.setProperty('--r', i)));

slides.forEach((s, i) => {
  const b = document.createElement('button');
  b.setAttribute('aria-label', 'Slide ' + (i + 1) + ' of ' + slides.length);
  s.tabIndex = -1; s.setAttribute('aria-label', (i + 1) + ' of ' + slides.length);
  b.addEventListener('click', e => { e.stopPropagation(); go(i); });
  bars.appendChild(b);
});

// haptics: Android vibrate, iOS switch-toggle tick
const hap = document.querySelector('#hapticLbl');
function buzz() {
  if (navigator.vibrate) { navigator.vibrate(8); return; }
  if (matchMedia('(pointer:coarse)').matches) hap.click();
}

// count-up for big numbers
function countUp(el) {
  const to = parseFloat(el.dataset.to), dec = el.dataset.fmt === 'dec', sfx = el.dataset.suffix || '';
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('capturing')) return;
  const t0 = el._run = performance.now(), dur = 1300;
  const fmt = v => (dec ? v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString('en-US')) + sfx;
  (function f(t) {
    if (el._run !== t0) return;
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(2, -10 * p);
    el.textContent = fmt(p >= 1 ? to : to * e);
    if (p < 1 && el.closest('.slide.on')) requestAnimationFrame(f); else el.textContent = fmt(to);
  })(t0);
}

const auto = /[?&]autoplay/.test(location.search) && !matchMedia('(prefers-reduced-motion: reduce)').matches;
function go(i, quiet) {
  if (i < 0 || i >= slides.length || i === cur) return;
  slides.forEach((s, k) => { s.classList.toggle('on', k === i); s.classList.toggle('past', k < i); });
  [...bars.children].forEach((b, k) => { b.classList.toggle('done', auto ? k < i : k <= i); b.classList.toggle('now', auto && k === i); b.setAttribute('aria-current', k === i ? 'step' : 'false'); });
  if (auto) bars.children[i].style.setProperty('--dwell', (/^(intro|summary)$/.test(slides[i].dataset.name) ? 6.5 : 4.5) + 's');
  cur = i;
  const s = slides[i];
  const theme = themeOf(s).pop();
  top.style.setProperty('--chrome', dark.has(theme) ? '#fff' : '#241038');
  if (phone.matches) themeMeta.content = getComputedStyle(s).getPropertyValue('--bg').trim();
  s.querySelectorAll('.count').forEach(countUp);
  if (!quiet) { buzz(); if (!document.activeElement || document.activeElement === document.body || document.activeElement.classList.contains('slide')) s.focus({ preventScroll: true }); }
  try { history.replaceState(null, '', '#' + s.dataset.name); } catch (_) {}
}

// tap left half of the card to go back, right half to go forward; swipe works too
let sx = null, sy = null, st = 0;
deck.addEventListener('pointerdown', e => { sx = e.clientX; sy = e.clientY; st = performance.now(); });
deck.addEventListener('pointerup', e => {
  if (sx === null) return;
  const dx = e.clientX - sx, dy = e.clientY - sy; sx = null;
  if (e.target.closest('button, a')) return;
  if (e.target.closest('.spark[data-c]')) return;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { go(cur + (dx < 0 ? 1 : -1)); return; }
  if (Math.abs(dx) < 8 && Math.abs(dy) < 8 && performance.now() - st < 500) { const r = slides[cur].querySelector('.card').getBoundingClientRect(); go(e.clientX < r.left + r.width / 2 ? cur - 1 : cur + 1); }
});
document.addEventListener('keydown', e => {
  if (['ArrowRight', ' ', 'PageDown'].includes(e.key)) { e.preventDefault(); go(cur + 1); }
  if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); go(cur - 1); }
  if (e.key === 'Home') go(0);
  if (e.key === 'End') go(slides.length - 1);
});

// show all 10
document.querySelectorAll('[data-more]').forEach(b => b.addEventListener('click', e => {
  e.stopPropagation();
  const list = b.closest('.body').querySelector('.rows');
  const all = list.classList.toggle('all');
  b.textContent = all ? 'Show top ' + list.querySelectorAll('.row:not(.extra)').length : 'Show all ' + list.children.length;
  buzz();
}));

// day tooltips
const tip = document.getElementById('tip');
document.querySelectorAll('.dots i[data-tip]').forEach(d => {
  d.addEventListener('pointerenter', e => { if (e.pointerType !== 'mouse') return; const r = d.getBoundingClientRect(); tip.textContent = d.dataset.tip; tip.style.left = (r.left + r.width / 2) + 'px'; tip.style.top = r.top + 'px'; tip.style.opacity = 1; });
  d.addEventListener('pointerleave', () => tip.style.opacity = 0);
});

// day graphs: hover (mouse) or drag (finger) reads one day; at rest the label shows the peak.
// The deck ignores pointerup on a graph, so a scrub never changes slide.
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function dayAt(sp, k, hot) {
  const c = sp._c || (sp._c = sp.dataset.c.split(',').map(Number)), bars = sp.querySelectorAll('i');
  const pk = [...bars].findIndex(b => b.classList.contains('pk'));
  if (k == null) k = pk < 0 ? c.indexOf(Math.max(...c)) : pk;
  let sl = sp.querySelector('.sl');
  if (!sl) { sl = document.createElement('b'); sl.className = 'sl'; sp.appendChild(sl); }
  const d = new Date(+sp.dataset.y, 0, 1 + k), u = sp.dataset.u || 'message';
  sl.textContent = `${MON[d.getMonth()]} ${d.getDate()} · ${c[k].toLocaleString('en-US')} ${c[k] === 1 ? u : u + 's'}`;
  sp.querySelectorAll('i.cur').forEach(b => b.classList.remove('cur'));
  if (hot) bars[k].classList.add('cur');
  sp.classList.toggle('hot', !!hot);
  const w = sl.offsetWidth, x = bars[k].offsetLeft + bars[k].offsetWidth / 2;
  sl.style.transform = `translateX(${Math.max(0, Math.min(sp.clientWidth - w, x - w / 2))}px)`;
}
document.querySelectorAll('.spark[data-c]').forEach(sp => {
  const n = sp.querySelectorAll('i').length;
  const at = e => { const r = sp.getBoundingClientRect(); return Math.max(0, Math.min(n - 1, Math.floor((e.clientX - r.left) / r.width * n))); };
  const rest = () => dayAt(sp);
  sp.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') sp.setPointerCapture(e.pointerId); dayAt(sp, at(e), true); });
  sp.addEventListener('pointermove', e => { if (e.pointerType === 'mouse' || sp.hasPointerCapture(e.pointerId)) dayAt(sp, at(e), true); });
  sp.addEventListener('pointerup', e => { if (e.pointerType !== 'mouse') rest(); });
  sp.addEventListener('pointercancel', rest);
  sp.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') rest(); });
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(rest);
  addEventListener('resize', rest);
});

// summary card tilts toward the pointer
const tilt = document.querySelector('.tilt');
if (tilt && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const card = tilt.querySelector('.card'), sheen = card.querySelector('.sheen');
  tilt.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    card.style.transition = 'transform .08s linear';
    card.style.transform = `rotateY(${(x - .5) * 14}deg) rotateX(${(.5 - y) * 14}deg)`;
    sheen.style.setProperty('--mx', x * 100 + '%'); sheen.style.setProperty('--my', y * 100 + '%');
  });
  tilt.addEventListener('pointerleave', () => { card.style.transition = ''; card.style.transform = ''; });
}

// save or share the current slide as a 1080x1920 image; one action, named for what it does here
const actBtns = [...document.querySelectorAll('[data-act]')];
let canShare = false;
try { canShare = !!(navigator.canShare && navigator.canShare({ files: [new File([''], 'x.png', { type: 'image/png' })] })); } catch (_) {}
const ACT = canShare ? 'Share' : 'Save image';
const label = t => actBtns.forEach(b => b.querySelector('.lbl').textContent = t);
const busy = on => actBtns.forEach(b => b.disabled = on);
if (canShare) actBtns.forEach(b => b.querySelector('path').setAttribute('d', 'M12 15V4M8 8l4-4 4 4M6 12v7h12v-7'));
label(ACT);
let ready = null, resetT = 0;
function flash(t, ms) { label(t); clearTimeout(resetT); resetT = setTimeout(() => { label(ACT); busy(false); }, ms || 1800); }
async function render(s) {
  // capture a clone at a fixed 360x640 so every device gets exactly 1080x1920, final frame, no chrome
  const box = document.createElement('section');
  box.className = themeOf(s).join(' ') + ' capturing';
  box.setAttribute('aria-hidden', 'true');
  box.style.cssText = 'position:fixed;left:-10000px;top:0;--cw:360px;--ch:640px';
  const card = s.querySelector('.card').cloneNode(true);
  card.removeAttribute('id'); card.style.transform = 'none'; card.classList.add('saving');
  card.querySelectorAll('.chrome').forEach(n => n.remove());
  box.appendChild(card); document.body.appendChild(box);
  card.querySelectorAll('.count').forEach(c => c.textContent = (c.dataset.fmt === 'dec' ? (+c.dataset.to).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : (+c.dataset.to).toLocaleString('en-US')) + (c.dataset.suffix || ''));
  card.querySelectorAll('.hero.fit, .split b, .grid4 dd, .stats3 dd').forEach(e => fit(e));
  card.querySelectorAll('.spark[data-c]').forEach(sp => dayAt(sp));
  card.querySelectorAll('.hero.name, .hero.diag, .diag-sm').forEach(fitName);
  card.querySelectorAll('.ptitle:not(.poster .ptitle), .stretch span').forEach(e => fit(e, 3));
  try { return await modernScreenshot.domToBlob(card, { scale: 3, width: 360, height: 640 }); }
  finally { box.remove(); }
}
// The image library is fetched only when you tap Share, never when the wrap opens.
// integrity pins the exact reviewed file: the browser refuses any other copy.
let shotLib = null;
function loadShot() {
  if (window.modernScreenshot) return Promise.resolve();
  return shotLib || (shotLib = new Promise((ok, fail) => {
    const sc = Object.assign(document.createElement('script'), { src: 'https://cdn.jsdelivr.net/npm/modern-screenshot@4.4.39/dist/index.js', integrity: 'sha384-NeS4652m0nhya1JOA13DmKmR24bnK/+kQGMmJ3Ws7qipMG64xmyweG66thRmpU+Y', crossOrigin: 'anonymous' });
    const give = () => { shotLib = null; sc.remove(); fail(new Error('image library unavailable')); };
    const t = setTimeout(give, 10000);
    sc.onload = () => { clearTimeout(t); ok(); };
    sc.onerror = () => { clearTimeout(t); give(); };
    document.head.appendChild(sc);
  }));
}
function download(blob, name) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
actBtns.forEach(btn => btn.addEventListener('click', async e => {
  e.stopPropagation();
  const s = slides[cur], name = `${FILE}_${s.dataset.name}.png`;
  const held = ready && ready.slide === s ? ready.blob : null; ready = null;
  let blob = held;
  if (!blob) {
    label(canShare ? 'Preparing…' : 'Saving…'); busy(true);
    try { await loadShot(); } catch (_) { flash('Offline. Take a screenshot', 2400); return; }
    try { blob = await render(s); } catch (err) { console.error(err); flash('Could not save. Take a screenshot', 2400); return; }
  }
  if (canShare) {
    try {
      await navigator.share({ files: [new File([blob], name, { type: 'image/png' })], text: `My ${document.title} — wrap2026.com` });
      buzz(); label(ACT); busy(false);
    } catch (err) {
      if (err.name === 'AbortError') { label(ACT); busy(false); return; }
      // the share sheet needs a fresh tap after a slow render; keep the image for it
      if (err.name === 'NotAllowedError' && !held) { ready = { slide: s, blob }; label('Tap to share'); busy(false); return; }
      download(blob, name); flash('Saved');
    }
    return;
  }
  download(blob, name); buzz(); flash('Saved');
}));

if (location.search.includes('still')) document.body.classList.add('capturing');
if (auto) {
  document.body.classList.add('auto');
  bars.addEventListener('animationend', e => { if (e.animationName === 'fill') go(cur + 1 < slides.length ? cur + 1 : 0, true); });
  // press and hold pauses, like stories
  deck.addEventListener('pointerdown', () => document.body.classList.add('held'));
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(t => deck.addEventListener(t, () => document.body.classList.remove('held')));
}
const start = slides.findIndex(s => '#' + s.dataset.name === location.hash);
go(start > 0 ? start : 0, true);
})();
</script>
</body></html>'''


def gen_html(d, contacts, path):
    import html as _html
    from datetime import datetime as dt, date as ddate, timedelta

    esc = lambda v: _html.escape(str(v))
    s = d['stats']
    top = d['top']
    n = lambda h: esc(get_name(h, contacts))
    ptype, proast = d['personality']
    year = int(d.get('year', dt.now().year))
    hr = d['hour']
    hr_str = "12AM" if hr == 0 else f"{hr}AM" if hr < 12 else "12PM" if hr == 12 else f"{hr-12}PM"

    now = dt.now()
    if year == now.year:
        days_elapsed = max(1, (now - dt(year, 1, 1)).days)
    else:
        days_elapsed = 366 if year % 4 == 0 else 365
    msgs_per_day = s[0] // days_elapsed

    busiest_top = d.get('busiest_day_top') or []
    if d['busiest_day']:
        bd = dt.strptime(d['busiest_day'][0], '%Y-%m-%d')
        busiest_str = bd.strftime('%b %-d')
        busiest_count = d['busiest_day'][1]
        busiest_mult = busiest_count / max(sum(d['daily_counts'].values()) / days_elapsed, 1e-9)
        busiest_vs = f", {busiest_mult:,.1f}".rstrip('0').rstrip('.') + '× a normal day' if busiest_mult >= 1.5 else ''

    def num(v, fmt='int', suffix=''):
        """Big number that counts up when its slide opens."""
        shown = f"{v:,}" if fmt == 'int' else f"{v:,.1f}"
        return f'<span class="count" data-to="{v}" data-fmt="{fmt}" data-suffix="{esc(suffix)}">{shown}{esc(suffix)}</span>'

    MIN_CONVOS = 10
    def plural(v, one, many=None):
        return one if v == 1 else (many or one + 's')
    def mins(m):
        if m < 1: return "&lt;1 min"
        if m < 60: return f"{round(m)} min"
        return f"{m/60:,.1f} hr"

    def rows(items, hide_after=5):
        """items: list of (label_html, value_html, weight 0..1)"""
        out = []
        for i, (label, value, w) in enumerate(items, 1):
            hidden = ' extra' if i > hide_after else ''
            out.append(f'<li class="row{hidden}" style="--w:{max(0.04, min(1, w)):.3f};--d:{i}"><span class="rk">{i}</span><span class="nm">{label}</span><span class="vl">{value}</span></li>')
        return '<ol class="rows">' + ''.join(out) + '</ol>'

    def avatar_glyph(name):
        """First emoji of a name, or a person silhouette for numbers and symbols."""
        t = str(name).strip()
        if t and ord(t[0]) >= 0x2190 and not t[0].isalnum():
            k = 1
            while k < len(t) and (t[k] in '\u200d\ufe0f' or 0x1F3FB <= ord(t[k]) <= 0x1F3FF or t[k - 1] == '\u200d'):
                k += 1
            return f'<span class="ae">{esc(t[:k])}</span>'
        return '<svg class="ag" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="8" r="4.2"/><path d="M3.5 21a8.5 8.5 0 0 1 17 0z"/></svg>'
    def initials(name):
        parts = [p for p in str(name).replace('+', ' ').split() if p[:1].isalpha()]
        return esc(''.join(p[0] for p in parts[:2]).upper()) if parts else avatar_glyph(name)
    def avatar(name, cls=''):
        return f'<span class="av a{sum(map(ord, str(name))) % 5} {cls}">{initials(name)}</span>'

    def stack(names):
        return '<div class="stack" aria-hidden="true">' + ''.join(avatar(x) for x in names[:5]) + '</div>'

    def more_btn(count, shown=5):
        return f'<button class="more chrome" data-more>Show all {count}</button>' if count > shown else ''

    def slide(theme, body, name):
        return f'<section class="slide t-{theme}" data-name="{name}"><div class="card"><div class="body">{body}</div><footer class="mark"><span>wrap2026.com</span><span>iMessage · {year}</span></footer></div></section>'

    slides = []

    # Intro
    slides.append(slide('cobalt', f'''
        <div class="intro">
          <h1 class="stretch"><span>Wrapped</span><span>{year}</span></h1>
          <div class="thread">
            <div class="bub r a1">you up?</div>
            <div class="bub r a2">I went through your texts.</div>
            <div class="bub r a3">We need to talk about {year}.</div>
          </div>
          <p class="hint chrome a4">Tap to start</p>
        </div>''', 'intro'))

    # Total messages
    per_day = f" That's about {msgs_per_day:,} a day." if msgs_per_day else ''
    slides.append(slide('lilac', f'''
        <div class="pile" aria-hidden="true">{''.join('<i class="s"></i>' if (k * s[1]) % max(s[0],1) < s[1] else '<i></i>' for k in range(min(msgs_per_day, 240)))}</div>
        <p class="lead">This year you sent and received</p>
        <div class="hero">{num(s[0])}</div>
        <p class="after">{plural(s[0], 'message')}.{per_day}</p>
        <div class="split">
          <div><b>{s[1]:,}</b><span>you sent</span></div>
          <div><b>{s[2]:,}</b><span>you got</span></div>
          <div><b>{s[3]:,}</b><span>{plural(s[3], 'person', 'people')}</span></div>
        </div>''', 'total'))

    # Words
    words = d['words']
    pages = max(1, words // 250)
    novels = max(1, round(pages / 300))
    if words: slides.append(slide('white', f'''
        <div class="redact" aria-hidden="true">{''.join(f'<i style="--w:{w}%"></i>' for w in (92, 64, 81, 100, 47, 88, 73, 95, 58, 84, 69))}</div>
        <p class="lead">You typed</p>
        <div class="hero">{num(words)}</div>
        <p class="after">{plural(words, 'word')}. About {pages:,} {plural(pages, 'page')}, or {novels:,} {plural(novels, 'novel')} nobody asked for.</p>''', 'words'))

    # Year in dots: 12 rows (months) x 31 columns (days)
    if d['daily_counts']:
        max_count = max(d['daily_counts'].values()) or 1
        last = now.date() if year == now.year else ddate(year, 12, 31)
        month_rows = []
        for m in range(1, 13):
            cells = []
            for day in range(1, 32):
                try:
                    cur = ddate(year, m, day)
                except ValueError:
                    cells.append('<i class="na"></i>')
                    continue
                if cur > last:
                    cells.append('<i class="fut"></i>')
                    continue
                key = cur.strftime('%Y-%m-%d')
                c = d['daily_counts'].get(key, 0)
                lvl = 0 if c == 0 else 1 if c <= max_count * .15 else 2 if c <= max_count * .35 else 3 if c <= max_count * .65 else 4
                cells.append(f'<i class="l{lvl}" data-tip="{c:,} on {cur.strftime("%b %-d")}"></i>')
            month_rows.append(f'<div class="mrow"><span>{ddate(year, m, 1).strftime("%b")}</span><div class="dots">{"".join(cells)}</div></div>')
        slides.append(slide('ink', f'''
            <p class="lead">Your year, one dot per day.</p>
            <div class="year">{"".join(month_rows)}</div>
            <div class="split">
              <div><b>{d['avg_daily']:,}</b><span>a day, on average</span></div>
              <div><b>{esc(d['busiest_month'])}</b><span>busiest month</span></div>
              <div><b>{d['quiet_days']:,}</b><span>{plural(d['quiet_days'], 'day')} of silence</span></div>
            </div>''', 'year'))

    # Your #1 and inner circle
    if top:
        slides.append(slide('pink', f'''
            {avatar(top[0]["name"], 'xl')}
            <p class="lead">The person you texted most</p>
            <div class="hero name">{esc(top[0]["name"])}</div>
            <p class="after">{num(top[0]["count"])} {plural(top[0]["count"], 'message')}. {(lambda p: f'{p}%' if p else 'Less than 1%')(round(top[0]["count"] / max(s[0], 1) * 100))} of all your messages.</p>''', 'number-one'))
        mx = top[0]['count'] or 1
        slides.append(slide('lilac', f'''
            <div class="stack" aria-hidden="true">{''.join(avatar(c["name"]) for c in top[:5])}</div>
            <p class="lead">Your inner circle</p>
            {rows([(esc(c["name"]), f'{c["count"]:,}', c["count"] / mx) for c in top[:10]])}
            {more_btn(len(top[:10]))}''', 'inner-circle'))

    # Groups
    gs = d['group_stats']
    if gs['count'] > 0 and gs['total'] > 0 and d['group_leaderboard']:
        yours = round(gs['sent'] / max(gs['total'], 1) * 100)
        role = "a lurker" if yours < 40 else "the main character" if yours > 60 else "a solid contributor"
        def gname(gc):
            if isinstance(gc['name'], str):
                return esc(gc['name'])
            names = [n(h[0]) for h in gc['name'][:2]]
            extra = gc['participant_count'] - len(names)
            return ', '.join(f'<bdi>{x}</bdi>' for x in names) + (f" +{extra}" if extra > 0 else '')
        lb = d['group_leaderboard'][:10]
        gmx = lb[0]['msg_count'] if lb else 1
        slides.append(slide('cobalt', f'''
            <div class="stack groups" aria-hidden="true">{''.join(avatar(gname(gc)) for gc in lb[:5])}</div>
            <p class="lead">You were in {num(gs['count'])} {plural(gs['count'], 'group chat')} and sent {yours}% of the messages. You're {role}.</p>
            {rows([(gname(gc), f'{gc["msg_count"]:,}', gc["msg_count"] / gmx) for gc in lb]) if lb else ''}
            {more_btn(len(lb))}''', 'groups'))

    # Personality
    glyph = {'NOCTURNAL': '🌙', 'TERMINALLY': '📱', 'TOO COOL': '🧊', 'POPULAR': '💅', 'YAPPER': '🗣️', 'STARTER': '🎬', 'WAITER': '⏳'}
    g = next((v for k, v in glyph.items() if k in ptype), '🫡')
    slides.append(slide('night', f'''
        <div class="sticker" aria-hidden="true">{g}</div>
        <p class="lead">Diagnosis</p>
        <div class="hero diag">{esc(ptype.lower())}</div>
        <p class="after">{esc(proast[0].upper() + proast[1:])}.</p>''', 'personality'))

    # Who starts
    you_start = d['starter_pct'] > 50
    slides.append(slide('cobalt', f'''
        <div class="thread big">
          <div class="bub {"s" if you_start else "r"}">hey</div>
          <div class="bub {"r" if you_start else "s"}">hey!</div>
        </div>
        <p class="lead">You start</p>
        <div class="hero">{num(d['starter_pct'], 'int', '%')}</div>
        <p class="after">of your conversations. {"Someone has to." if you_start else "You let them come to you."}</p>''', 'starter'))

    # Response time
    r = d['resp']
    verdict = "Basically instant." if r < 2 else "Respectable." if r < 15 else "People have moved on by then."
    slides.append(slide('white', f'''
        <div class="thread"><div class="bub r typing"><i></i><i></i><i></i></div></div>
        <p class="lead">Your typical reply takes</p>
        <div class="hero">{num(round(r * 60)) if r < 1 else num(round(r))}<small>{"sec" if r < 1 else "min"}</small></div>
        <p class="after">{verdict} Half your replies are faster than that.</p>''', 'response'))

    # Peak hours
    peak_day = f'<p class="after">on {esc(d["day"])}s.</p>' if d.get('day') not in (None, '', '???') else ''
    slides.append(slide('night', f'''
        <div class="clock" style="--a:{(hr % 12) * 30 + 0}deg" aria-hidden="true">{''.join(f'<i style="--t:{k*30}deg"></i>' for k in range(12))}<b></b><u></u></div>
        <p class="lead">You text most at</p>
        <div class="hero">{hr_str}</div>
        {peak_day}''', 'peak'))

    # Streak + marathon
    streak = d['streak'] if d.get('streak') and d['streak']['length'] > 1 else None
    if streak or d.get('marathon'):
        parts = []
        if streak:
            st = streak
            parts.append(f'''<div class="duo"><div class="hero sm">{num(st['length'])}</div><p class="after">days in a row with <b>{n(st['handle'])}</b>, {st['start'].strftime('%b %-d')} to {st['end'].strftime('%b %-d')}.</p></div>''')
        if d.get('marathon'):
            mm = d['marathon']
            mdate = dt.strptime(mm['date'], '%Y-%m-%d').strftime('%b %-d')
            over = f", over {mm['hours']:,} {plural(mm['hours'], 'hour')}" if mm['hours'] >= 1 else ''
            parts.append(f'''<div class="duo"><div class="hero sm">{num(mm['count'])}</div><p class="after">{plural(mm['count'], 'message')} with <b>{n(mm['handle'])}</b> on {mdate}{over}.</p></div>''')
        chain = ''
        if streak:
            chain = '<div class="chain" aria-hidden="true">' + '<i></i>' * min(streak['length'], 120) + '</div>'
        slides.append(slide('lilac', chain + '<p class="lead">Your longest runs</p>' + ''.join(parts), 'streaks'))

    # 3am bestie
    if d['late']:
        ln = d['late'][0]
        slides.append(slide('night', f'''
            <div class="moon" aria-hidden="true"></div>
            <div class="stars" aria-hidden="true">{''.join(f'<i style="left:{x}%;top:{y}%;--d:{k}"></i>' for k, (x, y) in enumerate([(8, 14), (30, 30), (52, 9), (18, 44), (66, 36), (40, 52), (84, 54), (12, 62)]))}</div>
            <p class="lead">Between midnight and 5am, you texted</p>
            <div class="hero name">{n(ln[0])}</div>
            <p class="after">{num(ln[1])} {plural(ln[1], 'time')}. Go to sleep.</p>''', 'three-am'))

    # Busiest day
    if d['busiest_day']:
        bmx = busiest_top[0][1] if busiest_top else 1
        spark = ''
        if d['daily_counts']:
            dc = d['daily_counts']; peak = max(dc.values()) or 1
            last = now.date() if year == now.year else ddate(year, 12, 31)
            days = [ddate(year, 1, 1) + timedelta(days=k) for k in range((last - ddate(year, 1, 1)).days + 1)]
            bars = ''.join(f'<i class="{"pk" if x.isoformat() == d["busiest_day"][0] else ""}" style="--h:{max(2, dc.get(x.isoformat(), 0) / peak * 100):.1f}%"></i>' for x in days)
            spark = f'<div class="spark" aria-hidden="true" data-y="{year}" data-c="{",".join(str(dc.get(x.isoformat(), 0)) for x in days)}">{bars}</div>'
        slides.append(slide('pink', f'''
            {spark}
            <p class="lead">Your most unhinged day</p>
            <div class="hero">{busiest_str}</div>
            <p class="after">{num(busiest_count)} {plural(busiest_count, 'message')}{busiest_vs}. What happened?</p>
            {rows([(n(h), f'{c:,}', c / bmx) for h, c in busiest_top[:10]], 3) if busiest_top else ''}
            {more_btn(len(busiest_top[:10]), 3)}''', 'busiest-day'))

    # Biggest fan / down bad
    if d['fan']:
        f = d['fan'][0]
        slides.append(slide('cobalt', f'''
            {avatar(get_name(f[0], contacts), 'xl')}
            <p class="lead">Your biggest fan</p>
            <div class="hero name">{n(f[0])}</div>
            <p class="after">texts you {num(round(f[1]/f[2], 1), 'dec', '×')} more than you text them.</p>
            <div class="vs"><div style="--w:1"><span>{n(f[0])}</span><b>{f[1]:,}</b></div><div style="--w:{f[2]/max(f[1],1):.3f}"><span>You</span><b>{f[2]:,}</b></div></div>''', 'biggest-fan'))
    if d['simp']:
        si = d['simp'][0]
        slides.append(slide('pink', f'''
            {avatar(get_name(si[0], contacts), 'xl')}
            <p class="lead">You're down bad for</p>
            <div class="hero name">{n(si[0])}</div>
            <p class="after">You text them {num(round(si[1]/si[2], 1), 'dec', '×')} more than they text you.</p>
            <div class="vs"><div style="--w:1"><span>You</span><b>{si[1]:,}</b></div><div style="--w:{si[2]/max(si[1],1):.3f}"><span>{n(si[0])}</span><b>{si[2]:,}</b></div></div>''', 'down-bad'))

    # Reply speed lists
    if d.get('priority_list'):
        pl = d['priority_list'][:5]
        slides.append(slide('white', f'''
            {stack([get_name(h, contacts) for h, _, _ in pl])}
            <p class="lead">You reply fastest to</p>
            {rows([(n(h), mins(t), 1 - i / 6) for i, (h, t, _) in enumerate(pl)])}
            <p class="after">They get the instant reply. Everyone else waits.</p>''', 'priority'))
    if d.get('fast_responders'):
        fr = d['fast_responders'][:5]
        slides.append(slide('lilac', f'''
            {stack([get_name(h, contacts) for h, _, _ in fr])}
            <p class="lead">These people drop everything for you</p>
            {rows([(n(h), mins(t), 1 - i / 6) for i, (h, t, _) in enumerate(fr)])}
            <p class="after">Their typical reply time. You're a priority.</p>''', 'fast-responders'))

    # Who reaches out
    if d.get('initiation_breakdown'):
        ib = d['initiation_breakdown']
        pct_desc = lambda xs: sorted(xs, key=lambda x: x[1] / x[2], reverse=True)
        # 10+ conversations so a percentage means something; unsaved numbers are mostly automated senders
        ok = [(h, y, t, tc) for h, y, t, tc in ib if tc >= MIN_CONVOS and not re.fullmatch(r'[+\d\s().-]+', get_name(h, contacts))]
        you_out = pct_desc([(h, y, tc) for h, y, t, tc in ok if y / tc > 0.7][:5])
        they_in = pct_desc([(h, t, tc) for h, y, t, tc in ok if t / tc > 0.7][:5])
        you_out, they_in = (you_out if len(you_out) > 1 else []), (they_in if len(they_in) > 1 else [])
        if you_out or they_in:
            tight = lambda r: r.replace('class="rows"', 'class="rows tight"', 1)
            body = '<div class="thread big"><div class="bub s">hey</div><div class="bub s">you there?</div><div class="bub s">hello??</div></div>' if len(you_out) + len(they_in) <= 6 else ''
            if you_out:
                body += '<p class="lead">You usually text first</p>' + tight(rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in you_out]))
            if they_in:
                body += '<p class="lead gap">They usually text first</p>' + tight(rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in they_in]))
            slides.append(slide('cobalt', body, 'who-reaches-out'))

    # Heating up / ghosted
    if d.get('heating'):
        ht = d['heating'][:5]
        hmx = max((b - a) for _, a, b in ht) or 1
        slides.append(slide('pink', f'''
            <div class="sticker" aria-hidden="true">🔥</div>
            <p class="lead">Heating up since June</p>
            {rows([(n(h), f'+{b-a:,}', (b - a) / hmx) for h, a, b in ht])}
            <p class="after">Extra messages since June, compared to before.</p>''', 'heating-up'))
    if d.get('ghosted'):
        gh = d['ghosted'][:5]
        gmx2 = max(b for _, b, _ in gh) or 1
        slides.append(slide('lav', f'''
            <div class="sticker" aria-hidden="true">👻</div>
            <p class="lead">They went quiet after June</p>
            {rows([(n(h), f'{b:,} <i>to</i> {a:,}', b / gmx2) for h, b, a in gh])}
            <p class="after">Their messages to you, before June and after.</p>''', 'ghosted'))

    # Emoji
    if d['emoji'] and any(e[1] > 0 for e in d['emoji']):
        em = [e for e in d['emoji'] if e[1] > 0]
        spans = ''.join(f'<span style="--d:{i}">{esc(e[0])}</span>' for i, e in enumerate(em[1:]))
        emoji_row = f'<div class="emoji">{spans}</div>' if spans else ''
        slides.append(slide('white', f'''
            <div class="sticker big" aria-hidden="true">{esc(em[0][0])}</div>
            <p class="lead">Your emotional range</p>
            {emoji_row}
            <p class="after">{esc(em[0][0])} alone: {em[0][1]:,} {plural(em[0][1], 'time')}.</p>''', 'emoji'))

    # Summary: the poster people post
    wave = spark.replace('class="spark"', 'class="spark pwave"', 1) if d['busiest_day'] else ''
    one = f'<div class="one">{avatar(top[0]["name"])}<div><b>{esc(top[0]["name"])}</b><span>My #1, {top[0]["count"]:,} {plural(top[0]["count"], "message")}</span></div></div>' if top else ''
    slides.append(f'''
    <section class="slide t-stage" data-name="summary">
      <div class="tilt">
        <div class="card summary poster" id="summaryCard">
          <div class="sheen" aria-hidden="true"></div>
          <div class="body">
            <h2 class="ptitle"><span>Wrapped</span> <span>{year}</span></h2>
            {wave}
            <div class="hero">{s[0]:,}<small>{plural(s[0], 'message')}</small></div>
            <p class="diag-sm">{esc(ptype.lower())}</p>
            {one}
            <dl class="stats3">
              <div><dt>People</dt><dd>{s[3]:,}</dd></div>
              <div><dt>I text first</dt><dd>{d['starter_pct']}%</dd></div>
              <div><dt>Typical reply</dt><dd>{mins(d['resp'])}</dd></div>
            </dl>
            <button class="cta chrome" data-act><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span class="lbl">Save image</span></button>
          </div>
          <footer class="mark"><span>wrap2026.com</span><span>iMessage · {year}</span></footer>
        </div>
      </div>
    </section>''')

    html_out = TEMPLATE.replace('__TITLE__', f'iMessage Wrapped {year}') \
                       .replace('__FILE__', f'imessage_wrapped_{year}') \
                       .replace('__SLIDES__', ''.join(slides))
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html_out)
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default=None)
    parser.add_argument('--use-2025', action='store_true')
    args = parser.parse_args()

    print("\n" + "="*50)
    print("  iMessage WRAPPED 2026 | wrap2026.com")
    print("="*50 + "\n")

    print("[*] Checking access...")
    check_access()
    print("    ✓ OK")

    print("[*] Loading contacts...")
    contacts = extract_contacts()
    print(f"    ✓ {len(contacts)} indexed")

    ts_start, ts_end, ts_jun = (TS_2025, TS_2025_END, TS_JUN_2025) if args.use_2025 else (TS_2026, TS_2026_END, TS_JUN_2026)
    year = "2025" if args.use_2025 else "2026"

    test = q(f"SELECT COUNT(*) FROM message WHERE (date/1000000000+978307200)>{TS_2026}")[0][0]
    if test < 100 and not args.use_2025:
        print(f"    ⚠️  {test} msgs in 2026, using 2025")
        ts_start, ts_end, ts_jun = TS_2025, TS_2025_END, TS_JUN_2025
        year = "2025"

    # Set output filename based on year
    output_file = args.output or f'imessage_wrapped_{year}.html'

    spinner = Spinner()

    print(f"[*] Analyzing {year}...")
    spinner.start("Reading message database...")
    data = analyze(ts_start, ts_end, ts_jun, contacts)
    data['year'] = int(year)  # Pass the year to gen_html
    spinner.stop(f"{data['stats'][0]:,} messages analyzed")

    print("[*] Generating report...")
    spinner.start("Building your wrapped...")
    gen_html(data, contacts, output_file)
    spinner.stop(f"Saved to {output_file}")
    
    subprocess.run(['open', output_file])
    print("\n  Done! Click through your wrapped.\n  It has your contacts' names: share slides, not the file.\n")

if __name__ == '__main__':
    main()
