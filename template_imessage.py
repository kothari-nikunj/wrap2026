def gen_html(d, contacts, path):
    import html as _html
    import json as _json
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
        busiest_mult = round(busiest_count / max(msgs_per_day, 1), 1)

    def num(v, fmt='int', suffix=''):
        """Big number that counts up when its slide opens."""
        shown = f"{v:,}" if fmt == 'int' else str(v)
        return f'<span class="count" data-to="{v}" data-fmt="{fmt}" data-suffix="{esc(suffix)}">{shown}{esc(suffix)}</span>'

    def mins(m):
        if m < 1: return "under a minute"
        if m < 60: return f"{int(m)} min"
        return f"{m/60:.1f} hr"

    def rows(items, hide_after=5):
        """items: list of (label_html, value_html, weight 0..1)"""
        out = []
        for i, (label, value, w) in enumerate(items, 1):
            hidden = ' extra' if i > hide_after else ''
            out.append(f'<li class="row{hidden}" style="--w:{max(0.04, min(1, w)):.3f};--d:{i}"><span class="rk">{i}</span><span class="nm">{label}</span><span class="vl">{value}</span></li>')
        return '<ol class="rows">' + ''.join(out) + '</ol>'

    def initials(name):
        parts = [p for p in str(name).replace('+', ' ').split() if p[:1].isalpha()]
        return esc(''.join(p[0] for p in parts[:2]).upper() or '#')
    def avatar(name, cls=''):
        return f'<span class="av a{sum(map(ord, str(name))) % 5} {cls}">{initials(name)}</span>'

    def stack(names):
        return '<div class="stack" aria-hidden="true">' + ''.join(avatar(x) for x in names[:5]) + '</div>'

    def more_btn(count):
        return f'<button class="more chrome" data-more>Show all {count}</button>' if count > 5 else ''

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
    slides.append(slide('lilac', f'''
        <div class="pile" aria-hidden="true">{''.join('<i class="s"></i>' if (k * s[1]) % max(s[0],1) < s[1] else '<i></i>' for k in range(min(msgs_per_day, 240)))}</div>
        <p class="lead">This year you sent and received</p>
        <div class="hero">{num(s[0])}</div>
        <p class="after">messages. That's about {msgs_per_day:,} a day, one bubble each.</p>
        <div class="split">
          <div><b>{s[1]:,}</b><span>you sent</span></div>
          <div><b>{s[2]:,}</b><span>you got</span></div>
          <div><b>{s[3]:,}</b><span>people</span></div>
        </div>''', 'total'))

    # Words
    words = d['words']
    pages = max(1, words // 250)
    slides.append(slide('white', f'''
        <div class="redact" aria-hidden="true">{''.join(f'<i style="--w:{w}%"></i>' for w in (92, 64, 81, 100, 47, 88, 73, 95, 58, 84, 69))}</div>
        <p class="lead">You typed</p>
        <div class="hero">{num(words)}</div>
        <p class="after">words. About {pages:,} pages, or {max(1, round(pages/300))} {"novel" if round(pages/300) <= 1 else "novels"} nobody asked for.</p>''', 'words'))

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
              <div><b>{d['avg_daily']}</b><span>a day, on average</span></div>
              <div><b>{esc(d['busiest_month'])}</b><span>busiest month</span></div>
              <div><b>{d['quiet_days']}</b><span>days of silence</span></div>
            </div>''', 'year'))

    # Your #1 and inner circle
    if top:
        slides.append(slide('pink', f'''
            {avatar(top[0]["name"], 'xl')}
            <p class="lead">The person you texted most</p>
            <div class="hero name">{esc(top[0]["name"])}</div>
            <p class="after">{num(top[0]["count"])} messages. {round(top[0]["count"] / max(s[0], 1) * 100)}% of your whole year.</p>''', 'number-one'))
        mx = top[0]['count'] or 1
        slides.append(slide('lilac', f'''
            <div class="stack" aria-hidden="true">{''.join(avatar(c["name"]) for c in top[:5])}</div>
            <p class="lead">Your inner circle</p>
            {rows([(esc(c["name"]), f'{c["count"]:,}', c["count"] / mx) for c in top[:10]])}
            {more_btn(len(top[:10]))}''', 'inner-circle'))

    # Groups
    gs = d['group_stats']
    if gs['count'] > 0:
        yours = round(gs['sent'] / max(gs['total'], 1) * 100)
        role = "a lurker" if yours < 40 else "the main character" if yours > 60 else "a solid contributor"
        def gname(gc):
            if isinstance(gc['name'], str):
                return esc(gc['name'])
            names = [n(h[0]) for h in gc['name'][:2]]
            extra = gc['participant_count'] - len(names)
            return ', '.join(names) + (f" +{extra}" if extra > 0 else '')
        lb = d['group_leaderboard'][:10]
        gmx = lb[0]['msg_count'] if lb else 1
        slides.append(slide('cobalt', f'''
            <div class="stack groups" aria-hidden="true">{''.join(avatar(gname(gc)) for gc in lb[:5])}</div>
            <p class="lead">You were in {num(gs['count'])} group chats and wrote {yours}% of what they said. You're {role}.</p>
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
    verdict = "Basically instant." if r < 10 else "Respectable." if r < 60 else "People have moved on by then."
    slides.append(slide('white', f'''
        <div class="thread"><div class="bub r typing"><i></i><i></i><i></i></div></div>
        <p class="lead">Your average reply takes</p>
        <div class="hero">{num(r)}<small>min</small></div>
        <p class="after">{verdict}</p>''', 'response'))

    # Peak hours
    slides.append(slide('night', f'''
        <div class="clock" style="--a:{(hr % 12) * 30 + 0}deg" aria-hidden="true">{''.join(f'<i style="--t:{k*30}deg"></i>' for k in range(12))}<b></b><u></u></div>
        <p class="lead">You text most at</p>
        <div class="hero">{hr_str}</div>
        <p class="after">on {esc(d['day'])}s.</p>''', 'peak'))

    # Streak + marathon
    if d.get('streak') or d.get('marathon'):
        parts = []
        if d.get('streak'):
            st = d['streak']
            parts.append(f'''<div class="duo"><div class="hero sm">{num(st['length'])}</div><p class="after">days in a row with <b>{n(st['handle'])}</b>, {st['start'].strftime('%b %-d')} to {st['end'].strftime('%b %-d')}.</p></div>''')
        if d.get('marathon'):
            mm = d['marathon']
            mdate = dt.strptime(mm['date'], '%Y-%m-%d').strftime('%b %-d')
            parts.append(f'''<div class="duo"><div class="hero sm">{num(mm['count'])}</div><p class="after">messages with <b>{n(mm['handle'])}</b> on {mdate}, over {mm['hours']} hours.</p></div>''')
        chain = ''
        if d.get('streak'):
            chain = '<div class="chain" aria-hidden="true">' + '<i></i>' * min(d['streak']['length'], 120) + '</div>'
        slides.append(slide('lilac', chain + '<p class="lead">Your longest runs</p>' + ''.join(parts), 'streaks'))

    # 3am bestie
    if d['late']:
        ln = d['late'][0]
        slides.append(slide('night', f'''
            <div class="moon" aria-hidden="true"></div>
            <div class="stars" aria-hidden="true">{''.join(f'<i style="left:{x}%;top:{y}%;--d:{k}"></i>' for k, (x, y) in enumerate([(8, 14), (30, 30), (52, 9), (18, 44), (66, 36), (40, 52), (84, 54), (12, 62)]))}</div>
            <p class="lead">Between midnight and 5am, you texted</p>
            <div class="hero name">{n(ln[0])}</div>
            <p class="after">{num(ln[1])} times. Go to sleep.</p>''', 'three-am'))

    # Busiest day
    if d['busiest_day']:
        bmx = busiest_top[0][1] if busiest_top else 1
        spark = ''
        if d['daily_counts']:
            dc = d['daily_counts']; peak = max(dc.values()) or 1
            last = now.date() if year == now.year else ddate(year, 12, 31)
            days = [ddate(year, 1, 1) + timedelta(days=k) for k in range((last - ddate(year, 1, 1)).days + 1)]
            bars = ''.join(f'<i class="{"pk" if x.isoformat() == d["busiest_day"][0] else ""}" style="--h:{max(2, dc.get(x.isoformat(), 0) / peak * 100):.1f}%"></i>' for x in days)
            spark = f'<div class="spark" aria-hidden="true">{bars}</div>'
        slides.append(slide('pink', f'''
            {spark}
            <p class="lead">Your most unhinged day</p>
            <div class="hero">{busiest_str}</div>
            <p class="after">{num(busiest_count)} messages, {busiest_mult}× a normal day. What happened?</p>
            {rows([(n(h), f'{c:,}', c / bmx) for h, c in busiest_top[:10]]) if busiest_top else ''}
            {more_btn(len(busiest_top[:10]))}''', 'busiest-day'))

    # Biggest fan / down bad
    if d['fan']:
        f = d['fan'][0]
        slides.append(slide('cobalt', f'''
            {avatar(get_name(f[0], contacts), 'xl')}
            <p class="lead">Your biggest fan</p>
            <div class="hero name">{n(f[0])}</div>
            <p class="after">texts you {num(round(f[1]/(f[2]+1), 1), 'dec', '×')} more than you text them.</p>
            <div class="vs"><div style="--w:1"><span>{n(f[0])}</span><b>{f[1]:,}</b></div><div style="--w:{f[2]/max(f[1],1):.3f}"><span>You</span><b>{f[2]:,}</b></div></div>''', 'biggest-fan'))
    if d['simp']:
        si = d['simp'][0]
        slides.append(slide('pink', f'''
            {avatar(get_name(si[0], contacts), 'xl')}
            <p class="lead">You're down bad for</p>
            <div class="hero name">{n(si[0])}</div>
            <p class="after">You text them {num(round(si[1]/(si[2]+1), 1), 'dec', '×')} more than they text you.</p>
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
            {rows([(n(h), mins(t), 1 - i / 6) for i, (h, t, _) in enumerate(fr)])}''', 'fast-responders'))

    # Who reaches out
    if d.get('initiation_breakdown'):
        ib = d['initiation_breakdown']
        you_out = [(h, y, tc) for h, y, t, tc in ib if tc > 0 and y / tc > 0.7][:3]
        they_in = [(h, t, tc) for h, y, t, tc in ib if tc > 0 and t / tc > 0.7][:3]
        if you_out or they_in:
            body = '<div class="thread big"><div class="bub s">hey</div><div class="bub s">you there?</div><div class="bub s">hello??</div></div>'
            if you_out:
                body += '<p class="lead">You always text first</p>' + rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in you_out])
            if they_in:
                body += '<p class="lead gap">They always text first</p>' + rows([(n(h), f'{int(v/tc*100)}%', v / tc) for h, v, tc in they_in])
            slides.append(slide('cobalt', body, 'who-reaches-out'))

    # Heating up / ghosted
    if d.get('heating'):
        ht = d['heating'][:5]
        hmx = max((b - a) for _, a, b in ht) or 1
        slides.append(slide('pink', f'''
            <div class="sticker" aria-hidden="true">🔥</div>
            <p class="lead">Heating up since June</p>
            {rows([(n(h), f'+{b-a:,}', (b - a) / hmx) for h, a, b in ht])}''', 'heating-up'))
    if d.get('ghosted'):
        gh = d['ghosted'][:5]
        gmx2 = max(b for _, b, _ in gh) or 1
        slides.append(slide('lav', f'''
            <div class="sticker" aria-hidden="true">👻</div>
            <p class="lead">They went quiet after June</p>
            {rows([(n(h), f'{b:,} <i>to</i> {a:,}', b / gmx2) for h, b, a in gh])}
            <p class="after">Messages before June, then after.</p>''', 'ghosted'))

    # Emoji
    if d['emoji'] and any(e[1] > 0 for e in d['emoji']):
        em = [e for e in d['emoji'] if e[1] > 0]
        slides.append(slide('white', f'''
            <div class="sticker big" aria-hidden="true">{esc(em[0][0])}</div>
            <p class="lead">Your emotional range</p>
            <div class="emoji">{"".join(f'<span style="--d:{i}">{esc(e[0])}</span>' for i, e in enumerate(em[1:]))}</div>
            <p class="after">{esc(em[0][0])} alone: {em[0][1]:,} times.</p>''', 'emoji'))

    # Summary
    top3 = ', '.join(esc(c["name"]) for c in top[:3]) if top else "Nobody yet"
    slides.append(f'''
    <section class="slide t-stage" data-name="summary">
      <div class="tilt">
        <div class="card summary" id="summaryCard">
          <div class="sheen" aria-hidden="true"></div>
          <div class="body">
            <p class="lead">My {year} in texts</p>
            <div class="hero">{s[0]:,}</div>
            <p class="after">messages</p>
            <dl class="grid4">
              <div><dt>People</dt><dd>{s[3]:,}</dd></div>
              <div><dt>Words</dt><dd>{words:,}</dd></div>
              <div><dt>I start</dt><dd>{d['starter_pct']}%</dd></div>
              <div><dt>Reply</dt><dd>{d['resp']} min</dd></div>
            </dl>
            <p class="diag-sm">{esc(ptype.lower())}</p>
            <p class="top3">{top3}</p>
          </div>
          <footer class="mark"><span>wrap2026.com</span><span>iMessage · {year}</span></footer>
        </div>
      </div>
    </section>''')

    html_out = TEMPLATE.replace('__TITLE__', f'iMessage Wrapped {year}') \
                       .replace('__FILE__', f'imessage_wrapped_{year}') \
                       .replace('__SLIDES__', ''.join(slides))
    with open(path, 'w') as fh:
        fh.write(html_out)
    return path
