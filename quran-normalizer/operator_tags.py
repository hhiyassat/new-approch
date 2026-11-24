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



# ---------------------------------------------------------------- المطابقة بالشكل (الكتالوج المشكول)
import csv as _csv
_HARAKAT = set('\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u06E1')  # + السكون الصغير القرآني


_ALIF_FORMS = {'أ': 'ا\u0654', 'إ': 'ا\u0655', 'آ': 'ا\u0653', 'ٱ': 'ا'}


def vsig(text):
    """توقيع مشكول: كل حرف أساسي مع علاماته مرتّبةً، بلا علامة الحرف الأخير (الإعراب الآخِر يتغير بالوقف).
    صور الألف تُوحَّد، والهمزة السفلى المكتوبة منفصلة تُعامل علامةً على الألف."""
    units = []
    for ch in text:
        if ch in _HARAKAT or ch == '\u0654' or ch == '\u0655' or ch == '\u0653':
            if units:
                units[-1] = units[-1] + ch
        elif ch in (TATWEEL, '\u200f') or ch.isspace() or ch in set(WAQF) or ch in set(NON_PHONETIC):
            continue
        elif ch in _ALIF_FORMS:
            units.append(_ALIF_FORMS[ch])
        else:
            units.append(ch)
    out = []
    for u in units:
        letter = u[0]
        marks = ''.join(sorted(c for c in u[1:]))
        out.append(letter + marks)
    if out:
        # الحركة الآخِرة تُحذف، أما الشدة فجزء من هوية الحرف (إنَّ ليست إنْ)
        last = out[-1]
        out[-1] = last[0] + ('\u0651' if '\u0651' in last[1:] else '')
    return tuple(out)


def has_vocalization(text):
    return any(ch in _HARAKAT for ch in text)


def _cases_from_note(note):
    cases = []
    for name, stems in (('جر', ('مجرور', 'حرف جر', 'جر ')), ('نصب', ('منصوب',)), ('رفع', ('مرفوع',)), ('جزم', ('مجزوم', 'جازم'))):
        pos = [note.find(st) for st in stems if st in note]
        if pos:
            cases.append((min(p for p in pos if p >= 0), name))
    return [n for _, n in sorted(cases)]


def _load_vocalized_catalog():
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'operators', 'operators_catalog_split_vocalized.csv')
    table = {}
    if not os.path.exists(path):
        return table
    for r in _csv.DictReader(open(path, encoding='utf-8-sig')):
        op = (r.get('Operator') or '').strip()
        if not op:
            continue
        key = vsig(op)
        table.setdefault(key, []).append(dict(
            operator=op, purpose=(r.get('Purpose/Usage') or '').strip(),
            group=(r.get('Arabic Group Name') or '').strip(),
            cases=_cases_from_note(r.get('Note') or ''), note=(r.get('Note') or '').strip()))
    return table


VOCAL = _load_vocalized_catalog()


def _unit_boundary(word):
    """حدّ الوحدة: الحرف الأول مقطع CV مستقل (لا CVV ولا ملتحم).
    → (مُثبت؟، الحالة). لا يُرشَّح أي عامل قبل إثبات هذا الحد."""
    try:
        from gate import build_cells, syllabify
        cells = build_cells(word)
    except ValueError:
        return False, 'UNSUPPORTED_GLYPH', None
    sylls, residue = syllabify(cells)
    if residue or not sylls:
        return False, 'NO_CLEAN_SYLLABLES', None
    shape = sylls[0]['shape']
    if sylls[0]['cells'] == [0] and cells[0].vowel and shape == 'CV':
        return True, 'PROVEN_CV_UNIT', shape
    if sylls[0]['cells'] != [0]:
        return False, 'MERGED_WITH_FOLLOWING', shape
    return False, 'FIRST_SYLLABLE_' + shape, shape



_BUILT = None
_BUILT_VOCAL = None


def _built_skeletons():
    """هياكل المداخل المبنية الصالحة (من المعجم المنظّف). لا تُستعمل إلا بادئةً طويلة."""
    global _BUILT
    if _BUILT is None:
        import csv, os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lexicon', 'mabniyat.tsv')
        _BUILT = set()
        if os.path.exists(path):
            for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
                if r.get('skeleton') and len(r['skeleton']) >= 2:
                    _BUILT.add(r['skeleton'])
    return _BUILT


def _built_vocal_full():
    """مداخل المبنيات المشكولة (من المعجم). لا تُطابَق إلا كاملةً بالشكل."""
    global _BUILT_VOCAL
    if _BUILT_VOCAL is None:
        import csv, os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lexicon', 'mabniyat.tsv')
        _BUILT_VOCAL = set()
        if os.path.exists(path):
            for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
                head = (r.get('headword') or '').strip()
                if head and has_vocalization(head):
                    _BUILT_VOCAL.add(vsig(head))
    return _BUILT_VOCAL


def _built_full_match(word):
    return vsig(word) in _built_vocal_full()


def _unused_built_prefix(sk):
    return any(sk.startswith(b) and len(b) < len(sk) for b in _built_skeletons())


def _root_exclusion_proven(word):
    """استبعاد كون الحرف الأول أصليًا يحتاج مورد جذور؛ لا يوجد مورد كهذا في المستودع بعد."""
    return False, 'NO_ROOT_RESOURCE'

def _is_article_text(text):
    try:
        from gate import build_cells
        c = build_cells(text)
    except ValueError:
        return False
    return bool(c) and c[0].carrier == 'ء' and 'WASLA' in c[0].flags


def _cell_ids(text, start=0):
    try:
        from gate import build_cells
        return ' '.join(str(c.idx + start) for c in build_cells(text)), True
    except ValueError:
        return 'UNREADABLE', False


def tags_for_word(word, next_word=None):
    """→ (الوسم، المعامل، الحالة المتوقعة، الدليل، الطرف المرتبط، حالة_العلاقة، حد_الوحدة، حالة_الوظيفة، خلايا_الطرف).
    القاعدة: لا قرار على نص غير مشكول. الجدول الرئيسي: عوامل الكلمات الكاملة المطابقة بالشكل وعلاقتها بالكلمة التالية.
    السوابق المتصلة تبقى في التشخيص (DIAGNOSTIC_ONLY) مع سبب الحجب."""
    out = []
    if not has_vocalization(word):
        out.append(('عامل', word, '', 'UNVOCALIZED_INPUT', word, 'DIAGNOSTIC_ONLY', 'UNVOCALIZED_TEXT_REJECTED', 'NOT_EVALUATED', ''))
        return out
    vs = vsig(word)
    if vs in VOCAL:
        rows_v = VOCAL[vs]
        evidence_v = 'WORD_OPERATOR_VOCALIZED'
        # قرينة واحدة مؤكدة بالشكل: «ما» بعدها «إلا» بالشكل تكون نافية حاصرة
        if vs == vsig('مَا') and next_word and has_vocalization(next_word) and vsig(next_word) == vsig('إِلَّا'):
            narrowed = [r for r in rows_v if 'نفي' in r['purpose']]
            if narrowed:
                rows_v = narrowed
                evidence_v = 'WORD_OPERATOR_SENSE_NEXT_ILLA'
        self_ids, _ = _cell_ids(word)
        uniq = []
        for r in rows_v:
            k = (r['purpose'], tuple(r['cases']))
            if k not in [(u['purpose'], tuple(u['cases'])) for u in uniq]:
                uniq.append(r)
        for r in uniq:
            case = ' / '.join(r['cases']) if r['cases'] else '—'
            label = r['operator'] + ' (' + r['purpose'] + ')' if r['purpose'] else r['operator']
            out.append(('عامل', label, case, evidence_v, word, 'CANDIDATE', 'WHOLE_WORD', 'CANDIDATE_CASE', self_ids))
            if next_word:
                ids, readable = _cell_ids(next_word)
                rel = 'CANDIDATE' if readable else 'SUSPENDED_OPERAND_UNREADABLE'
                out.append(('معمول', label, case, 'ADJACENT_AFTER_OPERATOR', next_word, rel, 'NEXT_WORD', 'CANDIDATE_CASE', ids))
        return out
    try:
        from gate import build_cells
        cells = build_cells(word)
    except ValueError:
        return out
    if len(cells) > 1 and cells[0].carrier in PROCLITIC:
        o = PROCLITIC[cells[0].carrier]
        ok, why, shape = _unit_boundary(word)
        root_ok, root_why = _root_exclusion_proven(word)
        if not cells[0].vowel or 'UNMARKED' in cells[0].flags:
            ok, why = False, 'FIRST_LETTER_NOT_A_VOWELLED_UNIT'
        if not ok:
            reason = why
        elif _built_full_match(word):
            reason = 'BUILT_FULL_MATCH_BLOCKS_PROCLITIC'
        elif not root_ok:
            reason = root_why
        else:
            reason = 'ELIGIBLE_BUT_NOT_TABLED'
        operator_ids = str(cells[0].idx)
        operand_ids = ' '.join(str(c.idx) for c in cells[1:])
        operand_text = word[cells[1].span[0]:]
        func = 'UNDECIDED' if ok else 'NOT_EVALUATED'
        if ok and _is_article_text(operand_text):
            func = 'NEXT_ARTICLE_CANDIDATE'
        out.append(('عامل', o['plain'], 'جر', 'PROCLITIC_DIAGNOSTIC', word, 'DIAGNOSTIC_ONLY', reason, func, operator_ids))
        out.append(('معمول', o['plain'], 'جر', 'PROCLITIC_DIAGNOSTIC', operand_text, 'DIAGNOSTIC_ONLY', reason, func, operand_ids))
    return out
