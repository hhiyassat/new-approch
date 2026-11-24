# -*- coding: utf-8 -*-
"""
وسم العامل والمعمول من جدول العوامل المطبوع (data/operators/printed_operators_final.jsonl).

- عامل: كلمة تطابق عاملًا مطبوعًا (كلمة كاملة)، أو سابقة جرّ متصلة بالكلمة (ب، ل، ك، من...).
- معمول: الكلمة التي يطلبها العامل:
    * المعمول في السابقة المتصلة: الباقي بعد السابقة مباشرة (دليل PROCLITIC_OPERATOR).
    * الكلمة الكاملة التالية لعامل مستقل (دليل ADJACENT_AFTER_OPERATOR، وهو مرشح لا حكم نهائي).
- الحالة الإعرابية المتوقعة من أثر العامل المطبوع (جر / نصب / رفع). ما لا أثر له يبقى فارغًا.
الوسم لا يثبت إعرابًا قطعيًا؛ هو تتبّع لعلاقة مرشحة تُحسم بالسياق.
"""
import json, os, re
from gate import MARKCHARS, TATWEEL, WAQF, NON_PHONETIC

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, 'data', 'operators', 'printed_operators_final.jsonl')
IGNORE = set(MARKCHARS) | {TATWEEL, '‏'} | set(WAQF) | set(NON_PHONETIC)


def skeleton(s):
    out = []
    for ch in s:
        if ch in IGNORE or ch.isspace():
            continue
        out.append({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي'}.get(ch, ch))
    return ''.join(out)


def _effect_cases(effect):
    """كل الحالات المذكورة في الأثر، بترتيب النص: قد يذكر الأثر نصب الاسم ورفع الخبر معًا."""
    e = effect or ''
    found = []
    for name, stems in (('جر', ('جر ', 'جر', 'يجر', 'تجر')), ('نصب', ('نصب', 'تنصب', 'ينصب')), ('رفع', ('رفع', 'ترفع', 'يرفع'))):
        pos = [e.find(st) for st in stems if st in e]
        if pos:
            found.append((min(p for p in pos if p >= 0), name))
    return [name for _, name in sorted(found)]


def load_operators():
    """كل معاني العامل تُجمع: الحالة هي مجموعة الأثر من جميع المعاني، لا المعنى الأول وحده."""
    ops = []
    with open(CATALOG, encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            plain = rec.get('plain') or rec.get('printed_form') or ''
            meanings = rec.get('meanings') or []
            cases, effects = [], []
            for m in meanings:
                eff = m.get('grammatical_effect', '') or ''
                if eff:
                    effects.append(eff)
                for c in _effect_cases(eff):
                    if c not in cases:
                        cases.append(c)
            ops.append(dict(plain=plain, skeleton=skeleton(plain), effect=' | '.join(effects),
                            case=' / '.join(cases), cases=cases, printed_number=rec.get('printed_number')))
    return ops


OPS = load_operators()
def _merge(records):
    """عوامل تشترك في الهيكل الصامتي (إن/أن): تُدمج، ولا يُفقد أي أثر."""
    m = {}
    for o in records:
        if not o['skeleton']:
            continue
        g = m.get(o['skeleton'])
        if g is None:
            m[o['skeleton']] = dict(o, plains=[o['plain']])
            m[o['skeleton']]['cases'] = list(o['cases'])
        else:
            if o['plain'] not in g['plains']:
                g['plains'].append(o['plain'])
            for c in o['cases']:
                if c not in g['cases']:
                    g['cases'].append(c)
            g['case'] = ' / '.join(g['cases'])
            g['effect'] = g['effect'] + ' | ' + o['effect'] if o['effect'] else g['effect']
            g['plain'] = ' / '.join(g['plains'])
    return m


WHOLE = _merge(OPS)
# سوابق الجر العامة فقط. الواو والتاء تجران في القسم خاصة، فلا تُوسمان سابقتين عامتين.
GENERAL_JARR_PROCLITICS = {'ب', 'ل', 'ك'}
PROCLITIC = {o['skeleton']: o for o in OPS if o['skeleton'] in GENERAL_JARR_PROCLITICS and 'جر' in o['cases']}


def tags_for_word(word, next_word=None):
    """→ قائمة وسوم: (الوسم، المعامل، الحالة، الدليل، الكلمة المرتبطة)."""
    out = []
    sk = skeleton(word)
    if sk in WHOLE:
        o = WHOLE[sk]
        out.append(('عامل', o['plain'], o['case'], 'WORD_OPERATOR', word, 'CANDIDATE'))
        if next_word:
            out.append(('معمول', o['plain'], o['case'], 'ADJACENT_AFTER_OPERATOR', next_word, 'CANDIDATE'))
        return out
    if sk and sk[0] in PROCLITIC and len(sk) > 1:
        o = PROCLITIC[sk[0]]
        out.append(('عامل', o['plain'], 'جر', 'PROCLITIC_OPERATOR', word, 'CANDIDATE'))
        out.append(('معمول', o['plain'], 'جر', 'PROCLITIC_OPERATOR', word, 'CANDIDATE'))
    return out
