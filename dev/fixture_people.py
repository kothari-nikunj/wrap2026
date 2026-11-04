"""Render People Wrapped from made-up data: python3 dev/fixture_people.py out.html"""
import sys, base64, importlib.util
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = sys.argv[1]
spec = importlib.util.spec_from_file_location('w', root / 'people_wrapped.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

SHORT = """Mostly logistics. "Running 10 late" appears 41 times, and "here" another 30.

The one real thread was the couch. You argued for three days in March about whether a green velvet sofa was "a statement or a mistake", and they sent a photo of it in the living room with "statement." That was the end of it."""

MEDIUM = """This was the year of the Lisbon trip. It started in January with "ok hear me out" and a link to a $412 flight, and by February you had a shared spreadsheet with a tab called "absolutely not" for the restaurants you vetoed.

The trip itself shows up as a burst of 300 messages in four days, mostly "where are you" and "I'm at the tram stop, the OTHER tram stop." After you got back, they sent "I think about that custard tart weekly" and you replied "same" in under a minute.

The fall was quieter. They started a new job in September, and the messages turned into short check-ins: "surviving?", "barely", "drinks thursday?" Thursday drinks happened five times."""

LONG = """You two talked every single day, and most of it was the house. In February they sent "we're actually doing this" with a screenshot of a pre-approval letter, and for the next four months the thread was listings, open-house photos, and your running scorecard. You rated 23 houses. The one on Alder Street got a 9 and the note "the kitchen is a crime but the yard."

The offer fight happened in May. They wanted to go $40k over asking; you said "you will hate yourself in October." They went $25k over and lost it to a cash buyer. The next message, two hours later, was just "ok you were right but I'm sad."

Then June, and the Alder Street sellers came back. "THEY CALLED BACK" at 7:12am, followed by eleven exclamation points and a voice memo you replied to with "I'm crying at a red light."

Moving day was July 19. You were there at 6am with coffee and a label maker, and the thread that week is a list of what went missing: the drill, one of the cats for forty minutes ("found her in the dryer, she's fine, I'm not"), and the box marked "important cables" that turned out to be empty.

The rest of the year was the yard. Tomatoes in August ("we have 40 tomatoes and no plan"), a raccoon in September, and a long argument in October about whether a fire pit needs a permit. It does. They found out the hard way.

You ended the year with "come over Sunday, we finally have chairs." You said yes before they finished typing."""

VERY_LONG = LONG + """

There was also the side plot with the band. They joined a cover band in March as the second guitarist, and you were sent every rehearsal recording, all of them labeled "rough." You gave notes. They ignored every note. The first gig was at a brewery in April for an audience of "maybe 30, half were our parents," and you were there with a sign that said "PLAY FREE BIRD" that they never forgave.

By November the band had a name, three originals, and a fight about the name. The last message about it was "we're going with Tuesday Parking and I don't want to hear it." You didn't say anything. You sent a thumbs up and a link to the domain, already registered."""

MOM = """Mom texts you "good morning" with a sunflower emoji almost every day: 287 times this year. You replied to about half of them, usually with a heart.

The real conversations were in April, when Grandpa was in the hospital. Those messages are short and frequent: "out of surgery", "he asked for pudding", "he's complaining about the pudding, good sign." She signed off every night with "love you, sleep."

She also discovered voice-to-text in June, which produced "please call me when you have a moment it is not an emergency period" and, later, "the dog ate a sock exclamation point." """

summaries = [LONG, MOM, MEDIUM, VERY_LONG, SHORT, MEDIUM, LONG, SHORT]
names = ['Jordan Lee', 'Mom ❤️', 'Alexandria Montgomery-Okafor', 'Sam Martinez', 'Priya Natarajan', 'Dad', 'Maya',
         'Chris O.', 'Theo', 'Aunt Rina', '+1 (415) 555-0134', 'Bartholomew', 'Kelsey Wu', 'Ben', 'Nora <script>',
         'Rafael Gómez', 'Ivy', 'Coach Dan', 'Lena & Marco', 'Grace Park', 'Omar', 'Zoe', 'Wes Anderson-Kim', 'Hana', 'Pete']
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g" x2="1" y2="1">'
       '<stop stop-color="#FF5FA2"/><stop offset="1" stop-color="#2F4BFF"/></linearGradient></defs>'
       '<rect width="100" height="100" fill="url(#g)"/><circle cx="50" cy="40" r="18" fill="#EEE8FF"/>'
       '<ellipse cx="50" cy="92" rx="32" ry="26" fill="#EEE8FF"/></svg>')
photo = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()

people = []
for i, n in enumerate(names):
    total = int(9400 * 0.86 ** i) + 120
    sent = int(total * (0.38 + (i % 5) * 0.06))
    people.append({
        'name': n, 'total': total, 'sent': sent, 'received': total - sent,
        'handles': {'imessage': [n]} if i % 3 else {'imessage': [n], 'whatsapp': [n]},
        'photo': photo if i in (1, 5, 9) else None,
        'summary': summaries[i % len(summaries)] if i != 13 else '',
    })

w.generate_html(people, '2026', out)
print(out)
