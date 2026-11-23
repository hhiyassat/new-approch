# -*- coding: utf-8 -*-
"""تقطيع الكلمة المطبّعة إلى مقاطع مرخّصة، مع رسم كل مقطع."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_licensed as cl
from dagger_normalize import normalize

VOW = {'a': 'َ', 'u': 'ُ', 'i': 'ِ'}
LONG = {'aa': ('َ', 'ا'), 'uu': ('ُ', 'و'), 'ii': ('ِ', 'ي')}
SUK = 'ْ'


def _render_nuc(nuc):
    if nuc in LONG:
        v, l = LONG[nuc]
        return v + l
    return VOW.get(nuc, '')


def syllables(word):
    """→ (المقاطع المرسومة، الأشكال، المخالفات) أو None للفظ الجلالة/المقطعات."""
    norm = normalize(word, mushaf=True)
    toks = cl.tokens(norm)
    # نعيد التقطيع مع الأشكال وبيانات كل مقطع
    sy, bad = [], []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t[0] != 'C' or i + 1 >= n or toks[i + 1][0] not in ('V', 'VV'):
            if t[0] == 'C' and sy:
                sy[-1]['coda'].append(t[1]); i += 1; continue
            bad.append(t); i += 1; continue
        cur = {'onset': t[1], 'nuc': toks[i + 1][1], 'coda': []}
        j = i + 2
        cons = []
        while j < n and toks[j][0] == 'C':
            cons.append(toks[j][1]); j += 1
        if j < n and toks[j][0] in ('V', 'VV'):
            cur['coda'] = cons[:-1]; nxt = j - 1
        else:
            cur['coda'] = cons; nxt = j
        sy.append(cur); i = nxt
    out, shapes = [], []
    for k, s in enumerate(sy):
        longv = s['nuc'] in LONG
        shape = 'C' + ('VV' if longv else 'V') + 'C' * len(s['coda'])
        shapes.append(shape)
        txt = s['onset'] + _render_nuc(s['nuc']) + ''.join(c + SUK for c in s['coda'])
        out.append(txt)
    return out, shapes, bad, norm


if __name__ == '__main__':
    for w in sys.argv[1:] or ['بِسۡمِ', 'ٱللَّهِ', 'ٱلرَّحۡمَٰنِ', 'ٱلرَّحِيمِ']:
        r = syllables(w)
        if r is None:
            print(w, '→ لا يُقطَّع'); continue
        o, sh, bad, norm = r
        print(w, '→', norm, '|', ' . '.join(o), '|', ' . '.join(sh), '| بقايا' if bad else '')
