# -*- coding: utf-8 -*-
"""اختبارات ملحق التقشير بالمقاطع: الأمثلة الملزمة وضوابط التوسع الخاطئ."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from syllable_peel import propose


def _cands(w):
    return propose(w)['candidates']


def test_no_cut_inside_syllable_nun():
    # نَ داخل المقطع نَكْ: لا يُنشأ حد يفصل النون وحدها
    assert not [c for c in _cands('نَكْتُبُ') if c['detached_text'] == 'نَ']


def test_prefix_inside_syllable_not_licensed():
    assert all(c['final_verdict'] != 'LICENSED' for c in _cands('نَكْتُبُ'))


def test_suffix_hu_is_geometry_ok_but_pending():
    c = [c for c in _cands('نَكْتُبُهُ') if c['side'] == 'right' and c['detached_text'] == 'هُ'][0]
    assert c['geometry_verdict'] == 'OK' and c['final_verdict'] == 'PENDING'


def test_article_unit_licensed_at_syllable_boundary():
    c = [c for c in _cands('ٱلۡكِتَٰبُ') if c['detached_text'] == 'ٱلۡ'][0]
    assert c['final_verdict'] == 'LICENSED'


def test_geminate_cut_rejected():
    c = [c for c in _cands('كَلَّا') if c['side'] == 'left'][0]
    assert c['geometry_verdict'] == 'REJECT' and c['final_verdict'] == 'REJECTED'


def test_detached_part_candidates_are_independent():
    # فشل حد لا يوقف حدًا آخر في الكلمة نفسها
    res = _cands('نَكْتُبُهُ')
    assert any(c['geometry_verdict'] == 'OK' for c in res) and any(c['geometry_verdict'] == 'OK' for c in res)


def test_article_rule_only_for_exact_unit():
    # ٱلۡكِ ليست وحدة ال: لا ترخيص لها بالتعريف
    c = [c for c in _cands('ٱلۡكِتَٰبُ') if c['detached_text'] == 'ٱلۡكِ'][0]
    assert c['final_verdict'] != 'LICENSED'


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
