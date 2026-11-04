"""Render the combined wrap from made-up data: python3 dev/fixture_combined.py out.html [imessage-only|whatsapp-only]"""
import sys, random, importlib.util
from datetime import date, timedelta
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'both'
spec = importlib.util.spec_from_file_location('w', root / 'combined_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

random.seed(4)
daily = {}
d0 = date(2026, 1, 1)
for i in range(306):
    d = d0 + timedelta(days=i)
    base = 240 + (80 if d.weekday() >= 5 else 0) + (160 if 60 < i < 80 else 0)
    daily[d.isoformat()] = max(0, int(random.gauss(base, 90))) if random.random() > .04 else 0
daily['2026-03-14'] = 812
names = ['Mom', 'Jordan Lee', 'Alex Chen', 'Sam Martinez', 'Priya Natarajan', 'Dad', 'Maya', 'Chris O.', 'Theo', 'Aunt Rina']
srcs = ['imessage', 'whatsapp', 'imessage', 'whatsapp', 'whatsapp', 'imessage', 'imessage', 'whatsapp', 'imessage', 'whatsapp']
top = [{'name': n, 'total': c, 'sent': c // 2, 'received': c - c // 2, 'source': s, 'handle': n}
       for n, c, s in zip(names, [7204, 5918, 3377, 2940, 2102, 1760, 1403, 1220, 980, 861], srcs)]
im, wa = (47832, 23410, 24422, 312), (21540, 9800, 11740, 148)
data = {
  'stats': tuple(a + b for a, b in zip(im, wa)), 'imessage_stats': im, 'whatsapp_stats': wa,
  'top': top, 'words': 1292410,
  'personality': ('THE YAPPER', 'carries every conversation alone'),
  'hour': 22, 'day': 'Sunday', 'starter_pct': 62, 'resp': 4,
  'group_stats': {'count': 51, 'total': 28220, 'sent': 6102},
  'group_leaderboard': [{'name': n, 'msg_count': c, 'source': s} for n, c, s in
      [('Sunday dinner crew', 4210, 'imessage'), ('Cousins 🇮🇳 (official)', 3980, 'whatsapp'), ('Fantasy league', 2311, 'imessage'), ('Family', 1870, 'whatsapp'), ('Climbing <3', 1402, 'imessage')]],
  'late': [('Jordan Lee', 412, 'whatsapp')], 'busiest_day': ('2026-03-14', 812),
  'fan': [('Aunt Rina', 640, 120)], 'simp': [('Priya Natarajan', 1500, 602)],
  'priority_list': [('Mom', .6, 0), ('Priya Natarajan', 1.4, 0), ('Jordan Lee', 2, 0), ('Maya', 3.5, 0), ('Theo', 7, 0)],
  'fast_responders': [('Dad', .4, 0), ('Alex Chen', 1.2, 0), ('Sam Martinez', 4, 0), ('Chris O.', 9, 0), ('Mom', 74, 0)],
  'initiation_breakdown': [('Theo', 90, 10, 100), ('Maya', 40, 5, 45), ('Aunt Rina', 4, 60, 64), ('Dad', 10, 70, 80)],
  'heating': [('Priya Natarajan', 120, 1980), ('Theo', 200, 780), ('Maya', 90, 520)],
  'ghosted': [('Chris O.', 640, 12), ('Roommate Ben', 300, 0), ('Kelsey', 210, 4)],
  'emoji': [('😭', 2811), ('💀', 1990), ('🙏', 1204), ('😂', 990), ('❤️', 870)],
  'daily_counts': daily, 'avg_daily': 226, 'busiest_month': 'Mar', 'quiet_days': 11,
}
w.gen_html(data, out, '2026', mode != 'whatsapp-only', mode != 'imessage-only')
print(out)
