"""Render call_wrapped from made-up data: python3 dev/fixture_call.py out.html"""
import sys, random, importlib.util
from datetime import date, datetime, timedelta
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = sys.argv[1]
spec = importlib.util.spec_from_file_location('w', root / 'call_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

random.seed(7)
daily = {}
d0 = date(2026, 1, 1)
for i in range(306):
    d = d0 + timedelta(days=i)
    base = 4 + (3 if d.weekday() >= 5 else 0) + (5 if 120 < i < 150 else 0)
    c = max(0, int(random.gauss(base, 3)))
    if c:
        daily[d.isoformat()] = c
daily['2026-05-17'] = 31
total = sum(daily.values())

names = ['Mom', 'Jordan Lee', 'Alex Chen', 'Sam Martinez', 'Priya Natarajan', 'Dad', 'Maya', 'Chris O.', 'Theo', 'Aunt Rina']
def st(count, dur, plats):
    return {'count': count, 'duration': dur, 'outgoing': count // 2, 'incoming': count // 2, 'answered': count - 3, 'missed': 3, 'platforms': plats}
top_count = [(n, st(c, c * 410, p)) for n, c, p in zip(names, [212, 160, 131, 98, 77, 64, 51, 40, 33, 28],
             [['Phone', 'FaceTime'], ['Phone'], ['WhatsApp'], ['Phone', 'WhatsApp'], ['FaceTime'], ['Phone'], ['Phone', 'FaceTime', 'WhatsApp'], ['Phone'], ['FaceTime'], ['Phone']])]
top_duration = [(n, st(c, s, p)) for n, c, s, p in [('Jordan Lee', 160, 151200, ['Phone']), ('Mom', 212, 118800, ['Phone', 'FaceTime']),
                ('Priya Natarajan', 77, 72000, ['FaceTime']), ('Alex Chen', 131, 40100, ['WhatsApp']), ('Theo', 33, 21000, ['FaceTime'])]]

data = {
  'stats': {'total': total, 'outgoing': 702, 'incoming': total - 702 - 300, 'answered': total - 288, 'missed': 288, 'total_duration': 1_012_340},
  'platforms': {'Phone': {'count': total - 512 - 240, 'duration': 600000}, 'FaceTime': {'count': 512, 'duration': 300000}, 'WhatsApp': {'count': 240, 'duration': 112340}},
  'video_voice': {'video': 341, 'voice': total - 341},
  'top_count': top_count, 'top_duration': top_duration,
  'longest_call': {'name': 'Jordan Lee', 'duration': 4 * 3600 + 37 * 60, 'timestamp': datetime(2026, 3, 8, 21, 14).timestamp(), 'is_video': False,
                   'outgoing': True, 'answered': True, 'platform': 'Phone', 'phone': '5550001111'},
  'peak_hour': 18, 'peak_day': 'Sunday',
  'night_owls': [('Jordan Lee', 23), ('Theo', 9)], 'early_birds': [('Mom', 40)],
  'missed_kings': [('Aunt Rina', 27), ('Dad', 12)], 'avoiders': [],
  'speed_dialers': [], 'marathon_talkers': [],
  'daily_counts': daily, 'busiest_day': ('2026-05-17', 31),
  'h1_h2': {'h1': 900, 'h2': 1100},
  'heating_up': [('Priya Natarajan', 12, 65), ('Theo', 8, 25), ('Maya', 4, 19)],
  'cooling_down': [('Chris O.', 34, 6), ('Roommate Ben', 20, 2), ('Kelsey', 15, 4)],
  'monthly_counts': {}, 'monthly_duration': {}, 'busiest_month': 'May', 'avg_daily': round(total / len(daily), 1),
  'quiet_days': 306 - len(daily), 'unique_contacts': 143,
  'first_call': {'name': 'Mom', 'timestamp': datetime(2026, 1, 1, 0, 3).timestamp(), 'outgoing': True, 'duration': 300,
                 'answered': True, 'platform': 'Phone', 'is_video': False, 'phone': '5550002222'},
  'biggest_fans': [('Mom', 118), ('Dad', 60)], 'longest_streak': ('Mom', 23),
  'weekday_weekend': {'weekday': round(total * .64), 'weekend': total - round(total * .64)},
  'duration_buckets': {'quick': 612, 'normal': 801, 'marathon': 133},
  'ghosts': [('Unknown Caller', 14), ('Dentist Office', 9), ('Chris O.', 6), ('Kelsey', 3)],
  'avg_callback_time': 42,
  'newcomer': {'name': 'Kelsey', 'count': 41, 'new': 9, 'kept': 62},
  'personality': ('THE CHATTY CATHY', "Once you're on the phone, you're ON the phone"),
}
w.gen_html(data, out, '2026', True, True, datetime(2026, 1, 1, 0, 3).timestamp(), datetime(2026, 11, 2).timestamp())
print(out)
