"""Render a wrap from made-up data: python3 dev/fixture.py imessage out.html"""
import sys, random, importlib.util
from datetime import date, timedelta
from pathlib import Path

root = Path(__file__).resolve().parent.parent
which, out = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location('w', root / f'{which}_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

random.seed(4)
daily = {}
d0 = date(2026, 1, 1)
for i in range(306):
    d = d0 + timedelta(days=i)
    base = 180 + (60 if d.weekday() >= 5 else 0) + (140 if 60 < i < 80 else 0)
    daily[d.isoformat()] = max(0, int(random.gauss(base, 70))) if random.random() > .04 else 0
daily['2026-03-14'] = 612
names = ['Mom', 'Jordan Lee', 'Alex Chen', 'Sam Martinez', 'Priya Natarajan', 'Dad', 'Maya', 'Chris O.', 'Theo', 'Aunt Rina']
top = [{'name': n, 'count': c} for n, c in zip(names, [6204, 4918, 3377, 2940, 2102, 1760, 1403, 1220, 980, 861])]
data = {
  'year': 2026, 'stats': (47832, 23410, 24422, 312), 'top': top, 'words': 892410,
  'personality': ('NOCTURNAL MENACE', 'terrorizes people at ungodly hours'),
  'hour': 23, 'day': 'Sunday', 'starter_pct': 62, 'resp': 4,
  'group_stats': {'count': 38, 'total': 18220, 'sent': 4102},
  'group_leaderboard': [{'name': n, 'participant_count': 5, 'msg_count': c} for n, c in
      [('Sunday dinner crew', 4210), ('Bachelor party 🍾', 2980), ('Fantasy league', 2311), ('Family', 1870), ('Climbing', 1402), ('Book club', 990), ('Roommates 2019', 610)]],
  'streak': {'handle': 'Mom', 'length': 87, 'start': date(2026, 4, 2), 'end': date(2026, 6, 27)},
  'marathon': {'handle': 'Jordan Lee', 'date': '2026-03-14', 'count': 488, 'hours': 14},
  'late': [('Jordan Lee', 412)], 'busiest_day': ('2026-03-14', 612),
  'busiest_day_top': [('Jordan Lee', 488), ('Mom', 41), ('Alex Chen', 30), ('Theo', 22), ('Maya', 12), ('Dad', 9)],
  'fan': [('Aunt Rina', 640, 120)], 'simp': [('Priya Natarajan', 1500, 602)],
  'priority_list': [('Mom', .6, 0), ('Priya Natarajan', 1.4, 0), ('Jordan Lee', 2, 0), ('Maya', 3.5, 0), ('Theo', 7, 0)],
  'fast_responders': [('Dad', .4, 0), ('Alex Chen', 1.2, 0), ('Sam Martinez', 4, 0), ('Chris O.', 9, 0), ('Mom', 14, 0)],
  'initiation_breakdown': [('Theo', 90, 10, 100), ('Maya', 40, 5, 45), ('Aunt Rina', 4, 60, 64), ('Dad', 10, 70, 80)],
  'heating': [('Priya Natarajan', 120, 1980), ('Theo', 200, 780), ('Maya', 90, 520)],
  'ghosted': [('Chris O.', 640, 12), ('Roommate Ben', 300, 0), ('Kelsey', 210, 4)],
  'emoji': [('😭', 2811), ('💀', 1990), ('🙏', 1204), ('😂', 990), ('❤️', 870), ('🥲', 400)],
  'daily_counts': daily, 'avg_daily': 156, 'busiest_month': 'Mar', 'quiet_days': 11,
}
w.gen_html(data, {}, out)
print(out)
