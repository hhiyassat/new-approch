# -*- coding: utf-8 -*-
"""اختبارات التقشير المرخّص: لكل قاعدة ضابط موجب ومقابل يكشف التوسع الخاطئ (حدود التقطيع §١٢)."""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peel as Pl
from gate import build_cells


def _one(word, rule=None):
    res = Pl.analyze(word)
    if rule:
        res = [a for a in res if a['rule']['rule_id'] == rule]
    assert res, f'لا اقتراح لـ {word}'
    return res[0]


def _verdicts(word):
    return [a['verdict'] for a in Pl.analyze(word)]


# 1) سابقة حقيقية مقابل حرف أصلي مشابه
def test_silent_wasla_split_is_pending_not_licensed():
    # ٱ بعد حركة السابقة مكتوبة بلا حركة: الكلمة كاملة لا تُقطَّع بها الآن، فالفصل PENDING
    a = _one('وَٱلنَّاسِ', 'PRO-ART')
    assert a['verdict'] == 'PENDING' and 'صامتة' in a['reason']
    assert any(b.get('kind') == 'CONNECTED' for b in a['boundary_checks'])


def test_silent_wasla_licensed_only_when_word_syllabifies():
    # الشرط المعاكس: إن قُطّعت الكلمة كاملة بلا مشكلة يصبح الفصل مرخّصًا عند الحاجة
    a = Pl._evaluate('وَٱلنَّاسِ', build_cells('وَٱلنَّاسِ'), 'PRO-ART',
                     [('PRO', [0]), ('ART', [1, 2]), ('HOST', [3, 4, 5])], True, [], dict(_src(), word_ok=True))
    assert a['verdict'] == 'LICENSED', 'عند قبول الكلمة كاملة يجتاز الفصل'


def test_root_waw_not_licensed():
    a = _one('وَجَدَ', 'PRO-SINGLE')
    assert a['verdict'] == 'PENDING', 'الواو قد تكون جذرًا، فلا تُقشّر وحدها'
    assert any(x['kind'] == 'WHOLE_WORD' for x in a['alternatives'])


# 2) لاحقة ضميرية مقابل نهاية أصلية
def test_pronoun_suffix_never_licensed():
    for w in ('كِتَابُهُ', 'وَجْهُ'):
        for a in Pl.analyze(w):
            if a['rule']['rule_id'] == 'SUFFIX-PRONOUN':
                assert a['verdict'] != 'LICENSED', w


# 3) مضيف قصير مرخّص مقابل بقية قصيرة غير مرخّصة
def test_short_licensed_host():
    a = _one('ٱلۡحَقُّ', 'ART-WRITTEN')
    assert a['verdict'] == 'LICENSED'
    assert a['units'][2]['candidate_role'] == 'HOST'


def test_short_unlicensed_residue_rejected():
    a = _one('ٱلمْبِ', 'ART-WRITTEN')
    assert a['verdict'] == 'REJECTED'
    assert 'بقية' in a['reason']


# 4) كلمة كاملة محمية مقابل تركيب قابل للفصل
def test_protected_relative_whole_word():
    for w in ('ٱلَّذِي', 'وَٱلَّذِي', 'ٱلَّذِينَ'):
        a = Pl.analyze(w)[0]
        assert a['verdict'] == 'REJECTED' and 'موصول' in a['reason'], w


# 5) جزء مفصول صحيح وبقية معيبة؛ يُرفض الفصل
def test_valid_part_defective_residue_rejected():
    a = _one('كَلَّا', 'PRO-SINGLE')
    assert a['verdict'] == 'REJECTED', 'كَ + لَّا يُرفض لأن البقية بلا مقطع صحيح'
    assert a['boundary_checks'][0]['left_valid'] is True
    assert a['boundary_checks'][0]['residual_valid'] is False


# 6) بقية صحيحة وجزء مفصول معيب؛ يُرفض الفصل
def test_defective_detached_part_rejected():
    # م ساكنة بلا مقطع في الجزء المفصول، والبقية «ب» مرخّصة: يُرفض الحد
    cells = build_cells('مْبِ')
    a = Pl._evaluate('مْبِ', cells, 'PRO-SINGLE', [('HOST', [0]), ('HOST', [1])],
                     True, [], _src())
    assert a['verdict'] == 'REJECTED'
    assert a['boundary_checks'][0]['left_valid'] is False
    assert a['boundary_checks'][0]['residual_valid'] is True


# 7) طرفان صحيحان مقطعيًا دون دليل صرفي؛ لا يُعتمد الفصل
def test_valid_sides_without_morph_evidence_pending():
    a = _one('يَقُولُ', 'VERB-PREFIX')
    assert a['verdict'] == 'PENDING', 'بادئة المضارعة تحتاج دليل الفعل'


# 8) شدة أصلية مقابل فك مرخّص عبر الحد
def test_shadda_cut_refused():
    cells = build_cells('كَلَّا')
    a = Pl._evaluate('كَلَّا', cells, 'PRO-SINGLE', [('PRO', [0, 1]), ('HOST', [2])],
                     True, [], _src())
    assert a['verdict'] == 'REJECTED' and 'شدة مقطوعة' in a['reason']


def test_article_linked_shadda_licensed_across_boundary():
    a = _one('ٱلرَّحِيمِ', 'ART-WRITTEN')
    assert a['verdict'] == 'LICENSED'
    assert a['boundary_checks'][0]['shadda_origin'] == 'ARTICLE_LINKED'
    assert a['units'][2]['syllables'][0].get('onset_geminate') is True


# 9) ساكن داخلي من الشدة أو التعريف مقابل ساكن آخر
def test_internal_sukun_origin_guard():
    cells = build_cells('ٱلنَّاسِ')
    assert Pl._internal_sukun(cells, list(range(len(cells))))[0]['origin'] == 'SHADDA'
    cells[1].flags.append('UNMARKED')
    assert Pl._internal_sukun(cells, list(range(len(cells))))[0]['origin'] == 'UNKNOWN'


def test_unknown_sukun_makes_pending():
    # الساكن الأول (شدة النون) بمصدر غير محسوم داخل المضيف: PENDING لا قبول ولا رفض
    cells = build_cells('ٱلنَّاسِ')
    cells[1].flags.append('UNMARKED')
    a = Pl._evaluate('ٱلنَّاسِ', cells, 'ART-WRITTEN', [('ART', [0]), ('HOST', [1, 2, 3])],
                     True, [], _src())
    assert a['verdict'] == 'PENDING' and 'غير محسوم' in a['reason']


# 10) تحليلان محتملان دون اختيار اعتباطي
def test_two_licensed_readings_become_conflict():
    a1 = dict(verdict='LICENSED', units=[dict(cell_ids=[0, 1])], boundary_checks=[dict(cut_at_cell=1)], reason='')
    a2 = dict(verdict='LICENSED', units=[dict(cell_ids=[0, 1])], boundary_checks=[dict(cut_at_cell=2)], reason='')
    out = Pl._resolve_conflicts([a1, a2])
    assert [x['verdict'] for x in out] == ['CONFLICT', 'CONFLICT']


# 11) اقتراح ينزع حرفًا ثبتت أصالته؛ يُرفض
def test_removed_root_letter_rejected():
    cells = build_cells('كَلَّا')
    a = Pl._evaluate('كَلَّا', cells, 'PRO-SINGLE', [('PRO', [0]), ('HOST', [1, 2])],
                     True, [], _src())
    assert a['verdict'] == 'REJECTED'
    a2 = Pl._evaluate('كَلَّا', cells, 'PRO-SINGLE', [('PRO', [1]), ('HOST', [0, 2])],
                      True, [], _src())
    assert a2['verdict'] == 'REJECTED', 'نزع ل بدل الكاف يُرفض'


# 12) فقد خلية أو تكرارها: تغطية المصدر
def test_coverage_exceptions_are_explained():
    cov_ok, exc = Pl._coverage('ٱلنَّاسِ', build_cells('ٱلنَّاسِ'))
    assert cov_ok
    assert {e['status'] for e in exc} == {'ELIDED_SOLAR_LAM', 'MADD_ABSORBED'}


def test_coverage_unmapped_letter_fails():
    cells = build_cells('بِسۡمِ')
    ok, _ = Pl._coverage('بِسۡمِ', cells[:-1])
    assert not ok, 'حذف خلية يكشفه فاحص المصدر'


# 13) إعادة التشغيل تعيد النتائج والترتيب نفسيهما
def test_rerun_is_deterministic():
    for w in ('وَٱلنَّاسِ', 'كَلَّا', 'يَقُولُ', 'كِتَابُهُ'):
        assert Pl.analyze(w) == Pl.analyze(w)


# بنية الخرج والشجرة والتقسيم
def test_unit_tree_partitions_cells_exactly():
    a = _one('وَٱلنَّاسِ', 'PRO-ART')
    n = len(build_cells('وَٱلنَّاسِ'))
    assert a['units'][0]['children'] == ['U1', 'U2', 'U3']
    ids = [i for u in a['units'][1:] for i in u['cell_ids']]
    assert sorted(ids) == list(range(n)) and len(ids) == n, 'لا فقد ولا تكرار'


def test_output_has_required_fields():
    a = _one('ٱلنَّاسِ', 'ART-WRITTEN')
    for key in ('analysis_id', 'source_id', 'source_version', 'word_occurrence_id', 'original_text',
                'normalized_text', 'units', 'boundary_checks', 'rule', 'verdict', 'reason',
                'alternatives', 'parent_analysis_id'):
        assert key in a, key
    assert a['source_version'] == Pl.ABSENT, 'غياب القيمة يُمثَّل بغيابٍ معلوم'
    for key in ('rule_id', 'rule_version', 'cause', 'conditions', 'obstacles', 'evidence',
                'residual_obligations'):
        assert key in a['rule']


def test_no_candidate_is_not_rejection():
    assert Pl.analyze('قَالَ') == []


def test_analysis_does_not_mutate_cells():
    cells = build_cells('وَٱلنَّاسِ')
    before = copy.deepcopy(cells)
    Pl.analyze('وَٱلنَّاسِ', cells=cells)
    assert cells == before


def _src():
    return dict(source_id=Pl.ABSENT, source_version=Pl.ABSENT, occurrence_id=Pl.ABSENT,
                original_text=None, solar=False)


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
            except Exception as e:
                fails += 1; print('ERROR', name, type(e).__name__, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
