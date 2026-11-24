# -*- coding: utf-8 -*-
"""اختبار الربط: أحداث التطبيع ونتيجة التقشير على الكلمة نفسها، والربط لا يغيّر الأحكام."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_linked as RL
from peel import analyze
from gate import build_cells

def test_article_agrees_when_both_see_it():
    norm, ev, verdicts, err, art_n, art_p = RL.link_word('ٱلرَّحِيمِ')
    assert art_n and art_p and RL.agreement(art_n, art_p) == 'AGREE_ARTICLE'

def test_link_does_not_change_peel_verdict():
    w = 'ٱلرَّحِيمِ'
    before = sorted(a['verdict'] for a in analyze(w, cells=build_cells(w)))
    RL.link_word(w)
    after = sorted(a['verdict'] for a in analyze(w, cells=build_cells(w)))
    assert before == after

def test_word_without_article_has_no_article_agreement():
    _, _, _, _, art_n, art_p = RL.link_word('كِتَابُهُ')
    assert RL.agreement(art_n, art_p) == 'NONE' or RL.agreement(art_n, art_p) != 'AGREE_ARTICLE'

if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except Exception as e:
                fails += 1; print('FAIL', name, type(e).__name__, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
    sys.exit(1 if fails else 0)
