# -*- coding: utf-8 -*-
"""
التقشير بإزالة الوحدات من طرفي الكلمة (القاعدة المعتمدة).

- تُزال وحدة CV من الطرف، والحروف تؤكّد هوية الوحدة المنزوعة ولا تُبحث عنها.
- تُنفَّذ الخطوة ثم يُتوقف إذا بدأ الباقي بسكون.
- بعد التوقف: إن بقي ثلاثة صوامت مكتوبة فالنتيجة ROOT_SEARCH.
- الحرف المفرد (سابقة، مضارعة، لاحقة) خطوة PENDING، ولا تُنزع إن أنقص الباقي عن ثلاثة صوامت.
- ال المكتوبة (ٱ وصل + ل) خطوة LICENSED.
- الشدة تُعدّ صامتًا واحدًا مكتوبًا؛ والخلية الثانية من الشدة لا تُعدّ.
"""
from gate import build_cells

PROCLITIC = set('وفبلك')
VERB_PREFIX = set('ءنيت')
SUFFIX_FORMS = ('هما', 'هم', 'هن', 'ها', 'كم', 'كن', 'نا', 'ني', 'ه', 'ك')


def _silent(c):
    return c.carrier == 'ء' and 'WASLA' in c.flags and 'UNMARKED' in c.flags and c.sukun and not c.vowel


def _written_consonants(cells):
    return sum(1 for c in cells if c.shadda != 'second' and not _silent(c))


def edge_peel(word):
    cells = build_cells(word)
    lo, hi = 0, len(cells)           # الباقي = cells[lo:hi]
    steps, status = [], None

    def remainder_starts_sukun():
        # الصامتة لا تُعدّ سكونًا بدائيًا، والشدة الأولى مع ثانيتها بداية مشدّدة مرخّصة
        return lo < hi and not cells[lo].vowel and not _silent(cells[lo]) and cells[lo].shadda != 'first'

    while lo < hi:
        progressed = False
        # ---- نهاية: لاحقة ضميرية (تُزال من الطرف الأيمن)
        if hi - lo >= 2 and cells[hi - 1].vowel:
            for suf in SUFFIX_FORMS:
                n = len(suf)
                if hi - lo - n >= 1 and ''.join(c.carrier for c in cells[hi - n:hi]) == suf:
                    tail = cells[hi - n:hi]
                    if _written_consonants(cells[lo:hi - n]) >= 3:
                        steps.append(dict(side='right', role='SUFFIX', verdict='PENDING', text=suf,
                                          cells=[c.idx for c in tail]))
                        hi -= n; progressed = True
                    break
        if progressed:
            continue
        # ---- بداية: ال المكتوبة، ثم سابقة أو مضارعة مفردة
        c0 = cells[lo]
        if c0.carrier == 'ء' and 'WASLA' in c0.flags and lo + 1 <= hi:
            unit = [c0]
            if lo + 1 < hi and cells[lo + 1].carrier == 'ل' and cells[lo + 1].sukun and not cells[lo + 1].vowel:
                unit.append(cells[lo + 1])
            # ٱ الصامتة بعد حركة السابقة: الحسم معلّق بقرار منظومة التقطيع
            verdict = 'PENDING' if _silent(c0) else 'LICENSED'
            steps.append(dict(side='left', role='ART', verdict=verdict,
                              text=''.join(c.carrier for c in unit), cells=[c.idx for c in unit]))
            lo += len(unit); progressed = True
        elif c0.vowel and c0.shadda != 'first' and c0.carrier in PROCLITIC | VERB_PREFIX:
            role = 'PROCLITIC' if c0.carrier in PROCLITIC else 'VERB_PREFIX'
            if _written_consonants(cells[lo + 1:hi]) >= 3:
                steps.append(dict(side='left', role=role, verdict='PENDING', text=c0.carrier, cells=[c0.idx]))
                lo += 1; progressed = True
        if not progressed:
            break
        if remainder_starts_sukun():
            status = 'STOP_STARTS_WITH_SUKUN'
            break

    core = cells[lo:hi]
    k = _written_consonants(core)
    core_text = ''.join(c.carrier for c in core if c.shadda != 'second')
    if status is None:
        status = 'ROOT_SEARCH' if k == 3 else 'STOP'
    elif k == 3:
        status = 'ROOT_SEARCH'
    verdict = 'PENDING' if any(s['verdict'] == 'PENDING' for s in steps) else (
        'LICENSED' if steps else 'NO_STEP')
    return dict(word=word, status=status, verdict=verdict, steps=steps, core=core_text,
                core_consonants=k)


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:]:
        r = edge_peel(w)
        print(f"{w:14} {r['status']:24} {r['verdict']:8} core={r['core']:10} k={r['core_consonants']} "
              f"steps={[(s['side'], s['role'], s['text']) for s in r['steps']]}")
