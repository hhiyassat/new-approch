# -*- coding: utf-8 -*-
"""اختبارات وسم العامل والمعمول: كل وسم مرشح، ولا وسم حاسم."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import operator_tags as T


def test_word_operator_with_nasb_rafa():
    tags = T.tags_for_word('إِنَّ', 'ٱلنَّاسِ')
    assert tags[0][0] == 'عامل' and tags[0][2] == 'نصب / رفع' and tags[0][3] == 'WORD_OPERATOR'


def test_proclitic_jarr_operator_is_candidate_only():
    tags = T.tags_for_word('بِٱلۡغَيۡبِ')
    assert all(t[5] == 'CANDIDATE' for t in tags)
    assert tags[0][2] == 'جر' and tags[1][0] == 'معمول'


def test_adjacent_operand_is_candidate_for_word_operator():
    tags = T.tags_for_word('عَنِ', 'ٱلنَّاسِ')
    assert [t[0] for t in tags] == ['عامل', 'معمول'] and tags[1][3] == 'ADJACENT_AFTER_OPERATOR'


def test_conjunction_waw_is_not_a_general_proclitic():
    # الواو العاطفة ليست عاملًا جارًّا؛ لا تُوسم وَ... بوصفها عاملًا
    assert T.tags_for_word('وَٱلنَّاسِ') == []


def test_non_operator_has_no_tag():
    assert T.tags_for_word('ٱلنَّاسِ') == []


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn(); print('PASS', name)
            except AssertionError as e:
                fails += 1; print('FAIL', name, e)
    print('ALL PASS' if not fails else f'{fails} FAILED')
