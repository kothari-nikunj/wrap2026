#!/usr/bin/env python3
"""
WhatsApp Wrapped 2026 - Your texting habits, exposed.
Usage: python3 whatsapp_wrapped.py
"""

import argparse, os, plistlib, re, sqlite3, subprocess, sys, threading, time
from datetime import datetime

# WhatsApp database locations (try in order)
WHATSAPP_PATHS = [
    os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/com.whatsapp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/desktop.WhatsApp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
]

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

# Timestamps: Apple Cocoa Core Data Time (seconds since Jan 1, 2001)
# Add 978307200 to convert to Unix timestamp
COCOA_OFFSET = 978307200

def _local_ts(y, m=1, d=1):
    """Cocoa time of local midnight. The stats bucket days and hours in local time, so the year must too."""
    return int(datetime(y, m, d).timestamp()) - COCOA_OFFSET

TS_2026, TS_JUN_2026, TS_2026_END = _local_ts(2026), _local_ts(2026, 6), _local_ts(2027) - 1
TS_2025, TS_JUN_2025, TS_2025_END = _local_ts(2025), _local_ts(2025, 6), _local_ts(2026) - 1

WHATSAPP_DB = None

def find_database():
    """Find the WhatsApp database path."""
    for path in WHATSAPP_PATHS:
        if os.path.exists(path):
            return path
    return None

def extract_contacts():
    """Extract contact names from WhatsApp's ZWAPROFILEPUSHNAME table."""
    contacts = {}
    try:
        conn = sqlite3.connect(WHATSAPP_DB)
        for row in conn.execute("SELECT ZJID, ZPUSHNAME FROM ZWAPROFILEPUSHNAME WHERE ZPUSHNAME IS NOT NULL"):
            jid, name = row
            if jid and name:
                contacts[jid] = name
        conn.close()
    except Exception:
        pass
    return contacts

def get_name(jid, contacts):
    """Get display name for a WhatsApp JID."""
    if not jid:
        return "Unknown"
    # Check contacts first
    if jid in contacts:
        return contacts[jid]
    # Extract phone number from JID (format: 1234567890@s.whatsapp.net)
    if '@' in jid:
        phone = jid.split('@')[0]
        # Format as phone number
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone.startswith('1'):
            return f"+1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        return f"+{phone}"
    return jid

NEW_MIN, HISTORY_MONTHS = 10, 6

def group_people(rows, key_label):
    """1:1 rows (handle, this year, last year, before this year) -> {contact key: [label, this, last, before]}"""
    people = {}
    for h, this, last, before in rows:
        key, label = key_label(h)
        p = people.setdefault(key, [label, 0, 0, 0])
        p[1] += this or 0; p[2] += last or 0; p[3] += before or 0
    return people

def find_newcomer(people, history_ok):
    """New = no 1:1 before this year. None when last year's history is too thin to tell, or nobody is new."""
    if not history_ok: return None
    regulars = [p for p in people.values() if p[1] >= NEW_MIN]
    new = sorted((p for p in regulars if not p[3]), key=lambda p: (-p[1], p[0]))
    if not new: return None
    return {'name': new[0][0], 'count': new[0][1], 'new': len(new), 'kept': sum(1 for p in regulars if p[2])}

def check_access():
    global WHATSAPP_DB
    WHATSAPP_DB = find_database()

    if not WHATSAPP_DB:
        print("\n[FATAL] WhatsApp database not found.")
        print("   Make sure WhatsApp is installed and you've sent/received messages.")
        print("\n   Expected locations:")
        for path in WHATSAPP_PATHS:
            print(f"   - {path}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(WHATSAPP_DB)
        conn.execute("SELECT 1 FROM ZWAMESSAGE LIMIT 1")
        conn.close()
    except Exception:
        print("\n[!] ACCESS DENIED")
        print("   System Settings -> Privacy & Security -> Full Disk Access -> turn on the app running this (Terminal, iTerm, Ghostty, Codex), then reopen it")
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
        conn = sqlite3.connect(f"file:{os.path.expanduser('~/Library/Messages/chat.db')}?mode=ro", uri=True)
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
    conn = _connect(WHATSAPP_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def analyze(ts_start, ts_end, ts_jun, contacts):
    d = {}
    load_own_imessage(); load_own_whatsapp()

    # WhatsApp schema:
    # ZWAMESSAGE: ZTEXT, ZISFROMME (0=received, 1=sent), ZMESSAGEDATE, ZCHATSESSION
    # ZWACHATSESSION: Z_PK, ZCONTACTJID, ZSESSIONTYPE (0=DM, 1=group, 2=broadcast), ZPARTNERNAME
    # ZWAPROFILEPUSHNAME: ZJID, ZPUSHNAME (contact names)

    # CTE for 1:1 chats (ZSESSIONTYPE = 0)
    one_on_one_cte = """
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        )
    """

    # Stats: total, sent, received, unique contacts (1:1 only)
    raw_stats = q(f"""{one_on_one_cte}
        SELECT COUNT(*), SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END), COUNT(DISTINCT dm.ZCONTACTJID)
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
    """)[0]
    # People (grouped by name, so a number and a @lid id of one person count once) and newcomers
    ts_prev = _local_ts(datetime.fromtimestamp(ts_start + COCOA_OFFSET).year - 1)
    people = group_people(q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, SUM(m.ZMESSAGEDATE>{ts_start}), SUM(m.ZMESSAGEDATE>={ts_prev} AND m.ZMESSAGEDATE<{ts_start}), SUM(m.ZMESSAGEDATE<{ts_start})
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID
    """), lambda j: (get_name(j, contacts),) * 2)
    d['stats'] = (raw_stats[0] or 0, raw_stats[1] or 0, raw_stats[2] or 0, sum(1 for p in people.values() if p[1]))
    months = q(f"""{one_on_one_cte}
        SELECT COUNT(DISTINCT strftime('%m',datetime(m.ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')))
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>={ts_prev} AND m.ZMESSAGEDATE<{ts_start}
    """)[0][0]
    d['newcomer'] = find_newcomer(people, months >= HISTORY_MONTHS)

    # Top contacts (1:1 only)
    d['top'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, COUNT(*) t, SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END)
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID ORDER BY t DESC LIMIT 20
    """)

    # Late night texters (1:1 only) - messages between midnight and 5am
    d['late'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, COUNT(*) n FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        AND CAST(strftime('%H',datetime(m.ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')) AS INT)<5
        GROUP BY dm.ZCONTACTJID HAVING n>5 ORDER BY n DESC LIMIT 5
    """)

    # Peak hour
    r = q(f"SELECT CAST(strftime('%H',datetime(ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')) AS INT) h, COUNT(*) c FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end} GROUP BY h ORDER BY c DESC LIMIT 1")
    d['hour'] = r[0][0] if r else 12

    # Peak day
    days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    r = q(f"SELECT CAST(strftime('%w',datetime(ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')) AS INT) d, COUNT(*) FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end} GROUP BY d ORDER BY 2 DESC LIMIT 1")
    d['day'] = days[r[0][0]] if r else '???'

    # Ghosted (1:1 only) - people who texted before June but not after
    d['ghosted'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, SUM(CASE WHEN m.ZISFROMME=0 AND m.ZMESSAGEDATE<{ts_jun} THEN 1 ELSE 0 END) b, SUM(CASE WHEN m.ZISFROMME=0 AND m.ZMESSAGEDATE>={ts_jun} THEN 1 ELSE 0 END) a
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID HAVING b>10 AND a<3 ORDER BY b DESC LIMIT 5
    """)

    # Heating up (1:1 only) - relationships growing in H2
    d['heating'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, SUM(CASE WHEN m.ZMESSAGEDATE<{ts_jun} THEN 1 ELSE 0 END) h1, SUM(CASE WHEN m.ZMESSAGEDATE>={ts_jun} THEN 1 ELSE 0 END) h2
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID HAVING h1>20 AND h2>h1*1.5 ORDER BY (h2-h1) DESC LIMIT 5
    """)

    # Biggest fan (1:1 only) - people who text you way more than you text them
    d['fan'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END) t, SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END) y
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID HAVING t>y*2 AND y>0 AND (t+y)>100 ORDER BY (t*1.0/NULLIF(y,0)) DESC LIMIT 5
    """)

    # Simp (1:1 only) - people you text way more than they text you
    d['simp'] = q(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END) y, SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END) t
        FROM ZWAMESSAGE m
        JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY dm.ZCONTACTJID HAVING y>t*2 AND t>0 AND (t+y)>100 ORDER BY (y*1.0/NULLIF(t,0)) DESC LIMIT 5
    """)

    # Response time (1:1 only)
    r = q(f"""
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        ),
        g AS (
            SELECT m.ZMESSAGEDATE ts, m.ZISFROMME, m.ZCHATSESSION,
                   LAG(m.ZMESSAGEDATE) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pt,
                   LAG(m.ZISFROMME) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pf
            FROM ZWAMESSAGE m
            JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        )
        SELECT MEDIAN(ts-pt)/60.0 FROM g
        WHERE ZISFROMME=1 AND pf=0 AND (ts-pt)<86400 AND (ts-pt)>10
    """)
    d['resp'] = round(r[0][0], 1) if r[0][0] is not None else 30

    # Per-person response time: who you reply to fastest (YOUR PRIORITY LIST)
    d['priority_list'] = q(f"""
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        ),
        response_pairs AS (
            SELECT dm.ZCONTACTJID,
                   m.ZMESSAGEDATE ts,
                   m.ZISFROMME,
                   LAG(m.ZMESSAGEDATE) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pt,
                   LAG(m.ZISFROMME) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pf
            FROM ZWAMESSAGE m
            JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE > {ts_start} AND m.ZMESSAGEDATE < {ts_end}
        )
        SELECT ZCONTACTJID, MEDIAN(ts - pt)/60.0 as avg_resp_min, COUNT(*) as reply_count
        FROM response_pairs
        WHERE ZISFROMME = 1 AND pf = 0
        AND (ts - pt) BETWEEN 10 AND 86400
        GROUP BY ZCONTACTJID
        HAVING reply_count >= 50
        ORDER BY avg_resp_min ASC
        LIMIT 5
    """)

    # Per-person response time: who replies to YOU fastest (WHO DROPS EVERYTHING)
    d['fast_responders'] = q(f"""
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        ),
        response_pairs AS (
            SELECT dm.ZCONTACTJID,
                   m.ZMESSAGEDATE ts,
                   m.ZISFROMME,
                   LAG(m.ZMESSAGEDATE) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pt,
                   LAG(m.ZISFROMME) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) pf
            FROM ZWAMESSAGE m
            JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE > {ts_start} AND m.ZMESSAGEDATE < {ts_end}
        )
        SELECT ZCONTACTJID, MEDIAN(ts - pt)/60.0 as avg_resp_min, COUNT(*) as reply_count
        FROM response_pairs
        WHERE ZISFROMME = 0 AND pf = 1
        AND (ts - pt) BETWEEN 10 AND 86400
        GROUP BY ZCONTACTJID
        HAVING reply_count >= 50
        ORDER BY avg_resp_min ASC
        LIMIT 5
    """)

    # Per-person initiation breakdown (WHO TEXTS FIRST per person)
    d['initiation_breakdown'] = q(f"""
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        ),
        conversation_starts AS (
            SELECT dm.ZCONTACTJID, m.ZISFROMME,
                   m.ZMESSAGEDATE ts,
                   LAG(m.ZMESSAGEDATE) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) prev_ts
            FROM ZWAMESSAGE m
            JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE > {ts_start} AND m.ZMESSAGEDATE < {ts_end}
        )
        SELECT ZCONTACTJID,
               SUM(CASE WHEN ZISFROMME = 1 THEN 1 ELSE 0 END) as you_started,
               SUM(CASE WHEN ZISFROMME = 0 THEN 1 ELSE 0 END) as they_started,
               COUNT(*) as total_convos
        FROM conversation_starts
        WHERE prev_ts IS NULL OR (ts - prev_ts) > 14400
        GROUP BY ZCONTACTJID
        HAVING total_convos >= 5
        ORDER BY total_convos DESC
        LIMIT 60
    """)

    # Emoji usage (batch query)
    emojis = ['😂','❤️','😭','🔥','💀','✨','🙏','👀','💯','😈']
    emoji_cases = ', '.join([f"SUM(CASE WHEN ZTEXT LIKE '%{e}%' THEN 1 ELSE 0 END)" for e in emojis])
    r = q(f"SELECT {emoji_cases} FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end} AND ZISFROMME=1")
    counts = {e: c or 0 for e, c in zip(emojis, r[0])} if r else {e: 0 for e in emojis}
    d['emoji'] = sorted(counts.items(), key=lambda x:-x[1])[:5]

    # Total words sent
    r = q(f"""
        SELECT
            COUNT(*) as msg_count,
            COALESCE(SUM(LENGTH(ZTEXT) - LENGTH(REPLACE(ZTEXT, ' ', ''))), 0) as extra_words
        FROM ZWAMESSAGE
        WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end}
        AND ZISFROMME=1
        AND ZTEXT IS NOT NULL
        AND LENGTH(ZTEXT) > 0
    """)
    msg_count = r[0][0] or 0
    extra_words = r[0][1] or 0
    d['words'] = msg_count + extra_words

    # Busiest day
    r = q(f"SELECT DATE(datetime(ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')) d, COUNT(*) c FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end} GROUP BY d ORDER BY c DESC LIMIT 1")
    if r:
        d['busiest_day'] = (r[0][0], r[0][1])
    else:
        d['busiest_day'] = None

    # Conversation starter % (1:1 only)
    r = q(f"""
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND NOT is_own(ZCONTACTJID)
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION
            FROM ZWAMESSAGE m
            JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        ),
        convos AS (
            SELECT m.ZISFROMME,
                   m.ZMESSAGEDATE as ts,
                   LAG(m.ZMESSAGEDATE) OVER (PARTITION BY m.ZCHATSESSION ORDER BY m.ZMESSAGEDATE) as prev_ts
            FROM ZWAMESSAGE m
            JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        )
        SELECT
            SUM(CASE WHEN ZISFROMME=1 THEN 1 ELSE 0 END) as you_started,
            COUNT(*) as total
        FROM convos
        WHERE prev_ts IS NULL OR (ts - prev_ts) > 14400
    """)
    if r and r[0][1] and r[0][1] > 0:
        you_started = r[0][0] or 0
        d['starter_pct'] = round((you_started / r[0][1]) * 100)
    else:
        d['starter_pct'] = 50

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
        SELECT DATE(datetime(ZMESSAGEDATE+{COCOA_OFFSET},'unixepoch','localtime')) as d, COUNT(*) as c
        FROM ZWAMESSAGE
        WHERE ZMESSAGEDATE>{ts_start} AND ZMESSAGEDATE<{ts_end}
        GROUP BY d
        ORDER BY d
    """)
    d['daily_counts'] = {row[0]: row[1] for row in daily_counts}

    # Calculate streaks and stats
    from datetime import datetime as dt
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
    group_chat_cte = """
        WITH group_sessions AS (
            SELECT Z_PK FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 1
        ),
        group_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION
            FROM ZWAMESSAGE m
            JOIN group_sessions s ON m.ZCHATSESSION = s.Z_PK
        )
    """

    # Group chat overview
    r = q(f"""{group_chat_cte}
        SELECT
            (SELECT COUNT(DISTINCT gm.ZCHATSESSION) FROM group_messages gm
             JOIN ZWAMESSAGE m ON m.Z_PK = gm.msg_id
             WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}) as group_count,
            COUNT(*) as total_msgs,
            SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END) as sent
        FROM ZWAMESSAGE m
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        AND m.Z_PK IN (SELECT msg_id FROM group_messages)
    """)
    if r and r[0][0]:
        d['group_stats'] = {
            'count': r[0][0] or 0,
            'total': r[0][1] or 0,
            'sent': r[0][2] or 0
        }
    else:
        d['group_stats'] = {'count': 0, 'total': 0, 'sent': 0}

    # Group chat leaderboard
    r = q(f"""
        WITH group_sessions AS (
            SELECT Z_PK, ZPARTNERNAME FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 1
        )
        SELECT
            s.Z_PK as chat_id,
            s.ZPARTNERNAME as name,
            COUNT(*) as msg_count
        FROM ZWAMESSAGE m
        JOIN group_sessions s ON m.ZCHATSESSION = s.Z_PK
        WHERE m.ZMESSAGEDATE>{ts_start} AND m.ZMESSAGEDATE<{ts_end}
        GROUP BY s.Z_PK
        ORDER BY msg_count DESC
        LIMIT 5
    """)
    d['group_leaderboard'] = []
    for row in r:
        chat_id, name, msg_count = row
        d['group_leaderboard'].append({
            'chat_id': chat_id,
            'name': name or "Unnamed Group",
            'msg_count': msg_count
        })

    return d

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="theme-color" content="#160A26">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect x='4' y='10' width='56' height='40' rx='20' fill='%232F4BFF'/><path d='M14 44 L8 58 L26 48Z' fill='%232F4BFF'/></svg>">
<!-- This page is one self-contained file. The policy below makes the browser block every network request from it. -->
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src data: blob:">
<style>
/* Fonts are embedded as data, not loaded from a font service: Anybody and Onest, SIL Open Font License 1.1. */
/* fonts:begin */
/* anybody-latin-ext.woff2 */
@font-face{font-family:'Anybody';font-style:normal;font-weight:400 900;font-stretch:50% 150%;font-display:swap;unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF;src:url("data:font/woff2;base64,\
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\
M+Xh8pqJeflMBNWmF1EQkTHZMvWvOhTJM7UzI0ovpZcydV48+okKdm6otKp4Vf3CmGoghuLSjxkZkxQzuJS/1LeMjZ0Ym7nCubwZ\
t2qlZ2U5Dl/f4ol6OnpOeol6FXrPjsgcMT3ym6EyDzKdmYnMMuYwc0P/sUGjwV2D54ZEQwPDUMM8wz7DJcMvmaJGlkaBxtbGIcZV\
xjPG/2bVmYyabJmiTWWmVqZBptlm7WbTZr9yyebG5v7m6eYt5hPmLyygxX3LNKtTVtFWhVZDVmtWOllQRVXzqhm1tnVy2sy039Qr\
ajG4ckxxLCd9AVgLjoD9EO34dugm9AwGTzRO7IOn4QmEeLJ1MjlrStYq5CNKPdU7lZ49LXsF2oDeRLc1SjaLYfG2lblL9bMG1Hi0\
bDSD29YiW4D1jv22w39MtJer1/HrRE/+9trgJffJjgU70v1r+3f3n+3/yNOn8u/6paf/8Sl2dd+V2HV995vP/rtnwp7+/X96/uje\
qr0nbszf95UX37z446XPL/28J2jWuwkAZwdADAXIHAD4WAKq8ZupH6XWUo/RPx9nR8CdQBDVJEQCAA/8t0EAWrkikGJyXJbK5TRn\
YasznFH0jO5OU2wpWWDHF/FHZa5WxijeFMPIIF32TicjzuZlwwvFlkKH62+sNjN7HsO0Od9X5YJJ5/hddNCpBox5xriECXcq9O0G\
rzjhbH6XpZeG+ERzPkTD+aoEi/zBHB1JXoa+G47UI1uhj9l8aswiwfz/mI/V1OBXDFkS6fdcD0SMa9nKkDMt0VayzrRwmUoghbBg\
QW8kmI23dBApruxdp3HzDfMCIlp5ZAJnfYE/lRdPJsJiy/ihhY4dXENkoGaQgARjFZcCQgNYUv+70lDd9nMlYkQ4M67Zr+YbGzir\
LyST7rslRM8DyEOeIDAjEXjJbiGiI0GtkILQ7bUvoxNJFHA2dn82NjZO9hRBhKxYb1wbPwkZpHlOTjS+ZA4gdTolPSXTawxO2DP0\
bPscf/g9PrR8wGIQFgBLVgnO3B5FJqH+IBAeIrVXya4RSHpZ6+bJONHfXhpySion7iTV0V5cYCVnfgvhUwsC+8rAcNJLUoKbIjRA\
YhGxAH1tRsbBgYBRaAqhpREZQINFQtkQCs6gmq3NP64IsnL5Kp+Jk7Vk5x+2/+01zjYbwEiWadLklWe3vfIaeIAPLy7qOziuXYfP\
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") format('woff2')}
/* anybody-latin.woff2 */
@font-face{font-family:'Anybody';font-style:normal;font-weight:400 900;font-stretch:50% 150%;font-display:swap;unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;src:url("data:font/woff2;base64,\
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\
kk0HZuyLqUIRAA==") format('woff2')}
/* onest-latin-ext.woff2 */
@font-face{font-family:'Onest';font-style:normal;font-weight:400 600;font-display:swap;unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF;src:url("data:font/woff2;base64,\
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\
Pz6BrFZIthAeN7r7DVXLT0GGCNKx6YR6tXqoXsg46I5qPasQqWVYyOdNFtnKEGb9GUxZVXYou1zHqoY/giyRUo/8K1pDsT3ODDkW\
ocIhNDnSii5ui9WU6PNR5QtSCggzOkHL9rEltKY+9pCNbmeIJ8qndC0+FG4zN9xEDRiMAyjQq3NZhimXN4r5+dypw8anFTXt4MUN\
oY/zrrsIcF1SlI1im4thOC0/ujvjg+tiLpeCTyNIQVit7dBAaonACJsBvhWB2PEOxUhHZ9Ipz/LHV/wnxsYgJCQm7MHRg6oDmm5X\
Kg/K6Ht9JPtiWRGA2gCD0GfF0HxcgTGY/aJhnh8mhw7WPhBfR/eCdXhxhK4QJfCrPAWiqaHJvMTUur+GwKO79dzxH/4nATSqLQ1o\
Fw3liE8Zu8qyVHgauvMyBQm4DTzzfWh8rQCpIXUeUm6abWIePtgmqi86bH8Yv0Now+rqbmbjmPgN60daJmomN82GCQbFhB0MSVvE\
qAxYSa12j5vnewTlOjU21yO3e26x19lppKe9JySR5GGz/btcw1ZZWh3BX0y98a0ezFV8T0g61IFLaJJQ8q3wncUnPzxO+hIFlFpp\
88xPwStM1HxPY1lgy0WtziRYI7/tpHqHcCk/fOESQxmaGwgA95fnWUJEyuEFl7AEbjh01x1dt1WqSoXvgK3RVqNWfd7+yb3nekRr\
CcJoiWvk97bRf74LtbFJaIm2V/Bo55OVpZohhxxfXaOD+2VVDFXrWDuozuHoqt9QLnIcmPg9eAY+UAjlQ+d2108jej/ogZp2zsOV\
kwXjBzkpoHrgVXVWltM5I3c4xWizvHqqym6NXXJRgAJjXACwjtvjdPZInOcw4Ej8v4inEEN2auQvubppmrom6ehUUJlZ04C0gYBR\
3yRMMLE1V/Eg4MpmPLa7UJbhSncTmjxUrSAIMOCtFOcNGjzkIme6EfSFoLQiZW2z2SyqU/pq7zWo9eEojq5I2kJUZyCSMGq1OJKA\
4AUiluuOsBMP03WWE8TQksgwpIrkMJjZJ14cZ1p9R0eLEmVQolGq73RIdCCkVCCFKDafGudVmTjYtqARdpyssymHlfpDK+V9Xx5M\
dkt/HlYC+zOwc2XByw7OHiKL1jkOF+nExkE0wVaH+OgpfAqmihZGWZ4K3WwoEmX7rXbbmumUyypmVJZREZZxnwllfSUfpE3brbOp\
9JQZeH7A3sBkKs48bzeMjpccN9VMOGk0dcOxIPX2MQTTearU5rHqDg1T90hze6rG9GM+hRVN4ki7JtlBUDBYzHTMAY7jOCcohqzG\
0DVBoqVliXymrp06c/wYwBFfGDWexlQ70w0UcQ4WmuGLYweE/ixIimHg73GiiLxzWSz2zyRajDYGsq1YNjodBgdw/VNfns/ytI4G\
Kaph+pSSaWgKzyTiQ742WMKSyb1qw2kUfRJ1WyRlnkWTiA99EPt+RcHLAvBr05eqcPoMFiurrhzt6pRpxUoeuH7QKIhSX4esUcUs\
H31kZqKNK1vv7TxfgZGzW2gG58bNUoYGrN1p/7J5lgwuBYZBP95dN2ytQFD4cvXQ2tWsJQJsoy6t85zzpaFeGd2vkK4NgGQWvjkQ\
idD0rdYjqICJQx/VxfUgx/bI8Oy/gXRAIv6siYSzVKgzHBWTjYpSMr18+Q/0LIwOCZJsNZ2oUEPVVI+jI9TI/fZut/XolMs01G5O\
DNkEitzmars7AvTn1v3ibfUNDfV4kYIGK3CTKKMegqL1EpsOSRAcS8z+W2UkPRDb1xYpp7jCTnRKLQoWMXT5NjTolyaBpFOJ79yI\
c3SAftm3LM9gOGRLaeeMuNvq+SMMTjZSXKS90tgqNopp1MX9znJ9o75KmOOaHtTJ3Y23fv6eR+G/WW2K3ZXCMibzHq3Fvp+M+Nma\
RKRpEiAPJ5UrOnvMsp1W15QcK3clahp7nsPuk5VEGKCVNjtA91tLEp7e6a/i+6zbGf5ZCq2q1fG9UUIqp/O07WgMzyY3jieOvyL+\
6p499/oYY4OJjNsbFed+Isum92R3aPTdCKR0meyLM5WqLvI006Y0kWp+IQh8SG/FqLqiV61umiIKAITkdKt2agTxEw5LPHNfg+en\
tcWh6dkTXOpkOm7G5MpWfWJ8fBfGHhcTOloC276zdSLSuN11Ic8F74cHBTBablmmYVrzzYpKYFoGo1NcKLJiY5EkND0R4Vl9JSwL\
4/iEVWsBhgo5S/5GPPXFTtxyqcjjuJBFOFOuxfCwjlpznlfifOxuTiLLYGw4jxEztIiOme6y2l2WlXC6PbrIQsksCH+xxjtTltjo\
yo1tyXgkeimxN6LmbASezRr48/NAnJyP6bN2FgSO5LP0zQFnOwB1xAC16gKOHYMHMUdYscVUaGxufrO2QO++Zgxqix58w6iBs9Ld\
2ZDdGwt5PJosHDrhnXCnHQbszDANltnLs6jluBYjIg5ifmmJSRMxnofcE0+BwMBjjnZaH4HdszaD6RBhrw9MUeM/t0pzZhkUg7NZ\
pWfbfkA7Ig7JBEHFYpLJxfht3u3xvJ6oYZeSIqyb4jYJLfaEXZ0LmmOTJwNUbSiljjg+zXPfj+jmpITyDMNTjrpVadBIp0+qKTht\
jDICcYE1lY3T/WZz9Uv6dFvuV7sy/E45+YXaTOD94rNVqxYuh2pHH4r/wv+Z4z/UhdAyOcOb8gj7bCD3EOwqY+KSQG3LCG5Hisyl\
oSe7BRJC2VXWhMOh3jA43/FWt0WH/XCgESsTMO97qC/Bixyb9wWLJKNltV6+br8DsZ5lPZ1R0isZMxy7bqI77x1sl5H2ZJyRVc7e\
LBM/4HtXEk7q6ap6RvVc0wNUkT7nSF82cDDa+iAUdM8DJAqqsi60HWn1+hqysNzRjRCMYD0THf/UEYohJ8koY0qS/BhEPG69YW70\
evCFTWO3erK3RPVrOTLgroVZ7cwEAfIY6x+eaBBV64meX6SeuqgcAXou23DIRgPCPhfTnAZHO3aW+fRawPWLaKQfawv4LqcmrJ6v\
VysJwKBY0SIdGwg7CIELlVWO77o5DJrIBYFhlpplMlLp87kzaWIwEc78IPpGve0WzeX26OEoEa9wlNjk7PbqktRrmmkxkLBveGYP\
QK9W4zQ03onrouhOlPHs08bZFsJjhwu4tNK+XTdNnT29XhSS425rStMIhi0LsNYMG/GnbT5BzBO0GMsYj+afQOIGPVtJJfbQW12Y\
b/LJk26txIzS10f/8vGrqLS2lNh/nDf1RP99zusfH91wKiJP8MdcZW2w/+2XbV6GMPbQ3iGW/h3i4AW/MTmDxRHaZpa3BawoNRvp\
bNfW63WI8uRsTHMaZT5R9Aku4HBIX03m2HLxYWBRppx4cBXyXPZUMhK0n9OHlV5p7GwwKs5ieToCDwkFvX8vZE5f0udFcrpT4Jug\
hfeCTqMc2pSS0xkUy82RiYkt6ahN0AU/bHAnoaemhwuBWWmYFhMQ+bp6k8Y+xR8/fbs804CI4ITj60DFmaKgkNR29QgmWjdcPfDg\
jCCXE/UEDG1zXzVMaj6q9EtonXssfvdk8uypDgJxm7LVNAscnBXXz/sagT7spSBvKuoK5EAiv7rklrkzVxfODKka1YBVHE3uszOW\
Y4EDJ7ZVbcGoUTcZ1BksN9wXDau1+UgR+MJ4EGcA/1fef9cSIIN1JZDCH3EmMjlCwxOagQtnrdT9sG/Q8KJ2G8XEOD2DbGkqiBz2\
nVJppUlD3W+vET6EV8OrjU4gjU29Q4m0NYdhDEIqT/zO4m1IGpuwxjSxBUDxjE4ojU3IQ4lUg3RtLd2vdqqgvL7RRQyPWLwNS2NT\
85hmTgrgebABqrMhMaEUSEK4YBanda7CGZokhj2LTjTQX8BADtnwTuk+sQ828iIcnASOMa1c7sRYNxFprDVcjm3i+DgWTleXXz4Z\
Xmia4xy4PUWmZXIMYrh5RUZkkbNvLLRiZq6r0TmTXpvYWniFFvBP+a7WFjrvAtrin9Rz8ETQPdSetUmbqlQ2puChlzCp5SFAuekt\
Q0AOT/8/H/x7rkiNhhsLYNpx2XYuKbVKrdcyvwIy3qJTPT8yV+r2xdpoDnCinaP+BwF4ZuZ7DjnLzemmZL9kfFtDIqJux91+HT94\
/c14+G4QAfdrTclv9Ulj6b2oH8zDguEB5hWOpVlTN4oaBc3LpVtgtKmsX+YT217C+VkEgWV3xvx+H5R4zjNccR81q5McRrBpxGnH\
77XG0E39VBanPM971P/4+emgwD7y9vc6D/p/4iUviautThYkb6cx/qmZa6s0JByBo98kgY3aDQHfGSnEGtpB9yDaE3ucoxt6gNEJ\
5G+v7jFSFX/yBYy3rHXfZ8ivty3NQBjXgnxiqKL/vsoP2pQonhOU4kptORngy0iRo0vIb0Ut7EnPv350PPgVP2x7951uSjSrmmbN\
uCHWamgebK76MThNsAZ6UIaybvVvXWjcPvfjH8lAovz3gG5Fsr6LOfZ6JvKkCbRQ53wSbaLJ1C00AHhwB5R98hWiyXw41AWnNz4E\
x+AsuOEyW0MYDk24BXAj0Yf3wQM4KCm7gr28vL+cMT5RnOmWgJazMhuoDbD5zVEWC/YqOu17dZVBjfnw9qsCgO6EcnN1VkuGxctI\
diPrStlkOZUyond+UBjiwQaA4TUTL06UfgizbbIri8v0YQET6cSG1118nUyim7sZ4VQOzYhXbR5NlEhO3mhJKC5nLUsmB+baoexf\
ZozJeKSi4X/0MQ8XMOxu37Paf3hNRRvnFe3HbRp20uhLWtPy2aWzafnwxWZScgjuYds8s4/KNL7ysP3lduqGDDUJvBXe+iboa2Z+\
yvUPj5rq92K3mkl5/GmeNZdL+3NvsX2N4091zs8Wzqy71UaSrNYkGhe1tJjuxHhGyJ2GEUVJaUQqE/9I8qjVkXAqw5Yyeg6zz1ry\
0/2knS07I+vO7+SbNAxWlGTVRUcSE8VEOsCs3RKNusNsm8R1kxMdD7Qquxif6A9POh/rrfPVsmep3jvkiy/R4puPylf1LNEHVzLE\
l7ygWUqtIdX0mlZP7o+6Y6ORFSjHnMXx7qfp7OKuTaF6TbODq9b52cUXFSjjmYzSfjVlF3yq9kl4d2v7N0e3I9XBw/TBlXOnMiUE\
ds9wqQZaZwKAwmUS396uAcHrQkc/zRihlnqOs/4licYoQbX+kp48pLUhuwGTPVEKjSpKWEPJgQ8jM2u58oG23brpjAjA9TuL5Xac\
N6+uwwgoRjVl28QFvAp8/1SAgxx64uF54MIR0OJkOtO3qBGRZVYN/CLpBi7eAiFaM18p5vl00pW7BSVBHBQ5ZAAADMd5+3Slwcte\
qO9z1F1SjpBNxx2jE+hYnKy14Ii7w1N7++OCZAFNOzXxgU7Q9N23rID7PQzPvHgKMaSoLjt5VBiVvFVxGa9rvVHqwZhepmyMo9PS\
IiuAKkWdeZOZjVXMuGrW4AbTmT8LHuk2U+RlEY7yArWxS9Ky+r3HrN9HzcC9lIrwpRgfF5llNoZuSVCdKEaZYth9PFPg8nwmUI01\
xbi7yKSmRuPzaNTu+g7iBLuVXQGQ/IwnVpWglWZNZhrxfpg60Y1KxZLD5NQNEp6W0/xaF7aXZCXCGBM686frdkEamiNtR9N+s1yT\
r9Qdy5BZVrB5b54WhzrHYbIoS9etkaTMC0bl6eWrcQ9KoUYWkHXVlDlthSZwd083LIDUfXhcMRc/DE98MXYbKkhhfpTBg1naukmM\
wHhdVu42J316HWzkL/AksY3ujH13fWfl/dkA6buCIv7id5/I+umzaJzNwCvsjjtbG4631FDPUIiOVlgErZdDGbp4COtgMVQHwro+\
6Hhy5nybCp8O2uj4iiH8awbDlSdhIwc/8o55XxL15248j4iZxzWNscMsWrg6B00Z0/DAyuUYR+jsa1s0mZxrCx9xSXs2sF3fcO0w\
QEfSogpafswtxD57un6GfN72bGfMgZDxPX/Utvh8BjvjfvKNf84aNMw0MHZcn2HIBtgAzm/gO5Uj10yom2ubhe+jU2uV9+3afAKh\
jwEhD/r3leD3rgG+JASbXf2t3r+7mdMauANAH9BTh35Gz3xk8zv80fBX5Rr4AYrGVL9zKnG2By7PzXN5N9Yucmm5AIH36mpdBdn+\
rfTue9a77wX/fjt5597bOHgVuHYGdBvBOfWOKhLu/NhuJ+IkNReFc9RkJ5HZAoysrm4y9nBRjfbhgWqGSTQ3l5grN/FfKi7Qlmva\
yjpI/ZxP5qKWmcbBfWDfgmGcJNW87JvKNX1Ztmk0YErvhtGhQ1a1+d506V09bj7WdS+5dMkXZ3rXj+7qpHRrxPglTmmQ5MqMVypU\
WeE433QnxoEed1TzyUlnOyBYRVoUJHl3nYjIipzsKSeDQ2ZFWvGZ8u7a7f20uwH84EXr0YzRp8vhgrnIli7KsuyREC9qW/zd/r1J\
kgyLSzOjpBeTHWt3Gs2SYM1sqOtbTJMRie+n4vjoSI42Cz3zgScP+mkv27eK3luqEVokvp/yeo8O4/jLxyzHY1kj8mJfzRxnusWm\
zQ23t/EF4DZ4Pbzph7W7RZQU1GoJlp9Y7SCVbsrtRKI0FQyJIUuyXnGnx+xlnJHpW7RKWh5N5F9aJ+LasDc6xXgc7EKOSLl2dCqC\
I5FI827cuqoCLFj69cp6Htpr6/xJVAxHQhiVtucXJDOYGI4CYRL1YjO16h4NIQhtCvYvsGFBGEkIUHJdB4S+Y+rsrsG1ZxfAm7fP\
7jhocscC+nzT22hSzc9jISUUOweB2wJqxC24YWNq98bk11I3P8tnkt1uwKgpLkKmLqPIDG5EEbwLkoFiJqv1Cr46x/a+NZn6I3HZ\
K3dzft91sR/Bu0xZNUYIi06/WeSSUzXgsFofvwIn01MDjGIaJPPV6R9rs4ORxYIXKnLxnOfMQsB1b599k7rd/RZoosmmuCIbq6qZ\
EJvV6vdh1ciKNWnv21pczEGNzWqNI15PggvK+TE4Dafr8uTPD4GJNoypOzrneAaIjchW0UBR+R8CTovyjQ1ksT7EBbF9tq6EUHIp\
3m8q4bLlpUNmfJ7KsiC5KnzWP1N5oTqi3z8WecgDz+hrn7QDjaaSPZ3Tqqa7zfg8xfMd5aoutL6g4sLcXkeCV7oL0A0aoxrkaA9N\
tRwGzZZSgTM+t/K8q1zViS59DgZoQfMIXX8sVpEHbv+UjtQN6LqzxjJwxudGBi2v6kSXngZ0TwuaRxjGdXwCeeCi8RAtpBswDAcv\
gBf2ttpVH866Cos68yy7RVVL6erLreQUFybuK1EW4TUvMrEOtLYPjk03zcLBYKO+UY6vgtYXNeyqyTSa7D6treEF4LxBaDHY6euZ\
icyyUlprgqOv8y71iu1E0RGH/aTYSvLKBlGW3QmU+u7tViQBzbmKk+5q0YcBTxTZ1htsy7Ta408DIx7o3LCjAVOLXeIvt08Mkyrj\
7L7GeDnG+eyC56Vjrf0ANwGxGcsTqLAQSBZRFDXp6aDbnWGmz0qaWqhtbasDLTh+xN+gWnFAfSvAD8BZONu8oDOdxbJFqFoVpAy8\
mAXidm25Phog5DKWfdx94SxbTS17yM3W9IIHfDeBfd75eNbwrxlxcAyn4PTG4DsNDt0+YnOTH7huAWVYpaQGmF3aSwGlfUqRpH8v\
bTQtGcTFQ8Tmu3K6Q5WdeWcrjTKngbgtT7c+B1qWyU6Jh2UY69FS2HMYRsKVfCly90qRxWEq+w/RBe00B5k9+17BtOfDzfmOZ3xG\
V02GK4pbfBeVJuW6cpChSnvYMJHkoF7GosejZEWhpJi5L1+BpqSgodod6umJFIQcVFqpuHqVWGmPGfWydgw3q0fR0g9Kepn7MhZo\
SvpZfFaBTIOw0cfGge/1VCrwdfU5E2gTwD68bHvB2MT09f71rxty9d8KfAKgXdXUScogWqhsZaaBQjPuH+GQJ8FsthybkMiOQL+M\
ahXD8nOhquzSBKn0OVsi6KcE1hBjPCy8at9h3nr6joKLhh/RGfejHlZYq8Txx/D6C5emgRPad9dfFLv3tl6lpwmPZaVitkhPq8pJ\
+6Pp2WZ/C10OVm4gedJGoWkmdIKSYdBJM9tHauVRDc6W6Wn/+1LV+ymTT77XOZh29QhShKYPWbXy/oKmWZac9PvtTNXsxZhHgXd0\
0ppfChLgwef2/XL8WLmMD8F7bUAdo3+OfqH3KVT2bUkLJLH4Dp15+dqOOXgvRyHmpbzYvfIGz/CoC2vXZcVihMAcQi5z/85OVf3h\
NsFsfGd4y2q6LBaQBsRrE3I5UBpM8zJ6zO2YFp8xuYH1fnnMrKn385ANIyzOLYktyuoCjoivNqso0kWPy8E8NKhEC3hzqhJ9LKSR\
/r0oufZzHvQAzANsqDQ33msHu8B3c3C39uZLR23gkCNaaH2CTGmHnnhk9X9FjSY8oLDKMHx0/fmU5VI5ZFP/CWs0d/724cr+JACb\
WDhJ3jl4c4w/IgV4uOQulZvyVLRK81HJBz84l/my22RSeTa7wNWtb3KSBPx3C39sktstOHK7m9BOioV83hGxoaY5kJz6Cm+Xpi7c\
+ebsXtft1Mw0lroTa7oZEqflbc/a4cWh8XGg1USuQZfeM2Hj46Vi5lcOHboXInywSqdKZ0MelCMed+Jecf2vXudI9kBCcRarupHn\
EcTT57PWtVKq67cjDf59Q4BKRCwbSyxLtDtdslhzgCudzg9cI1sxlg66hmoPk7TcTi9wST4bPeLzGANLxdNztS88MVOZe5rYLx6Z\
Ahug3viHgqfi2qoD6ogi61SmPYFYJguNh3UWfNB6tPHNeQSfIzqPoEtTqDVuxd2n1b6ROv+AOMkj2vPdt8LSzPfBqNHpkUUpfVxp\
CzMOXC1d0RePD4ny7dQgCxd+ixLPAB/u7xpevHEhrjSphpg9FBycyFdqoYo3tsQn3/+yxMF5teGZHem//0+xToRJHurrxfwbZPgz\
1x+GDP4FAAr54v4N4pyj/3+mcfw1AH96ScApXrZ1n3zPpYtzvQEYMLQt4H8kWlzuFBC89tDPOUe0gVEtUM5130Bq9SNJXiPt5g1r\
Pmk3fQ1Jzx3SEOS0EEv1vsyaJEMEBSpIr7GK4COxmLRLCtgTPQ8qnef1Av3/4RlaWf3cdFhzPbJ17yGlZNCeqtskrrW7A+3qamH/\
FAT9XXFb95mElgvivjMvzbRLminHEVqaHpc8QKSt4B4mT7meP/Dzs8VO1ABCgbzKg5HfIYvj4ohsxuXuOUjlQxBpCP2TEJ89k9CU\
oufNe+V/NhPFsLB+sH67KohgrLWLgnpqpRDajwTiE0IDiPBb+ZJXm1jWYMzIU/iBmQq8BKvgXZDZzxcOZ2kzgSmwBWbAeeI5uOvQ\
7YpoKDHq+HFgz/crRAitfvjlgksV41oYOI5LMib/omRu8RLnWJlv3xQZNVWnwcvtmfZDKwvIEaPMB5yJ71P5aygdA0quyHrkHDFZ\
V5yjQ0KcFHjQtjzk/4JkVP7rXDPrOlfSAjI7OjPQWARz34qTvijyEvNO5GJ4EFdwlwe84udk0O4dyXaOBOJ5kXjyk4k9860FojWP\
MojXD2eCWpT1MEJHj5pP1lYG7xkaA5/76qaY0qm2JkNKOlPiD3R4pxxk2XxL2eReJGL5bVAFgfYYXi8cic6kPG2qKWDqOP0diydG\
wBipGBahJ96JxC9Hg1Q6bSVCKQSOVYzgZRTge2irGsE/a9CIizmMknLXR1n1DwzXhp8UIYxQ8m8YQ8u7ME6S02ECq3RAolgLSWLB\
TWm84nNbCGCNIDwFDMINU4ERY2B0dT/CNOB4GKYDxY2wMUyn60zizUCmvW8LTYWqO8zAQnPYDGO1YSY28sLmGFCFLWCID1tiKiBs\
BRsnbA0FU7Px3xbwngILlFATCpFnnky5L6xl83BLqBWbpxWuFiqRaaGfPXUtKQ3lywaVvOwwBqq0Uompmc9adJ1dJMvoGz/xqYWR\
vdu05HsoW0GpprXUKh/5dctFSvgSa4VZW6BpC5NW0Gp5spEpaiVBEzVLiy3qkE20wI3SaWeLpRZa8W1ke2Q5pDNNsuvd0A2n2jbW\
T7zpEiUln31YodpqhA4wtFTxgPIT5BeUGpwJIGvkRNHiPVsop+Iz88FK52IUjoGsOW9G+UWyTSNLzSeSKWv5DSzR8sXMPHmGJ0n7\
DLvAHI9u9iL1/z9zBOAOQ8EQjgjgyMn/FCIiEjiHjAyAF0NEQVMQFRkB39+hIToyxjUmMUWQqWHwb8zCjDnCWCCKJddEGgqVRm9P\
kZbBZLGr4XB56TLw5RUyCtrXuyIUZVJSFqtkVlVT19DUyqqto2sou+HeDlat0Q54IMijCZP58jeHwIkUEOWDi4lLSEoFd+mNMrIh\
cvLt8h1FJWUVVbVQdY2imlraOu0ti+vq6RsYljCCjEuGwVSkNK39/T9mhDNZbE4ZLg818YJVb4oTXst6816jjw56rvnu8B3ZQ379\
+UcgUWgMFocnEElkCpXWo67/0BlMFpvD5fEFQpFYIpXJFUqVWqPV6Q1Gk9litdkdTs4urm7uHp5e3j6+fv5Lyyv11bX1jc2t7Z3d\
vf1Gs9XudHsESdEMy/GCKMmKCjXdMC0bYcf1ZkEYxUma5bwohVSCaD4ltWx2hxu3XrhzcXXvwaMn/xpUxoy8EklxEWbUkxSqU4/Y\
C9EnTzsvcasMu+ejKuUD+Eh722AMo0E5RKSighEvjpDEDM7H0w5IcUYxHpW8gCQ8MxQG+CTzvKxgaozYQirb5f50BqbrJqaFNKq9\
otx0VLKQKdVGeeRsRnASkhrFEw7LW06lHBbiowuHEF/jng6LtuyloiEyqMMWroO601LRchpW8kZXhlke1YS5FqrVyMmbme82HPf4\
rTZGDNbMgEC2QjzqTrvWk/WmCnVrpr5zvxSsNzgNm1ajms8/11RNclGsqEPSGXqNaluwHY7u5Tsz5jsKmkhWEQlo5gLWOwoLqkl6\
WiBRRCQi6V5/IPzonBFlpKH5EU3R5M2C37REe8aoX6vH8/qzD/AX/z9xBQwdrRoc9UN1c3hPXQjxQf/QNTMxSJ4ZCZ1yJQLtSkUq\
sC5svT6m3U9zfuMjoAsXcX0+RFchClHwQhDCW/Rb4E14i/4QPoTPwCepxt6hWP5o5WCvhEn8hwzwxvFzUaV2FsI47Q45lOTl+nqh\
s2UpfdtgT0zYmPviQDw5nV/vFTXQP49OAoolihXvFjIMJlFyKzQAgqKqBlhMzC8nIXn7y0Euf4YXVcr3d0g5C3K6S8l/2eYmT0xR\
C1+nnLHPgt6CBdGJizwfhifHZ9zxdHA9K3DTumuPpKIPwfuuEp1mFL0qdkE3qnhOzKJFFT1XE3sdi15sAAjBKIkjGPG3ZooGZd4M\
faU+ENdL9EjtnTe2DhfhfW3MVz+SC8pR/20TBLGH4BJXwdIbUqfVsrzVC4dtO78RN4JkIkisfMHRWYDC5+MaWyZbr+zCqPkGK66S\
1hnb1fUbZBmFw/LarjxHLrhsaRCVbLJw5/o5iCjYxqIbG4eoVtcef0JW04XbOqF5KUMTF7pxtQTKyJDMgFfKlZU5i0+KehuuonqV\
ODgA") format('woff2')}
/* onest-latin.woff2 */
@font-face{font-family:'Onest';font-style:normal;font-weight:400 600;font-display:swap;unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;src:url("data:font/woff2;base64,\
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") format('woff2')}
/* fonts:end */
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
.after.rule{max-width:none;margin-top:1.2em;padding-top:.9em;border-top:1.5px solid var(--soft)}

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
/* Image export for Save/Share: modern-screenshot 4.4.39, MIT License, Copyright (c) 2021-present wxm.
   Embedded here so nothing is downloaded. It draws the slide to a PNG inside this page. Its fetch() helper
   is for pages with remote images; this page has none, and the policy in <head> blocks network requests anyway. */
/* shot:begin */
(function () {
var Pe = Object.defineProperty, _e = Object.defineProperties;
var Ue = Object.getOwnPropertyDescriptors;
var L = Object.getOwnPropertySymbols;
var Z = Object.prototype.hasOwnProperty, ee = Object.prototype.propertyIsEnumerable;
var te = Math.pow, Q = (e, t, r) => t in e ? Pe(e, t, { enumerable: !0, configurable: !0, writable: !0, value: r }) : e[t] = r, T = (e, t) => {
  for (var r in t || (t = {}))
    Z.call(t, r) && Q(e, r, t[r]);
  if (L)
    for (var r of L(t))
      ee.call(t, r) && Q(e, r, t[r]);
  return e;
}, R = (e, t) => _e(e, Ue(t));
var re = (e, t) => {
  var r = {};
  for (var n in e)
    Z.call(e, n) && t.indexOf(n) < 0 && (r[n] = e[n]);
  if (e != null && L)
    for (var n of L(e))
      t.indexOf(n) < 0 && ee.call(e, n) && (r[n] = e[n]);
  return r;
};
var S = (e, t, r) => new Promise((n, a) => {
  var s = (l) => {
    try {
      i(r.next(l));
    } catch (u) {
      a(u);
    }
  }, o = (l) => {
    try {
      i(r.throw(l));
    } catch (u) {
      a(u);
    }
  }, i = (l) => l.done ? n(l.value) : Promise.resolve(l.value).then(s, o);
  i((r = r.apply(e, t)).next());
});
function ue(e, t) {
  return e[13] = 1, e[14] = t >> 8, e[15] = t & 255, e[16] = t >> 8, e[17] = t & 255, e;
}
const fe = "p".charCodeAt(0), de = "H".charCodeAt(0), me = "Y".charCodeAt(0), ge = "s".charCodeAt(0);
let q;
function $e() {
  const e = new Int32Array(256);
  for (let t = 0; t < 256; t++) {
    let r = t;
    for (let n = 0; n < 8; n++)
      r = r & 1 ? 3988292384 ^ r >>> 1 : r >>> 1;
    e[t] = r;
  }
  return e;
}
function Be(e) {
  let t = -1;
  q || (q = $e());
  for (let r = 0; r < e.length; r++)
    t = q[(t ^ e[r]) & 255] ^ t >>> 8;
  return t ^ -1;
}
function Le(e) {
  const t = e.length - 1;
  for (let r = t; r >= 4; r--)
    if (e[r - 4] === 9 && e[r - 3] === fe && e[r - 2] === de && e[r - 1] === me && e[r] === ge)
      return r - 3;
  return 0;
}
function he(e, t, r = !1) {
  const n = new Uint8Array(13);
  t *= 39.3701, n[0] = fe, n[1] = de, n[2] = me, n[3] = ge, n[4] = t >>> 24, n[5] = t >>> 16, n[6] = t >>> 8, n[7] = t & 255, n[8] = n[4], n[9] = n[5], n[10] = n[6], n[11] = n[7], n[12] = 1;
  const a = Be(n), s = new Uint8Array(4);
  if (s[0] = a >>> 24, s[1] = a >>> 16, s[2] = a >>> 8, s[3] = a & 255, r) {
    const o = Le(e);
    return e.set(n, o), e.set(s, o + 13), e;
  } else {
    const o = new Uint8Array(4);
    o[0] = 0, o[1] = 0, o[2] = 0, o[3] = 9;
    const i = new Uint8Array(54);
    return i.set(e, 0), i.set(o, 33), i.set(n, 37), i.set(s, 50), i;
  }
}
const Me = "AAlwSFlz", Oe = "AAAJcEhZ", We = "AAAACXBI";
function je(e) {
  let t = e.indexOf(Me);
  return t === -1 && (t = e.indexOf(Oe)), t === -1 && (t = e.indexOf(We)), t;
}
const H = "[modern-screenshot]", x = typeof window != "undefined", qe = x && "Worker" in window, we = x && "atob" in window, Ve = x && "btoa" in window;
var le;
const z = x ? (le = window.navigator) == null ? void 0 : le.userAgent : "", pe = z.includes("Chrome"), M = z.includes("AppleWebKit") && !pe, X = z.includes("Firefox"), He = (e) => e && "__CONTEXT__" in e, ze = (e) => e.constructor.name === "CSSFontFaceRule", Xe = (e) => e.constructor.name === "CSSImportRule", A = (e) => e.nodeType === 1, U = (e) => typeof e.className == "object", ye = (e) => e.tagName === "image", Ge = (e) => e.tagName === "use", F = (e) => A(e) && typeof e.style != "undefined" && !U(e), Ye = (e) => e.nodeType === 8, Je = (e) => e.nodeType === 3, D = (e) => e.tagName === "IMG", O = (e) => e.tagName === "VIDEO", Ke = (e) => e.tagName === "CANVAS", ne = (e) => e.tagName === "TEXTAREA", Qe = (e) => e.tagName === "INPUT", Ze = (e) => e.tagName === "STYLE", et = (e) => e.tagName === "SCRIPT", tt = (e) => e.tagName === "SELECT", rt = (e) => e.tagName === "SLOT", nt = (e) => e.tagName === "IFRAME", C = (...e) => console.warn(H, ...e), ot = (e) => console.time(`${H} ${e}`), at = (e) => console.timeEnd(`${H} ${e}`), st = (e) => {
  var r;
  const t = (r = e == null ? void 0 : e.createElement) == null ? void 0 : r.call(e, "canvas");
  return t && (t.height = t.width = 1), t && "toDataURL" in t && Boolean(t.toDataURL("image/webp").includes("image/webp"));
}, V = (e) => e.startsWith("data:");
function be(e, t) {
  if (e.match(/^[a-z]+:\/\//i))
    return e;
  if (x && e.match(/^\/\//))
    return window.location.protocol + e;
  if (e.match(/^[a-z]+:/i) || !x)
    return e;
  const r = W().implementation.createHTMLDocument(), n = r.createElement("base"), a = r.createElement("a");
  return r.head.appendChild(n), r.body.appendChild(a), t && (n.href = t), a.href = e, a.href;
}
function W(e) {
  var t;
  return (t = e && A(e) ? e == null ? void 0 : e.ownerDocument : e) != null ? t : window.document;
}
const j = "http://www.w3.org/2000/svg";
function Se(e, t, r) {
  const n = W(r).createElementNS(j, "svg");
  return n.setAttributeNS(null, "width", e.toString()), n.setAttributeNS(null, "height", t.toString()), n.setAttributeNS(null, "viewBox", `0 0 ${e} ${t}`), n;
}
function Ee(e, t) {
  let r = new XMLSerializer().serializeToString(e);
  return t && (r = r.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE\uFFFF]/ug, "")), `data:image/svg+xml;charset=utf-8,${encodeURIComponent(r)}`;
}
function it(e, t = "image/png", r = 1) {
  return S(this, null, function* () {
    try {
      return yield new Promise((n, a) => {
        e.toBlob((s) => {
          s ? n(s) : a(new Error("Blob is null"));
        }, t, r);
      });
    } catch (n) {
      if (we)
        return C("Failed canvas to blob", { type: t, quality: r }, n), ct(e.toDataURL(t, r));
      throw n;
    }
  });
}
function ct(e) {
  var i, l;
  const [t, r] = e.split(","), n = (l = (i = t.match(/data:(.+);/)) == null ? void 0 : i[1]) != null ? l : void 0, a = window.atob(r), s = a.length, o = new Uint8Array(s);
  for (let u = 0; u < s; u += 1)
    o[u] = a.charCodeAt(u);
  return new Blob([o], { type: n });
}
function Ce(e, t) {
  return new Promise((r, n) => {
    const a = new FileReader();
    a.onload = () => r(a.result), a.onerror = () => n(a.error), a.onabort = () => n(new Error(`Failed read blob to ${t}`)), t === "dataUrl" ? a.readAsDataURL(e) : t === "arrayBuffer" && a.readAsArrayBuffer(e);
  });
}
const lt = (e) => Ce(e, "dataUrl"), ut = (e) => Ce(e, "arrayBuffer");
function k(e, t) {
  const r = W(t).createElement("img");
  return r.decoding = "sync", r.loading = "eager", r.src = e, r;
}
function P(e, t) {
  return new Promise((r) => {
    const { timeout: n, ownerDocument: a, onError: s } = t != null ? t : {}, o = typeof e == "string" ? k(e, W(a)) : e;
    let i = null, l = null;
    function u() {
      r(o), i && clearTimeout(i), l == null || l();
    }
    if (n && (i = setTimeout(u, n)), O(o)) {
      const c = o.currentSrc || o.src;
      if (!c)
        return o.poster ? P(o.poster, t).then(r) : u();
      if (o.readyState >= 2)
        return u();
      const f = u, d = (m) => {
        C(
          "Failed video load",
          c,
          m
        ), s == null || s(m), u();
      };
      l = () => {
        o.removeEventListener("loadeddata", f), o.removeEventListener("error", d);
      }, o.addEventListener("loadeddata", f, { once: !0 }), o.addEventListener("error", d, { once: !0 });
    } else {
      const c = ye(o) ? o.href.baseVal : o.currentSrc || o.src;
      if (!c)
        return u();
      const f = () => S(this, null, function* () {
        if (D(o) && "decode" in o)
          try {
            yield o.decode();
          } catch (m) {
            C(
              "Failed to decode image, trying to render anyway",
              o.dataset.originalSrc || c,
              m
            );
          }
        u();
      }), d = (m) => {
        C(
          "Failed image load",
          o.dataset.originalSrc || c,
          m
        ), u();
      };
      if (D(o) && o.complete)
        return f();
      l = () => {
        o.removeEventListener("load", f), o.removeEventListener("error", d);
      }, o.addEventListener("load", f, { once: !0 }), o.addEventListener("error", d, { once: !0 });
    }
  });
}
function ft(e, t) {
  return S(this, null, function* () {
    F(e) && (D(e) || O(e) ? yield P(e, { timeout: t }) : yield Promise.all(
      ["img", "video"].flatMap((r) => Array.from(e.querySelectorAll(r)).map((n) => P(n, { timeout: t })))
    ));
  });
}
const ve = function() {
  let t = 0;
  const r = () => (
    // eslint-disable-next-line no-bitwise
    `0000${(Math.random() * te(36, 4) << 0).toString(36)}`.slice(-4)
  );
  return () => (t += 1, `u${r()}${t}`);
}();
function Te(e) {
  return e == null ? void 0 : e.split(",").map((t) => t.trim().replace(/"|'/g, "").toLowerCase()).filter(Boolean);
}
function dt(e) {
  return {
    time: (t) => e && ot(t),
    timeEnd: (t) => e && at(t),
    warn: (...t) => e && C(...t)
  };
}
function mt(e) {
  return {
    cache: e ? "no-cache" : "force-cache"
  };
}
function N(e, t) {
  return S(this, null, function* () {
    return He(e) ? e : gt(e, R(T({}, t), { autoDestruct: !0 }));
  });
}
function gt(e, t) {
  return S(this, null, function* () {
    var m, h, w, y, g;
    const { scale: r = 1, workerUrl: n, workerNumber: a = 1 } = t || {}, s = Boolean(t == null ? void 0 : t.debug), o = (m = t == null ? void 0 : t.features) != null ? m : !0, i = (h = e.ownerDocument) != null ? h : x ? window.document : void 0, l = (y = (w = e.ownerDocument) == null ? void 0 : w.defaultView) != null ? y : x ? window : void 0, u = /* @__PURE__ */ new Map(), c = R(T({
      // Options
      width: 0,
      height: 0,
      quality: 1,
      type: "image/png",
      scale: r,
      backgroundColor: null,
      style: null,
      filter: null,
      maximumCanvasSize: 0,
      timeout: 3e4,
      progress: null,
      debug: s,
      fetch: T({
        requestInit: mt((g = t == null ? void 0 : t.fetch) == null ? void 0 : g.bypassingCache),
        placeholderImage: "data:image/png;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
        bypassingCache: !1
      }, t == null ? void 0 : t.fetch),
      fetchFn: null,
      font: {},
      drawImageInterval: 100,
      workerUrl: null,
      workerNumber: a,
      onCloneNode: null,
      onEmbedNode: null,
      onCreateForeignObjectSvg: null,
      includeStyleProperties: null,
      autoDestruct: !1
    }, t), {
      // InternalContext
      __CONTEXT__: !0,
      log: dt(s),
      node: e,
      ownerDocument: i,
      ownerWindow: l,
      dpi: r === 1 ? null : 96 * r,
      svgStyleElement: Ae(i),
      svgDefsElement: i == null ? void 0 : i.createElementNS(j, "defs"),
      svgStyles: /* @__PURE__ */ new Map(),
      defaultComputedStyles: /* @__PURE__ */ new Map(),
      workers: [
        ...new Array(
          qe && n && a ? a : 0
        )
      ].map(() => {
        try {
          const b = new Worker(n);
          return b.onmessage = (p) => S(this, null, function* () {
            var I, J, B, K;
            const { url: E, result: v } = p.data;
            v ? (J = (I = u.get(E)) == null ? void 0 : I.resolve) == null || J.call(I, v) : (K = (B = u.get(E)) == null ? void 0 : B.reject) == null || K.call(B, new Error(`Error receiving message from worker: ${E}`));
          }), b.onmessageerror = (p) => {
            var v, I;
            const { url: E } = p.data;
            (I = (v = u.get(E)) == null ? void 0 : v.reject) == null || I.call(v, new Error(`Error receiving message from worker: ${E}`));
          }, b;
        } catch (b) {
          return C("Failed to new Worker", b), null;
        }
      }).filter(Boolean),
      fontFamilies: /* @__PURE__ */ new Set(),
      fontCssTexts: /* @__PURE__ */ new Map(),
      acceptOfImage: `${[
        st(i) && "image/webp",
        "image/svg+xml",
        "image/*",
        "*/*"
      ].filter(Boolean).join(",")};q=0.8`,
      requests: u,
      drawImageCount: 0,
      tasks: [],
      features: o,
      isEnable: (b) => {
        var p, E;
        return b === "restoreScrollPosition" ? typeof o == "boolean" ? !1 : (p = o[b]) != null ? p : !1 : typeof o == "boolean" ? o : (E = o[b]) != null ? E : !0;
      }
    });
    c.log.time("wait until load"), yield ft(e, c.timeout), c.log.timeEnd("wait until load");
    const { width: f, height: d } = ht(e, c);
    return c.width = f, c.height = d, c;
  });
}
function Ae(e) {
  if (!e)
    return;
  const t = e.createElement("style"), r = t.ownerDocument.createTextNode(`
.______background-clip--text {
  background-clip: text;
  -webkit-background-clip: text;
}
`);
  return t.appendChild(r), t;
}
function ht(e, t) {
  let { width: r, height: n } = t;
  if (A(e) && (!r || !n)) {
    const a = e.getBoundingClientRect();
    r = r || a.width || Number(e.getAttribute("width")) || 0, n = n || a.height || Number(e.getAttribute("height")) || 0;
  }
  return { width: r, height: n };
}
function wt(e, t) {
  return S(this, null, function* () {
    const {
      log: r,
      timeout: n,
      drawImageCount: a,
      drawImageInterval: s
    } = t;
    r.time("image to canvas");
    const o = yield P(e, { timeout: n }), { canvas: i, context2d: l } = pt(e.ownerDocument, t), u = () => {
      try {
        l == null || l.drawImage(o, 0, 0, i.width, i.height);
      } catch (c) {
        C("Failed to drawImage", c);
      }
    };
    if (u(), t.isEnable("fixSvgXmlDecode"))
      for (let c = 0; c < a; c++)
        yield new Promise((f) => {
          setTimeout(() => {
            u(), f();
          }, c + s);
        });
    return t.drawImageCount = 0, r.timeEnd("image to canvas"), i;
  });
}
function pt(e, t) {
  const { width: r, height: n, scale: a, backgroundColor: s, maximumCanvasSize: o } = t, i = e.createElement("canvas");
  i.width = Math.floor(r * a), i.height = Math.floor(n * a), i.style.width = `${r}px`, i.style.height = `${n}px`, o && (i.width > o || i.height > o) && (i.width > o && i.height > o ? i.width > i.height ? (i.height *= o / i.width, i.width = o) : (i.width *= o / i.height, i.height = o) : i.width > o ? (i.height *= o / i.width, i.width = o) : (i.width *= o / i.height, i.height = o));
  const l = i.getContext("2d");
  return l && s && (l.fillStyle = s, l.fillRect(0, 0, i.width, i.height)), { canvas: i, context2d: l };
}
const yt = [
  "width",
  "height",
  "-webkit-text-fill-color"
], bt = [
  "stroke",
  "fill"
];
function Ne(e, t, r) {
  var y;
  const { defaultComputedStyles: n, ownerDocument: a } = r, s = e.nodeName.toLowerCase(), o = U(e) && s !== "svg", i = o ? bt.map((g) => [g, e.getAttribute(g)]).filter(([, g]) => g !== null) : [], l = [
    o && "svg",
    s,
    i.map((g, b) => `${g}=${b}`).join(","),
    t
  ].filter(Boolean).join(":");
  if (n.has(l))
    return n.get(l);
  let u = r.sandbox;
  if (!u)
    try {
      a && (u = a.createElement("iframe"), u.id = `__SANDBOX__-${ve()}`, u.width = "0", u.height = "0", u.style.visibility = "hidden", u.style.position = "fixed", a.body.appendChild(u), (y = u.contentWindow) == null || y.document.write('<!DOCTYPE html><meta charset="UTF-8"><title></title><body>'), r.sandbox = u);
    } catch (g) {
      C("Failed to create iframe sandbox", g);
    }
  if (!u)
    return /* @__PURE__ */ new Map();
  const c = u.contentWindow;
  if (!c)
    return /* @__PURE__ */ new Map();
  const f = c.document;
  let d, m;
  o ? (d = f.createElementNS(j, "svg"), m = d.ownerDocument.createElementNS(d.namespaceURI, s), i.forEach(([g, b]) => {
    m.setAttributeNS(null, g, b);
  }), d.appendChild(m)) : d = m = f.createElement(s), m.textContent = " ", f.body.appendChild(d);
  const h = c.getComputedStyle(m, t), w = /* @__PURE__ */ new Map();
  for (let g = h.length, b = 0; b < g; b++) {
    const p = h.item(b);
    yt.includes(p) || w.set(p, h.getPropertyValue(p));
  }
  return f.body.removeChild(d), n.set(l, w), w;
}
function Ie(e, t, r) {
  var i;
  const n = /* @__PURE__ */ new Map(), a = [], s = /* @__PURE__ */ new Map();
  if (r)
    for (const l of r)
      o(l);
  else
    for (let l = e.length, u = 0; u < l; u++) {
      const c = e.item(u);
      o(c);
    }
  for (let l = a.length, u = 0; u < l; u++)
    (i = s.get(a[u])) == null || i.forEach((c, f) => n.set(f, c));
  function o(l) {
    const u = e.getPropertyValue(l), c = e.getPropertyPriority(l), f = l.lastIndexOf("-"), d = f > -1 ? l.substring(0, f) : void 0;
    if (d) {
      let m = s.get(d);
      m || (m = /* @__PURE__ */ new Map(), s.set(d, m)), m.set(l, [u, c]);
    }
    t.get(l) === u && !c || (d ? a.push(d) : n.set(l, [u, c]));
  }
  return n;
}
const St = [
  ":before",
  ":after"
  // ':placeholder', TODO
], Et = [
  ":-webkit-scrollbar",
  ":-webkit-scrollbar-button",
  // ':-webkit-scrollbar:horizontal', TODO
  ":-webkit-scrollbar-thumb",
  ":-webkit-scrollbar-track",
  ":-webkit-scrollbar-track-piece",
  // ':-webkit-scrollbar:vertical', TODO
  ":-webkit-scrollbar-corner",
  ":-webkit-resizer"
];
function Ct(e, t, r, n) {
  const { ownerWindow: a, svgStyleElement: s, svgStyles: o, currentNodeStyle: i } = n;
  if (!s || !a)
    return;
  function l(u) {
    var b;
    const c = a.getComputedStyle(e, u);
    let f = c.getPropertyValue("content");
    if (!f || f === "none")
      return;
    f = f.replace(/(')|(")|(counter\(.+\))/g, "");
    const d = [ve()], m = Ne(e, u, n);
    i == null || i.forEach((p, E) => {
      m.delete(E);
    });
    const h = Ie(c, m, n.includeStyleProperties);
    h.delete("content"), h.delete("-webkit-locale"), ((b = h.get("background-clip")) == null ? void 0 : b[0]) === "text" && t.classList.add("______background-clip--text");
    const w = [
      `content: '${f}';`
    ];
    if (h.forEach(([p, E], v) => {
      w.push(`${v}: ${p}${E ? " !important" : ""};`);
    }), w.length === 1)
      return;
    try {
      t.className = [t.className, ...d].join(" ");
    } catch (p) {
      return;
    }
    const y = w.join(`
  `);
    let g = o.get(y);
    g || (g = [], o.set(y, g)), g.push(`.${d[0]}:${u}`);
  }
  St.forEach(l), r && Et.forEach(l);
}
function vt(e, t) {
  ne(e) && (t.innerHTML = e.value), (ne(e) || Qe(e) || tt(e)) && t.setAttribute("value", e.value);
}
function Tt(e, t, r, n) {
  var f, d, m, h;
  const { ownerWindow: a, includeStyleProperties: s, currentParentNodeStyle: o } = n, i = t.style, l = a.getComputedStyle(e), u = Ne(e, null, n);
  o == null || o.forEach((w, y) => {
    u.delete(y);
  });
  const c = Ie(l, u, s);
  return c.delete("transition-property"), c.delete("all"), c.delete("d"), c.delete("content"), r && (c.delete("margin-top"), c.delete("margin-right"), c.delete("margin-bottom"), c.delete("margin-left"), c.delete("margin-block-start"), c.delete("margin-block-end"), c.delete("margin-inline-start"), c.delete("margin-inline-end"), c.set("box-sizing", ["border-box", ""])), ((f = c.get("background-clip")) == null ? void 0 : f[0]) === "text" && t.classList.add("______background-clip--text"), pe && (c.has("font-kerning") || c.set("font-kerning", ["normal", ""]), (((d = c.get("overflow-x")) == null ? void 0 : d[0]) === "hidden" || ((m = c.get("overflow-y")) == null ? void 0 : m[0]) === "hidden") && ((h = c.get("text-overflow")) == null ? void 0 : h[0]) === "ellipsis" && e.scrollWidth === e.clientWidth && c.set("text-overflow", ["clip", ""])), c.forEach(([w, y], g) => {
    i.setProperty(g, w, y);
  }), c;
}
function At(e, t) {
  var r;
  try {
    if ((r = e == null ? void 0 : e.contentDocument) != null && r.body)
      return G(e.contentDocument.body, t);
  } catch (n) {
    C("Failed to clone iframe", n);
  }
  return e.cloneNode(!1);
}
function xe(e) {
  if (e.ownerDocument)
    try {
      const a = e.toDataURL();
      if (a !== "data:,")
        return k(a, e.ownerDocument);
    } catch (a) {
    }
  const t = e.cloneNode(!1), r = e.getContext("2d"), n = t.getContext("2d");
  try {
    return r && n && n.putImageData(
      r.getImageData(0, 0, e.width, e.height),
      0,
      0
    ), t;
  } catch (a) {
    C("Failed to clone canvas", a);
  }
  return t;
}
function Nt(e) {
  return S(this, null, function* () {
    if (e.ownerDocument && !e.currentSrc && e.poster)
      return k(e.poster, e.ownerDocument);
    const t = e.cloneNode(!1);
    t.crossOrigin = "anonymous", e.currentSrc && e.currentSrc !== e.src && (t.src = e.currentSrc);
    const r = t.ownerDocument;
    if (r) {
      let n = !0;
      if (yield P(t, {
        onError: () => n = !1
      }), !n)
        return e.poster ? k(e.poster, e.ownerDocument) : t;
      t.currentTime = e.currentTime, yield new Promise((s) => {
        t.addEventListener("seeked", s, { once: !0 });
      });
      const a = r.createElement("canvas");
      a.width = e.offsetWidth, a.height = e.offsetHeight;
      try {
        const s = a.getContext("2d");
        s && s.drawImage(t, 0, 0, a.width, a.height);
      } catch (s) {
        return C("Failed to clone video", s), e.poster ? k(e.poster, e.ownerDocument) : t;
      }
      return xe(a);
    }
    return t;
  });
}
function It(e) {
  const t = e.cloneNode(!1);
  return e.currentSrc && e.currentSrc !== e.src && (t.src = e.currentSrc, t.srcset = ""), t.loading === "lazy" && (t.loading = "eager"), t;
}
function xt(e, t) {
  return Ke(e) ? xe(e) : nt(e) ? At(e, t) : D(e) ? It(e) : O(e) ? Nt(e) : e.cloneNode(!1);
}
const oe = /* @__PURE__ */ new Set([
  "symbol"
  // test/fixtures/svg.symbol.html
]);
function ae(e, t, r, n) {
  return S(this, null, function* () {
    if (A(r) && (Ze(r) || et(r)) || n.filter && !n.filter(r))
      return;
    oe.has(t.nodeName) || oe.has(r.nodeName) ? n.currentParentNodeStyle = void 0 : n.currentParentNodeStyle = n.currentNodeStyle;
    const a = yield G(r, n);
    n.isEnable("restoreScrollPosition") && kt(e, a), t.appendChild(a);
  });
}
function se(e, t, r) {
  return S(this, null, function* () {
    var a, s;
    const n = (s = A(e) ? (a = e.shadowRoot) == null ? void 0 : a.firstChild : void 0) != null ? s : e.firstChild;
    for (let o = n; o; o = o.nextSibling)
      if (!Ye(o))
        if (A(o) && rt(o) && typeof o.assignedNodes == "function") {
          const i = o.assignedNodes();
          for (let l = 0; l < i.length; l++)
            yield ae(e, t, i[l], r);
        } else
          yield ae(e, t, o, r);
  });
}
function kt(e, t) {
  if (!F(e) || !F(t))
    return;
  const { scrollTop: r, scrollLeft: n } = e;
  if (!r && !n)
    return;
  const { transform: a } = t.style, s = new DOMMatrix(a), { a: o, b: i, c: l, d: u } = s;
  s.a = 1, s.b = 0, s.c = 0, s.d = 1, s.translateSelf(-n, -r), s.a = o, s.b = i, s.c = l, s.d = u, t.style.transform = s.toString();
}
function Rt(e, t) {
  const { backgroundColor: r, width: n, height: a, style: s } = t, o = e.style;
  if (r && o.setProperty("background-color", r, "important"), n && o.setProperty("width", `${n}px`, "important"), a && o.setProperty("height", `${a}px`, "important"), s)
    for (const i in s)
      o[i] = s[i];
}
const Dt = /^[\w-:]+$/;
function G(e, t, r = !1) {
  return S(this, null, function* () {
    var i, l, u, c;
    const { ownerDocument: n, ownerWindow: a, fontFamilies: s } = t;
    if (n && Je(e))
      return n.createTextNode(e.data);
    if (n && a && A(e) && (F(e) || U(e))) {
      const f = yield xt(e, t);
      if (t.isEnable("removeAbnormalAttributes")) {
        const h = f.getAttributeNames();
        for (let w = h.length, y = 0; y < w; y++) {
          const g = h[y];
          Dt.test(g) || f.removeAttribute(g);
        }
      }
      const d = t.currentNodeStyle = Tt(e, f, r, t);
      r && Rt(f, t);
      let m = !1;
      if (t.isEnable("copyScrollbar")) {
        const h = [
          (i = d.get("overflow-x")) == null ? void 0 : i[0],
          (l = d.get("overflow-y")) == null ? void 0 : l[1]
        ];
        m = h.includes("scroll") || (h.includes("auto") || h.includes("overlay")) && (e.scrollHeight > e.clientHeight || e.scrollWidth > e.clientWidth);
      }
      return Ct(e, f, m, t), vt(e, f), (c = Te((u = d.get("font-family")) == null ? void 0 : u[0])) == null || c.forEach((h) => s.add(h)), O(e) || (yield se(e, f, t)), f;
    }
    const o = e.cloneNode(!1);
    return yield se(e, o, t), o;
  });
}
function Ft(e) {
  if (e.ownerDocument = void 0, e.ownerWindow = void 0, e.svgStyleElement = void 0, e.svgDefsElement = void 0, e.svgStyles.clear(), e.defaultComputedStyles.clear(), e.sandbox) {
    try {
      e.sandbox.remove();
    } catch (t) {
    }
    e.sandbox = void 0;
  }
  e.workers = [], e.fontFamilies.clear(), e.fontCssTexts.clear(), e.requests.clear(), e.tasks = [];
}
function Pt(e) {
  const i = e, { url: t, timeout: r, responseType: n } = i, a = re(i, ["url", "timeout", "responseType"]), s = new AbortController(), o = r ? setTimeout(() => s.abort(), r) : void 0;
  return fetch(t, T({ signal: s.signal }, a)).then((l) => {
    if (!l.ok)
      throw new Error("Failed fetch, not 2xx response", { cause: l });
    switch (n) {
      case "dataUrl":
        return l.blob().then(lt);
      case "text":
      default:
        return l.text();
    }
  }).finally(() => clearTimeout(o));
}
function _(e, t) {
  const { url: r, requestType: n = "text", responseType: a = "text", imageDom: s } = t;
  let o = r;
  const {
    timeout: i,
    acceptOfImage: l,
    requests: u,
    fetchFn: c,
    fetch: {
      requestInit: f,
      bypassingCache: d,
      placeholderImage: m
    },
    workers: h
  } = e;
  n === "image" && (M || X) && e.drawImageCount++;
  let w = u.get(r);
  if (!w) {
    d && d instanceof RegExp && d.test(o) && (o += (/\?/.test(o) ? "&" : "?") + new Date().getTime());
    const y = T({
      url: o,
      timeout: i,
      responseType: a,
      headers: n === "image" ? { accept: l } : void 0
    }, f);
    w = {
      type: n,
      resolve: void 0,
      reject: void 0,
      response: null
    }, w.response = (() => S(this, null, function* () {
      if (c && n === "image") {
        const g = yield c(r);
        if (g)
          return g;
      }
      return !M && r.startsWith("http") && h.length ? new Promise((g, b) => {
        h[u.size & h.length - 1].postMessage(T({ rawUrl: r }, y)), w.resolve = g, w.reject = b;
      }) : Pt(y);
    }))().catch((g) => {
      if (u.delete(r), n === "image" && m)
        return C("Failed to fetch image base64, trying to use placeholder image", o), typeof m == "string" ? m : m(s);
      throw g;
    }), u.set(r, w);
  }
  return w.response;
}
function ke(e, t, r, n) {
  return S(this, null, function* () {
    if (!Re(e))
      return e;
    for (const [a, s] of _t(e, t))
      try {
        const o = yield _(
          r,
          {
            url: s,
            requestType: n ? "image" : "text",
            responseType: "dataUrl"
          }
        );
        e = e.replace(Ut(a), `$1${o}$3`);
      } catch (o) {
        C("Failed to fetch css data url", a, o);
      }
    return e;
  });
}
function Re(e) {
  return /url\((['"]?)([^'"]+?)\1\)/.test(e);
}
const De = /url\((['"]?)([^'"]+?)\1\)/g;
function _t(e, t) {
  const r = [];
  return e.replace(De, (n, a, s) => (r.push([s, be(s, t)]), n)), r.filter(([n]) => !V(n));
}
function Ut(e) {
  const t = e.replace(/([.*+?^${}()|\[\]\/\\])/g, "\\$1");
  return new RegExp(`(url\\(['"]?)(${t})(['"]?\\))`, "g");
}
function $t(e, t) {
  return S(this, null, function* () {
    const {
      ownerDocument: r,
      svgStyleElement: n,
      fontFamilies: a,
      fontCssTexts: s,
      tasks: o,
      font: i
    } = t;
    if (!(!r || !n || !a.size))
      if (i && i.cssText) {
        const l = ce(i.cssText, t);
        n.appendChild(r.createTextNode(`${l}
`));
      } else {
        const l = Array.from(r.styleSheets).filter((c) => {
          try {
            return "cssRules" in c && Boolean(c.cssRules.length);
          } catch (f) {
            return C(`Error while reading CSS rules from ${c.href}`, f), !1;
          }
        });
        yield Promise.all(
          l.flatMap((c) => Array.from(c.cssRules).map((f, d) => S(this, null, function* () {
            if (Xe(f)) {
              let m = d + 1;
              const h = f.href;
              let w = "";
              try {
                w = yield _(t, {
                  url: h,
                  requestType: "text",
                  responseType: "text"
                });
              } catch (g) {
                C(`Error fetch remote css import from ${h}`, g);
              }
              const y = w.replace(
                De,
                (g, b, p) => g.replace(p, be(p, h))
              );
              for (const g of Lt(y))
                try {
                  c.insertRule(
                    g,
                    g.startsWith("@import") ? m += 1 : c.cssRules.length
                  );
                } catch (b) {
                  C("Error inserting rule from remote css import", { rule: g, error: b });
                }
            }
          })))
        ), l.flatMap((c) => Array.from(c.cssRules)).filter((c) => {
          var f;
          return ze(c) && Re(c.style.getPropertyValue("src")) && ((f = Te(c.style.getPropertyValue("font-family"))) == null ? void 0 : f.some((d) => a.has(d)));
        }).forEach((c) => {
          const f = c, d = s.get(f.cssText);
          d ? n.appendChild(r.createTextNode(`${d}
`)) : o.push(
            ke(
              f.cssText,
              f.parentStyleSheet ? f.parentStyleSheet.href : null,
              t
            ).then((m) => {
              m = ce(m, t), s.set(f.cssText, m), n.appendChild(r.createTextNode(`${m}
`));
            })
          );
        });
      }
  });
}
const Bt = /(\/\*[\s\S]*?\*\/)/gi, ie = /((@.*?keyframes [\s\S]*?){([\s\S]*?}\s*?)})/gi;
function Lt(e) {
  if (e == null)
    return [];
  const t = [];
  let r = e.replace(Bt, "");
  for (; ; ) {
    const s = ie.exec(r);
    if (!s)
      break;
    t.push(s[0]);
  }
  r = r.replace(ie, "");
  const n = /@import[\s\S]*?url\([^)]*\)[\s\S]*?;/gi, a = new RegExp(
    "((\\s*?(?:\\/\\*[\\s\\S]*?\\*\\/)?\\s*?@media[\\s\\S]*?){([\\s\\S]*?)}\\s*?})|(([\\s\\S]*?){([\\s\\S]*?)})",
    "gi"
  );
  for (; ; ) {
    let s = n.exec(r);
    if (s)
      a.lastIndex = n.lastIndex;
    else if (s = a.exec(r), s)
      n.lastIndex = a.lastIndex;
    else
      break;
    t.push(s[0]);
  }
  return t;
}
const Mt = /url\([^)]+\)\s*format\((["']?)([^"']+)\1\)/g, Ot = /src:\s*(?:url\([^)]+\)\s*format\([^)]+\)[,;]\s*)+/g;
function ce(e, t) {
  const { font: r } = t, n = r ? r == null ? void 0 : r.preferredFormat : void 0;
  return n ? e.replace(Ot, (a) => {
    for (; ; ) {
      const [s, , o] = Mt.exec(a) || [];
      if (!o)
        return "";
      if (o === n)
        return `src: ${s};`;
    }
  }) : e;
}
function Wt(e, t) {
  if (D(e)) {
    const r = e.currentSrc || e.src;
    if (!V(r))
      return [
        _(t, {
          url: r,
          imageDom: e,
          requestType: "image",
          responseType: "dataUrl"
        }).then((n) => {
          n && (e.srcset = "", e.dataset.originalSrc = r, e.src = n || "");
        })
      ];
    (M || X) && t.drawImageCount++;
  } else if (U(e) && !V(e.href.baseVal)) {
    const r = e.href.baseVal;
    return [
      _(t, {
        url: r,
        imageDom: e,
        requestType: "image",
        responseType: "dataUrl"
      }).then((n) => {
        n && (e.dataset.originalSrc = r, e.href.baseVal = n || "");
      })
    ];
  }
  return [];
}
const jt = [
  "background-image",
  "border-image-source",
  "-webkit-border-image",
  "-webkit-mask-image",
  "list-style-image"
];
function qt(e, t) {
  return jt.map((r) => {
    const n = e.getPropertyValue(r);
    return !n || n === "none" ? null : ((M || X) && t.drawImageCount++, ke(n, null, t, !0).then((a) => {
      !a || n === a || e.setProperty(
        r,
        a,
        e.getPropertyPriority(r)
      );
    }));
  }).filter(Boolean);
}
function Vt(e, t) {
  var i;
  const { ownerDocument: r, svgDefsElement: n } = t, a = (i = e.getAttribute("href")) != null ? i : e.getAttribute("xlink:href");
  if (!a)
    return [];
  const [s, o] = a.split("#");
  if (o) {
    const l = `#${o}`, u = r == null ? void 0 : r.querySelector(`svg ${l}`);
    if (s && e.setAttribute("href", l), n != null && n.querySelector(l))
      return [];
    if (u)
      return n == null || n.appendChild(u.cloneNode(!0)), [];
    if (s)
      return [
        _(t, {
          url: s,
          responseType: "text"
        }).then((c) => {
          n == null || n.insertAdjacentHTML("beforeend", c);
        })
      ];
  }
  return [];
}
function Fe(e, t) {
  const { tasks: r } = t;
  A(e) && ((D(e) || ye(e)) && r.push(...Wt(e, t)), Ge(e) && r.push(...Vt(e, t))), F(e) && r.push(...qt(e.style, t)), e.childNodes.forEach((n) => {
    Fe(n, t);
  });
}
function Ht(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t);
    if (A(r.node) && U(r.node))
      return r.node;
    const {
      ownerDocument: n,
      log: a,
      tasks: s,
      svgStyleElement: o,
      svgDefsElement: i,
      svgStyles: l,
      font: u,
      progress: c,
      autoDestruct: f,
      onCloneNode: d,
      onEmbedNode: m,
      onCreateForeignObjectSvg: h
    } = r;
    a.time("clone node");
    const w = yield G(r.node, r, !0);
    if (o && n) {
      let E = "";
      l.forEach((v, I) => {
        E += `${v.join(`,
`)} {
  ${I}
}
`;
      }), o.appendChild(n.createTextNode(E));
    }
    a.timeEnd("clone node"), d == null || d(w), u !== !1 && A(w) && (a.time("embed web font"), yield $t(w, r), a.timeEnd("embed web font")), a.time("embed node"), Fe(w, r);
    const y = s.length;
    let g = 0;
    const b = () => S(this, null, function* () {
      for (; ; ) {
        const E = s.pop();
        if (!E)
          break;
        try {
          yield E;
        } catch (v) {
          C("Failed to run task", v);
        }
        c == null || c(++g, y);
      }
    });
    c == null || c(g, y), yield Promise.all([...Array(4)].map(b)), a.timeEnd("embed node"), m == null || m(w);
    const p = zt(w, r);
    return i && p.insertBefore(i, p.children[0]), o && p.insertBefore(o, p.children[0]), f && Ft(r), h == null || h(p), p;
  });
}
function zt(e, t) {
  const { width: r, height: n } = t, a = Se(r, n, e.ownerDocument), s = a.ownerDocument.createElementNS(a.namespaceURI, "foreignObject");
  return s.setAttributeNS(null, "x", "0%"), s.setAttributeNS(null, "y", "0%"), s.setAttributeNS(null, "width", "100%"), s.setAttributeNS(null, "height", "100%"), s.append(e), a.appendChild(s), a;
}
function Y(e, t) {
  return S(this, null, function* () {
    var o;
    const r = yield N(e, t), n = yield Ht(r), a = Ee(n, r.isEnable("removeControlCharacter"));
    r.autoDestruct || (r.svgStyleElement = Ae(r.ownerDocument), r.svgDefsElement = (o = r.ownerDocument) == null ? void 0 : o.createElementNS(j, "defs"), r.svgStyles.clear());
    const s = k(a, n.ownerDocument);
    return yield wt(s, r);
  });
}
function Yt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { log: n, type: a, quality: s, dpi: o } = r, i = yield Y(r);
    n.time("canvas to blob");
    const l = yield it(i, a, s);
    if (["image/png", "image/jpeg"].includes(a) && o) {
      const u = yield ut(l.slice(0, 33));
      let c = new Uint8Array(u);
      return a === "image/png" ? c = he(c, o) : a === "image/jpeg" && (c = ue(c, o)), n.timeEnd("canvas to blob"), new Blob([c, l.slice(33)], { type: a });
    }
    return n.timeEnd("canvas to blob"), l;
  });
}
function $(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { log: n, quality: a, type: s, dpi: o } = r, i = yield Y(r);
    n.time("canvas to data url");
    let l = i.toDataURL(s, a);
    if (["image/png", "image/jpeg"].includes(s) && o && we && Ve) {
      const [u, c] = l.split(",");
      let f = 0, d = !1;
      if (s === "image/png") {
        const p = je(c);
        p >= 0 ? (f = Math.ceil((p + 28) / 3) * 4, d = !0) : f = 33 / 3 * 4;
      } else
        s === "image/jpeg" && (f = 18 / 3 * 4);
      const m = c.substring(0, f), h = c.substring(f), w = window.atob(m), y = new Uint8Array(w.length);
      for (let p = 0; p < y.length; p++)
        y[p] = w.charCodeAt(p);
      const g = s === "image/png" ? he(y, o, d) : ue(y, o), b = window.btoa(String.fromCharCode(...g));
      l = [u, ",", b, h].join("");
    }
    return n.timeEnd("canvas to data url"), l;
  });
}
function Xt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { width: n, height: a, ownerDocument: s } = r, o = yield $(r), i = Se(n, a, s), l = i.ownerDocument.createElementNS(i.namespaceURI, "image");
    return l.setAttributeNS(null, "href", o), l.setAttributeNS(null, "height", "100%"), l.setAttributeNS(null, "width", "100%"), i.appendChild(l), Ee(i, r.isEnable("removeControlCharacter"));
  });
}
function Jt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), { ownerDocument: n, width: a, height: s, scale: o, type: i } = r, l = i === "image/svg+xml" ? yield Xt(r) : yield $(r), u = k(l, n);
    return u.width = Math.floor(a * o), u.height = Math.floor(s * o), u.style.width = `${a}px`, u.style.height = `${s}px`, u;
  });
}
function Kt(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/jpeg" }))
    );
  });
}
function Qt(e, t) {
  return S(this, null, function* () {
    const r = yield N(e, t), n = yield Y(r);
    return n.getContext("2d").getImageData(0, 0, n.width, n.height).data;
  });
}
function Zt(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/png" }))
    );
  });
}
function er(e, t) {
  return S(this, null, function* () {
    return $(
      yield N(e, R(T({}, t), { type: "image/webp" }))
    );
  });
}
window.modernScreenshot = { domToBlob: Yt };
})();
/* shot:end */
</script>
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

# Additions on top of TEMPLATE, injected before </style> so TEMPLATE stays a verbatim copy of template_shell.py.
# fit() measures .hero.fit as inline-block, but a flex item is always blockified and stretches to the column,
# so wide numbers were never shrunk. Shrink-wrapping it lets the measurement see the real text width.
EXTRA_CSS = ''


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

    def hero(kind, text):
        """Opening tag for a name/diagnosis hero, shrunk so its longest word stays on one line."""
        longest = max((len(w) for w in str(text).split()), default=0)
        if longest <= 9:
            return f'<div class="hero {kind}">'
        style = f' style="font-size:{3.4 * 13 / longest:.2f}em"' if longest > 13 else ''
        return f'<div class="hero {kind} sm"{style}>'

    def more_btn(count):
        return f'<button class="more chrome" data-more>Show all {count}</button>' if count > 5 else ''

    # optional slides can drop out, so never let two neighbors share a theme
    swap = {'pink': 'lav', 'lav': 'lilac', 'lilac': 'white', 'white': 'lilac', 'cobalt': 'ink', 'ink': 'night', 'night': 'ink'}
    last_theme = [None]
    def slide(theme, body, name):
        if theme == last_theme[0]:
            theme = swap[theme]
        last_theme[0] = theme
        return f'<section class="slide t-{theme}" data-name="{name}"><div class="card"><div class="body">{body}</div><footer class="mark"><span>wrap2026.com</span><span>WhatsApp · {year}</span></footer></div></section>'

    slides = []

    # Intro
    slides.append(slide('cobalt', f'''
        <div class="intro">
          <h1 class="stretch"><span>Wrapped</span><span>{year}</span></h1>
          <div class="thread">
            <div class="bub r a1">you up?</div>
            <div class="bub r a2">I went through your WhatsApp.</div>
            <div class="bub r a3">Your {year} texting habits, exposed.</div>
          </div>
          <p class="hint chrome a4">Tap to start</p>
        </div>''', 'intro'))

    # Total messages
    slides.append(slide('lilac', f'''
        <div class="pile" aria-hidden="true">{''.join('<i class="s"></i>' if (k * s[1]) % max(s[0],1) < s[1] else '<i></i>' for k in range(min(msgs_per_day, 240)))}</div>
        <p class="lead">This year you sent and received</p>
        <div class="hero">{num(s[0])}</div>
        <p class="after">{plural(s[0], 'message')}. That's the total damage.</p>
        <div class="split">
          <div><b>{msgs_per_day:,}</b><span>a day</span></div>
          <div><b>{s[1]:,}</b><span>you sent</span></div>
          <div><b>{s[2]:,}</b><span>you got</span></div>
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
                c = d['daily_counts'].get(cur.strftime('%Y-%m-%d'), 0)
                lvl = 0 if c == 0 else 1 if c <= max_count * .15 else 2 if c <= max_count * .35 else 3 if c <= max_count * .65 else 4
                cells.append(f'<i class="l{lvl}" data-tip="{c:,} {"message" if c == 1 else "messages"} on {cur.strftime("%b %-d")}"></i>')
            month_rows.append(f'<div class="mrow"><span>{ddate(year, m, 1).strftime("%b")}</span><div class="dots">{"".join(cells)}</div></div>')
        slides.append(slide('ink', f'''
            <p class="lead">Your year, one dot per day.</p>
            <div class="year">{"".join(month_rows)}</div>
            <div class="split">
              <div><b>{d['avg_daily']:,}</b><span>a day, on average</span></div>
              <div><b>{esc(d['busiest_month'])}</b><span>busiest month</span></div>
              <div><b>{d['quiet_days']:,}</b><span>quiet {plural(d['quiet_days'], 'day')}</span></div>
            </div>''', 'year'))

    # Your #1 and inner circle
    if top:
        first = get_name(top[0][0], contacts)
        slides.append(slide('pink', f'''
            {avatar(first, 'xl')}
            <p class="lead">The person you texted most</p>
            {hero('name', first)}{esc(first)}</div>
            <p class="after">{num(top[0][1])} {plural(top[0][1], 'message')}. {(lambda p: f'{p}%' if p else 'Less than 1%')(round(top[0][1] / max(s[0], 1) * 100))} of all your messages.</p>''', 'number-one'))
        top5 = top[:5]
        mx = top5[0][1] or 1
        slides.append(slide('lilac', f'''
            {stack([get_name(h, contacts) for h, *_ in top5])}
            <p class="lead">Your inner circle</p>
            {rows([(n(h), f'{t:,}', t / mx) for h, t, *_ in top5])}''', 'inner-circle'))

    # New phone, who dis? (new people this year vs. people from last year)
    nc = d.get('newcomer')
    if nc:
        circle = f"{nc['new']:,} new {plural(nc['new'], 'person', 'people')} this year."
        if nc['kept']:  # nobody from last year: say nothing rather than '0 ... still here'
            circle += f" {nc['kept']:,} from last year {plural(nc['kept'], 'is', 'are')} still here."
        slides.append(slide('white', f'''
            {avatar(nc["name"], 'xl')}
            <p class="lead">New phone, who dis?</p>
            {hero('name', nc["name"])}{esc(nc["name"])}</div>
            <p class="after">{num(nc["count"])} {plural(nc["count"], 'message')}, and you'd never texted before this year.</p>
            <p class="after rule">{circle}</p>''', 'newcomer'))

    # Groups
    gs = d['group_stats']
    if gs['count'] > 0 and gs['total'] > 0 and d['group_leaderboard']:
        yours = round(gs['sent'] / max(gs['total'], 1) * 100)
        role = "a lurker" if yours < 40 else "the main character" if yours > 60 else "a solid contributor"
        lb = d['group_leaderboard'][:5]
        gmx = lb[0]['msg_count'] if lb else 1
        slides.append(slide('cobalt', f'''
            {stack([gc['name'] for gc in lb]) if lb else '<div class="sticker" aria-hidden="true">👥</div>'}
            <p class="lead">You were in {num(gs['count'])} {plural(gs['count'], 'group chat')} and sent {yours}% of the messages. You're {role}.</p>
            {rows([(esc(gc['name']), f'{gc["msg_count"]:,}', gc["msg_count"] / gmx) for gc in lb]) if lb else '<p class="after">No group data.</p>'}''', 'groups'))

    # Personality
    glyph = {'NOCTURNAL': '🌙', 'TERMINALLY': '📱', 'TOO COOL': '🧊', 'POPULAR': '💅', 'YAPPER': '🗣️', 'STARTER': '🎬', 'WAITER': '⏳'}
    g = next((v for k, v in glyph.items() if k in ptype), '🫡')
    slides.append(slide('night', f'''
        <div class="sticker" aria-hidden="true">{g}</div>
        <p class="lead">Your texting personality</p>
        {hero('diag', ptype)}{esc(ptype.lower())}</div>
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
    verdict = "Basically instant." if r < 2 else "Normal. Respectable, even." if r < 15 else "Slow. People have moved on by then."
    slides.append(slide('white', f'''
        <div class="thread big">
          <div class="bub r">you there?</div>
          <div class="bub s typing"><i></i><i></i><i></i></div>
        </div>
        <p class="lead">Your typical reply takes</p>
        <div class="hero">{num(round(r * 60)) if r < 1 else num(round(r))}<small>{"sec" if r < 1 else "min"}</small></div>
        <p class="after">{verdict} Half your replies are faster than that.</p>''', 'response'))

    # Peak hours
    peak_day = f'<p class="after">on {esc(d["day"])}s.</p>' if d.get('day') not in (None, '', '???') else ''
    slides.append(slide('lav', f'''
        <div class="clock" style="--a:{(hr % 12) * 30}deg" aria-hidden="true">{''.join(f'<i style="--t:{k*30}deg"></i>' for k in range(12))}<b></b><u></u></div>
        <p class="lead">You text most at</p>
        <div class="hero">{hr_str}</div>
        {peak_day}''', 'peak'))

    # 3am bestie
    if d['late']:
        ln = d['late'][0]
        slides.append(slide('night', f'''
            <div class="moon" aria-hidden="true"></div>
            <div class="stars" aria-hidden="true">{''.join(f'<i style="left:{x}%;top:{y}%;--d:{k}"></i>' for k, (x, y) in enumerate([(8, 14), (30, 30), (52, 9), (18, 44), (66, 36), (40, 52), (84, 54), (12, 62)]))}</div>
            <p class="lead">Between midnight and 5am, you texted</p>
            {hero('name', get_name(ln[0], contacts))}{n(ln[0])}</div>
            <p class="after">{num(ln[1])} {plural(ln[1], 'time')}. Go to sleep.</p>''', 'three-am'))

    # Busiest day
    if d['busiest_day']:
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
            <p class="after">{num(busiest_count)} {plural(busiest_count, 'message')} in one day{busiest_vs}. What happened?</p>''', 'busiest-day'))

    # Biggest fan / down bad
    if d['fan']:
        f = d['fan'][0]
        slides.append(slide('cobalt', f'''
            {avatar(get_name(f[0], contacts), 'xl')}
            <p class="lead">Your biggest fan</p>
            {hero('name', get_name(f[0], contacts))}{n(f[0])}</div>
            <p class="after">texts you {num(round(f[1]/f[2], 1), 'dec', '×')} more than you text them.</p>
            <div class="vs"><div style="--w:1"><span>{n(f[0])}</span><b>{f[1]:,}</b></div><div style="--w:{f[2]/max(f[1],1):.3f}"><span>You</span><b>{f[2]:,}</b></div></div>''', 'biggest-fan'))
    if d['simp']:
        si = d['simp'][0]
        slides.append(slide('pink', f'''
            {avatar(get_name(si[0], contacts), 'xl')}
            <p class="lead">You're down bad for</p>
            {hero('name', get_name(si[0], contacts))}{n(si[0])}</div>
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
            <p class="after">They see your name and stop what they're doing.</p>''', 'fast-responders'))

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
                body += '<p class="lead">You usually reach out first</p>' + tight(rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in you_out]))
            if they_in:
                body += '<p class="lead gap">They usually reach out first</p>' + tight(rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in they_in]))
            slides.append(slide('cobalt', body, 'who-reaches-out'))

    # Heating up / ghosted
    if d.get('heating'):
        ht = d['heating'][:5]
        hmx = max((b - a) for _, a, b in ht) or 1
        slides.append(slide('pink', f'''
            <div class="sticker" aria-hidden="true">🔥</div>
            <p class="lead">Heating up since June</p>
            {rows([(n(h), f'+{b-a:,}', (b - a) / hmx) for h, a, b in ht])}
            <p class="after">More messages since June than before. Getting stronger.</p>''', 'heating-up'))
    if d.get('ghosted'):
        gh = d['ghosted'][:5]
        gmx2 = max(b for _, b, _ in gh) or 1
        slides.append(slide('lav', f'''
            <div class="sticker" aria-hidden="true">👻</div>
            <p class="lead">They chose peace after June</p>
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
    one = f'<div class="one">{avatar(get_name(top[0][0], contacts))}<div><b>{n(top[0][0])}</b><span>My #1, {top[0][1]:,} {plural(top[0][1], "message")}</span></div></div>' if top else ''
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
          <footer class="mark"><span>wrap2026.com</span><span>WhatsApp · {year}</span></footer>
        </div>
      </div>
    </section>''')

    html_out = TEMPLATE.replace('</style>', EXTRA_CSS + '\n</style>', 1).replace('__TITLE__', f'WhatsApp Wrapped {year}') \
                       .replace('__FILE__', f'whatsapp_wrapped_{year}') \
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
    print("  WhatsApp WRAPPED 2026 | wrap2026.com")
    print("="*50 + "\n")

    print("[*] Checking access...")
    check_access()
    print(f"    ✓ Found database: {WHATSAPP_DB.replace(os.path.expanduser('~'), '~')}")

    print("[*] Loading contacts...")
    contacts = extract_contacts()
    print(f"    ✓ {len(contacts)} indexed")

    ts_start, ts_end, ts_jun = (TS_2025, TS_2025_END, TS_JUN_2025) if args.use_2025 else (TS_2026, TS_2026_END, TS_JUN_2026)
    year = "2025" if args.use_2025 else "2026"

    test = q(f"SELECT COUNT(*) FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{TS_2026}")[0][0]
    if test < 100 and not args.use_2025:
        print(f"    ⚠️  {test} msgs in 2026, using 2025")
        ts_start, ts_end, ts_jun = TS_2025, TS_2025_END, TS_JUN_2025
        year = "2025"

    # Set output filename based on year
    output_file = args.output or f'whatsapp_wrapped_{year}.html'

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
