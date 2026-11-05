"""Run combined merge_data on small made-up inputs. python3 dev/test_merge.py"""
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('w', root / 'combined_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)


def side(total, gaps, starter):
    return {'stats': (total, total // 2, total - total // 2, 3), 'resp_gaps': gaps, 'starter_pct': starter,
            'words': 100, 'emoji': {}, 'daily_counts': {'2026-01-01': total}, 'top': [], 'busiest_day': ('2026-01-01', total)}


for has_im, has_wa in [(True, True), (True, False), (False, True)]:
    d = w.merge_data(side(300, [1, 2, 3], 60), side(100, [10, 20], 20), {}, {}, has_im, has_wa)
    print(has_im, has_wa, 'resp', d['resp'], 'starter', d['starter_pct'])

d = w.merge_data(side(300, [1, 2, 3], 60), side(100, [10, 20], 20), {}, {}, True, True)
assert d['resp'] == 3, d['resp']  # pooled median of [1,2,3,10,20]
assert d['starter_pct'] == 50, d['starter_pct']  # (60*300 + 20*100) / 400
print('ok')
