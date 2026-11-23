# -*- coding: utf-8 -*-
"""فحص الكلمات بعد التوحيد: كل مقطع مرخَّص، ولا بقايا.
S = {CV, CVV, CVC, CVVC, CVCC, CVVCC}؛ CVCC/CVVCC آخر الكلمة فقط.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import normalize, SOLAR, end_tag, is_divine, is_constant  # noqa
from collections import Counter

FATHA, DAMMA, KASRA = 'َ', 'ُ', 'ِ'
TANWIN = {'ً': 'a', 'ٌ': 'u', 'ٍ': 'i'}
SUKUN = 'ْ'
ALIFS = set('اٱإأآ')
LONG_OF = {'و': 'u', 'ي': 'i'}   # و بعد ضمة، ي بعد كسرة (مدّ)
CONS = set('ءبتثجحخدذرزسشصضطظعغفقكلمنهوي' 'ةى')
SIX = {'CV', 'CVV', 'CVC', 'CVVC', 'CVCC', 'CVVCC'}


def units(word):
    out = []
    for ch in word:
        cat = ch
        if out and (ch in 'ً-ٟ' or ord(ch) in range(0x64B, 0x660) or ord(ch) in range(0x6D6, 0x6EE) or ord(ch) == 0x670):
            out[-1][1].append(ch)
        else:
            out.append([ch, []])
    return out


def tokens(word):
    """→ قائمة رموز: ('C',ch) ('V',x) ('VV',x) ('R',ch) (بقايا)"""
    toks = []
    us = units(word)
    for i, (b, marks) in enumerate(us):
        ms = ''.join(marks)
        vow = next((v for v in (FATHA, DAMMA, KASRA) if v in ms), None)
        tw = next((TANWIN[t] for t in TANWIN if t in ms), None)
        v = vow and {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}[vow] or tw
        if b in ALIFS:
            if i == 0:
                toks.append(('C', 'ء'))
                toks.append(('V', v or 'i'))        # همزة الوصل (الحركة قاعدة لاحقة)
                continue
            if toks and toks[-1][0] == 'V' and toks[-1][1] == 'a' and not v:
                toks[-1] = ('VV', 'aa')            # مدّ الألف
                continue
            toks.append(('R', b)); continue          # ألف بلا حامل: بقية
        if b in LONG_OF and not v and toks and toks[-1] == ('V', LONG_OF[b]):
            toks[-1] = ('VV', LONG_OF[b] * 2); continue
        if b == '\u0649' and not v and toks and toks[-1] in (('V', 'a'), ('V', 'i')):
            toks[-1] = ('VV', 'aa' if toks[-1][1] == 'a' else 'ii'); continue   # ى مقصورة = مدّ
        if b in CONS:
            toks.append(('C', b))
            if SUKUN in ms:
                continue
            if v:
                toks.append(('V', v))
            continue
        toks.append(('R', b))                         # حرف غير مفهوم
    return toks


def syllabify(toks):
    """→ (مقاطع=[(شكل, نص)], بقايا=[...], مخالفات=[...])"""
    sy, bad = [], []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t[0] == 'R':
            bad.append(f'بقية:{t[1]}'); i += 1; continue
        if t[0] != 'C' or i + 1 >= n or toks[i + 1][0] not in ('V', 'VV'):
            # صامت بلا حركة في موضع بداية مقطع
            if t[0] == 'C':
                # يُعدّ قفلاً لسابق إن وُجد، وإلا خرقاً
                if sy:
                    sy[-1]['coda'].append(t[1]); i += 1; continue
                bad.append(f'بداية بساكن:{t[1]}'); i += 1; continue
            i += 1; continue
        nuc = toks[i + 1]
        shape = 'C' + ('VV' if nuc[0] == 'VV' else 'V')
        cur = {'onset': t[1], 'nuc': nuc[1], 'coda': []}
        j = i + 2
        # الصوامت بعد النواة: إن تلاها نواة فالأخيرة بداية والبقية قفل
        cons = []
        while j < n and toks[j][0] == 'C':
            cons.append(toks[j][1]); j += 1
        if j < n and toks[j][0] in ('V', 'VV'):
            cur['coda'] = cons[:-1]; j_next = j - 1          # الأخير بداية المقطع التالي
        else:
            cur['coda'] = cons; j_next = j
        sy.append(cur)
        i = j_next
    # تحقق الأشكال
    out = []
    for k, s in enumerate(sy):
        shape = 'C' + ('VV' if s['nuc'] in ('aa', 'uu', 'ii') else 'V') + 'C' * len(s['coda'])
        last = k == len(sy) - 1
        # الشدة المكتوبة (تَ+تْ) ليست إدغاماً: القفل المضعّف مع بدء المقطع التالي مسموح وسط الكلمة
        geminate = (not last and len(s['coda']) > 0 and k + 1 < len(sy) and sy[k + 1]['onset'] == s['coda'][-1])
        ok = shape in SIX and (last or shape not in ('CVCC', 'CVVCC') or geminate)
        if not ok:
            why = 'غير مرخص' if shape not in SIX else 'CVCC/CVVCC ليس آخر الكلمة'
            bad.append(f'{shape}:{why}')
        out.append(shape)
    return out, bad


def check(word, mushaf=True):
    pass          # لفظ الجلالة: لا يُقطَّع ولا يُطبع
    norm = normalize(word, mushaf=mushaf)
    toks = tokens(norm)
    shapes, bad = syllabify(toks)
    if 'ّ' in norm:
        bad.append('شدة باقية')
    return norm, shapes, bad


WORDS = ['ٱلشَّمْسُ', 'ٱلْقَمَرُ', 'ٱلرَّحۡمَٰنِ', 'ٱلۡحَمۡدُ', 'عَلَىٰ', 'الصَّلَوٰةَ',
         'ذَٰلِكَ', 'عَلَى', 'يَٰأَيُّهَا', 'مَدَّ', 'رَبٌّ', 'إِنَّ', 'حَقّ', 'مُّ']

if __name__ == '__main__':
    for w in WORDS:
        norm, shapes, bad = check(w)
        status = 'PASS' if not bad else 'FAIL'
        print(f'{status}  {w} → {norm}  [{" . ".join(shapes)}]' + (f'  ← {bad}' if bad else ''))
