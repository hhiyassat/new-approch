# -*- coding: utf-8 -*-
"""اختبارات التقشير بإزالة الوحدات من الطرفين: الأمثلة المعتمدة من المستخدم وموانعها."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_peel import edge_peel as E


def test_suffix_then_prefix_to_root_search():
    r = E('نَكْتُبُهُ')
    assert [s['side'] + ':' + s['text'] for s in r['steps']] == ['right:ه', 'left:ن']
    assert r['status'] == 'ROOT_SEARCH' and r['core'] == 'كتب'


def test_prefix_leaving_sukun_stops_and_searches_root():
    r = E('نَكْتُبُ')
    assert r['status'] == 'ROOT_SEARCH' and r['core'] == 'كتب'


def test_article_licensed_then_stop():
    r = E('ٱلنَّاسِ')
    assert r['steps'][0]['role'] == 'ART' and r['steps'][0]['verdict'] == 'LICENSED'
    assert r['status'] == 'STOP'


def test_no_step_when_removal_leaves_two_consonants():
    r = E('كَلَّا')
    assert r['steps'] == [] and r['core_consonants'] == 2


def test_letters_only_confirm_do_not_search():
    # لا تُنزع حروف لم تكن في الطرف: ٱلرَّحِيمِ تبقى كما هي بعد ال
    r = E('ٱلرَّحِيمِ')
    assert [s['text'] for s in r['steps']] == ['ء']
    assert r['core'] == 'رحم'


def test_silent_wasla_article_is_pending():
    r = E('وَٱلنَّاسِ')
    art = [s for s in r['steps'] if s['role'] == 'ART'][0]
    assert art['verdict'] == 'PENDING'


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
