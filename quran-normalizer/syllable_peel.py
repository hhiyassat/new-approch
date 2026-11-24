# -*- coding: utf-8 -*-
"""
ملحق التقشير الهندسي بالمقاطع: الحدود عند حدود المقاطع الموجودة فقط.

- لا يُنشأ حد داخل مقطع، ولا يُبحث عن حرف يشبه سابقة أو لاحقة.
- الهندسة (GeometryOK): الطرفان مقطعيًا مرخّصان، والحد لا يقطع شدة، والبقية لا تبدأ بساكن.
- الصرف (MorphologicalLicense): يؤكد هوية الجزء المفصول فقط؛ الشهادة الوحيدة الحالية: ال المكتوبة.
- الجذر لا يُسجَّل مقتطعًا بالتقشير؛ يُقترح كمرشح منفصل.
"""
from gate import build_cells, syllabify, _is_relative
from peel import _is_silent, _is_pair, _coverage, ABSENT

# حروف الإلحاق المسموح نزعها: ال (ء ل) + سألتمونيها (س ا ل ت م و ن ي ه) + المضارعة (ء ن ي ت).
# كل حرف خارج هذه المجموعة من أحرف الجذر، ولا يجوز أن يدخل جزء مُزال.
AFFIX_LETTERS = set('ءلساتمونيه')
PROCLITIC = set('وفبلك')
VERB_PREFIX = set('ءنيت')
SUFFIX_FORMS = ('هما', 'هم', 'هن', 'ها', 'كم', 'كن', 'نا', 'ني', 'ه', 'ك')


def _written(cells):
    return [c for c in cells if c.shadda != 'second' and not _is_silent(c)]


def _morph(word, cells, detached, side):
    """→ (الحكم، الدليل). الدليل يؤكد الهوية فقط."""
    if not detached:
        return 'PENDING', 'جزء فارغ'
    first = detached[0]
    if side == 'left' and first.carrier == 'ء' and 'WASLA' in first.flags:
        # الجزء المفصول هو وحدة ال فقط: ٱ + ل مكتوبة، أو ٱ وحدها إن كانت اللام شمسية محذوفة
        is_article_unit = (len(detached) == 1 and 'SOLAR_LAM_ELIDED' in first.flags) or \
            (len(detached) == 2 and detached[1].carrier == 'ل' and detached[1].sukun and not detached[1].vowel)
        if is_article_unit:
            start = first.span[0]
            if _is_relative(word[start:]):
                return 'REJECTED', 'اسم موصول: الكلمة الكاملة محمية'
            if any(_is_silent(c) for c in detached):
                return 'PENDING', 'ٱ صامتة بعد حركة السابقة: الحسم معلّق بقرار التقطيع'
            return 'LICENSED', 'ال المكتوبة (ٱ + ل)'
    roots = [c.carrier for c in detached if c.carrier not in AFFIX_LETTERS]
    if roots:
        return 'REJECTED', 'ROOT_LETTER_IN_DETACHED: أحرف جذرية في الجزء المزال: ' + ' '.join(roots)
    if len(detached) == 1 and side == 'left' and first.vowel and first.carrier in PROCLITIC:
        return 'PENDING', 'سابقة مفردة: الحرف قد يكون أصلًا في الجذر'
    if len(detached) == 1 and side == 'left' and first.vowel and first.carrier in VERB_PREFIX:
        return 'PENDING', 'بادئة مضارعة مرشحة: تحتاج دليل الفعل'
    if side == 'right' and ''.join(c.carrier for c in detached) in SUFFIX_FORMS:
        return 'PENDING', 'لاحقة ضميرية مرشحة: النهاية قد تكون أصلية'
    return 'PENDING', 'لا شهادة صرفية لهذا الجزء'


def propose(word):
    cells = build_cells(word)
    sylls, residue = syllabify(cells)
    n = len(cells)
    if residue or not all(s['valid'] for s in sylls):
        return dict(word=word, status='SYLLABLE_FAIL', candidates=[])
    groups = [[cells[i] for i in s['cells']] for s in sylls]
    cov_ok, cov_exc = _coverage(word, cells)
    out = []
    out = []
    # ال الشمسية: ٱ داخل مقطع ءَنْ، فلا حد مقطعي يفصلها. تُسجَّل PENDING بالسبب، دون استثناء.
    if cells and cells[0].carrier == 'ء' and 'SOLAR_LAM_ELIDED' in cells[0].flags:
        out.append(dict(
            candidate_id=f'{word}#article@solar', side='left', boundary_cell=None,
            source_cells=[cells[0].idx], left_syllables=[], right_syllables=[],
            left_cells=[], right_cells=[cells[i].idx for i in range(1, n)], coverage_exceptions=cov_exc,
            detached_text=word[cells[0].span[0]:cells[0].span[1]],
            geometry_verdict='NO_SYLLABLE_BOUNDARY', geometry_reason='ٱ داخل مقطع ءَنْ',
            morphology_evidence='ال شمسية: اللام محذوفة وتحويلها مسجّل',
            host_integrity=False, final_verdict='PENDING',
            reason='MORPHOLOGICAL_BOUNDARY_INSIDE_SYLLABLE', parent_analysis_id=ABSENT))
    groups = [[cells[i] for i in s['cells']] for s in sylls]
    cov_ok, cov_exc = _coverage(word, cells)
    # الحدود: بين كل مقطعين متتاليين فقط
    for k in range(len(groups) - 1):
        cut = groups[k + 1][0].idx
        for side in ('left', 'right'):
            detached = cells[:cut] if side == 'left' else cells[cut:]
            residual = cells[cut:] if side == 'left' else cells[:cut]
            geo, reason = 'OK', 'الهندسة سليمة'
            if any(_is_pair(cells[i], cells[i + 1]) for i in range(cut - 1, cut) if i + 1 < n) or \
               any(_is_pair(cells[i], cells[i + 1]) and i < cut < i + 1 + 1 for i in range(0, n - 1)):
                geo, reason = 'REJECT', 'حد يقطع شدة دون تمثيل مرخّص'
            elif not residual or not residual[0].vowel:
                geo, reason = 'REJECT', 'البقية تبدأ بساكن'
            elif not cov_ok:
                geo, reason = 'REJECT', 'تغطية المصدر ناقصة'
            morph, evidence = (('PENDING', 'لم تُفحص: الهندسة مرفوضة') if geo != 'OK'
                               else _morph(word, cells, detached, side))
            if geo != 'OK':
                final = 'REJECTED'
            elif morph == 'REJECTED':
                final = 'REJECTED'
            else:
                final = morph
            out.append(dict(
                candidate_id=f'{word}#{side}@{cut}', side=side, boundary_cell=cut,
                source_cells=[c.idx for c in detached],
                # الطرفان بموضع الكلمة لا بحسب الجزء المرشح: اليسار قبل الحد واليمين بعده
                left_syllables=[x['shape'] for x in sylls[:k + 1]],
                right_syllables=[x['shape'] for x in sylls[k + 1:]],
                left_cells=[c.idx for g in groups[:k + 1] for c in g],
                right_cells=[c.idx for g in groups[k + 1:] for c in g],
                coverage_exceptions=cov_exc,
                detached_text=word[detached[0].span[0]:detached[-1].span[1]] if detached else '',
                geometry_verdict=geo, geometry_reason=reason,
                morphology_evidence=evidence, host_integrity=geo == 'OK' and bool(residual),
                final_verdict=final, reason=reason if geo != 'OK' else (evidence if final != 'REJECTED' or evidence.startswith('ROOT') else evidence),
                parent_analysis_id=ABSENT))
    return dict(word=word, status='OK', candidates=out, coverage=cov_exc)


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:]:
        r = propose(w)
        for c in r['candidates']:
            print(f"{w:14} {c['side']:5} detach={c['detached_text']:8} geo={c['geometry_verdict']} "
                  f"final={c['final_verdict']:8} {c['reason']}")
        if not r['candidates']:
            print(w, r['status'], 'لا حدود')
