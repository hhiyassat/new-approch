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
    for name, stems in (('جر', ('جر ', 'جر', 'يجر', 'تجر')), ('نصب', ('نصب', 'تنصب', 'ينصب')), ('رفع', ('رفع', 'ترفع', 'يرفع')), ('جزم', ('جزم', 'يجزم', 'تجزم'))):
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
            cases, effects, senses = [], [], []
            for m in meanings:
                eff = m.get('grammatical_effect', '') or ''
                if eff:
                    effects.append(eff)
                sc = _effect_cases(eff)
                for c in sc:
                    if c not in cases:
                        cases.append(c)
                senses.append((m.get('meaning_label') or '', tuple(sc)))
            # المعاني التي لها الحالات نفسها تُجمع في مجموعة واحدة، ويبقى كل معنى مسمّى
            groups = {}
            for label, sc in senses:
                groups.setdefault(sc, []).append(label)
            sense_groups = [dict(labels=labels, cases=list(sc)) for sc, labels in groups.items()]
            ops.append(dict(plain=plain, skeleton=skeleton(plain), effect=' | '.join(effects),
                            case=' / '.join(cases), cases=cases, senses=sense_groups,
                            printed_number=rec.get('printed_number')))
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
            m[o['skeleton']]['sense_groups'] = list(o['senses'])
        else:
            if o['plain'] not in g['plains']:
                g['plains'].append(o['plain'])
            for c in o['cases']:
                if c not in g['cases']:
                    g['cases'].append(c)
            g['case'] = ' / '.join(g['cases'])
            seen = {(tuple(x['labels']), tuple(x['cases'])) for x in g['sense_groups']}
            g['sense_groups'] = g['sense_groups'] + [x for x in o['senses']
                                                    if (tuple(x['labels']), tuple(x['cases'])) not in seen]
            g['effect'] = g['effect'] + ' | ' + o['effect'] if o['effect'] else g['effect']
            g['plain'] = ' / '.join(g['plains'])
    return m


WHOLE = _merge(OPS)
# سوابق الجر العامة فقط. الواو والتاء تجران في القسم خاصة، فلا تُوسمان سابقتين عامتين.
GENERAL_JARR_PROCLITICS = {'ب', 'ل', 'ك'}
PROCLITIC = {o['skeleton']: o for o in OPS if o['skeleton'] in GENERAL_JARR_PROCLITICS and 'جر' in o['cases']}


def _unit_boundary(word):
    """حدّ الوحدة: الحرف الأول مقطع مستقل بحركته (CV) دون التحام بما بعده.
    → (مُثبت؟، الحالة). لا يُرشَّح أي عامل قبل إثبات هذا الحد."""
    try:
        from gate import build_cells, syllabify
        cells = build_cells(word)
    except ValueError:
        return False, 'UNSUPPORTED_GLYPH'
    sylls, residue = syllabify(cells)
    if residue or not sylls:
        return False, 'NO_CLEAN_SYLLABLES'
    first = sylls[0]['cells']
    if first == [0] and cells[0].vowel:
        return True, 'PROVEN_CV_UNIT'
    return False, 'MERGED_WITH_FOLLOWING'


def _is_article_text(text):
    return skeleton(text).startswith('ال')


def tags_for_word(word, next_word=None):
    """→ قائمة وسوم: (الوسم، المعامل، الحالة المتوقعة، الدليل، الكلمة المرتبطة، حالة_العلاقة، حد_الوحدة، حالة_الوظيفة).
    كل وسم مرشح. العلاقة تُعلَّق (SUSPENDED) إذا لم تُعرف هوية الطرف الآخر."""
    out = []
    sk = skeleton(word)
    if sk in WHOLE:
        o = WHOLE[sk]
        uniq, keys = [], set()
        for grp in o['sense_groups']:
            k = (tuple(grp['labels']), tuple(grp['cases']))
            if k not in keys:
                keys.add(k); uniq.append(grp)
        # قرينة واحدة مؤكدة: «ما» بعدها «إلا» تكون نافية حاصرة، فتُحذف المعاني الأخرى لهذا الوقوع
        if sk == 'ما' and next_word and skeleton(next_word) in ('الا',):
            uniq = [g for g in uniq if any('النفي' in l for l in g['labels'])] or uniq
            evidence_base = 'WORD_OPERATOR_SENSE_NEXT_ILLA'
        else:
            evidence_base = 'WORD_OPERATOR_SENSE'
        bound_ok, bound_state = _unit_boundary(word)
        for grp in uniq:
            case = ' / '.join(grp['cases']) if grp['cases'] else '—'
            label = o['plain'] + ' (' + ' / '.join(l for l in grp['labels'] if l) + ')' if grp['labels'] and any(grp['labels']) else o['plain']
            # الكلمة الكاملة عامل: حدّها هو الكلمة نفسها، فالحد لا يُختبر بالتقطيع هنا
            out.append(('عامل', label, case, evidence_base, word, 'CANDIDATE', 'WHOLE_WORD', 'CANDIDATE_CASE'))
            if next_word:
                try:
                    from gate import build_cells
                    build_cells(next_word)
                    rel = 'CANDIDATE'
                except ValueError:
                    rel = 'SUSPENDED_OPERAND_UNREADABLE'
                out.append(('معمول', label, case, 'ADJACENT_AFTER_OPERATOR', next_word, rel, 'NEXT_WORD', 'CANDIDATE_CASE'))
        return out
    if sk and sk[0] in PROCLITIC and len(sk) > 1:
        ok, why = _unit_boundary(word)
        if not ok:
            # لا ترشيح قبل إثبات حد الوحدة: الحرف ملتحم بما بعده في المقطع نفسه
            return []
        o = PROCLITIC[sk[0]]
        cells_text_start = None
        try:
            from gate import build_cells
            c = build_cells(word)
            cells_text_start = c[1].span[0]
        except (ValueError, IndexError):
            return []
        operand = word[cells_text_start:]
        # الوظيفة لا تُعيَّن بالشكل وحده: قرينة الكلمة التالية (ال) تبقيها مرشّحة لا محسومة
        func = 'NEXT_ARTICLE_CANDIDATE' if _is_article_text(operand) else 'UNDECIDED'
        evidence = 'PROCLITIC_OPERATOR_BRANCHED_SUFFIX' if sk.endswith('وا') else 'PROCLITIC_OPERATOR'
        out.append(('عامل', o['plain'], 'جر', evidence, operand, 'CANDIDATE', why, func))
        out.append(('معمول', o['plain'], 'جر', evidence, operand, 'CANDIDATE', why, func))
    return out
