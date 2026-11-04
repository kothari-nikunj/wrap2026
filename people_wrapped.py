#!/usr/bin/env python3
"""
People Wrapped 2026 - AI-powered analysis of your top messaging relationships.

## Quick Start

1. Download this file
2. Start Claude Code with: `claude --dangerously-skip-permissions`
3. Say: "Run python3 people_wrapped.py"
4. Wait ~10 minutes for extraction + AI summaries
5. Open people_wrapped_2026.html in your browser

That's it! No API key needed - Claude Code generates the summaries.

Note: The --dangerously-skip-permissions flag is needed because Claude Code writes
25 summary files. Without it, you'd have to approve each file write individually.

## Prerequisites

- macOS with iMessage and/or WhatsApp
- Full Disk Access for Terminal (System Settings → Privacy & Security → Full Disk Access)
- Claude Code

## How It Works

1. Script extracts your top 25 contacts from iMessage/WhatsApp databases
2. Script prints "CLAUDE CODE: Please generate summaries..."
3. Claude Code reads the message files and generates personalized summaries
4. Script builds a beautiful swipeable HTML report

The "trick" is that Claude Code itself IS the AI - no external API call needed.

---

## FOR CLAUDE CODE

When this script prints "CLAUDE CODE: Please generate summaries...", YOU are the AI.
Read each JSON file and write a summary directly. Do not write Python scripts or call
any API - you ARE the language model, just read the messages and write the summary.

For each contact:
1. Read the JSON file (use limit=2000 for large files)
2. Write a personal summary based on the messages you see
3. Save it back to the JSON with the summary field added

### CRITICAL: What makes a GOOD summary vs BAD summary

BAD summaries use generic adjectives and describe personality traits:
- "relentless hustle", "intellectually stimulating", "vibe-coded networking"
- "unwavering support", "infectious energy", "thoughtful approach"
- These could be written WITHOUT reading the messages - that's how you know they're bad

GOOD summaries quote actual messages and describe specific events:
- Pull their exact words in quotes: when they said "...", their reply "..."
- Reference specific things from the conversation: the trip, the project, the decision
- Tell what HAPPENED, not what they're LIKE

The test: Could this summary be written without reading the messages?
- If YES → it's generic, rewrite it
- If NO → it's grounded in the actual conversation, keep it

RULES:
1. QUOTE their words - find the memorable lines from the actual messages
2. BE SPECIFIC - the trip to X, the project about Y, the debate over Z
3. AVOID generic adjectives - no "amazing", "incredible", "inspiring"
4. TELL WHAT HAPPENED - events and moments, not personality descriptions
5. BE HONEST - if the messages are mostly logistics, say that; don't invent depth

IMPORTANT: Do NOT use Task tool, parallel agents, or write Python scripts.
YOU are the AI. Just read and write directly.
Use /model sonnet for larger context. After all summaries: python3 people_wrapped.py build

---
"""

import sqlite3, os, sys, re, subprocess, argparse, glob, threading, time, base64, json
from datetime import datetime, timedelta
from pathlib import Path

# Database paths
IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESSBOOK_DIR = os.path.expanduser("~/Library/Application Support/AddressBook")
WHATSAPP_PATHS = [
    os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/com.whatsapp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/desktop.WhatsApp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
]

WHATSAPP_DB = None
DATA_DIR = "people_wrapped_data"

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
            print(f"\r  {frame} {self.message}", end='', flush=True)
            time.sleep(0.1)
            i += 1

    def start(self, message=None):
        if message:
            self.message = message
        self.spinning = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()

    def stop(self, final_message=None):
        self.spinning = False
        if self.thread:
            self.thread.join()
        if final_message:
            print(f"\r  ✓ {final_message}".ljust(60))
        else:
            print()

# Cocoa offset for timestamp conversion
COCOA_OFFSET = 978307200

def extract_text_from_attributed_body(data):
    """Extract plain text from iMessage attributedBody blob."""
    if not data:
        return None
    try:
        idx = data.find(b'NSString')
        if idx != -1:
            match = re.search(b'\\x95\\x84\\x01\\+.(.*?)\\x86', data[idx:], re.DOTALL)
            if match:
                text = match.group(1)
                try:
                    return text.decode('utf-8', errors='ignore').strip()
                except:
                    pass
            match = re.search(b'\\x01\\+.(.*?)(?:\\x86|\\x00\\x00)', data[idx:], re.DOTALL)
            if match:
                text = match.group(1)
                try:
                    return text.decode('utf-8', errors='ignore').strip()
                except:
                    pass
    except:
        pass
    return None

def get_year_timestamps(year):
    """Get start/end timestamps for a year in both iMessage and WhatsApp formats."""
    year = int(year)
    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year, 12, 31, 23, 59, 59)

    start_unix = int(start_dt.timestamp())
    end_unix = int(end_dt.timestamp())

    start_imessage = start_unix
    end_imessage = end_unix

    start_whatsapp = start_unix - COCOA_OFFSET
    end_whatsapp = end_unix - COCOA_OFFSET

    return {
        'start_unix': start_unix,
        'end_unix': end_unix,
        'start_imessage': start_imessage,
        'end_imessage': end_imessage,
        'start_whatsapp': start_whatsapp,
        'end_whatsapp': end_whatsapp,
    }

def normalize_phone(phone):
    if not phone: return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    elif len(digits) > 10:
        return digits
    return digits[-10:] if len(digits) >= 10 else (digits if len(digits) >= 7 else None)

def extract_imessage_contacts():
    """Extract contacts from macOS AddressBook with their record IDs for photo matching."""
    contacts = {}
    contact_record_ids = {}
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
                    if digits:
                        contacts[digits] = name
                        contact_record_ids[digits] = owner
                        if len(digits) >= 10:
                            contacts[digits[-10:]] = name
                            contact_record_ids[digits[-10:]] = owner
                        if len(digits) >= 7:
                            contacts[digits[-7:]] = name
                            contact_record_ids[digits[-7:]] = owner
                        if len(digits) == 11 and digits.startswith('1'):
                            contacts[digits[1:]] = name
                            contact_record_ids[digits[1:]] = owner
            for owner, email in conn.execute("SELECT ZOWNER, ZADDRESS FROM ZABCDEMAILADDRESS WHERE ZADDRESS IS NOT NULL"):
                if owner in people:
                    key = email.lower().strip()
                    contacts[key] = people[owner]
                    contact_record_ids[key] = owner
            conn.close()
        except: pass
    return contacts, contact_record_ids

def extract_whatsapp_contacts():
    """Extract contact names from WhatsApp's push names and chat session partner names."""
    contacts = {}
    if not WHATSAPP_DB:
        return contacts
    try:
        conn = sqlite3.connect(WHATSAPP_DB)
        for row in conn.execute("SELECT ZJID, ZPUSHNAME FROM ZWAPROFILEPUSHNAME WHERE ZPUSHNAME IS NOT NULL"):
            jid, name = row
            if jid and name:
                contacts[jid] = name
        for row in conn.execute("SELECT ZCONTACTJID, ZPARTNERNAME FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND ZPARTNERNAME IS NOT NULL"):
            jid, name = row
            if jid and name and jid not in contacts:
                contacts[jid] = name
        conn.close()
    except:
        pass
    return contacts

def get_contact_photo(record_id):
    """Get contact photo as base64 string from AddressBook."""
    if not record_id:
        return None

    search_patterns = [
        os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "Images", f"{record_id}"),
        os.path.join(ADDRESSBOOK_DIR, "Images", f"{record_id}"),
    ]

    for pattern in search_patterns:
        matches = glob.glob(pattern)
        for path in matches:
            if os.path.isfile(path):
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                        if data[:8] == b'\x89PNG\r\n\x1a\n':
                            mime = 'image/png'
                        elif data[:2] == b'\xff\xd8':
                            mime = 'image/jpeg'
                        else:
                            mime = 'image/jpeg'
                        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
                except:
                    pass
    return None

def get_name_imessage(handle, contacts):
    if '@' in handle:
        lookup = handle.lower().strip()
        if lookup in contacts: return contacts[lookup]
        return handle.split('@')[0]
    digits = re.sub(r'\D', '', str(handle))
    if digits in contacts: return contacts[digits]
    if len(digits) == 11 and digits.startswith('1'):
        if digits[1:] in contacts: return contacts[digits[1:]]
    if len(digits) >= 10 and digits[-10:] in contacts:
        return contacts[digits[-10:]]
    if len(digits) >= 7 and digits[-7:] in contacts:
        return contacts[digits[-7:]]
    return handle

def get_record_id_for_handle(handle, contact_record_ids):
    """Get AddressBook record ID for a handle."""
    # URN-style identifiers (business accounts) don't have AddressBook records
    if handle.startswith('urn:'):
        return None
    if '@' in handle:
        lookup = handle.lower().strip()
        if lookup in contact_record_ids:
            return contact_record_ids[lookup]
        return None
    digits = re.sub(r'\D', '', str(handle))
    if digits in contact_record_ids:
        return contact_record_ids[digits]
    if len(digits) == 11 and digits.startswith('1'):
        if digits[1:] in contact_record_ids:
            return contact_record_ids[digits[1:]]
    if len(digits) >= 10 and digits[-10:] in contact_record_ids:
        return contact_record_ids[digits[-10:]]
    if len(digits) >= 7 and digits[-7:] in contact_record_ids:
        return contact_record_ids[digits[-7:]]
    return None

def get_name_whatsapp(jid, contacts):
    if not jid:
        return "Unknown"
    if jid in contacts:
        return contacts[jid]
    if '@' in jid:
        phone = jid.split('@')[0]
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone.startswith('1'):
            return f"+1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        return f"+{phone}"
    return jid

def find_whatsapp_database():
    """Find the WhatsApp database path."""
    for path in WHATSAPP_PATHS:
        if os.path.exists(path):
            return path
    return None

def check_access():
    """Check access to databases. Returns (has_imessage, has_whatsapp)."""
    global WHATSAPP_DB

    has_imessage = False
    has_whatsapp = False

    if os.path.exists(IMESSAGE_DB):
        try:
            conn = sqlite3.connect(IMESSAGE_DB)
            conn.execute("SELECT 1 FROM message LIMIT 1")
            conn.close()
            has_imessage = True
        except:
            pass

    WHATSAPP_DB = find_whatsapp_database()
    if WHATSAPP_DB:
        try:
            conn = sqlite3.connect(WHATSAPP_DB)
            conn.execute("SELECT 1 FROM ZWAMESSAGE LIMIT 1")
            conn.close()
            has_whatsapp = True
        except:
            pass

    if not has_imessage and not has_whatsapp:
        print("\n[!] ACCESS DENIED - Neither iMessage nor WhatsApp accessible")
        print("   System Settings -> Privacy & Security -> Full Disk Access -> Add Terminal")
        subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles'])
        sys.exit(1)

    return has_imessage, has_whatsapp

def count_addressbook_photos():
    """Count available contact photos."""
    count = 0
    search_patterns = [
        os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "Images", "*"),
        os.path.join(ADDRESSBOOK_DIR, "Images", "*"),
    ]
    seen = set()
    for pattern in search_patterns:
        for path in glob.glob(pattern):
            if os.path.isfile(path) and path not in seen:
                seen.add(path)
                count += 1
    return count

def q_imessage(sql):
    conn = sqlite3.connect(IMESSAGE_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def q_whatsapp(sql):
    conn = sqlite3.connect(WHATSAPP_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def get_top_contacts_combined(timestamps, top_n, has_imessage, has_whatsapp, imessage_contacts, whatsapp_contacts, contact_record_ids):
    """Get top N contacts by message count across both platforms."""
    contacts_data = {}
    phone_to_name = {}

    ts_start_im = timestamps['start_imessage']
    ts_end_im = timestamps['end_imessage']
    ts_start_wa = timestamps['start_whatsapp']
    ts_end_wa = timestamps['end_whatsapp']

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

    if has_imessage:
        rows = q_imessage(f"""{one_on_one_cte}
            SELECT h.id, COUNT(*) t, SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.is_from_me=0 THEN 1 ELSE 0 END)
            FROM message m JOIN handle h ON m.handle_id=h.ROWID
            WHERE (m.date/1000000000+{COCOA_OFFSET}) BETWEEN {ts_start_im} AND {ts_end_im}
            AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
            AND NOT (LENGTH(REPLACE(REPLACE(h.id, '+', ''), '-', '')) BETWEEN 5 AND 6 AND REPLACE(REPLACE(h.id, '+', ''), '-', '') GLOB '[0-9]*')
            AND h.id NOT LIKE 'urn:%'
            GROUP BY h.id ORDER BY t DESC LIMIT 100
        """)
        for h, t, s, r in rows:
            name = get_name_imessage(h, imessage_contacts)
            record_id = get_record_id_for_handle(h, contact_record_ids)
            if name not in contacts_data:
                contacts_data[name] = {
                    'name': name,
                    'total': 0,
                    'sent': 0,
                    'received': 0,
                    'handles': {},
                    'record_id': record_id,
                }
            contacts_data[name]['total'] += t
            contacts_data[name]['sent'] += s
            contacts_data[name]['received'] += r
            contacts_data[name]['handles']['imessage'] = h
            if record_id and not contacts_data[name]['record_id']:
                contacts_data[name]['record_id'] = record_id
            normalized = normalize_phone(h)
            if normalized:
                phone_to_name[normalized] = name

    if has_whatsapp:
        wa_cte = """
            WITH dm_sessions AS (
                SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0
            ),
            dm_messages AS (
                SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
                FROM ZWAMESSAGE m JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
            )
        """
        rows = q_whatsapp(f"""{wa_cte}
            SELECT dm.ZCONTACTJID, COUNT(*) t, SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END)
            FROM ZWAMESSAGE m JOIN dm_messages dm ON m.Z_PK = dm.msg_id
            WHERE m.ZMESSAGEDATE BETWEEN {ts_start_wa} AND {ts_end_wa}
            GROUP BY dm.ZCONTACTJID ORDER BY t DESC LIMIT 100
        """)
        for h, t, s, r in rows:
            wa_phone = None
            if h and '@' in h:
                wa_phone = normalize_phone(h.split('@')[0])

            merge_name = None
            if wa_phone and wa_phone in phone_to_name:
                merge_name = phone_to_name[wa_phone]

            if not merge_name and wa_phone:
                ab_name = imessage_contacts.get(wa_phone)
                if ab_name and ab_name in contacts_data:
                    merge_name = ab_name

            if merge_name and merge_name in contacts_data:
                contacts_data[merge_name]['total'] += t
                contacts_data[merge_name]['sent'] += s
                contacts_data[merge_name]['received'] += r
                contacts_data[merge_name]['handles']['whatsapp'] = h
            else:
                name = get_name_whatsapp(h, whatsapp_contacts)
                if wa_phone:
                    ab_name = imessage_contacts.get(wa_phone)
                    if ab_name:
                        name = ab_name
                if name not in contacts_data:
                    contacts_data[name] = {
                        'name': name,
                        'total': 0,
                        'sent': 0,
                        'received': 0,
                        'handles': {},
                        'record_id': get_record_id_for_handle(wa_phone, contact_record_ids) if wa_phone else None,
                    }
                contacts_data[name]['total'] += t
                contacts_data[name]['sent'] += s
                contacts_data[name]['received'] += r
                contacts_data[name]['handles']['whatsapp'] = h

    sorted_contacts = sorted(contacts_data.values(), key=lambda x: -x['total'])[:top_n]

    for contact in sorted_contacts:
        contact['photo'] = get_contact_photo(contact['record_id'])

    return sorted_contacts

def get_messages_for_contact(contact, timestamps, has_imessage, has_whatsapp):
    """Get all messages for a contact, pre-filtered for analysis."""
    messages = []

    ts_start_im = timestamps['start_imessage']
    ts_end_im = timestamps['end_imessage']
    ts_start_wa = timestamps['start_whatsapp']
    ts_end_wa = timestamps['end_whatsapp']

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

    if has_imessage and 'imessage' in contact['handles']:
        handle = contact['handles']['imessage']
        handle_escaped = handle.replace("'", "''")
        chat_query = f"""
            SELECT c.ROWID
            FROM chat c
            JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
            JOIN handle h ON chj.handle_id = h.ROWID
            WHERE h.id = '{handle_escaped}'
            GROUP BY c.ROWID
            HAVING COUNT(*) = 1
        """
        rows = q_imessage(f"""
            WITH target_chats AS ({chat_query})
            SELECT m.text, m.attributedBody, m.is_from_me, (m.date/1000000000+{COCOA_OFFSET}) as ts
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE cmj.chat_id IN (SELECT ROWID FROM target_chats)
            AND (m.date/1000000000+{COCOA_OFFSET}) BETWEEN {ts_start_im} AND {ts_end_im}
            AND (m.text IS NOT NULL OR m.attributedBody IS NOT NULL)
            ORDER BY m.date
        """)
        for text, attributed_body, is_from_me, ts in rows:
            msg_text = text
            if not msg_text and attributed_body:
                msg_text = extract_text_from_attributed_body(attributed_body)
            if msg_text:
                messages.append({
                    'text': msg_text,
                    'from_me': bool(is_from_me),
                    'ts': ts,
                    'platform': 'imessage'
                })

    if has_whatsapp and 'whatsapp' in contact['handles']:
        jid = contact['handles']['whatsapp']
        jid_escaped = jid.replace("'", "''")
        wa_cte = f"""
            WITH dm_sessions AS (
                SELECT Z_PK FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0 AND ZCONTACTJID = '{jid_escaped}'
            )
        """
        rows = q_whatsapp(f"""{wa_cte}
            SELECT m.ZTEXT, m.ZISFROMME, (m.ZMESSAGEDATE+{COCOA_OFFSET}) as ts
            FROM ZWAMESSAGE m
            WHERE m.ZCHATSESSION IN (SELECT Z_PK FROM dm_sessions)
            AND m.ZMESSAGEDATE BETWEEN {ts_start_wa} AND {ts_end_wa}
            AND m.ZTEXT IS NOT NULL
            ORDER BY m.ZMESSAGEDATE
        """)
        for text, is_from_me, ts in rows:
            if text:
                messages.append({
                    'text': text,
                    'from_me': bool(is_from_me),
                    'ts': ts,
                    'platform': 'whatsapp'
                })

    messages.sort(key=lambda x: x['ts'])

    filtered = []
    prev_text = None
    for msg in messages:
        text = msg['text'].strip()

        if len(text) < 3:
            continue

        if text in ['￼', 'Image', 'Attachment', 'Photo', 'Video', 'Audio', 'Sticker']:
            continue

        if text.startswith(('Loved "', 'Liked "', 'Disliked "', 'Laughed at "', 'Emphasized "', 'Questioned "')):
            continue

        if re.match(r'^https?://\S+$', text):
            continue

        if text == prev_text:
            continue

        prev_text = text
        msg['text'] = text
        filtered.append(msg)

    return filtered

def generate_initials_svg(name):
    """Generate an SVG avatar with initials."""
    parts = name.split()
    if len(parts) >= 2:
        initials = parts[0][0].upper() + parts[-1][0].upper()
    elif parts:
        initials = parts[0][0].upper()
    else:
        initials = "?"

    hash_val = sum(ord(c) for c in name)
    hue = hash_val % 360

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="hsl({hue}, 60%, 45%)"/>
  <text x="50" y="50" font-family="system-ui, -apple-system, sans-serif" font-size="40" font-weight="600" fill="white" text-anchor="middle" dominant-baseline="central">{initials}</text>
</svg>'''

    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"

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
<script src="https://cdn.jsdelivr.net/npm/modern-screenshot@4.4.39/dist/index.js"></script>
<style>
:root{
  --ink:#241038; --night:#160A26; --lilac:#EEE8FF; --lav:#DCD3F5;
  --cobalt:#2F4BFF; --pink:#FF5FA2; --white:#FFFFFF;
  --cw:min(100vw, calc(92dvh * 9 / 16));
  --ch:calc(var(--cw) * 16 / 9);
  --display:'Anybody',system-ui,sans-serif;
  --body:'Onest',system-ui,sans-serif;
  --ease:cubic-bezier(.2,.8,.2,1);
  --spring:cubic-bezier(.3,1.4,.5,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
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
.slide{position:absolute;inset:0;display:grid;place-items:center;opacity:0;visibility:hidden;transform:translateX(5%) scale(.97);transition:opacity .45s var(--ease),transform .55s var(--ease),visibility 0s .55s}
.slide.past{transform:translateX(-5%) scale(.97)}
.slide.on{opacity:1;visibility:visible;transform:none;transition:opacity .45s var(--ease),transform .55s var(--ease),visibility 0s}
.card{position:relative;width:var(--cw);height:var(--ch);border-radius:calc(var(--cw) * .075);background:var(--bg);color:var(--fg);font-size:calc(var(--cw) / 22);padding:5.2em 1.6em 1.3em;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.5)}
.body{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:.2em;min-height:0}
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
.rows.tight{margin-top:.5em;gap:.1em}
.rows.tight .row{padding:.4em 0}
.rows.tight .row:first-child{font-size:1em}
.more{align-self:flex-start;background:none;border:0;font-size:.75em;font-weight:600;opacity:.85;padding:.6em 0;text-decoration:underline;text-underline-offset:.25em}
@media (hover:hover){.more:hover{opacity:1}}

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
.vs div{display:flex;justify-content:space-between;align-items:center;font-weight:500;padding:.55em .8em;border-radius:.9em;background:var(--fg);color:var(--bg);width:max(11em, calc(var(--w) * 100%));max-width:100%;transform-origin:left}
.vs span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vs div:last-child{background:var(--soft);color:var(--fg)}
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
.summary{transform-style:preserve-3d;transition:transform .5s var(--ease);background:linear-gradient(160deg,#4A62FF 0%,var(--cobalt) 45%,#2236D9 100%)}
.summary .sheen{position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at var(--mx,30%) var(--my,20%),rgba(255,255,255,.28),transparent 45%);mix-blend-mode:soft-light;z-index:2}
.summary .hero{font-size:4.2em}
.grid4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.9em 1em;margin-top:1.3em;padding-top:1.1em;border-top:1.5px solid var(--soft)}
.grid4 dt{font-size:.7em;opacity:.85}
.grid4 dd{font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1.5em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.diag-sm{font-family:var(--display);font-weight:900;font-stretch:55%;font-variation-settings:"wdth" 55;font-size:2.4em;line-height:.9;margin-top:.7em;color:#FFC2DC}
.top3{font-size:.85em;opacity:.85;margin-top:.5em}
/* summary poster: the slide people post */
.ptitle{font-family:var(--display);font-weight:800;line-height:.9;letter-spacing:-.03em;white-space:nowrap;margin-bottom:auto;font-size:2.4em}
.ptitle span:first-child{font-stretch:58%;font-variation-settings:"wdth" 58}
.ptitle span:last-child{font-weight:900;font-stretch:150%;font-variation-settings:"wdth" 150;margin-left:.12em}
.poster .hero small{opacity:.85}
.wave{height:5.5em;padding:0}
.wave i{background:var(--white);opacity:.4}
.wave i.pk{background:var(--pink);opacity:1;box-shadow:none}
.one{display:flex;align-items:center;gap:.7em;margin-top:1.2em}
.one .av{width:2.9em;height:2.9em;flex:none;box-shadow:none}
.one b{display:block;font-family:var(--display);font-weight:800;font-stretch:75%;font-variation-settings:"wdth" 75;font-size:1.7em;line-height:1;letter-spacing:-.02em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.one div{min-width:0}
.one span{font-size:.8em;opacity:.85}
.poster .diag-sm{margin-top:.6em}
.poster .mark{opacity:1;gap:1em}
.cta{display:flex;justify-content:center;align-items:center;gap:.5em;margin-top:1.2em;border:0;border-radius:999px;padding:.9em 1em;background:var(--white);color:var(--cobalt);font-weight:600;font-size:.95em;transition:transform .15s ease-out}
.cta:not(:disabled):active{transform:scale(.96)}
.cta:focus-visible{outline-color:var(--white)}
.cta svg{width:1.1em;height:1.1em}

/* chrome: progress + controls, sized to the card */
.top{position:fixed;left:50%;transform:translateX(-50%);width:var(--cw);top:calc((100dvh - var(--ch)) / 2);padding:calc(var(--cw)*.035) calc(var(--cw)*.07) 0;z-index:10;color:var(--chrome,#fff);transition:color .4s}
.bars{display:flex;gap:4px}
.bars button{flex:1;height:3px;border:0;border-radius:3px;background:currentColor;opacity:.25;padding:0;position:relative}
.bars button::after{content:"";position:absolute;inset:-10px 0}
.bars button.done{opacity:.9}
.ctl{display:flex;justify-content:space-between;align-items:center;margin-top:12px;font-size:13px;font-weight:500}
.ctl .brand{font-family:var(--display);font-weight:800;font-stretch:120%;font-variation-settings:"wdth" 120;font-size:14px;opacity:.85}
.pills{display:flex;gap:6px}
.pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border:0;border-radius:999px;padding:7px 12px;background:color-mix(in srgb,currentColor 14%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .15s ease-out,background .2s}
@media (hover:hover){.pill:hover{background:color-mix(in srgb,currentColor 22%,transparent)}}
.pill:not(:disabled):active{transform:scale(.96)}
.pill svg{width:14px;height:14px}

/* entrance choreography, replayed on each slide */
.on .lead,.on .after,.on .split,.on .more,.on .mark{animation:rise .7s var(--ease) both}
.on .lead{animation-delay:.05s}
.on .hero{animation:heroIn .8s var(--spring) both;animation-delay:.15s}
.on .after{animation-delay:.45s}
.on .split,.on .grid4{animation:rise .7s var(--ease) both;animation-delay:.6s}
.on .row{animation:rowIn .55s var(--ease) both;animation-delay:calc(.2s + var(--d) * 70ms)}
.on .row::before{animation:grow .9s var(--ease) both;animation-delay:calc(.35s + var(--d) * 70ms)}
.on .bub{animation:pop .45s var(--spring) both}
.on .bub:nth-child(2){animation-delay:.55s}.on .bub:nth-child(3){animation-delay:1.1s}
.on .intro .a1{animation-delay:.9s}.on .intro .a2{animation-delay:1.6s}.on .intro .a3{animation-delay:2.3s}
.on .intro .a4{animation:rise .6s var(--ease) both;animation-delay:2.9s}
.on .stretch span:last-child{animation:stretch 1.4s var(--ease) both}
.on .stretch span:first-child{animation:rise .8s var(--ease) both}
.on .emoji span{animation:pop .5s var(--spring) both;animation-delay:calc(.25s + var(--d) * 90ms)}
.on .dots i{animation:dot .5s var(--ease) both;animation-delay:calc(var(--r, 0) * 45ms)}
.on .moon{animation:moon 1.4s var(--ease) both}
.on .redact i{animation:grow .8s var(--ease) both;transform-origin:left;animation-delay:calc(var(--k, 0) * 60ms)}
.on .chain i{animation:pop .3s var(--spring) both;animation-delay:calc(var(--k, 0) * 12ms)}
.on .spark i{animation:barUp .7s var(--ease) both;transform-origin:bottom;animation-delay:calc(var(--k, 0) * 2ms)}
@keyframes barUp{from{transform:scaleY(0)}}
.on .pile i{animation:pop .35s var(--spring) both;animation-delay:calc(var(--d, 0) * 1ms)}
.on .av{animation:pop .6s var(--spring) both;animation-delay:calc(.1s + var(--i, 0) * 90ms)}
.on .sticker{animation:sticker .8s var(--spring) both}
.on .clock b{animation:hand 1.6s var(--spring) both}
.on .vs div{animation:grow .9s var(--ease) both;animation-delay:.5s}
.on .vs div:last-child{animation-delay:.65s}
.on .ptitle span:first-child{animation:rise .8s var(--ease) both}
.on .ptitle span:last-child{animation:stretch 1.4s var(--ease) both}
.on .one{animation:rise .7s var(--ease) both;animation-delay:.7s}
.on .cta{animation:rise .7s var(--ease) both;animation-delay:.9s}
@keyframes sticker{from{opacity:0;transform:rotate(-40deg) scale(.4)}to{opacity:1;transform:rotate(-8deg)}}
@keyframes hand{from{transform:rotate(180deg)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:var(--o,1);transform:none}}
@keyframes heroIn{from{opacity:0;transform:translateY(24px) scale(.94);filter:blur(6px)}to{opacity:1;transform:none;filter:none}}
@keyframes rowIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.9)}to{opacity:1;transform:none}}
@keyframes stretch{from{font-stretch:50%;font-variation-settings:"wdth" 50;opacity:0}30%{opacity:1}to{font-stretch:150%;font-variation-settings:"wdth" 150}}
@keyframes dot{from{transform:scale(0)}to{transform:none}}
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
const dark = new Set(['t-cobalt','t-ink','t-night','t-stage']);
let cur = -1;

// fit text to the card width (numbers and the intro title)
function fit(el, max) {
  const anim = el.style.animation, disp = el.style.display;
  el.style.animation = 'none'; el.style.fontSize = ''; el.style.display = 'inline-block'; el.style.width = 'max-content'; el.classList.add('fitting');
  const base = parseFloat(getComputedStyle(el).fontSize), w = el.parentElement.clientWidth * .97;
  const ratio = w / el.getBoundingClientRect().width;
  el.style.fontSize = (max ? Math.min(base * ratio, base * max) : Math.min(base, base * ratio)) + 'px';
  el.style.animation = anim; el.style.display = disp; el.style.width = ''; el.classList.remove('fitting');
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
  document.querySelectorAll('.ptitle').forEach(e => fit(e, 3));
  document.querySelectorAll('.split b, .grid4 dd').forEach(e => fit(e));
  document.querySelectorAll('.hero.name, .hero.diag').forEach(fitName);
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
  const t0 = performance.now(), dur = 1300;
  const fmt = v => (dec ? v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString('en-US')) + sfx;
  (function f(t) {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(2, -10 * p);
    el.textContent = fmt(p >= 1 ? to : to * e);
    if (p < 1 && el.closest('.slide.on')) requestAnimationFrame(f); else el.textContent = fmt(to);
  })(t0);
}

function go(i, quiet) {
  if (i < 0 || i >= slides.length || i === cur) return;
  slides.forEach((s, k) => { s.classList.toggle('on', k === i); s.classList.toggle('past', k < i); });
  [...bars.children].forEach((b, k) => { b.classList.toggle('done', k <= i); b.setAttribute('aria-current', k === i ? 'step' : 'false'); });
  cur = i;
  const s = slides[i];
  const theme = [...s.classList].find(c => c.startsWith('t-'));
  top.style.setProperty('--chrome', dark.has(theme) ? '#fff' : '#241038');
  s.querySelectorAll('.count').forEach(countUp);
  if (!quiet) { buzz(); if (!document.activeElement || document.activeElement === document.body || document.activeElement.classList.contains('slide')) s.focus({ preventScroll: true }); }
  try { history.replaceState(null, '', '#' + s.dataset.name); } catch (_) {}
}

// tap left half of the card to go back, right half to go forward; swipe works too
let sx = null, sy = null;
deck.addEventListener('pointerdown', e => { sx = e.clientX; sy = e.clientY; });
deck.addEventListener('pointerup', e => {
  if (sx === null) return;
  const dx = e.clientX - sx, dy = e.clientY - sy; sx = null;
  if (e.target.closest('button, a')) return;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { go(cur + (dx < 0 ? 1 : -1)); return; }
  if (Math.abs(dx) < 8 && Math.abs(dy) < 8) { const r = slides[cur].querySelector('.card').getBoundingClientRect(); go(e.clientX < r.left + r.width / 2 ? cur - 1 : cur + 1); }
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
  b.textContent = all ? 'Show top 5' : b.textContent.replace('Show top 5', '');
  if (!all) b.textContent = 'Show all ' + list.children.length;
  buzz();
}));

// day tooltips
const tip = document.getElementById('tip');
document.querySelectorAll('.dots i[data-tip]').forEach(d => {
  d.addEventListener('pointerenter', e => { if (e.pointerType !== 'mouse') return; const r = d.getBoundingClientRect(); tip.textContent = d.dataset.tip; tip.style.left = (r.left + r.width / 2) + 'px'; tip.style.top = r.top + 'px'; tip.style.opacity = 1; });
  d.addEventListener('pointerleave', () => tip.style.opacity = 0);
});

// summary card tilts toward the pointer
const tilt = document.querySelector('.tilt');
if (tilt && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const card = tilt.querySelector('.card');
  tilt.addEventListener('pointermove', e => {
    const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    card.style.transition = 'transform .08s linear';
    card.style.transform = `rotateY(${(x - .5) * 14}deg) rotateX(${(.5 - y) * 14}deg)`;
    card.style.setProperty('--mx', x * 100 + '%'); card.style.setProperty('--my', y * 100 + '%');
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
  box.className = [...s.classList].find(c => c.startsWith('t-')) + ' capturing';
  box.setAttribute('aria-hidden', 'true');
  box.style.cssText = 'position:fixed;left:-10000px;top:0;--cw:360px;--ch:640px';
  const card = s.querySelector('.card').cloneNode(true);
  card.removeAttribute('id'); card.style.transform = 'none'; card.classList.add('saving');
  card.querySelectorAll('.chrome').forEach(n => n.remove());
  box.appendChild(card); document.body.appendChild(box);
  card.querySelectorAll('.count').forEach(c => c.textContent = (c.dataset.fmt === 'dec' ? (+c.dataset.to).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : (+c.dataset.to).toLocaleString('en-US')) + (c.dataset.suffix || ''));
  card.querySelectorAll('.hero.fit, .split b, .grid4 dd').forEach(e => fit(e));
  card.querySelectorAll('.hero.name, .hero.diag').forEach(fitName);
  card.querySelectorAll('.ptitle, .stretch span').forEach(e => fit(e, 3));
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
  if (!window.modernScreenshot) { flash('Offline. Take a screenshot', 2400); return; }
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
      if (err.name === 'NotAllowedError' && !held) { ready = { slide: s, blob }; label('Share now'); busy(false); return; }
      download(blob, name); flash('Saved');
    }
    return;
  }
  download(blob, name); buzz(); flash('Saved');
}));

if (location.search.includes('still')) document.body.classList.add('capturing');
const start = slides.findIndex(s => '#' + s.dataset.name === location.hash);
go(start > 0 ? start : 0, true);
})();
</script>
</body></html>'''

PEOPLE_CSS = r'''
/* person slides: avatar + rank, name, stats, then the story */
.who{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:auto;padding-bottom:1em}
.who .av{width:3.4em;height:3.4em;font-size:1.35em;overflow:hidden;box-shadow:0 .8em 2em -.9em rgba(36,16,56,.5)}
.av img{width:100%;height:100%;object-fit:cover;display:block}
.rank{font-family:var(--display);font-weight:900;font-stretch:125%;font-variation-settings:"wdth" 125;font-size:4.2em;line-height:.8;letter-spacing:-.05em;color:var(--tint);font-variant-numeric:tabular-nums}
.rank small{font-size:.42em;font-weight:800;letter-spacing:-.02em;vertical-align:.95em;margin-right:.06em}
.person .hero.name{font-size:3.5em;margin-bottom:.02em}
.person .split{margin-top:.9em;padding-top:.8em}
.person .split b{font-size:1.2em}
.split b .count{display:inline;font-size:1em;opacity:1;margin:0;line-height:inherit}
.story{flex:0 1 auto;min-height:5em;overflow-y:auto;overscroll-behavior:contain;margin:1em -.4em 0 0;padding-right:.4em;scrollbar-width:thin;scrollbar-color:var(--soft) transparent}
.story.below{-webkit-mask-image:linear-gradient(#000 calc(100% - 2.6em),transparent);mask-image:linear-gradient(#000 calc(100% - 2.6em),transparent)}
.story p{font-size:1em;line-height:1.58;opacity:.9;text-wrap:pretty;margin-bottom:.85em}
.story p:last-child{margin-bottom:.4em}
.story q{quotes:none;font-weight:600;opacity:1}
.story:focus-visible{outline-offset:2px}
.on .story{animation:rise .7s var(--ease) both;animation-delay:.7s}
.on .rank{animation:heroIn .8s var(--spring) both;animation-delay:.3s}
.closing .rows{margin-top:.5em}
'''

PEOPLE_JS_ANCHOR = "// tap left half of the card to go back, right half to go forward; swipe works too\n"
PEOPLE_JS = r'''// long stories scroll inside the card; a scroll is never a tap
let scrolledAt = 0;
document.querySelectorAll('.story').forEach(st => {
  const edge = () => st.classList.toggle('below', st.scrollTop + st.clientHeight < st.scrollHeight - 4);
  st.addEventListener('scroll', () => { scrolledAt = performance.now(); edge(); }, {passive: true});
  addEventListener('resize', edge); (document.fonts ? document.fonts.ready : Promise.resolve()).then(edge); edge();
});
'''
PEOPLE_TAP_ANCHOR = "  if (e.target.closest('button, a')) return;\n"
PEOPLE_TAP_GUARD = "  if (performance.now() - scrolledAt < 300) return;\n"


def generate_html(contacts_with_summaries, year, output_path):
    """Generate the swipeable HTML report."""
    import html as _html

    esc = lambda v: _html.escape(str(v))
    people = contacts_with_summaries
    count = len(people)

    def num(v):
        return f'<span class="count" data-to="{v}" data-fmt="int" data-suffix="">{v:,}</span>'

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

    def avatar(contact, cls=''):
        name = contact['name']
        photo = contact.get('photo')
        inner = f'<img src="{esc(photo)}" alt="">' if photo else initials(name)
        return f'<span class="av a{sum(map(ord, str(name))) % 5} {cls}" aria-hidden="true">{inner}</span>'

    def story(text):
        paras = []
        for para in text.split('\n\n'):
            if not para.strip():
                continue
            p = esc(para.strip())
            p = re.sub(r'&quot;((?:(?!&quot;)[^\n]){2,240}?)&quot;|“([^”\n]{2,240}?)”',
                       lambda m: '<q>“' + (m.group(1) or m.group(2)) + '”</q>', p)
            paras.append('<p>' + p.replace('\n', '<br>') + '</p>')
        return ''.join(paras)

    def slide(theme, body, name, extra=''):
        return (f'<section class="slide t-{theme}{extra}" data-name="{name}"><div class="card"><div class="body">{body}</div>'
                f'<footer class="mark"><span>wrap2026.com</span><span>People · {year}</span></footer></div></section>')

    slides = []

    # Intro
    slides.append(slide('cobalt', f'''
        <div class="intro">
          <h1 class="stretch"><span>People</span><span>{esc(year)}</span></h1>
          <div class="thread">
            <div class="bub r a1">I read your texts.</div>
            <div class="bub r a2">All of them.</div>
            <div class="bub r a3">Here are the {count} people who made your year.</div>
          </div>
          <p class="hint chrome a4">Tap to start</p>
        </div>''', 'intro'))

    # One slide per person; themes rotate so neighbours never match
    cycle = ['pink', 'lilac', 'ink', 'white', 'cobalt', 'lav', 'night']
    themes = [cycle[i % len(cycle)] for i in range(count)]
    if themes and themes[-1] == 'cobalt':
        themes[-1] = 'night'
    for i, contact in enumerate(people):
        summary = contact.get('summary') or 'No summary available.'
        slides.append(slide(themes[i], f'''
            <div class="who">{avatar(contact)}<div class="rank" aria-label="Number {i + 1}"><small>#</small>{i + 1}</div></div>
            <div class="hero name">{esc(contact['name'])}</div>
            <div class="split">
              <div><b>{num(contact['total'])}</b><span>messages</span></div>
              <div><b>{contact['sent']:,}</b><span>from you</span></div>
              <div><b>{contact['received']:,}</b><span>from them</span></div>
            </div>
            <div class="story" tabindex="0">{story(summary)}</div>''', f'person-{i + 1}', ' person'))

    # Closing
    total = sum(c['total'] for c in people)
    mx = max((c['total'] for c in people), default=1) or 1
    top_rows = ''.join(
        f'<li class="row" style="--w:{max(0.04, c["total"] / mx):.3f};--d:{k}"><span class="rk">{k}</span>'
        f'<span class="nm">{esc(c["name"])}</span><span class="vl">{c["total"]:,}</span></li>'
        for k, c in enumerate(people[:5], 1))
    slides.append(f'''
    <section class="slide t-stage closing" data-name="summary">
      <div class="tilt">
        <div class="card summary poster">
          <div class="sheen" aria-hidden="true"></div>
          <div class="body">
            <h2 class="ptitle"><span>Wrapped</span> <span>{esc(year)}</span></h2>
            <div class="hero">{total:,}</div>
            <p class="after">messages with the {count} people I talked to most.</p>
            <ol class="rows tight">{top_rows}</ol>
            <button class="cta chrome" data-act><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span class="lbl">Save image</span></button>
          </div>
          <footer class="mark"><span>wrap2026.com</span><span>People · {esc(year)}</span></footer>
        </div>
      </div>
    </section>''')

    page = TEMPLATE.replace('</style>', PEOPLE_CSS + '</style>', 1)
    assert PEOPLE_JS_ANCHOR in page and PEOPLE_TAP_ANCHOR in page
    page = page.replace(PEOPLE_JS_ANCHOR, PEOPLE_JS + '\n' + PEOPLE_JS_ANCHOR, 1)
    page = page.replace(PEOPLE_TAP_ANCHOR, PEOPLE_TAP_ANCHOR + PEOPLE_TAP_GUARD, 1)
    page = page.replace('__TITLE__', f'People Wrapped {esc(year)}') \
               .replace('__FILE__', f'people_wrapped_{esc(year)}') \
               .replace('__SLIDES__', ''.join(slides))
    with open(output_path, 'w') as f:
        f.write(page)
    return output_path


def extract_messages(year='2026', top_n=25):
    """Phase 1: Extract messages to JSON files."""
    print()
    print("=" * 60)
    print("  PEOPLE WRAPPED 2026 - Step 1: Extracting Messages")
    print("=" * 60)
    print()

    spinner = Spinner()
    print("Checking database access...")
    has_imessage, has_whatsapp = check_access()
    print(f"  {'✓' if has_imessage else '✗'} iMessage")
    print(f"  {'✓' if has_whatsapp else '✗'} WhatsApp")

    photo_count = count_addressbook_photos()
    print(f"  ✓ AddressBook ({photo_count} contact photos)")
    print()

    spinner.start("Extracting contacts...")
    imessage_contacts, contact_record_ids = extract_imessage_contacts()
    whatsapp_contacts = extract_whatsapp_contacts()
    spinner.stop(f"Contacts: {len(imessage_contacts)} iMessage, {len(whatsapp_contacts)} WhatsApp")

    timestamps = get_year_timestamps(year)

    spinner.start("Identifying top contacts...")
    top_contacts = get_top_contacts_combined(
        timestamps, top_n,
        has_imessage, has_whatsapp,
        imessage_contacts, whatsapp_contacts, contact_record_ids
    )
    spinner.stop(f"Found {len(top_contacts)} contacts")

    print()
    print(f"Top {len(top_contacts)} contacts:")
    for i, c in enumerate(top_contacts):
        platforms = list(c['handles'].keys())
        platform_str = ', '.join(platforms)
        print(f"  {i+1:2}. {c['name'][:25]:<25} — {c['total']:,} messages ({platform_str})")

    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)

    print()
    print("Extracting messages...")

    for i, contact in enumerate(top_contacts):
        name = contact['name']
        safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

        messages = get_messages_for_contact(contact, timestamps, has_imessage, has_whatsapp)

        # Save to JSON
        data = {
            'index': i,
            'name': name,
            'total': contact['total'],
            'sent': contact['sent'],
            'received': contact['received'],
            'handles': contact['handles'],
            'photo': contact.get('photo'),
            'record_id': contact.get('record_id'),
            'messages': messages,
            'year': year,
        }

        json_path = os.path.join(DATA_DIR, f"{i+1:02d}_{safe_name}.json")
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"  [{i+1}/{len(top_contacts)}] {name}: {len(messages)} messages")

    print()
    print(f"✓ Messages extracted to {DATA_DIR}/")
    return True


def get_contacts_needing_summaries():
    """Get list of contacts that don't have summaries yet."""
    if not os.path.exists(DATA_DIR):
        return []

    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    needs_summary = []

    for json_path in json_files:
        with open(json_path) as f:
            data = json.load(f)
        if not data.get('summary'):
            needs_summary.append({
                'path': json_path,
                'name': data['name'],
                'total': data['total'],
                'message_count': len(data.get('messages', []))
            })

    return needs_summary


def build_html(year='2026'):
    """Phase 3: Build HTML from JSON files with summaries."""
    output_path = f'people_wrapped_{year}.html'

    if not os.path.exists(DATA_DIR):
        print(f"Error: {DATA_DIR}/ not found.")
        return False

    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not json_files:
        print(f"Error: No JSON files found in {DATA_DIR}/")
        return False

    print()
    print("=" * 60)
    print("  PEOPLE WRAPPED 2026 - Step 3: Building HTML")
    print("=" * 60)
    print()

    contacts = []
    for json_path in json_files:
        with open(json_path) as f:
            data = json.load(f)
        contacts.append(data)
        has_summary = 'summary' in data and data['summary']
        status = "✓" if has_summary else "✗"
        print(f"  {status} {data['name']}")

    spinner = Spinner()
    spinner.start("Generating HTML...")
    generate_html(contacts, year, output_path)
    spinner.stop(f"Saved to {output_path}")

    print()
    print(f"✓ Done! Open {output_path} in your browser.")
    return True


def print_summary_instructions():
    """Print instructions for Claude Code to generate summaries."""
    needs_summary = get_contacts_needing_summaries()

    print()
    print("=" * 60)
    print("  PEOPLE WRAPPED 2026 - Step 2: Generate Summaries")
    print("=" * 60)
    print()
    print(f"  {len(needs_summary)} contacts need summaries:")
    for c in needs_summary:
        print(f"    - {c['name']} ({c['message_count']:,} messages)")
    print()
    print("=" * 60)
    print()
    print("  CLAUDE CODE: Please generate summaries for the contacts above.")
    print()
    print("  Read each JSON file in people_wrapped_data/ and write a personal,")
    print("  specific summary. Pull out inside jokes, memorable moments, how")
    print("  the relationship evolved. Be specific, quote when it captures")
    print("  something real.")
    print()
    print("  IMPORTANT: Do NOT use Task tool or parallel agents.")
    print("  Use /model sonnet for larger context window.")
    print()
    print("  When done: python3 people_wrapped.py build")
    print()


def main():
    """Main entry point - handles the full workflow."""
    parser = argparse.ArgumentParser(
        description='People Wrapped 2026 - AI-powered messaging relationship analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How it works:
  1. Run: python3 people_wrapped.py
  2. Script extracts your top 25 contacts from iMessage/WhatsApp
  3. Claude Code generates personalized summaries (no API key needed)
  4. Script builds a beautiful swipeable HTML report

Commands:
  python3 people_wrapped.py           Full workflow (extract → summarize → build)
  python3 people_wrapped.py extract   Just extract messages
  python3 people_wrapped.py summarize Show summary generation instructions
  python3 people_wrapped.py build     Just build HTML from existing data
  python3 people_wrapped.py status    Check progress

Options:
  --top N    Number of contacts to analyze (default: 25)
"""
    )
    parser.add_argument('command', nargs='?', default='run',
                       choices=['run', 'extract', 'summarize', 'build', 'status'],
                       help='Command to run')
    parser.add_argument('--year', default='2026', help='Year to analyze')
    parser.add_argument('--top', type=int, default=25, help='Number of top contacts (default: 25)')

    args = parser.parse_args()

    if args.command == 'extract':
        extract_messages(args.year, args.top)
    elif args.command == 'summarize':
        print_summary_instructions()
    elif args.command == 'build':
        build_html(args.year)
    elif args.command == 'status':
        needs = get_contacts_needing_summaries()
        total = len(glob.glob(os.path.join(DATA_DIR, "*.json"))) if os.path.exists(DATA_DIR) else 0
        complete = total - len(needs)
        print(f"\nProgress: {complete}/{total} summaries complete\n")
        if needs:
            print("Pending:")
            for c in needs:
                print(f"  - {c['name']}")
    elif args.command == 'run':
        # Full workflow
        print()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║              PEOPLE WRAPPED 2026                           ║")
        print("║      AI-powered analysis of your top relationships         ║")
        print("╚════════════════════════════════════════════════════════════╝")

        # Step 1: Check if extraction needed
        if not os.path.exists(DATA_DIR) or not glob.glob(os.path.join(DATA_DIR, "*.json")):
            extract_messages(args.year, args.top)
        else:
            print()
            print("✓ Messages already extracted. Skipping Step 1.")

        # Step 2: Check if summaries needed
        needs_summary = get_contacts_needing_summaries()
        if needs_summary:
            print_summary_instructions()
            # Don't exit - Claude Code will see this and generate summaries
            return
        else:
            print()
            print("✓ All summaries complete. Proceeding to Step 3.")

        # Step 3: Build HTML
        build_html(args.year)


if __name__ == '__main__':
    main()
