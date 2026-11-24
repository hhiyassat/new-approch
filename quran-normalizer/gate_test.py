# -*- coding: utf-8 -*-
"""اختبارات بوابة العوامل والمبنيات: حالات إلزامية، وسلبية، وتكامل المسار."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate
from gate import build_cells, syllabify, decide, LEXICON


def classes(r):
    return sorted(c['cls'] for c in r['candidates'])


def test_mandatory():
    assert classes(decide('لَيْتَ')) == ['حرف'] and decide('لَيْتَ')['candidates'][0]['role'] == 'عامل'
    assert classes(decide('لَيْسَ')) == ['فعل']
    assert classes(decide('بَيْتَ')) == ['اسم']
    r = decide('مَا'); assert r['status'] == 'PENDING' and classes(r) == ['اسم', 'حرف']
    r = decide('قَدْ'); assert r['status'] == 'PENDING' and classes(r) == ['اسم', 'حرف']
    assert decide('مِنْ')['candidates'][0]['cls'] == 'حرف'
    assert classes(decide('الَّذِي')) == ['اسم']      # لا تُسقط لامه بقاعدة أل
    assert decide('إِلَيَّ')['candidates'][0]['cls'] == 'حرف'


def test_identity_not_shape():
    # الشكل CVC . CV واحد، والهوية مختلفة
    a, b, c = (decide(w) for w in ('لَيْتَ', 'لَيْسَ', 'بَيْتَ'))
    assert [s[0] for s in a['syllables']] == [s[0] for s in b['syllables']] == [s[0] for s in c['syllables']]
    assert a['cells'] != b['cells'] and b['cells'] != c['cells']


def test_no_candidate_is_not_rejection():
    r = decide('هَذَا')
    assert r['status'] == 'NO_CANDIDATE' and r['syllables'][0][0] == 'CV'


def test_negative_medial_cvcc_rejected():
    r = decide('قَدْرْبَ')     # قفل مزدوج وسط الكلمة بلا شدة مكتوبة
    assert r['status'] == 'REJECTED', r


def test_solar_article_elided_and_tagged():
    # ٱلنَّاسِ: اللام الشمسية تُحذف (إدغام)، والشدة تصبح بدءاً للمقطع التالي
    r = decide('ٱلنَّاسِ')
    assert [s[0] for s in r['syllables']] == ['CVC', 'CVV', 'CV'], r
    assert 'SOLAR_LAM_ELIDED' in build_cells('ٱلنَّاسِ')[0].flags


def test_relative_keeps_lam():
    cells = build_cells('ٱلَّذِي')
    assert 'SOLAR_LAM_ELIDED' not in cells[0].flags and len(cells) == 4


def test_wasla_kept_and_inference_tagged():
    cells = build_cells('ٱلنَّاسِ')
    assert cells[0].span == (0, 1) and 'INFERRED_VOWEL' in cells[0].flags
    assert all(c.span[0] >= 0 for c in cells)


def test_integration_decision_uses_cell_path():
    word = 'مِنْ'
    r = decide(word)
    sylls, residue = syllabify(build_cells(word))
    assert [(s['shape'], s['span']) for s in sylls] == [(x[0], x[1]) for x in r['syllables']]
    assert r['cells'] == [(c.idx, c.carrier, c.vowel, c.long, c.shadda, c.flags) for c in build_cells(word)]


def test_lexicon_has_no_exhaustive_claim():
    assert all(e['exhaustive'] is False for e in LEXICON)


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
