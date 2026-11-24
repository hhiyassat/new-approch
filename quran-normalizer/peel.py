# -*- coding: utf-8 -*-
"""
التقشير المرخّص بعد التقطيع المقطعي (تمهيد SLG).

المدخل: كلمة مطبّعة وخلاياها (gate.build_cells). الخرج: تحليلات تقشير، لكل منها
هوية ووحدات وأدلة وحكم (LICENSED / REJECTED / PENDING / CONFLICT).

قواعد ثابتة في هذا الملف:
- لا تعديل لقواعد التطبيع؛ لا تُضاف حروف ولا حركات.
- لا حذف: كل خلية تبقى في وحدة واحدة، وبترتيبها.
- كل حد فصل يُفحص طرفاه مستقلًا؛ فشل طرف يرفض الحد لا الكلمة.
- غياب قيمة يُمثَّل بـ ABSENT، لا بقيمة مفترضة.
"""
import copy
from gate import (build_cells, syllabify, _is_relative, _key, LEXICON, _solar_elision, SOLAR,
                  MARKCHARS, NON_PHONETIC, WAQF, TATWEEL)

RULE_VERSION = '0.1.0'
ABSENT = 'ABSENT'

# سوابق الجر والعطف والتشبيه والقسم: تُعرف بالحرف وحده، ولا تُقشّر وحدها.
PROCLITIC_CATS = {
    'و': ('عطف', 'قسم', 'حال'),
    'ف': ('عطف',),
    'ب': ('جر', 'قسم'),
    'ل': ('جر', 'تعليل', 'ابتداء'),
    'ك': ('جر', 'تشبيه'),
}
# بادئات المضارعة (ء ن ي ت): لا تُحكم إلا بدليل الفعل.
VERB_PREFIX_CARRIERS = ('ن', 'ي', 'ت', 'ء')
# لواحق ضميرية: الأطول أولًا. كل منها مرشح فقط، لأن النهاية قد تكون أصلية.
SUFFIX_FORMS = ('هما', 'هم', 'هن', 'ها', 'كم', 'كن', 'نا', 'ني', 'ه', 'ك')

IGNORABLE = set(MARKCHARS) | set(NON_PHONETIC) | set(WAQF) | {TATWEEL, '‏'}
MADD_LETTERS = set('اوىي')

RULES = {
    'ART-WRITTEN': dict(
        cause='ال التعريف المكتوبة: ٱ (وصل) + ل (ساكنة أو محذوفة لشمسية)',
        conditions=['أول الكلمة ٱ', 'ل بعدها ساكنة مكتوبة، أو الحرف بعدها شمسي'],
        pending=None),
    'PRO-ART': dict(
        cause='سابقة حرف (و/ف/ب/ل/ك) متبوعة بال التعريف',
        conditions=['أول الكلمة حرف سابقة بحركة مكتوبة', 'بعدها ال مكتوبة أو شمسية'],
        pending=None),
    'PRO-SINGLE': dict(
        cause='سابقة حرف مفردة بلا ال بعدها: قد تكون حرف عطف/جر/تشبيه، وقد تكون جذرًا',
        conditions=['أول الكلمة حرف من مجموعة السوابق بحركة مكتوبة'],
        pending='سابقة مفردة: الحرف قد يكون أصلًا في الجذر، والحسم يحتاج معجمًا'),
    'VERB-PREFIX': dict(
        cause='بادئة مضارعة محتملة (ء ن ي ت)',
        conditions=['أول الكلمة من حروف المضارعة بحركة مكتوبة', 'لا ال بعدها'],
        pending='بادئة مضارعة مرشحة: تحتاج دليل الفعل قبل الحكم'),
    'SUFFIX-PRONOUN': dict(
        cause='لاحقة ضميرية محتملة',
        conditions=['آخر الكلمة يطابق صيغة لاحقة'],
        pending='لاحقة ضميرية مرشحة: النهاية قد تكون أصلية في الجذر، والحسم يحتاج دليلًا'),
}

_LEX_KEYS = [(_key(e['word']), e) for e in LEXICON]


# ---------------------------------------------------------------- أدوات الخلايا
def _is_pair(a, b):
    """شدة مكتوبة واحدة: نصفاها على الخلية نفسها من المصدر، بالحامل نفسه."""
    return a.shadda == 'first' and b.shadda == 'second' and a.carrier == b.carrier and a.span == b.span


def _article_len(cells, start=0):
    """→ (عدد خلايا ال من الموضع start، هل الحذف شمسي). (0، False) إن لم تبدأ بال."""
    if start >= len(cells) or cells[start].carrier != 'ء' or 'WASLA' not in cells[start].flags:
        return 0, False
    if 'SOLAR_LAM_ELIDED' in cells[start].flags:
        return 1, True
    j = start + 1
    if j < len(cells) and cells[j].carrier == 'ل' and cells[j].sukun and cells[j].vowel is None:
        return 2, False
    return 0, False


def _proclitic(cell):
    """سابقة حرف مكتوبة الحركة، أو None."""
    if cell.carrier in PROCLITIC_CATS and cell.vowel and not cell.shadda and 'UNMARKED' not in cell.flags:
        return cell.carrier
    return None


def _is_silent(c):
    """ٱ مكتوبة بلا حركة بعد حركة سابقة: صامتة في الوصل، ولا تُعدّ مقطعًا."""
    return c.carrier == 'ء' and 'WASLA' in c.flags and 'UNMARKED' in c.flags and c.sukun and not c.vowel


def _side(cells, ids, gem_ok):
    """تقطيع طرف واحد بعد إعادة ترقيم خلاياه. الصامتة تُسجَّل ولا تدخل التقطيع.
    gem_ok: يُسمح ببداية مشدّدة (شدة معلّقة بالتعريف) إن سبقها ال."""
    silent = [i for c, i in zip(cells, ids) if _is_silent(c)]
    keep = [(c, i) for c, i in zip(cells, ids) if not _is_silent(c)]
    if not keep:
        return dict(valid=bool(silent), syllables=[], residue=[], gem=None, silent_ids=silent,
                    reason='ٱ صامتة بعد السابقة' if silent else 'بقية فارغة')
    cells = [c for c, _ in keep]
    ids = [i for _, i in keep]
    gem = None
    if gem_ok and len(cells) >= 2 and _is_pair(cells[0], cells[1]):
        gem = ids[0]
        cells, ids = cells[1:], ids[1:]
    if not cells:
        return dict(valid=False, syllables=[], residue=[], gem=gem, silent_ids=silent, reason='بقية فارغة')
    sub = copy.deepcopy(cells)
    for k, c in enumerate(sub):
        c.idx = k
    sylls, residue = syllabify(sub)
    syl = [dict(shape=s['shape'], cell_ids=[ids[k] for k in s['cells']],
                valid=s['valid'], reason=s['reason']) for s in sylls]
    if gem is not None and syl:
        syl[0]['cell_ids'] = [gem] + syl[0]['cell_ids']
        syl[0]['onset_geminate'] = True
    res = [dict(cell_id=ids[t[1]], kind=t[0]) for t in residue]
    valid = not residue and bool(syl) and all(s['valid'] for s in syl)
    if residue:
        reason = 'بقية غير مقطّعة (صامت بلا مقطع): ' + ', '.join(str(r['cell_id']) for r in res)
    elif not syl:
        reason = 'بقية فارغة'
    elif not all(s['valid'] for s in syl):
        reason = next(s['reason'] for s in syl if not s['valid'])
    else:
        reason = 'مقاطع مرخّصة'
    return dict(valid=valid, syllables=syl, residue=res, gem=gem, silent_ids=silent, reason=reason)


def _coverage(word, cells):
    """تغطية المصدر: كل محرف يقع في خلية، أو يُفسَّر بتحويل معلن. يعيد (سليم، الاستثناءات)."""
    covered = {}
    for c in cells:
        for i in range(*c.span):
            covered.setdefault(i, c.idx)
    elided = _solar_elision(word)
    exc, ok = [], True
    for i, ch in enumerate(word):
        if i in covered or ch in IGNORABLE:
            continue
        if elided and elided[0] <= i < elided[1]:
            exc.append(dict(char=i, status='ELIDED_SOLAR_LAM', owner_cell=0))
            continue
        if ch in MADD_LETTERS:
            owners = [c for c in cells if c.span[1] <= i]
            if owners and 'SILENT_ALIF_WAW_PLURAL' in owners[-1].flags and ch == 'ا':
                exc.append(dict(char=i, status='SILENT_ALIF_WAW_PLURAL', owner_cell=owners[-1].idx))
                continue
            if owners:
                own = owners[-1]
                between = word[own.span[1]:i]
                if all(x in IGNORABLE for x in between):
                    exc.append(dict(char=i, status='MADD_ABSORBED', owner_cell=own.idx))
                    continue
        exc.append(dict(char=i, status='UNMAPPED', owner_cell=None))
        ok = False
    return ok, exc


def _internal_sukun(cells, ids, word=''):
    """أسكنة داخلية في الطرف: مصدر كل واحدة (مكتوب، أو من شدة، أو ألف خنجرية مكتوبة، أو غير محسوم)."""
    out = []
    for k, c in enumerate(cells[:-1]):
        if c.sukun:
            if 'UNMARKED' in c.flags:
                # حرف مدّ بالألف الخنجرية المكتوبة: أصله مكتوب، وغيره غير محسوم
                origin = 'WRITTEN_MADD' if '\u0670' in word[c.span[0]:c.span[1]] else 'UNKNOWN'
            elif c.shadda:
                origin = 'SHADDA'
            else:
                origin = 'WRITTEN'
            out.append(dict(cell_id=ids[k], origin=origin))
    return out


# ---------------------------------------------------------------- الاقتراحات
def _candidates(word, cells):
    """→ قائمة (rule_id، أطراف)، والأطراف متصلة وتبدأ من الصفر بالترتيب."""
    n = len(cells)
    if n == 0:
        return []
    out = []
    alen, _solar = _article_len(cells, 0)
    pro = _proclitic(cells[0])
    alen_after_pro, _s2 = _article_len(cells, 1) if pro else (0, False)
    if pro and alen_after_pro and n > 1 + alen_after_pro:
        out.append(('PRO-ART', [('PRO', [0]), ('ART', list(range(1, 1 + alen_after_pro))),
                                ('HOST', list(range(1 + alen_after_pro, n)))]))
    elif alen and n > alen:
        out.append(('ART-WRITTEN', [('ART', list(range(alen))), ('HOST', list(range(alen, n)))]))
    elif pro and n > 1:
        out.append(('PRO-SINGLE', [('PRO', [0]), ('HOST', list(range(1, n)))]))
    if not alen and not pro and n > 1:
        c0 = cells[0]
        if c0.carrier in VERB_PREFIX_CARRIERS and c0.vowel and 'WASLA' not in c0.flags and not c0.shadda:
            out.append(('VERB-PREFIX', [('VERB_PREFIX', [0]), ('HOST', list(range(1, n)))]))
    for suf in SUFFIX_FORMS:
        L = len(suf)
        if n - L >= 1 and ''.join(c.carrier for c in cells[n - L:]) == suf:
            out.append(('SUFFIX-PRONOUN', [('HOST', list(range(0, n - L))),
                                           ('SUFFIX', list(range(n - L, n)))]))
            break
    return out


ALLOWED_REMOVED = {
    'ART': {'ء', 'ل'},
    'PRO': set(PROCLITIC_CATS),
    'VERB_PREFIX': set(VERB_PREFIX_CARRIERS),
    'SUFFIX': set(''.join(SUFFIX_FORMS)),
}


def _evaluate(word, cells, rule_id, parts, cov_ok, cov_exc, source):
    """فحص اقتراح واحد: كل حد يُفحص بطرفيه، ثم يُحسم الحكم."""
    n = len(cells)
    all_ids = list(range(n))
    bchecks, fails = [], []
    cut_positions = []
    acc = 0
    for role, idxs in parts[:-1]:
        acc += len(idxs)
        cut_positions.append((acc, role))

    for p, left_role in cut_positions:
        if p < n and _is_silent(cells[p]):
            bchecks.append(dict(kind='CONNECTED', cut_at_cell=p, left_role=left_role,
                                note='ٱ صامتة بعد حركة السابقة: لا حد مقطعي هنا، والل تنضم لمقطع السابقة',
                                boundary_license=True))
            continue
        gem_ok = left_role == 'ART'
        left = _side(cells[:p], all_ids[:p], gem_ok=False)
        right = _side(cells[p:], all_ids[p:], gem_ok=gem_ok)
        pair_cut = _is_pair(cells[p - 1], cells[p]) if 0 < p < n else False
        if pair_cut:
            origin = 'SHADDA_CUT'
        elif p < n and p + 1 < n and _is_pair(cells[p], cells[p + 1]):
            origin = 'ARTICLE_LINKED' if gem_ok and cells[p].carrier in SOLAR else 'WRITTEN'
        else:
            origin = ABSENT
        removed_ok = all(set(c.carrier for c in cells[s:e]) <= ALLOWED_REMOVED.get(r, set())
                         for r, s, e in _spans_of(parts) if r != 'HOST')
        sukun = _internal_sukun(cells[p:], all_ids[p:], word) if right['valid'] else []
        touching = [s for s in sukun if s['origin'] == 'UNKNOWN' and s['cell_id'] in (p - 1, p, p + 1)]
        cut_ok = left['valid'] and right['valid'] and not pair_cut and cov_ok
        if pair_cut:
            fails.append('شدة مقطوعة عبر الحد، والفصل عبرها غير مرخّص')
        if not left['valid']:
            fails.append('الطرف الأيسر معيب: ' + left['reason'])
        if not right['valid']:
            fails.append('الطرف الأيمن معيب: ' + right['reason'])
        if not cov_ok:
            fails.append('تغطية المصدر ناقصة (حرف غير معلّل)')
        bchecks.append(dict(
            cut_at_cell=p,
            left_role=left_role,
            left_syllables=left['syllables'],
            residual_syllables=right['syllables'],
            left_valid=left['valid'],
            residual_valid=right['valid'],
            source_coverage_valid=cov_ok,
            shadda_origin=origin,
            internal_sukun_origin=sukun,
            unknown_sukun_touching_cut=touching,
            host_integrity=right['valid'] and removed_ok and not pair_cut,
            boundary_license=cut_ok and removed_ok,
        ))
        if not removed_ok:
            fails.append('يُنزع حرف لا ينتمي إلى السابقة المرخّصة')

    rule = RULES[rule_id]
    unknown_sukun = [s for b in bchecks for s in b.get('unknown_sukun_touching_cut', [])]
    lex = [e for k, e in _LEX_KEYS if k == _key(word)]
    art_parts = [idxs for role, idxs in parts if role == 'ART']
    art_start = cells[art_parts[0][0]].span[0] if art_parts else 0
    protected = _is_relative(word) or (bool(art_parts) and _is_relative(word[art_start:]))

    if protected:
        verdict, reason = 'REJECTED', 'اسم موصول: الكلمة الكاملة محمية، لا تُقشّر'
    elif fails:
        verdict, reason = 'REJECTED', fails[0]
    elif rule['pending']:
        verdict, reason = 'PENDING', rule['pending']
    elif any(_is_silent(cells[i]) for role, idxs in parts if role == 'ART' for i in idxs) \
            and not source.get('word_ok'):
        verdict, reason = 'PENDING', ('ٱ صامتة بعد حركة السابقة، والتقطيع الكامل للكلمة لا يعترف بها بعد '
                                      '(تُعدّ قفلًا): الحسم يحتاج قرارًا في منظومة التقطيع')
    elif unknown_sukun:
        verdict, reason = 'PENDING', 'ساكن داخلي في المضيف مصدره غير محسوم'
    elif lex:
        verdict, reason = 'PENDING', 'الكلمة الكاملة مدخل معجمي مرجعي: الحسم يحتاج دليل المعجم'
    else:
        verdict, reason = 'LICENSED', 'سلامة الطرفين وتغطية المصدر ودليل الفصل مكتمل'

    units = _units(word, cells, parts, source)
    cut_str = '-'.join(str(p) for p, _ in cut_positions)
    return dict(
        analysis_id=f"{source['source_id']}#{source['occurrence_id']}#{rule_id}#{cut_str}",
        source_id=source['source_id'],
        source_version=source['source_version'],
        word_occurrence_id=source['occurrence_id'],
        original_text=source['original_text'],
        normalized_text=word,
        units=units,
        boundary_checks=bchecks,
        source_coverage=cov_exc,
        rule=dict(rule_id=rule_id, rule_version=RULE_VERSION, cause=rule['cause'],
                  conditions=list(rule['conditions']),
                  obstacles=list(fails) + ([] if not protected else ['اسم موصول']),
                  evidence=[f'حد عند الخلية {p} بعد {r}' for p, r in cut_positions],
                  residual_obligations=(['أعد فحص البقية بعد كل فصل'] if verdict != 'LICENSED' else [])),
        verdict=verdict,
        reason=reason,
        alternatives=[],
        parent_analysis_id=ABSENT,
    )


def _spans_of(parts):
    s = 0
    for role, idxs in parts:
        yield role, s, s + len(idxs)
        s += len(idxs)


def _units(word, cells, parts, source):
    n = len(cells)
    root = dict(unit_id='U0', candidate_role='WORD', text=word, source_spans=[(0, len(word))],
                cell_ids=list(range(n)), source_mapping=[], syllables=[], children=[])
    out = [root]
    elided = _solar_elision(word) if source.get('solar') else None
    prev_role = None
    for k, (role, idxs) in enumerate(parts, start=1):
        sub = [cells[i] for i in idxs]
        start, end = sub[0].span[0], sub[-1].span[1]
        spans = [c.span for c in sub]
        mapping = [dict(cell_id=c.idx, carrier=c.carrier, span=c.span, flags=list(c.flags)) for c in sub]
        if role == 'ART' and elided:
            spans.append(elided)
            mapping.append(dict(elided=elided, flag='SOLAR_LAM_ELIDED'))
        sy = _side(sub, idxs, gem_ok=(role == 'HOST' and prev_role == 'ART'))
        if role == 'ART' and any(_is_silent(c) for c in sub):
            sy = dict(syllables=[], note='ٱ صامتة؛ الل ساكنة تنضم لمقطع السابقة')
        out.append(dict(unit_id=f'U{k}', candidate_role=role, text=word[start:end],
                        source_spans=spans, cell_ids=list(idxs), source_mapping=mapping,
                        syllables=sy['syllables'], children=[]))
        prev_role = role
    out[0]['children'] = [u['unit_id'] for u in out[1:]]
    return out


def _resolve_conflicts(analyses):
    """تحليلان مرخّصان يبدآن من الخلية نفسها بحدود مختلفة: متعارضان حتى يُحسما."""
    lic = [a for a in analyses if a['verdict'] == 'LICENSED']
    for a in lic:
        a_cells = tuple(a['units'][0]['cell_ids'][:1])
        rivals = [b for b in lic if b is not a and tuple(b['units'][0]['cell_ids'][:1]) == a_cells
                  and [x['cut_at_cell'] for x in b['boundary_checks']] !=
                      [x['cut_at_cell'] for x in a['boundary_checks']]]
        if rivals:
            for x in [a] + rivals:
                x['verdict'] = 'CONFLICT'
                x['reason'] = 'تحليلان مرخّصان بحدود مختلفة على الخلايا نفسها'
    return analyses


def analyze(word, cells=None, source_id=ABSENT, source_version=ABSENT,
            occurrence_id=ABSENT, original_text=None):
    """→ قائمة تحليلات التقشير للكلمة. قائمة فارغة إن لم يوجد اقتراح (غياب الاقتراح ليس رفضًا)."""
    if cells is None:
        cells = build_cells(word)
    cells_snapshot = copy.deepcopy(cells)
    source = dict(source_id=source_id, source_version=source_version, occurrence_id=occurrence_id,
                  original_text=word if original_text is None else original_text,
                  solar=bool(_solar_elision(word)))
    cov_ok, cov_exc = _coverage(word, cells)
    _ws, _wr = syllabify(copy.deepcopy(cells))
    word_ok = not _wr and all(s['valid'] for s in _ws)
    source['word_ok'] = word_ok
    results = [_evaluate(word, cells, rid, parts, cov_ok, cov_exc, source)
               for rid, parts in _candidates(word, cells)]
    results = _resolve_conflicts(results)
    ids = [r['analysis_id'] for r in results]
    for r in results:
        r['alternatives'] = [dict(kind='WHOLE_WORD', note='الكلمة كاملة وجه منافس ما لم يمنعه دليل')] + [
            dict(kind='ANALYSIS', analysis_id=i) for i in ids if i != r['analysis_id']]
    assert cells == cells_snapshot, 'التقشير لا يعدّل الخلايا'
    return results


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:] or ['ٱلنَّاسِ', 'وَٱلنَّاسِ', 'وَجَدَ', 'كَلَّا']:
        for a in analyze(w):
            print(w, a['rule']['rule_id'], a['verdict'], '|', a['reason'])
