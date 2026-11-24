r"""How often does requirements prose state a threshold of two or more?

The `1..1` question was settled on 2026-08-31 by counting: "exactly one"
appeared 0 times in 449k words. GoalShift now supports `k..*` dependency
multiplicities, so the same question arises for thresholds, and it deserves the
same treatment before `schema.py` widens `MULTS`.

What counts. A `k..*` dependency means "this depender needs at least k
providers". So the phrasing to look for is a lower bound of TWO OR MORE on a
count of PARTICIPANTS. "At least one" is excluded and counted separately,
because that is `1..*` and already supported.

Raw hits are not the answer. The 1..1 count found 26 "only one" and 72 "a
single X" and still concluded no, because reading the contexts showed almost
none constrained a participant. Most hits here turn out to be percentages,
durations and warranty periods, so what follows the number is classified and
every surviving candidate is printed in full to be read.

Run:  py -3.9 bench/threshold_phrases.py
"""

import os
import re

CORPUS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), 'reqshift_product')
DIRS = [os.path.join(CORPUS, 'genre_test'), os.path.join(CORPUS, 'gate_test')]

NUM = r'(?:two|three|four|five|six|seven|eight|nine|ten|[2-9]|\d\d+)'

THRESHOLD = {
    'at least N':      re.compile(r'\bat\s+least\s+' + NUM + r'\b', re.I),
    'minimum of N':    re.compile(r'\b(?:a\s+)?minimum\s+of\s+' + NUM + r'\b', re.I),
    'no fewer than N': re.compile(r'\bno\s+fewer\s+than\s+' + NUM + r'\b', re.I),
    'not less than N': re.compile(r'\bnot\s+less\s+than\s+' + NUM + r'\b', re.I),
    'N or more':       re.compile(r'\b' + NUM + r'\s+or\s+more\b', re.I),
    '>= N':            re.compile(r'(?:>=|≥)\s*' + NUM + r'\b'),
}
BASELINE = {
    'at least one':    re.compile(r'\bat\s+least\s+(?:one|1)\b', re.I),
    'one or more':     re.compile(r'\b(?:one|1)\s+or\s+more\b', re.I),
}

# What is being counted decides whether a threshold is about participants at
# all. "at least 10%" and "at least 2 years" are not dependencies on two
# providers. Word boundaries matter here: a bare "m" would swallow "modules".
UNITS = set("""percent cent year years month months week weeks day days hour
hours minute minutes second seconds time times mm cm metre metres meter meters
m km kg ton tons tonne tonnes kv kva mva volt volts amp amps ampere amperes hz
ohm ohms bar mpa degree degrees deg copy copies set sets no nos page pages mb
gb kb bit bits byte bytes cycle cycles inch inches ft feet lux db rpm va w kw
mw a v""".split())

_SPELLED = r'^\((?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\)\s*'


def unit_word(tail):
    """First real word after the number, or '%'.

    Matching the raw tail with a regex leaked: "%." has no word boundary after
    the percent sign, and "2 (two) years" starts with a parenthetical spelling
    of the same number. Both were landing in the participant bucket.
    """
    if tail.lstrip().startswith('%'):
        return '%'
    t = re.sub(r'^[^A-Za-z0-9(]+', '', tail)
    t = re.sub(_SPELLED, '', t, flags=re.I)
    t = re.sub(r'^[^A-Za-z]+', '', t)
    m = re.match(r'[A-Za-z]+', t)
    return m.group(0).lower() if m else ''


def is_unit(tail):
    w = unit_word(tail)
    return w == '%' or w in UNITS


def docs():
    for d in DIRS:
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.endswith('.txt'):
                    p = os.path.join(root, f)
                    yield p, open(p, encoding='utf-8', errors='replace').read()


def clean(s):
    return re.sub(r'\s+', ' ', s).strip().encode('ascii', 'replace').decode()


def ctx(text, m, width=115):
    return clean(text[max(0, m.start() - width):min(len(text), m.end() + width)])


def counted_thing(text, m, width=46):
    return clean(text[m.end():m.end() + width])


all_text, per_doc, words = [], {}, 0
for path, text in docs():
    all_text.append(text)
    per_doc[os.path.basename(path)] = text
    words += len(text.split())
joined = '\n'.join(all_text)

print('corpus: %d documents, %d words' % (len(per_doc), words))

print('\nALREADY SUPPORTED, for scale')
for name, rx in BASELINE.items():
    print('  %-18s %5d' % (name, len(rx.findall(joined))))

print('\nRAW HITS for a threshold of two or more')
hits, total = [], 0
for name, rx in THRESHOLD.items():
    ms = list(rx.finditer(joined))
    total += len(ms)
    hits += [(name, m) for m in ms]
    print('  %-18s %5d' % (name, len(ms)))
print('  %-18s %5d' % ('TOTAL', total))

units, maybe = [], []
for name, m in hits:
    (units if is_unit(counted_thing(joined, m)) else maybe).append((name, m))

print('\nWHAT IS ACTUALLY BEING COUNTED')
print('  %-34s %5d' % ('a unit or measure, not participants', len(units)))
print('  %-34s %5d' % ('possibly a participant count', len(maybe)))

print('\nEVERY SURVIVING CANDIDATE, what follows the number')
for i, (name, m) in enumerate(maybe, 1):
    print('%3d [%-14s] %s' % (i, name, counted_thing(joined, m)))

print('\nFULL CONTEXT for the first 30')
for i, (name, m) in enumerate(maybe[:30], 1):
    print('%3d ...%s...' % (i, ctx(joined, m)))
