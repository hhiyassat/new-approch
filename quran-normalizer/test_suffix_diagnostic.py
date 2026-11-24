# -*- coding: utf-8 -*-
"""اختبارات التشخيص: الترشيح داخل التمثيل لا يعني ترخيصًا ولا فصلًا."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from suffix_diagnostic import diagnose


def test_waw_alif_ending_is_orthographic_only():
    d = diagnose('كَفَرُوا')
    assert d['orthographic_ending'] and d['representation_candidate']
    assert not d['licensed_suffix'] and not d['executed_cut']


def test_no_ending_no_candidate():
    d = diagnose('كِتَابُ')
    assert not d['orthographic_ending'] and not d['representation_candidate']


def test_unsupported_glyph_is_reported_not_raised():
    d = diagnose('يُؤۡمِنُونَ')
    assert d['status'] == 'UNSUPPORTED_GLYPH' and d['executed_cut'] is False


def test_nothing_is_licensed_or_cut():
    for w in ('كَفَرُوا', 'كِتَابُ'):
        d = diagnose(w)
        assert d['licensed_suffix'] is False and d['executed_cut'] is False


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
