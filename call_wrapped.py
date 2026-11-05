#!/usr/bin/env python3
"""
Call Wrapped 2026 - Your calling habits across Phone, FaceTime & WhatsApp, exposed.
Usage: python3 call_wrapped.py
"""

import sqlite3, os, sys, re, subprocess, argparse, glob, threading, time
from datetime import datetime, timedelta
from collections import defaultdict

# Database paths
CALL_HISTORY_DB = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")
WHATSAPP_CALLS_DB = os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/CallHistory.sqlite")
ADDRESSBOOK_DIR = os.path.expanduser("~/Library/Application Support/AddressBook")

# Mac epoch offset (Jan 1, 2001 -> Jan 1, 1970)
MAC_EPOCH = 978307200

# Timestamps for 2026
TS_2026_START = datetime(2026, 1, 1).timestamp()
TS_2026_END = datetime(2026, 12, 31, 23, 59, 59).timestamp()
TS_JUN_2026 = datetime(2026, 6, 1).timestamp()

# Timestamps for 2025
TS_2025_START = datetime(2025, 1, 1).timestamp()
TS_2025_END = datetime(2025, 12, 31, 23, 59, 59).timestamp()
TS_JUN_2025 = datetime(2025, 6, 1).timestamp()


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
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()

    def stop(self, final_message=None):
        self.spinning = False
        if self.thread:
            self.thread.join()
        if final_message:
            print(f"\r    ✓ {final_message}".ljust(60))
        else:
            print()


def normalize_phone(phone):
    """Normalize phone number to last 10 digits."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    elif len(digits) > 10:
        return digits[-10:]
    return digits[-10:] if len(digits) >= 10 else (digits if len(digits) >= 7 else None)


def extract_contacts():
    """Extract contacts from macOS AddressBook."""
    contacts = {}
    db_paths = glob.glob(os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "AddressBook-v22.abcddb"))
    main_db = os.path.join(ADDRESSBOOK_DIR, "AddressBook-v22.abcddb")
    if os.path.exists(main_db):
        db_paths.append(main_db)

    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            people = {}
            for row in conn.execute("SELECT ROWID, ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL"):
                name = f"{row[1] or ''} {row[2] or ''}".strip()
                if name:
                    people[row[0]] = name
            for owner, phone in conn.execute("SELECT ZOWNER, ZFULLNUMBER FROM ZABCDPHONENUMBER WHERE ZFULLNUMBER IS NOT NULL"):
                if owner in people:
                    name = people[owner]
                    digits = re.sub(r'\D', '', str(phone))
                    if digits:
                        contacts[digits] = name
                        if len(digits) >= 10:
                            contacts[digits[-10:]] = name
                        if len(digits) >= 7:
                            contacts[digits[-7:]] = name
                        if len(digits) == 11 and digits.startswith('1'):
                            contacts[digits[1:]] = name
            conn.close()
        except:
            pass
    return contacts


def get_name(phone, contacts):
    """Resolve phone number to contact name."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))

    # Skip short codes
    if 5 <= len(digits) <= 6:
        return None

    # Skip toll-free
    if len(digits) >= 10 and digits[-10:-7] in ('800', '888', '877', '866', '855', '844', '833'):
        return None

    if digits in contacts:
        return contacts[digits]
    if len(digits) == 11 and digits.startswith('1'):
        if digits[1:] in contacts:
            return contacts[digits[1:]]
    if len(digits) >= 10 and digits[-10:] in contacts:
        return contacts[digits[-10:]]
    if len(digits) >= 7 and digits[-7:] in contacts:
        return contacts[digits[-7:]]
    return None


def check_access():
    """Check access to call databases. Returns (has_phone, has_whatsapp)."""
    has_phone = False
    has_whatsapp = False

    # Check Phone/FaceTime
    if os.path.exists(CALL_HISTORY_DB):
        try:
            conn = sqlite3.connect(CALL_HISTORY_DB)
            conn.execute("SELECT 1 FROM ZCALLRECORD LIMIT 1")
            conn.close()
            has_phone = True
        except:
            pass

    # Check WhatsApp
    if os.path.exists(WHATSAPP_CALLS_DB):
        try:
            conn = sqlite3.connect(WHATSAPP_CALLS_DB)
            conn.execute("SELECT 1 FROM ZWAAGGREGATECALLEVENT LIMIT 1")
            conn.close()
            has_whatsapp = True
        except:
            pass

    if not has_phone and not has_whatsapp:
        print("\n[!] ACCESS DENIED - Neither Phone nor WhatsApp call history accessible")
        print("   System Settings -> Privacy & Security -> Full Disk Access -> turn on the app running this (Terminal, iTerm, Ghostty, Codex), then reopen it")
        subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles'])
        sys.exit(1)

    return has_phone, has_whatsapp


def q_phone(sql):
    """Query phone call history database."""
    conn = sqlite3.connect(CALL_HISTORY_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r


def q_whatsapp(sql):
    """Query WhatsApp call history database."""
    conn = sqlite3.connect(WHATSAPP_CALLS_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r


def format_duration(seconds):
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s" if secs else f"{mins}m"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m" if mins else f"{hours}h"


def format_duration_short(seconds):
    """Format seconds as short duration (e.g., '2h 15m')."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m" if mins else f"{hours}h"


def analyze_phone_calls(ts_start, ts_end, ts_jun, contacts):
    """Analyze phone/FaceTime call history."""
    calls = []

    # Get all calls in date range
    rows = q_phone(f"""
        SELECT ZADDRESS, ZDURATION, ZDATE, ZORIGINATED, ZANSWERED, ZCALLTYPE
        FROM ZCALLRECORD
        WHERE (ZDATE + {MAC_EPOCH}) > {ts_start} AND (ZDATE + {MAC_EPOCH}) < {ts_end}
        ORDER BY ZDATE
    """)

    for row in rows:
        phone, duration, ts, originated, answered, call_type = row
        name = get_name(phone, contacts)
        if not name:
            continue

        # Determine call type: 1=Phone, 8=FaceTime Audio, 16=FaceTime Video
        if call_type in (8, 16):
            platform = 'FaceTime'
            is_video = call_type == 16
        else:
            platform = 'Phone'
            is_video = False

        calls.append({
            'name': name,
            'phone': normalize_phone(phone),
            'duration': duration or 0,
            'timestamp': ts + MAC_EPOCH,
            'outgoing': originated == 1,
            'answered': answered == 1,
            'platform': platform,
            'is_video': is_video,
        })

    return calls


def analyze_whatsapp_calls(ts_start, ts_end, ts_jun, contacts):
    """Analyze WhatsApp call history."""
    calls = []

    # Get WhatsApp contact names from multiple sources
    wa_contacts = {}  # JID -> name
    try:
        wa_msg_db = os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite")
        if os.path.exists(wa_msg_db):
            conn = sqlite3.connect(wa_msg_db)
            # Source 1: Push names (user's self-set display name)
            for row in conn.execute("SELECT ZJID, ZPUSHNAME FROM ZWAPROFILEPUSHNAME WHERE ZPUSHNAME IS NOT NULL"):
                jid, name = row
                if jid and name:
                    wa_contacts[jid] = name
            # Source 2: Chat session partner names (your saved contact name - higher priority)
            for row in conn.execute("SELECT ZCONTACTJID, ZPARTNERNAME FROM ZWACHATSESSION WHERE ZPARTNERNAME IS NOT NULL"):
                jid, name = row
                if jid and name and not name.startswith('+'):  # Skip if it's just a phone number
                    wa_contacts[jid] = name  # Override push name with your contact name
            conn.close()
    except:
        pass

    # Get all WhatsApp calls from ZWACDCALLEVENT (has duration!)
    # Join with participant table to get phone number/JID
    rows = q_whatsapp(f"""
        SELECT e.ZDURATION, e.ZDATE, e.ZOUTCOME, p.ZJIDSTRING
        FROM ZWACDCALLEVENT e
        JOIN ZWACDCALLEVENTPARTICIPANT p ON p.Z1PARTICIPANTS = e.Z_PK
        WHERE (e.ZDATE + {MAC_EPOCH}) > {ts_start} AND (e.ZDATE + {MAC_EPOCH}) < {ts_end}
        ORDER BY e.ZDATE
    """)

    for row in rows:
        duration, ts, outcome, jid = row

        # Handle both @s.whatsapp.net (phone) and @lid (internal ID) formats
        phone = jid.split('@')[0] if jid else None
        name = None

        # Try WhatsApp contacts first
        if jid in wa_contacts:
            name = wa_contacts[jid]
        # Try AddressBook lookup by phone number
        if not name and phone:
            name = get_name(phone, contacts)
        if not name:
            continue

        calls.append({
            'name': name,
            'phone': normalize_phone(phone),
            'duration': duration or 0,
            'timestamp': ts + MAC_EPOCH,
            'outgoing': True,  # Direction not in this table
            'answered': (duration or 0) > 0,  # Has duration = was answered
            'platform': 'WhatsApp',
            'is_video': False,  # Video flag not in this table
        })

    return calls


def analyze_calls(phone_calls, whatsapp_calls, ts_start, ts_end, ts_jun):
    """Combine and analyze all calls."""
    all_calls = phone_calls + whatsapp_calls
    all_calls.sort(key=lambda x: x['timestamp'])

    # === FIRST: Build name normalization map ===
    # Step 1: Phone-based matching (same phone = same person)
    phone_to_names = defaultdict(set)
    for c in all_calls:
        phone = c['phone']
        if phone:
            digits = re.sub(r'\D', '', str(phone))
            key = digits[-10:] if len(digits) >= 7 else None
            if key:
                phone_to_names[key].add(c['name'])

    name_normalize = {}
    for key, names in phone_to_names.items():
        best_name = max(names, key=len)
        for name in names:
            name_normalize[name] = best_name

    # Step 2: Name-based fuzzy matching for contacts without phone numbers
    # Match "Shimolee" -> "Shimolee Kothari" when unambiguous
    all_names = set(c['name'].strip() for c in all_calls)
    normalized_names = set(name_normalize.values())
    all_target_names = all_names | normalized_names

    # Build first-name index for reverse lookup
    first_name_to_full = {}
    for full_name in all_target_names:
        parts = full_name.strip().split()
        if len(parts) >= 2:
            first = parts[0].lower()
            if first not in first_name_to_full:
                first_name_to_full[first] = []
            first_name_to_full[first].append(full_name)

    for name in all_names:
        if name in name_normalize:
            continue  # Already normalized via phone
        name_clean = name.strip()
        name_lower = name_clean.lower()

        # Method 1: Check if any full name starts with this name + space
        matches = []
        for target in all_target_names:
            target_clean = target.strip()
            target_lower = target_clean.lower()
            if target_lower.startswith(name_lower + ' ') and len(target_clean) > len(name_clean):
                matches.append(target_clean)

        # Method 2: If name is a single word, check first-name index
        if not matches and ' ' not in name_clean:
            candidates = first_name_to_full.get(name_lower, [])
            # Only use if there's exactly one full name with this first name
            if len(candidates) == 1 and candidates[0] != name_clean:
                matches = candidates

        # Only use the match if there's exactly ONE (unambiguous)
        if len(matches) == 1:
            name_normalize[name] = matches[0]

    # Normalize all call names for consistent analytics
    for c in all_calls:
        c['name'] = name_normalize.get(c['name'].strip(), c['name'].strip())

    d = {}

    # Basic stats (note: WhatsApp direction unknown, so outgoing/incoming skewed)
    total_calls = len(all_calls)
    # Only count direction for Phone/FaceTime where we have accurate data
    phone_ft_calls = [c for c in all_calls if c['platform'] != 'WhatsApp']
    outgoing = sum(1 for c in phone_ft_calls if c['outgoing'])
    incoming = sum(1 for c in phone_ft_calls if not c['outgoing'])
    answered = sum(1 for c in all_calls if c['answered'])
    missed = total_calls - answered
    total_duration = sum(c['duration'] for c in all_calls)

    d['stats'] = {
        'total': total_calls,
        'outgoing': outgoing,
        'incoming': incoming,
        'answered': answered,
        'missed': missed,
        'total_duration': total_duration,
    }

    # Platform breakdown
    platform_stats = defaultdict(lambda: {'count': 0, 'duration': 0})
    for c in all_calls:
        platform_stats[c['platform']]['count'] += 1
        platform_stats[c['platform']]['duration'] += c['duration']
    d['platforms'] = dict(platform_stats)

    # Video vs voice (only accurate for Phone/FaceTime)
    video_calls = sum(1 for c in all_calls if c['is_video'])
    voice_calls = total_calls - video_calls
    d['video_voice'] = {'video': video_calls, 'voice': voice_calls}

    # Top contacts by call count - key by phone number to deduplicate
    phone_stats = defaultdict(lambda: {
        'count': 0, 'duration': 0, 'outgoing': 0, 'incoming': 0,
        'answered': 0, 'missed': 0, 'platforms': set(), 'names': set()
    })
    for c in all_calls:
        # Use last 10 digits of phone as key for consistent matching across platforms
        phone = c['phone']
        if phone:
            digits = re.sub(r'\D', '', str(phone))
            key = digits[-10:] if len(digits) >= 7 else None
        else:
            key = None
        # Fall back to name if no valid phone
        if not key:
            key = f"name:{c['name']}"
        cs = phone_stats[key]
        cs['count'] += 1
        cs['duration'] += c['duration']
        # Only count direction for Phone/FaceTime
        if c['platform'] != 'WhatsApp':
            cs['outgoing'] += 1 if c['outgoing'] else 0
            cs['incoming'] += 0 if c['outgoing'] else 1
        cs['answered'] += 1 if c['answered'] else 0
        cs['missed'] += 0 if c['answered'] else 1
        cs['platforms'].add(c['platform'])
        cs['names'].add(c['name'])

    # Convert to contact_stats with best display name, MERGING entries with same name
    contact_stats = {}
    for key, stats in phone_stats.items():
        # Pick the longest name as display name (e.g., "Shimolee Kothari" > "Shimolee")
        best_name = max(stats['names'], key=len)
        platforms = list(stats['platforms'])

        # Check if this name should merge with an existing entry
        # First check exact match
        merge_target = None
        if best_name in contact_stats:
            merge_target = best_name
        else:
            # Check if any existing name starts with best_name + space OR best_name starts with existing + space
            for existing_name in contact_stats.keys():
                existing_lower = existing_name.lower()
                best_lower = best_name.lower()
                if existing_lower.startswith(best_lower + ' '):
                    # Existing is longer (e.g., "Shimolee Kothari"), merge into it
                    merge_target = existing_name
                    break
                elif best_lower.startswith(existing_lower + ' '):
                    # best_name is longer, we'll rename the existing entry
                    merge_target = existing_name
                    break

        if merge_target:
            # Merge with existing entry
            existing = contact_stats[merge_target]
            existing['count'] += stats['count']
            existing['duration'] += stats['duration']
            existing['outgoing'] += stats['outgoing']
            existing['incoming'] += stats['incoming']
            existing['answered'] += stats['answered']
            existing['missed'] += stats['missed']
            existing['platforms'] = list(set(existing['platforms']) | set(platforms))

            # If best_name is longer, rename the entry
            if len(best_name) > len(merge_target):
                contact_stats[best_name] = contact_stats.pop(merge_target)
        else:
            # New entry
            contact_stats[best_name] = {
                'count': stats['count'],
                'duration': stats['duration'],
                'outgoing': stats['outgoing'],
                'incoming': stats['incoming'],
                'answered': stats['answered'],
                'missed': stats['missed'],
                'platforms': platforms
            }

    # Top 10 by call count
    top_by_count = sorted(contact_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    d['top_count'] = [(name, stats) for name, stats in top_by_count]

    # Top 10 by duration
    top_by_duration = sorted(contact_stats.items(), key=lambda x: x[1]['duration'], reverse=True)[:10]
    d['top_duration'] = [(name, stats) for name, stats in top_by_duration]

    # Longest single call
    if all_calls:
        longest = max(all_calls, key=lambda x: x['duration'])
        d['longest_call'] = longest
    else:
        d['longest_call'] = None

    # Peak hour
    hour_counts = defaultdict(int)
    for c in all_calls:
        hour = datetime.fromtimestamp(c['timestamp']).hour
        hour_counts[hour] += 1
    if hour_counts:
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        d['peak_hour'] = peak_hour
    else:
        d['peak_hour'] = 12

    # Peak day of week
    day_counts = defaultdict(int)
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    for c in all_calls:
        day = datetime.fromtimestamp(c['timestamp']).strftime('%w')
        day_counts[int(day)] += 1
    if day_counts:
        peak_day = max(day_counts.items(), key=lambda x: x[1])[0]
        d['peak_day'] = days[peak_day]
    else:
        d['peak_day'] = 'Unknown'

    # Night owl calls (midnight - 5am)
    night_owl_stats = defaultdict(int)
    for c in all_calls:
        hour = datetime.fromtimestamp(c['timestamp']).hour
        if hour < 5:
            night_owl_stats[c['name']] += 1
    night_owls = sorted(night_owl_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    d['night_owls'] = night_owls

    # Early bird calls (6-9am)
    early_bird_stats = defaultdict(int)
    for c in all_calls:
        hour = datetime.fromtimestamp(c['timestamp']).hour
        if 6 <= hour <= 9:
            early_bird_stats[c['name']] += 1
    early_birds = sorted(early_bird_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    d['early_birds'] = early_birds

    # Missed call king (who you miss calls from most) - Phone/FaceTime only (has direction)
    missed_from = defaultdict(int)
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and not c['answered'] and not c['outgoing']:
            missed_from[c['name']] += 1
    missed_kings = sorted(missed_from.items(), key=lambda x: x[1], reverse=True)[:5]
    d['missed_kings'] = missed_kings

    # Call avoider (who you call but doesn't answer) - Phone/FaceTime only
    unanswered_to = defaultdict(lambda: {'attempts': 0, 'answered': 0})
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and c['outgoing']:
            unanswered_to[c['name']]['attempts'] += 1
            if c['answered']:
                unanswered_to[c['name']]['answered'] += 1

    avoiders = []
    for name, stats in unanswered_to.items():
        if stats['attempts'] >= 3:  # Lower threshold since Phone/FaceTime only
            miss_rate = (stats['attempts'] - stats['answered']) / stats['attempts']
            if miss_rate > 0.5:
                avoiders.append((name, stats['attempts'] - stats['answered'], stats['attempts']))
    avoiders.sort(key=lambda x: x[1], reverse=True)
    d['avoiders'] = avoiders[:5]

    # Speed dialer (shortest avg call duration)
    avg_durations = []
    for name, stats in contact_stats.items():
        if stats['count'] >= 5 and stats['duration'] > 0:
            avg = stats['duration'] / stats['count']
            avg_durations.append((name, avg, stats['count']))
    avg_durations.sort(key=lambda x: x[1])
    d['speed_dialers'] = avg_durations[:5]

    # Marathon talkers (longest avg call duration)
    marathon_talkers = sorted(avg_durations, key=lambda x: x[1], reverse=True)[:5]
    d['marathon_talkers'] = marathon_talkers

    # Busiest day
    daily_counts = defaultdict(int)
    for c in all_calls:
        day_str = datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d')
        daily_counts[day_str] += 1

    d['daily_counts'] = dict(daily_counts)

    if daily_counts:
        busiest_day = max(daily_counts.items(), key=lambda x: x[1])
        d['busiest_day'] = busiest_day
    else:
        d['busiest_day'] = None

    # H1 vs H2 comparison
    h1_calls = sum(1 for c in all_calls if c['timestamp'] < ts_jun)
    h2_calls = sum(1 for c in all_calls if c['timestamp'] >= ts_jun)
    d['h1_h2'] = {'h1': h1_calls, 'h2': h2_calls}

    # Heating up (more calls in H2)
    contact_h1_h2 = defaultdict(lambda: {'h1': 0, 'h2': 0})
    for c in all_calls:
        if c['timestamp'] < ts_jun:
            contact_h1_h2[c['name']]['h1'] += 1
        else:
            contact_h1_h2[c['name']]['h2'] += 1

    heating_up = []
    for name, stats in contact_h1_h2.items():
        if stats['h1'] >= 3 and stats['h2'] > stats['h1'] * 1.5:
            heating_up.append((name, stats['h1'], stats['h2']))
    heating_up.sort(key=lambda x: x[2] - x[1], reverse=True)
    d['heating_up'] = heating_up[:5]

    # Cooling down (less calls in H2)
    cooling_down = []
    for name, stats in contact_h1_h2.items():
        if stats['h1'] >= 5 and stats['h2'] < stats['h1'] * 0.5:
            cooling_down.append((name, stats['h1'], stats['h2']))
    cooling_down.sort(key=lambda x: x[1] - x[2], reverse=True)
    d['cooling_down'] = cooling_down[:5]

    # Monthly breakdown
    monthly_counts = defaultdict(int)
    monthly_duration = defaultdict(int)
    for c in all_calls:
        month = datetime.fromtimestamp(c['timestamp']).strftime('%b')
        monthly_counts[month] += 1
        monthly_duration[month] += c['duration']
    d['monthly_counts'] = dict(monthly_counts)
    d['monthly_duration'] = dict(monthly_duration)

    # Busiest month
    if monthly_counts:
        d['busiest_month'] = max(monthly_counts.items(), key=lambda x: x[1])[0]
    else:
        d['busiest_month'] = 'N/A'

    # Average calls per day
    if daily_counts:
        d['avg_daily'] = round(total_calls / len(daily_counts), 1)
    else:
        d['avg_daily'] = 0

    # Quiet days (zero calls)
    year_start = datetime.fromtimestamp(ts_start)
    year_end = min(datetime.fromtimestamp(ts_end), datetime.now())
    total_days = (year_end - year_start).days + 1
    days_with_calls = len(daily_counts)
    d['quiet_days'] = total_days - days_with_calls

    # Unique contacts
    d['unique_contacts'] = len(contact_stats)

    # === NEW DELIGHTFUL INSIGHTS ===

    # First call of the year
    if all_calls:
        first_call = all_calls[0]
        d['first_call'] = first_call
    else:
        d['first_call'] = None

    # Who calls YOU most (biggest fan - inbound only, Phone/FaceTime only since WhatsApp has no direction)
    inbound_from = defaultdict(int)
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and not c['outgoing']:
            inbound_from[c['name']] += 1
    biggest_fans = sorted(inbound_from.items(), key=lambda x: x[1], reverse=True)[:5]
    d['biggest_fans'] = biggest_fans

    # Longest streak (consecutive days calling same person)
    streaks = {}
    for name in contact_stats.keys():
        person_dates = sorted(set(
            datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d')
            for c in all_calls if c['name'] == name
        ))
        if len(person_dates) < 2:
            continue
        max_streak = 1
        current_streak = 1
        for i in range(1, len(person_dates)):
            d1 = datetime.strptime(person_dates[i-1], '%Y-%m-%d')
            d2 = datetime.strptime(person_dates[i], '%Y-%m-%d')
            if (d2 - d1).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        if max_streak >= 3:
            streaks[name] = max_streak
    if streaks:
        best_streak = max(streaks.items(), key=lambda x: x[1])
        d['longest_streak'] = best_streak
    else:
        d['longest_streak'] = None

    # Weekday vs Weekend breakdown
    weekday_calls = sum(1 for c in all_calls if datetime.fromtimestamp(c['timestamp']).weekday() < 5)
    weekend_calls = total_calls - weekday_calls
    d['weekday_weekend'] = {'weekday': weekday_calls, 'weekend': weekend_calls}

    # Call duration buckets (quick <2min, normal 2-15min, marathon 15min+)
    quick_calls = sum(1 for c in all_calls if c['answered'] and c['duration'] < 120)
    normal_calls = sum(1 for c in all_calls if c['answered'] and 120 <= c['duration'] < 900)
    long_calls = sum(1 for c in all_calls if c['answered'] and c['duration'] >= 900)
    d['duration_buckets'] = {'quick': quick_calls, 'normal': normal_calls, 'marathon': long_calls}

    # Ghost protocol (missed calls you never returned) - Phone/FaceTime only
    # Build set of people you called (outgoing) - include all platforms for callback detection
    call_times_to = defaultdict(list)  # name -> list of outgoing call timestamps
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and c['outgoing']:
            call_times_to[c['name']].append(c['timestamp'])

    # Find missed calls you never returned (Phone/FaceTime only for incoming detection)
    ghosts = defaultdict(int)
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and not c['outgoing'] and not c['answered']:
            # Check if you ever called them back after this
            later_calls = [t for t in call_times_to.get(c['name'], []) if t > c['timestamp']]
            if not later_calls:
                ghosts[c['name']] += 1
    ghost_list = sorted(ghosts.items(), key=lambda x: x[1], reverse=True)[:5]
    d['ghosts'] = ghost_list

    # Call back speed (avg time to return missed calls, in minutes) - Phone/FaceTime only
    callback_times = []
    for c in all_calls:
        if c['platform'] != 'WhatsApp' and not c['outgoing'] and not c['answered']:
            # Find first outgoing call to this person after the missed call
            later_calls = [t for t in call_times_to.get(c['name'], []) if t > c['timestamp']]
            if later_calls:
                callback_time = (min(later_calls) - c['timestamp']) / 60  # minutes
                if callback_time < 1440:  # within 24 hours
                    callback_times.append(callback_time)
    if callback_times:
        d['avg_callback_time'] = round(sum(callback_times) / len(callback_times))
    else:
        d['avg_callback_time'] = None

    # Calling personality diagnosis
    # Based on: call frequency, duration, missed rate, callback speed, outgoing ratio
    answered_calls = [c for c in all_calls if c['answered']]
    avg_duration = sum(c['duration'] for c in answered_calls) / max(len(answered_calls), 1)
    outgoing_ratio = outgoing / max(total_calls, 1)
    miss_rate = missed / max(total_calls, 1)

    if avg_duration < 60 and total_calls > 200:
        personality = ("THE SPEED DIALER", "You treat calls like texts - quick, efficient, gone")
    elif avg_duration > 600 and total_calls > 50:
        personality = ("THE CHATTY CATHY", "Once you're on the phone, you're ON the phone")
    elif miss_rate > 0.4:
        personality = ("THE SCREENER", "Your phone is always on silent, isn't it?")
    elif outgoing_ratio > 0.7:
        personality = ("THE INITIATOR", "You don't wait for calls, you make them happen")
    elif outgoing_ratio < 0.3:
        personality = ("THE POPULAR ONE", "Everyone wants to talk to you")
    elif d['avg_callback_time'] and d['avg_callback_time'] < 10:
        personality = ("THE RESPONSIVE ONE", "Missed call? You'll call back in minutes")
    elif total_calls < 50:
        personality = ("THE PHONE PHOBIC", "Calls? In this economy? You prefer texts")
    elif weekend_calls > weekday_calls * 0.5:
        personality = ("THE WEEKEND WARRIOR", "Your phone comes alive on weekends")
    else:
        personality = ("THE BALANCED CALLER", "A healthy relationship with your phone")
    d['personality'] = personality

    return d


def get_data_coverage(ts_start, ts_end, has_phone, has_whatsapp):
    """Check how much of the year we have data for."""
    earliest = None
    latest = None

    if has_phone:
        rows = q_phone(f"""
            SELECT MIN(ZDATE + {MAC_EPOCH}), MAX(ZDATE + {MAC_EPOCH})
            FROM ZCALLRECORD
            WHERE (ZDATE + {MAC_EPOCH}) > {ts_start} AND (ZDATE + {MAC_EPOCH}) < {ts_end}
        """)
        if rows and rows[0][0]:
            earliest = rows[0][0]
            latest = rows[0][1]

    if has_whatsapp:
        rows = q_whatsapp(f"""
            SELECT MIN(ZDATE + {MAC_EPOCH}), MAX(ZDATE + {MAC_EPOCH})
            FROM ZWACDCALLEVENT
            WHERE (ZDATE + {MAC_EPOCH}) > {ts_start} AND (ZDATE + {MAC_EPOCH}) < {ts_end}
        """)
        if rows and rows[0][0]:
            if earliest is None or rows[0][0] < earliest:
                earliest = rows[0][0]
            if latest is None or rows[0][1] > latest:
                latest = rows[0][1]

    return earliest, latest


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
const POSTER = (location.search.match(/[?&]poster=([a-d])\b/) || [, 'a'])[1];
slides.forEach(s => { if (s.dataset.name === 'summary') s.classList.add('t-poster-' + POSTER); });
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

CALL_CSS = r'''
/* calls: waveform of the year, one bar per week */
.wave{display:flex;align-items:center;gap:.16em;height:11em;margin-bottom:auto}
.wave i{flex:1;height:var(--h);min-height:.3em;border-radius:1em;background:var(--fg);opacity:.32}
.wave i.pk{opacity:1;background:var(--tint)}

/* calls: platform share blocks */
.share{display:flex;flex-direction:column;gap:.4em;height:16em;margin-bottom:auto}
.share div{flex:var(--p) 1 0;min-height:3.1em;display:flex;justify-content:space-between;align-items:flex-end;padding:.6em .9em;border-radius:1.1em;background:var(--ab);color:var(--af);font-weight:600;transform-origin:top left}
.share b{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.5em;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}

/* calls: video vs voice tiles */
.tiles{display:grid;grid-template-columns:repeat(12,1fr);gap:.4em;margin-bottom:auto}
.tiles i{aspect-ratio:1;border-radius:50%;background:var(--soft);background:color-mix(in srgb,var(--fg) 18%,transparent)}
.tiles i.v{border-radius:.35em;background:var(--tint);box-shadow:0 0 .7em color-mix(in srgb,var(--tint) 55%,transparent)}

/* calls: ringing avatar */
.ringing{position:relative;align-self:flex-start;margin:2.4em 0 auto 2.6em;font-size:1em}
.ringing .av.xl{margin:0;position:relative;z-index:2}
.ringing b{position:absolute;inset:0;border-radius:50%;border:.14em solid var(--fg);transform:scale(calc(1.28 + var(--r) * .32));opacity:calc(.42 - var(--r) * .12);z-index:1}
.ringing u{position:absolute;right:-.3em;bottom:-.1em;z-index:3;display:grid;place-items:center;width:2.8em;height:2.8em;border-radius:50%;background:var(--fg);color:var(--bg);font-size:1.1em;text-decoration:none;box-shadow:0 0 0 .2em var(--bg)}
.ringing u svg{width:1.3em;height:1.3em}
@keyframes ring{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.1);opacity:0}}

/* calls: talk-time waffle, one square per slice of hours */
.waffle{display:grid;grid-template-columns:repeat(12,1fr);gap:.3em;margin-bottom:auto}
.waffle i{aspect-ratio:1;border-radius:.3em;background:var(--c)}
.c0{--c:var(--cobalt)}.c1{--c:var(--pink)}.c2{--c:var(--ink)}.c3{--c:#9FB0FF}.c4{--c:var(--lav)}
.sw{display:inline-block;width:.7em;height:.7em;border-radius:.2em;background:var(--c);margin-right:.45em;vertical-align:.02em}
.pf{font-size:.7em;margin-left:.4em;letter-spacing:.1em;opacity:.9}

/* calls: hour pies for the longest call */
.pies{display:flex;flex-wrap:wrap;gap:.55em;margin-bottom:auto}
.pies i{width:var(--s);height:var(--s);border-radius:50%;background:conic-gradient(var(--fg) calc(var(--p) * 1%),var(--soft) 0);box-shadow:inset 0 0 0 .14em color-mix(in srgb,var(--fg) 30%,transparent)}

/* calls: missed-call banners */
.notes{display:flex;flex-direction:column;gap:.45em;margin-bottom:auto}
.notes div{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.7em;padding:.65em .9em .65em .65em;border-radius:1.3em;background:color-mix(in srgb,var(--white) 72%,transparent);color:var(--ink);box-shadow:0 .6em 1.6em -1em rgba(36,16,56,.5)}
.notes div:nth-child(2){opacity:.85}.notes div:nth-child(3){opacity:.7}
.notes span{display:grid;place-items:center;width:2.3em;height:2.3em;border-radius:.7em;background:var(--ink);color:var(--pink)}
.notes span svg{width:1.2em;height:1.2em}
.notes p{line-height:1.2;min-width:0}
.notes p b{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.notes p em{font-style:normal;font-size:.8em;opacity:.65}
.notes small{font-size:.75em;opacity:.55;font-weight:500}
.notes .more-n{background:none;box-shadow:none;color:var(--fg);display:block;padding:.2em .2em 0;font-weight:600;font-size:.85em;opacity:.7}

/* calls: tear-off calendar page */
.cal{align-self:flex-start;margin:1em 0 auto .4em;width:8.4em;border-radius:1.3em;overflow:hidden;background:var(--white);color:var(--ink);text-align:center;transform:rotate(-6deg);box-shadow:0 1.4em 2.6em -1.2em rgba(22,10,38,.6)}
.cal span{display:block;background:var(--pink);font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1.1em;padding:.4em 0 .35em}
.cal b{display:block;font-family:var(--display);font-weight:900;font-stretch:120%;font-variation-settings:"wdth" 120;font-size:4.4em;line-height:1;padding:.12em 0 0;letter-spacing:-.04em}
.cal small{display:block;font-size:.85em;font-weight:600;opacity:.6;padding:.2em 0 .9em}
@keyframes calIn{from{opacity:0;transform:rotate(-30deg) scale(.5)}to{opacity:1;transform:rotate(-6deg)}}

/* calls: columns (week, call lengths) */
.cols{display:flex;align-items:flex-end;gap:.5em;height:14em;margin-bottom:auto}
.cols div{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;gap:.35em;min-width:0}
.cols i{width:100%;height:var(--h);min-height:.5em;border-radius:.7em .7em .25em .25em;background:var(--fg);opacity:.22;transform-origin:bottom}
.cols i.hi{opacity:1;background:var(--tint)}
.cols b{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-variant-numeric:tabular-nums;font-size:1.05em}
.cols span{font-size:.72em;font-weight:600;opacity:.7;white-space:nowrap}

/* calls: missed, then called back */
.lag{display:flex;flex-direction:column;align-items:flex-start;margin:.6em 0 auto}
.lag div{display:flex;align-items:center;gap:.6em;padding:.5em 1.1em .5em .5em;border-radius:999px;background:var(--soft);font-weight:600;font-size:1.1em}
.lag div:last-of-type{background:var(--fg);color:var(--bg)}
.lag div span{display:grid;place-items:center;width:2.2em;height:2.2em;border-radius:50%;background:var(--bg);color:var(--fg)}
.lag div:last-of-type span{background:var(--tint);color:var(--white)}
.lag span svg{width:1.1em;height:1.1em}
.lag p{display:flex;align-items:center;gap:.9em;height:7em;margin-left:1.5em;font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.05em}
.lag p::before{content:"";height:100%;border-left:.28em dotted currentColor;opacity:.45}

.on .wave i{animation:barMid .8s var(--ease) both;animation-delay:calc(var(--k, 0) * 12ms)}
@keyframes barMid{from{transform:scaleY(0)}}
.on .share div{animation:pop .55s var(--spring) both;animation-delay:calc(.1s + var(--k, 0) * 120ms)}
.on .tiles i{animation:pop .35s var(--spring) both;animation-delay:calc(var(--k, 0) * 7ms)}
.on .ringing b{animation:ring 2.4s var(--ease) infinite;animation-delay:calc(var(--r) * .8s)}
.on .ringing u{animation:pop .5s var(--spring) both;animation-delay:.5s}
.on .waffle i{animation:pop .3s var(--spring) both;animation-delay:calc(var(--k, 0) * 9ms)}
.on .pies i{animation:pop .5s var(--spring) both;animation-delay:calc(.1s + var(--k, 0) * 110ms)}
.on .notes div{animation:pop .5s var(--spring) both;animation-delay:calc(.1s + var(--k, 0) * 220ms)}
.on .cal{animation:calIn .8s var(--spring) both}
.on .cols i{animation:barUp .7s var(--ease) both;animation-delay:calc(.1s + var(--k, 0) * 80ms)}
.on .lag div{animation:pop .5s var(--spring) both}
.on .lag p{animation:rise .6s var(--ease) both;animation-delay:.4s}
.on .lag div:last-of-type{animation-delay:.8s}
'''


def gen_html(d, path, year, has_phone, has_whatsapp, earliest_date, latest_date):
    """Generate the wrapped HTML report."""
    import html as _html
    from datetime import date as ddate

    esc = lambda v: _html.escape(str(v))
    stats = d['stats']
    year_int = int(year)
    now = datetime.now()
    last_day = now.date() if year_int == now.year else ddate(year_int, 12, 31)

    hr = d['peak_hour']
    hr_str = "12AM" if hr == 0 else f"{hr}AM" if hr < 12 else "12PM" if hr == 12 else f"{hr-12}PM"

    if d['busiest_day']:
        bd = datetime.strptime(d['busiest_day'][0], '%Y-%m-%d')
        busiest_str = bd.strftime('%b %-d')
        busiest_count = d['busiest_day'][1]

    coverage_warning = ""
    if earliest_date:
        earliest_dt = datetime.fromtimestamp(earliest_date)
        if earliest_dt > datetime(year_int, 1, 1) + timedelta(days=7):
            coverage_warning = f"Data starts {earliest_dt.strftime('%b %-d')}"

    PHONE_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>'
    MISSED_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 5l6 6 4-4M13 7h-4M13 7v4"/><path d="M3 17c5-4 13-4 18 0l-2.4 2.4-3-1.6v-2.2a12 12 0 0 0-7.2 0v2.2l-3 1.6z" fill="currentColor" stroke="none"/></svg>'

    def num(v, fmt='int', suffix=''):
        shown = f"{v:,}" if fmt == 'int' else str(v)
        return f'<span class="count" data-to="{v}" data-fmt="{fmt}" data-suffix="{esc(suffix)}">{shown}{esc(suffix)}</span>'

    def dur_hero(sec):
        h, m = int(sec // 3600), int((sec % 3600) // 60)
        if h:
            return f'{h}<small>h</small> {m}<small>m</small>' if m else f'{h}<small>h</small>'
        if m:
            return f'{m}<small>min</small>'
        return f'{int(sec)}<small>sec</small>'

    def rows(items, hide_after=5):
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

    def ringing(name):
        return ('<div class="ringing" aria-hidden="true">' + ''.join(f'<b style="--r:{k}"></b>' for k in range(3))
                + avatar(name, 'xl') + f'<u>{PHONE_SVG}</u></div>')

    def more_btn(count):
        return f'<button class="more chrome" data-more>Show all {count}</button>' if count > 5 else ''

    def pf_icons(platforms):
        icons = ''.join(g for p, g in (('Phone', '📱'), ('FaceTime', '📹'), ('WhatsApp', '💬')) if p in platforms)
        return f'<span class="pf" aria-hidden="true">{icons}</span>' if icons else ''

    def sentence(t):
        t = str(t).strip()
        return t[:1].upper() + t[1:] + ('' if t[-1:] in '.?!' else '.')

    FALLBACK = {'cobalt': 'ink', 'ink': 'cobalt', 'night': 'ink', 'lilac': 'white', 'white': 'lav', 'lav': 'lilac', 'pink': 'lilac'}
    slides = []
    last_theme = [None]

    def slide(theme, body, name):
        if theme == last_theme[0]:
            theme = FALLBACK[theme]
        last_theme[0] = theme
        slides.append(f'<section class="slide t-{theme}" data-name="{name}"><div class="card"><div class="body">{body}</div><footer class="mark"><span>wrap2026.com</span><span>Calls · {esc(year)}</span></footer></div></section>')

    # Intro
    platforms_text = []
    if has_phone:
        platforms_text.append("Phone and FaceTime" if not has_whatsapp else "Phone, FaceTime")
    if has_whatsapp:
        platforms_text.append("WhatsApp")
    platform_str = " and ".join(platforms_text)
    calls_word = lambda v: 'call' if v == 1 else 'calls'
    slide('cobalt', f'''
        <div class="intro">
          <h1 class="stretch"><span>Wrapped</span><span>{esc(year)}</span></h1>
          <div class="thread">
            <div class="bub r a1">📞 Incoming call…</div>
            <div class="bub r a2">I went through your call log.</div>
            <div class="bub r a3">Your {esc(year)} calling habits, exposed.</div>
          </div>
          <p class="hint chrome a4">Tap to start · {esc(platform_str)}{f' · {esc(coverage_warning)}' if coverage_warning else ''}</p>
        </div>''', 'intro')

    # Total calls, with the year as a voice waveform
    wave = ''
    if d['daily_counts']:
        weeks = []
        day = ddate(year_int, 1, 1)
        while day <= last_day:
            weeks.append(sum(d['daily_counts'].get((day + timedelta(days=k)).isoformat(), 0) for k in range(7)))
            day += timedelta(days=7)
        wpk = max(weeks) or 1
        pk_i = weeks.index(wpk)
        wave = '<div class="wave" aria-hidden="true">' + ''.join(
            f'<i class="{"pk" if k == pk_i else ""}" style="--h:{max(4, c / wpk * 100):.1f}%;--k:{k}"></i>' for k, c in enumerate(weeks)) + '</div>'
    slide('lilac', f'''
        {wave}
        <p class="lead">This year you made and took</p>
        <div class="hero">{num(stats['total'])}</div>
        <p class="after">{calls_word(stats['total'])}. That's <b>{format_duration_short(stats['total_duration'])}</b> of your life on the phone.</p>
        <div class="split">
          <div><b>{d['avg_daily']}</b><span>a day</span></div>
          <div><b>{stats['outgoing']:,}</b><span>outgoing</span></div>
          <div><b>{stats['incoming']:,}</b><span>incoming</span></div>
        </div>''', 'total')

    # Platform split
    if len(d['platforms']) > 1:
        total_calls = stats['total']
        colorway = {'Phone': 'a0', 'FaceTime': 'a1', 'WhatsApp': 'a2'}
        plats = [(p, d['platforms'][p]['count']) for p in ['Phone', 'FaceTime', 'WhatsApp'] if p in d['platforms']]
        plats_ranked = sorted(plats, key=lambda x: x[1], reverse=True)
        lead_p, lead_c = plats_ranked[0]
        pct = lambda c: round(c / max(total_calls, 1) * 100)
        blocks = ''.join(f'<div class="{colorway[p]}" style="--p:{max(c, 1)};--k:{k}"><span>{p}</span><b>{pct(c)}%</b></div>' for k, (p, c) in enumerate(plats_ranked))
        slide('white', f'''
            <div class="share" aria-hidden="true">{blocks}</div>
            <p class="lead">Most of your calls went through</p>
            <div class="hero name">{lead_p}</div>
            <p class="after">{num(pct(lead_c), 'int', '%')} of all your calls. Loyal.</p>
            <div class="split">{''.join(f'<div><b>{c:,}</b><span>{p} calls</span></div>' for p, c in plats)}</div>''', 'platforms')

    # Video vs voice
    video = d['video_voice']['video']
    voice = d['video_voice']['voice']
    if video > 0:
        video_pct = round(video / max(stats['total'], 1) * 100)
        nv = max(1, round(video / max(stats['total'], 1) * 96))
        tiles = ''.join(f'<i class="{"v" if (k * 37) % 96 < nv else ""}" style="--k:{k}"></i>' for k in range(96))
        slide('ink', f'''
            <div class="tiles" aria-hidden="true">{tiles}</div>
            <p class="lead">You showed your face on</p>
            <div class="hero">{num(video_pct, 'int', '%')}</div>
            <p class="after">of your calls. Hope the lighting was good.</p>
            <div class="split">
              <div><b>{video:,}</b><span>video calls</span></div>
              <div><b>{voice:,}</b><span>voice calls</span></div>
              <div><b>{video_pct}%</b><span>face to face</span></div>
            </div>''', 'video-voice')

    # Your #1 and inner circle
    if d['top_count']:
        name, st = d['top_count'][0]
        slide('pink', f'''
            {avatar(name, 'xl')}
            <p class="lead">The person you called most</p>
            <div class="hero name">{esc(name)}</div>
            <p class="after">{num(st['count'])} {calls_word(st['count'])}, {format_duration_short(st['duration'])} of talk time. {pf_icons(st['platforms'])}</p>''', 'number-one')
        tc = d['top_count'][:10]
        mx = tc[0][1]['count'] or 1
        slide('lilac', f'''
            {stack([nm for nm, _ in tc])}
            <p class="lead">Your inner circle, by calls</p>
            {rows([(esc(nm) + pf_icons(s2['platforms']), f"{s2['count']:,}", s2['count'] / mx) for nm, s2 in tc])}
            {more_btn(len(tc))}''', 'inner-circle')

    # Talk time champions
    if d['top_duration']:
        td = d['top_duration'][:5]
        tot = sum(s2['duration'] for _, s2 in td) or 1
        cells, acc = [], 0
        for k, (_, s2) in enumerate(td):
            prev = round(acc / tot * 72)
            acc += s2['duration']
            cells += [k] * (round(acc / tot * 72) - prev)
        waffle = '<div class="waffle" aria-hidden="true">' + ''.join(f'<i class="c{c}" style="--k:{k}"></i>' for k, c in enumerate(cells)) + '</div>'
        dmx = td[0][1]['duration'] or 1
        slide('white', f'''
            {waffle}
            <p class="lead">Who you spend the most time with</p>
            {rows([(f'<span class="sw c{k}"></span>' + esc(nm) + pf_icons(s2['platforms']), format_duration_short(s2['duration']), s2['duration'] / dmx) for k, (nm, s2) in enumerate(td)])}''', 'talk-time')

    # Longest call: one pie per hour on the line
    if d['longest_call']:
        lc = d['longest_call']
        call_date = datetime.fromtimestamp(lc['timestamp']).strftime('%b %-d')
        call_type = 'video' if lc['is_video'] else 'voice'
        hours = lc['duration'] / 3600
        full = min(int(hours), 15)
        part = hours - int(hours) if int(hours) < 15 else 0
        fills = [100] * full + ([round(part * 100)] if part > 0.02 or full == 0 else [])
        size = '8em' if len(fills) <= 2 else '5.6em' if len(fills) <= 6 else '3.4em'
        pies = '<div class="pies" aria-hidden="true">' + ''.join(f'<i style="--p:{p};--s:{size};--k:{k}"></i>' for k, p in enumerate(fills)) + '</div>'
        slide('cobalt', f'''
            {pies}
            <p class="lead">Your longest call lasted</p>
            <div class="hero">{dur_hero(lc['duration'])}</div>
            <p class="after">A {call_type} call with <b>{esc(lc['name'])}</b> on {call_date}. One circle per hour.</p>''', 'longest-call')

    # Year in dots
    if d['daily_counts']:
        max_count = max(d['daily_counts'].values()) or 1
        month_rows = []
        for m in range(1, 13):
            cells = []
            for day in range(1, 32):
                try:
                    cur = ddate(year_int, m, day)
                except ValueError:
                    cells.append('<i class="na"></i>')
                    continue
                if cur > last_day:
                    cells.append('<i class="fut"></i>')
                    continue
                c = d['daily_counts'].get(cur.isoformat(), 0)
                lvl = 0 if c == 0 else 1 if c <= max_count * .25 else 2 if c <= max_count * .5 else 3 if c <= max_count * .75 else 4
                cells.append(f'<i class="l{lvl}" data-tip="{c:,} {"call" if c == 1 else "calls"} on {cur.strftime("%b %-d")}"></i>')
            month_rows.append(f'<div class="mrow"><span>{ddate(year_int, m, 1).strftime("%b")}</span><div class="dots">{"".join(cells)}</div></div>')
        note = f'<p class="after">{esc(coverage_warning)}. Your Mac only keeps about 1,000 calls.</p>' if coverage_warning else ''
        slide('ink', f'''
            <div class="year" style="margin:0 0 1.6em">{"".join(month_rows)}</div>
            <p class="lead">Your year on the phone, one dot per day.</p>
            {note}
            <div class="split">
              <div><b>{d['avg_daily']:,}</b><span>a day, on average</span></div>
              <div><b>{esc(d['busiest_month'])}</b><span>busiest month</span></div>
              <div><b>{d['quiet_days']}</b><span>quiet days</span></div>
            </div>''', 'activity')

    # Busiest day
    if d['busiest_day']:
        dc = d['daily_counts']
        peak = max(dc.values()) or 1
        days = [ddate(year_int, 1, 1) + timedelta(days=k) for k in range((last_day - ddate(year_int, 1, 1)).days + 1)]
        bars = ''.join(f'<i class="{"pk" if x.isoformat() == d["busiest_day"][0] else ""}" style="--h:{max(2, dc.get(x.isoformat(), 0) / peak * 100):.1f}%"></i>' for x in days)
        spark = f'<div class="spark" aria-hidden="true" data-y="{year_int}" data-u="call" data-c="{",".join(str(dc.get(x.isoformat(), 0)) for x in days)}">{bars}</div>'
        mult = round(busiest_count / max(d['avg_daily'], 0.1), 1)
        slide('pink', f'''
            {spark}
            <p class="lead">Your phone wouldn't stop on</p>
            <div class="hero sm">{busiest_str}</div>
            <p class="after">{num(busiest_count)} {calls_word(busiest_count)} in one day, {mult}× your usual. Someone was popular.</p>''', 'busiest-day')

    # Peak hours
    slide('night', f'''
        <div class="clock" style="--a:{(hr % 12) * 30}deg" aria-hidden="true">{''.join(f'<i style="--t:{k*30}deg"></i>' for k in range(12))}<b></b><u></u></div>
        <p class="lead">Your phone rings most at</p>
        <div class="hero">{hr_str}</div>
        <p class="after">on {esc(d['peak_day'])}s.</p>''', 'peak')

    # Call style: duration buckets
    buckets = d['duration_buckets']
    total_answered = buckets['quick'] + buckets['normal'] + buckets['marathon']
    if total_answered > 0:
        bk = [('quick', 'Under 2 min', 'Quick ones', 'under two minutes. In, out, done.'),
              ('normal', '2 to 15 min', 'Normal ones', 'between two and fifteen minutes. Civilized.'),
              ('marathon', '15+ min', 'Marathons', 'over fifteen minutes. Pace yourself.')]
        win = max(bk, key=lambda b: buckets[b[0]])
        bmx = buckets[win[0]] or 1
        cols = ''.join(f'<div><b>{buckets[key]:,}</b><i class="{"hi" if key == win[0] else ""}" style="--h:{max(3, buckets[key] / bmx * 100):.1f}%;--k:{k}"></i><span>{lbl}</span></div>' for k, (key, lbl, _, _) in enumerate(bk))
        slide('white', f'''
            <div class="cols" aria-hidden="true">{cols}</div>
            <p class="lead">Most of your calls were</p>
            <div class="hero name">{win[2]}</div>
            <p class="after">{num(round(buckets[win[0]] / total_answered * 100), 'int', '%')} of answered calls ran {win[3]}</p>''', 'call-style')

    # Night owl
    if d['night_owls']:
        owl = d['night_owls'][0]
        slide('night', f'''
            <div class="moon" aria-hidden="true"></div>
            <div class="stars" aria-hidden="true">{''.join(f'<i style="left:{x}%;top:{y}%;--d:{k}"></i>' for k, (x, y) in enumerate([(8, 14), (30, 30), (52, 9), (18, 44), (66, 36), (40, 52), (84, 54), (12, 62)]))}</div>
            <p class="lead">Between midnight and 5am, you were on the phone with</p>
            <div class="hero name">{esc(owl[0])}</div>
            <p class="after">{num(owl[1])} late-night {calls_word(owl[1])}. Go to sleep.</p>''', 'night-owl')

    # Missed call king
    if d['missed_kings']:
        king = d['missed_kings'][0]
        ago = ['now', '12m ago', '1h ago']
        banners = ''.join(f'<div style="--k:{k}"><span>{MISSED_SVG}</span><p><b>{esc(king[0])}</b><em>Missed call</em></p><small>{ago[k]}</small></div>' for k in range(min(king[1], 3)))
        if king[1] > 3:
            banners += f'<div class="more-n" style="--k:3">+{king[1] - 3:,} more</div>'
        slide('pink', f'''
            <div class="notes" aria-hidden="true">{banners}</div>
            <p class="lead">The calls you missed most came from</p>
            <div class="hero name">{esc(king[0])}</div>
            <p class="after">{num(king[1])} missed {calls_word(king[1])}. Maybe check your phone?</p>''', 'missed-king')

    # Ghost protocol
    if d['ghosts']:
        gh = d['ghosts'][:5]
        gmx = gh[0][1] or 1
        slide('lav', f'''
            <div class="sticker" aria-hidden="true">👻</div>
            <p class="lead">Missed calls you never returned</p>
            {rows([(esc(nm), f'{c:,}', c / gmx) for nm, c in gh])}
            <p class="after">They're still waiting.</p>''', 'ghosts')

    # Callback speed
    if d['avg_callback_time']:
        cb_time = d['avg_callback_time']
        cb_label, cb_roast = (('Lightning', 'They barely hung up.') if cb_time < 5 else
                              ('Responsive', 'Respectable.') if cb_time < 30 else
                              ('Eventually', 'They had moved on by then.') if cb_time < 120 else
                              ('Whenever', 'Whenever you get around to it.'))
        cb_display = f"{cb_time}m" if cb_time < 60 else f"{cb_time // 60}h {cb_time % 60}m"
        cb_hero = num(cb_time) + '<small>min</small>' if cb_time < 60 else f'{cb_time // 60}<small>h</small> {cb_time % 60}<small>m</small>'
        slide('white', f'''
            <div class="lag" aria-hidden="true">
              <div><span>{MISSED_SVG}</span>Missed call</div>
              <p>{cb_display} later</p>
              <div><span>{PHONE_SVG}</span>You called back</div>
            </div>
            <p class="lead">You return a missed call in</p>
            <div class="hero">{cb_hero}</div>
            <p class="after">on average. Verdict: <b>{cb_label.lower()}</b>. {cb_roast}</p>''', 'callback')

    # First call of the year
    if d['first_call']:
        fc = d['first_call']
        fdt = datetime.fromtimestamp(fc['timestamp'])
        fc_direction = "to" if fc['outgoing'] else "from"
        slide('cobalt', f'''
            <div class="cal" aria-hidden="true"><span>{fdt.strftime('%b')}</span><b>{fdt.day}</b><small>{fdt.strftime('%-I:%M %p')}</small></div>
            <p class="lead">Your {esc(year)} started with a call {fc_direction}</p>
            <div class="hero name">{esc(fc['name'])}</div>
            <p class="after">{fdt.strftime('%b %-d at %-I:%M %p')}. Good start.</p>''', 'first-call')

    # Biggest fan
    if d['biggest_fans']:
        fan = d['biggest_fans'][0]
        slide('lilac', f'''
            {ringing(fan[0])}
            <p class="lead">The person who calls you most</p>
            <div class="hero name">{esc(fan[0])}</div>
            <p class="after">{num(fan[1])} incoming {calls_word(fan[1])}. Someone really wants to hear your voice.</p>''', 'biggest-fan')

    # Longest streak
    if d['longest_streak']:
        streak_name, streak_days = d['longest_streak']
        cols_n = 7 if streak_days <= 28 else 15
        slide('white', f'''
            <div class="chain" style="grid-template-columns:repeat({cols_n},1fr)" aria-hidden="true">{'<i></i>' * min(streak_days, 120)}</div>
            <p class="lead">You called <b>{esc(streak_name)}</b> every day for</p>
            <div class="hero">{num(streak_days)}<small>days</small></div>
            <p class="after">in a row. Commitment level: high.</p>''', 'streak')

    # Weekday vs weekend
    ww = d['weekday_weekend']
    weekday_pct = round(ww['weekday'] / max(stats['total'], 1) * 100)
    weekend_pct = 100 - weekday_pct
    per_wd, per_we = ww['weekday'] / 5, ww['weekend'] / 2
    wk_mx = max(per_wd, per_we) or 1
    week = ''.join(f'<div><i class="{"hi" if (k >= 5) == (per_we > per_wd) else ""}" style="--h:{max(3, (per_we if k >= 5 else per_wd) / wk_mx * 100):.1f}%;--k:{k}"></i><span>{dn}</span></div>' for k, dn in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']))
    slide('lav', f'''
        <div class="cols" aria-hidden="true">{week}</div>
        <p class="lead">Weekdays got</p>
        <div class="hero">{num(weekday_pct, 'int', '%')}</div>
        <p class="after">of your calls. Weekends got {weekend_pct}%. {"Work-life balance is a myth." if weekday_pct >= 72 else "Your phone comes alive on weekends." if per_we > per_wd else "Pretty even, honestly."}</p>''', 'weekday-weekend')

    # Personality
    ptype, proast = d['personality']
    glyph = {'SPEED': '⚡', 'CHATTY': '🗣️', 'SCREENER': '📵', 'INITIATOR': '📲', 'POPULAR': '💅', 'RESPONSIVE': '🏃', 'PHOBIC': '🙈', 'WEEKEND': '🎉', 'BALANCED': '🧘'}
    g = next((v for k, v in glyph.items() if k in ptype), '📞')
    slide('night', f'''
        <div class="sticker" aria-hidden="true">{g}</div>
        <p class="lead">Your calling diagnosis</p>
        <div class="hero diag">{esc(sentence(ptype.lower()).rstrip('.'))}</div>
        <p class="after">{esc(sentence(proast.replace(' - ', ', ')))}</p>''', 'personality')

    # Heating up / cooling down
    if d['heating_up']:
        ht = d['heating_up'][:5]
        hmx = max(h2 - h1 for _, h1, h2 in ht) or 1
        slide('pink', f'''
            <div class="sticker" aria-hidden="true">🔥</div>
            <p class="lead">Calling more since June</p>
            {rows([(esc(nm), f'+{h2 - h1:,}', (h2 - h1) / hmx) for nm, h1, h2 in ht])}
            <p class="after">Extra calls since June, compared to before.</p>''', 'heating-up')
    if d['cooling_down']:
        cd = d['cooling_down'][:5]
        cmx = max(h1 for _, h1, _ in cd) or 1
        slide('lilac', f'''
            <div class="sticker" aria-hidden="true">🧊</div>
            <p class="lead">They went quiet after June</p>
            {rows([(esc(nm), f'{h1:,} <i>to</i> {h2:,}', h1 / cmx) for nm, h1, h2 in cd])}
            <p class="after">Calls before June, then after.</p>''', 'cooling-down')

    # Summary: the poster people post
    pwave = spark.replace('class="spark"', 'class="spark pwave"', 1) if d['busiest_day'] else ''
    one = f'<div class="one">{avatar(d["top_count"][0][0])}<div><b>{esc(d["top_count"][0][0])}</b><span>My #1, {d["top_count"][0][1]["count"]:,} {calls_word(d["top_count"][0][1]["count"])}</span></div></div>' if d['top_count'] else ''
    plat_line = ' · '.join(f"{p} {d['platforms'][p]['count']:,}" for p in ['Phone', 'FaceTime', 'WhatsApp'] if p in d['platforms'])
    slides.append(f'''
    <section class="slide t-stage" data-name="summary">
      <div class="tilt">
        <div class="card summary poster" id="summaryCard">
          <div class="sheen" aria-hidden="true"></div>
          <div class="body">
            <h2 class="ptitle"><span>Wrapped</span> <span>{esc(year)}</span></h2>
            {pwave}
            <div class="hero">{stats['total']:,}<small>{calls_word(stats['total'])}</small></div>
            <p class="pmeta">{plat_line}</p>
            <p class="diag-sm">{esc(sentence(ptype.lower()).rstrip('.'))}</p>
            {one}
            <dl class="stats3">
              <div><dt>People</dt><dd>{d['unique_contacts']:,}</dd></div>
              <div><dt>Talk time</dt><dd>{format_duration_short(stats['total_duration'])}</dd></div>
              <div><dt>Missed</dt><dd>{stats['missed']:,}</dd></div>
            </dl>
            <button class="cta chrome" data-act><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span class="lbl">Save image</span></button>
          </div>
          <footer class="mark"><span>wrap2026.com</span><span>Calls · {esc(year)}</span></footer>
        </div>
      </div>
    </section>''')

    html_out = TEMPLATE.replace('</style>', CALL_CSS + '</style>', 1) \
                       .replace('__TITLE__', f'Calls Wrapped {esc(year)}') \
                       .replace('__FILE__', f'call_wrapped_{esc(year)}') \
                       .replace('__SLIDES__', ''.join(slides))
    with open(path, 'w') as fh:
        fh.write(html_out)
    return path


def main():
    parser = argparse.ArgumentParser(description='Call Wrapped 2026 - Your calling habits exposed')
    parser.add_argument('--output', '-o', default=None, help='Output HTML file path')
    parser.add_argument('--use-2025', action='store_true', help='Use 2025 data instead of 2026')
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  CALLS WRAPPED 2026 | wrap2026.com")
    print("=" * 50 + "\n")

    print("[*] Checking access...")
    has_phone, has_whatsapp = check_access()

    platforms = []
    if has_phone:
        platforms.append("Phone/FaceTime")
        print(f"    ✓ Phone/FaceTime: {CALL_HISTORY_DB}")
    if has_whatsapp:
        platforms.append("WhatsApp")
        print(f"    ✓ WhatsApp: {WHATSAPP_CALLS_DB}")

    print(f"\n[*] Platforms: {' + '.join(platforms)}")

    print("[*] Loading contacts...")
    contacts = extract_contacts()
    print(f"    ✓ {len(contacts)} contacts loaded")

    # Determine year
    year = "2025" if args.use_2025 else "2026"
    ts_start = TS_2025_START if year == "2025" else TS_2026_START
    ts_end = TS_2025_END if year == "2025" else TS_2026_END
    ts_jun = TS_JUN_2025 if year == "2025" else TS_JUN_2026

    # Check data coverage
    earliest, latest = get_data_coverage(ts_start, ts_end, has_phone, has_whatsapp)
    if earliest:
        earliest_dt = datetime.fromtimestamp(earliest)
        print(f"    ℹ️  Earliest call data: {earliest_dt.strftime('%b %d, %Y')}")

    # Check if we have enough 2026 data
    if not args.use_2025:
        total_2026 = 0
        if has_phone:
            r = q_phone(f"SELECT COUNT(*) FROM ZCALLRECORD WHERE (ZDATE + {MAC_EPOCH}) > {ts_start}")
            total_2026 += r[0][0]
        if has_whatsapp:
            r = q_whatsapp(f"SELECT COUNT(*) FROM ZWAAGGREGATECALLEVENT WHERE (ZFIRSTDATE + {MAC_EPOCH}) > {ts_start}")
            total_2026 += r[0][0]

        if total_2026 < 10:
            print(f"    ⚠️  Only {total_2026} calls in 2026, using 2025")
            year = "2025"
            ts_start = TS_2025_START
            ts_end = TS_2025_END
            ts_jun = TS_JUN_2025
            earliest, latest = get_data_coverage(ts_start, ts_end, has_phone, has_whatsapp)

    output_file = args.output or f'call_wrapped_{year}.html'

    spinner = Spinner()

    # Analyze phone calls
    phone_calls = []
    if has_phone:
        print(f"[*] Analyzing Phone/FaceTime {year}...")
        spinner.start("Reading call history...")
        phone_calls = analyze_phone_calls(ts_start, ts_end, ts_jun, contacts)
        spinner.stop(f"{len(phone_calls)} phone/FaceTime calls analyzed")

    # Analyze WhatsApp calls
    whatsapp_calls = []
    if has_whatsapp:
        print(f"[*] Analyzing WhatsApp {year}...")
        spinner.start("Reading WhatsApp calls...")
        whatsapp_calls = analyze_whatsapp_calls(ts_start, ts_end, ts_jun, contacts)
        spinner.stop(f"{len(whatsapp_calls)} WhatsApp calls analyzed")

    print("[*] Combining and analyzing...")
    spinner.start("Crunching numbers...")
    data = analyze_calls(phone_calls, whatsapp_calls, ts_start, ts_end, ts_jun)
    spinner.stop(f"{data['stats']['total']} total calls processed")

    print("[*] Generating report...")
    spinner.start("Building your wrapped...")
    gen_html(data, output_file, year, has_phone, has_whatsapp, earliest, latest)
    spinner.stop(f"Saved to {output_file}")

    subprocess.run(['open', output_file])
    print("\n  Done! Click through your call wrapped.\n")


if __name__ == '__main__':
    main()
