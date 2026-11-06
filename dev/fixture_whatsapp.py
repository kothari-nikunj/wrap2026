"""Render WhatsApp Wrapped from made-up data: python3 dev/fixture_whatsapp.py out.html"""
import sys, random, importlib.util
from datetime import date, timedelta
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = sys.argv[1]
spec = importlib.util.spec_from_file_location('w', root / 'whatsapp_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

random.seed(7)
daily = {}
d0 = date(2026, 1, 1)
for i in range(306):
    d = d0 + timedelta(days=i)
    base = 120 + (50 if d.weekday() >= 5 else 0) + (110 if 150 < i < 175 else 0)
    daily[d.isoformat()] = max(0, int(random.gauss(base, 50))) if random.random() > .04 else 0
daily['2026-06-21'] = 540

# JIDs: fake names come from contacts, two numbers stay unresolved to exercise phone formatting
contacts = {f'{k}@s.whatsapp.net': v for k, v in {
    '1001': 'Mom', '1002': 'Jordan Lee', '1003': 'Alex Chen', '1004': 'Sam Martinez',
    '1005': 'Priya Natarajan', '1006': 'Dad', '1007': 'Maya', '1008': 'Chris O.',
    '1009': 'Theo', '1010': 'Aunt Rina', '1011': 'Kelsey', '1012': 'Roommate Ben', '1013': 'Bartholomew Featherstonehaugh',
}.items()}
j = lambda k: f'{k}@s.whatsapp.net'
top = [(j(k), t, t // 2, t - t // 2) for k, t in
       [(1001, 5204), (1002, 4118), (1003, 2977), (1004, 2240), ('15555550123', 1902), (1006, 1460), (1007, 1103)]]
data = {
  'year': 2026, 'stats': (38412, 18210, 20202, 214), 'top': top, 'words': 512880,
  'personality': ('CONVERSATION STARTER', 'always making the first move'),
  'hour': 21, 'day': 'Saturday', 'starter_pct': 68, 'resp': 7,
  'group_stats': {'count': 23, 'total': 41220, 'sent': 6102},
  'group_leaderboard': [{'chat_id': i, 'name': nm, 'msg_count': c} for i, (nm, c) in enumerate(
      [('Cousins <3 & co', 9210), ('Lisbon trip 🇵🇹', 6980), ('5-a-side Tuesdays', 4311), ('Family', 2870), ('Unnamed Group', 1402)])],
  'late': [(j(1013), 388)], 'busiest_day': ('2026-06-21', 540),
  'fan': [(j(1010), 640, 120)], 'simp': [(j(1005), 1500, 602)],
  'priority_list': [(j(1001), .6, 80), (j(1005), 1.4, 70), (j(1002), 2, 60), (j(1007), 3.5, 55), (j(1009), 7, 51)],
  'fast_responders': [(j(1006), .4, 90), (j(1003), 1.2, 80), (j(1004), 4, 70), (j('447700900123'), 9, 60), (j(1001), 14, 50)],
  'initiation_breakdown': [(j(1009), 72, 28, 100), (j(1007), 45, 0, 45), (j(1005), 80, 10, 90), (j(1008), 33, 3, 36), (j(1011), 60, 15, 75), (j(1010), 4, 60, 64), (j(1006), 10, 70, 80), (j(1012), 0, 41, 41)],
  'heating': [(j(1005), 120, 1980), (j(1009), 200, 780), (j(1007), 90, 520)],
  'ghosted': [(j(1008), 640, 2), (j(1012), 300, 0), (j(1011), 210, 1)],
  'emoji': [('😂', 2811), ('😭', 1990), ('🙏', 1204), ('❤️', 990), ('🔥', 870)],
  'newcomer': {'name': 'Bartholomew Featherstonehaugh', 'count': 12, 'new': 1, 'kept': 1},
  'daily_counts': daily, 'avg_daily': 126, 'busiest_month': 'Jun', 'quiet_days': 9,
}
w.gen_html(data, contacts, out)
print(out)
