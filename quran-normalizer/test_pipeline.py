# -*- coding: utf-8 -*-
"""اختبارات كل مرحلة من خط المعالجة، ثم الخط كاملاً."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P


def test_cells_keep_written_marks():
    cells = P.stage_cells('بِسۡمِ')
    assert [c.carrier for c in cells] == ['ب', 'س', 'م']
    assert [c.vowel for c in cells] == ['i', None, 'i']


def test_shadda_split_keeps_source_link():
    cells = P.stage_cells('مَدَّ')
    split = [c for c in cells if c.shadda]
    assert [c.shadda for c in split] == ['first', 'second']
    assert split[0].carrier == split[1].carrier == 'د'


def test_syllables_shapes():
    assert [s['shape'] for s in P.stage_syllables(P.stage_cells('بِسۡمِ'))[0]] == ['CVC', 'CV']
    assert [s['shape'] for s in P.stage_syllables(P.stage_cells('هَذَا'))[0]] == ['CV', 'CVV']


def test_checks_reject_medial_cvcc():
    sylls, res = P.stage_syllables(P.stage_cells('قَدْرْبَ'))
    assert P.stage_checks(sylls, res), 'يجب رفض القفل المزدوج وسط الكلمة'


def test_checks_accept_solar_article():
    sylls, res = P.stage_syllables(P.stage_cells('ٱلنَّاسِ'))
    assert P.stage_checks(sylls, res) == []


def test_classify_after_syllables_only():
    sylls, _ = P.stage_syllables(P.stage_cells('مِن'))
    assert P.stage_classify(sylls) == 'مبني'
    sylls, _ = P.stage_syllables(P.stage_cells('بِسۡمِ'))
    assert P.stage_classify(sylls) == 'مشتق'


def test_run_end_to_end():
    assert P.run('بِسۡمِ')['kind'] == 'مشتق'
    assert P.run('مِن')['kind'] == 'مبني'
    r = P.run('قَدْرْبَ')
    assert r['status'] == 'REJECTED' and 'kind' not in r


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
