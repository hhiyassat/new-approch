# -*- coding: utf-8 -*-
"""
ملحق التقشير بالمقاطع (تجريبي): الحدود عند حدود المقاطع الموجودة فقط.

المسار:
  حد مقطعي → سلامة الطرفين → أهلية الجزء (هل ينتمي إلى باب معروف) → شهادة الوظيفة والاتصال → الحكم.

- الأهلية: جزء لا ينتمي إلى أي باب معروف يُرفض بالسبب NO_AFFIX_CLASS.
  جزء ينتمي إلى باب معروف ولم تُثبت وظيفته يبقى PENDING بسبب محدد.
- انتماء الحروف وحده لا يكفي: الجزء يجب أن يطابق تركيبًا مرخّصًا في جهة الفصل
  (وحدة مفردة في الطرف، أو لاحقة متصلة بالطرف الأيمن).
- الحكم LICENSED لا يصدر إلا لأل المكتوبة بعد اكتمال الشهادة.
- ELIGIBILITY_GATE يُعطَّل فقط في اختبار يثبت أن البوابة هي سبب الرفض.
"""
from gate import build_cells, syllabify, _is_relative
from peel import _is_silent, _is_pair, _coverage, ABSENT

ELIGIBILITY_GATE = True

PROCLITIC = set('وفبل')            # سوابق تُعرف بوظيفتها عند الاختبار، لا بالحرف وحده
KAF = 'ك'                          # كاف التشبيه: لا تُقبل إلا قبل ال
VERB_PREFIX = set('ءنيت')         # بادئات المضارعة: لا تُحكم إلا بدليل الفعل
SUFFIX_FORMS = ('هما', 'هم', 'هن', 'ها', 'كم', 'كن', 'نا', 'ني', 'ه', 'ك')
# وظائف الضمائر المتصلة من جدول المبنيات (pronouns_classification): للوسم فقط، لا تُرخّص الجزء
SUFFIX_FUNCTIONS = {
    'ه': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر', 'اسم إن'),
    'ها': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر', 'اسم إن'),
    'هم': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر'),
    'هن': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر'),
    'هما': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر'),
    'ك': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر', 'اسم إن'),
    'كم': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر'),
    'كن': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر'),
    'نا': ('مفعول به', 'مضاف إليه', 'مجرور بحرف الجر', 'اسم إن'),
    'ني': ('مفعول به',),
}


def _is_article_unit(cells, detached, side):
    if side != 'left' or not detached or detached[0].carrier != 'ء' or 'WASLA' not in detached[0].flags:
        return False
    if len(detached) == 1 and 'SOLAR_LAM_ELIDED' in detached[0].flags:
        return True
    return (len(detached) == 2 and detached[1].carrier == 'ل'
            and detached[1].sukun and not detached[1].vowel)


def _eligibility(word, cells, detached, side, cut):
    """→ (الحكم، السبب). الحكم: LICENSED / PENDING / REJECTED."""
    if not detached:
        return 'REJECTED', 'NO_AFFIX_CLASS: جزء فارغ'
    first = detached[0]
    # 1) ال المكتوبة: وحدة كاملة فقط
    if _is_article_unit(cells, detached, side):
        if _is_relative(word[first.span[0]:]):
            return 'REJECTED', 'PROTECTED_RELATIVE: اسم موصول محمي'
        if any(_is_silent(c) for c in detached):
            return 'PENDING', 'ٱ صامتة بعد حركة السابقة: الحسم معلّق بقرار التقطيع'
        return 'LICENSED', 'ال المكتوبة (ٱ + ل)'
    # 2) وحدة مفردة مكتوبة الحركة في الطرف الأيسر
    if side == 'left' and len(detached) == 1 and first.vowel and not first.shadda and 'UNMARKED' not in first.flags:
        c = first.carrier
        if c in PROCLITIC:
            return 'PENDING', 'PROCLITIC_FUNCTION_UNPROVEN: السابقة تحتاج دليل وظيفتها'
        if c == KAF:
            # كاف التشبيه صنف مؤهل، ووظيفتها (تشبيه أو غيره، أو كاف أصلية) لم تثبت بعد
            return 'PENDING', 'KAF_FUNCTION_UNPROVEN: الكاف قد تكون للتشبيه أو من أصل الجذر'
        if c in VERB_PREFIX:
            return 'PENDING', 'VERB_PREFIX_UNPROVEN: البادئة تحتاج دليل الفعل'
    # 3) لاحقة ضميرية متصلة بالطرف الأيمن
    if side == 'right' and ''.join(c.carrier for c in detached) in SUFFIX_FORMS:
        form = ''.join(c.carrier for c in detached)
        funcs = ' / '.join(SUFFIX_FUNCTIONS.get(form, ()))
        return 'PENDING', 'SUFFIX_FUNCTION_UNPROVEN: النهاية قد تكون أصلية في الجذر؛ الوظائف المحتملة: ' + funcs
    # لا باب معروف: الحروف (إن كانت من الإلحاق) لا تكفي وحدها
    if not ELIGIBILITY_GATE:
        return 'PENDING', 'لا شهادة صرفية لهذا الجزء'
    return 'REJECTED', 'NO_AFFIX_CLASS: الجزء خارج أبواب التقشير المعتمدة'


def check_partition(n, detached, residual):
    """الباقي هو المتمّم المرتب للجزء المرشح. يفشل عند أي تقاطع أو فقد أو تكرار."""
    if set(detached) & set(residual):
        raise ValueError('تقاطع بين الجزء المرشح والباقي: ' + str(sorted(set(detached) & set(residual))))
    if sorted(detached + residual) != list(range(n)):
        raise ValueError('التغطية غير كاملة: فقد أو تكرار خلية')
    return sorted(residual)


def propose(word):
    cells = build_cells(word)
    sylls, residue = syllabify(cells)
    n = len(cells)
    if residue or not all(s['valid'] for s in sylls):
        return dict(word=word, status='SYLLABLE_FAIL', candidates=[])
    groups = [[cells[i] for i in s['cells']] for s in sylls]
    cov_ok, cov_exc = _coverage(word, cells)
    out = []
    # ال الشمسية: ٱ داخل مقطع ءَنْ، فلا حد مقطعي يفصلها. تُسجَّل PENDING بالسبب، دون استثناء.
    if cells and cells[0].carrier == 'ء' and 'SOLAR_LAM_ELIDED' in cells[0].flags:
        out.append(dict(
            candidate_id=f'{word}#article@solar', side='left', boundary_cell=None,
            source_cells=[cells[0].idx], left_syllables=[], right_syllables=[],
            residual_cells=[c.idx for c in cells[1:]], detached_cells=[cells[0].idx],
            coverage_exceptions=cov_exc,
            detached_text=word[cells[0].span[0]:cells[0].span[1]],
            geometry_verdict='NO_SYLLABLE_BOUNDARY', geometry_reason='ٱ داخل مقطع ءَنْ',
            eligibility='NOT_EVALUATED', morphology_evidence='ال شمسية: اللام محذوفة وتحويلها مسجّل',
            host_integrity=False, final_verdict='PENDING',
            reason='MORPHOLOGICAL_BOUNDARY_INSIDE_SYLLABLE', parent_analysis_id=ABSENT))
    for k in range(len(groups) - 1):
        cut = groups[k + 1][0].idx
        for side in ('left', 'right'):
            detached = cells[:cut] if side == 'left' else cells[cut:]
            residual = cells[cut:] if side == 'left' else cells[:cut]
            geo, reason = 'OK', 'الهندسة سليمة'
            if any(_is_pair(cells[i], cells[i + 1]) and i < cut < i + 2 for i in range(n - 1)):
                geo, reason = 'REJECT', 'حد يقطع شدة دون تمثيل مرخّص'
            elif not residual or not residual[0].vowel:
                geo, reason = 'REJECT', 'البقية تبدأ بساكن'
            elif not cov_ok:
                geo, reason = 'REJECT', 'تغطية المصدر ناقصة'
            if geo != 'OK':
                elig, why = 'NOT_EVALUATED', 'لم تُفحص الأهلية: الهندسة مرفوضة'
                final = 'REJECTED'
            else:
                elig, why = _eligibility(word, cells, detached, side, cut)
                final = elig
            out.append(dict(
                candidate_id=f'{word}#{side}@{cut}', side=side, boundary_cell=cut,
                source_cells=[c.idx for c in detached],
                left_syllables=[x['shape'] for x in sylls[:k + 1]],
                right_syllables=[x['shape'] for x in sylls[k + 1:]],
                residual_cells=check_partition(n, [c.idx for c in detached], [c.idx for c in residual]),
                detached_cells=[c.idx for c in detached],
                coverage_exceptions=cov_exc,
                detached_text=word[detached[0].span[0]:detached[-1].span[1]] if detached else '',
                geometry_verdict=geo, geometry_reason=reason,
                eligibility=elig, morphology_evidence=why,
                host_integrity=geo == 'OK' and bool(residual),
                final_verdict=final, reason=reason if geo != 'OK' else why,
                parent_analysis_id=ABSENT))
    return dict(word=word, status='OK', candidates=out)


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:]:
        r = propose(w)
        for c in r['candidates']:
            print(f"{w:14} {c['side']:5} detach={c['detached_text']:8} geo={c['geometry_verdict']} "
                  f"final={c['final_verdict']:8} {c['reason']}")
