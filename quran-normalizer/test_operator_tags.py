# -*- coding: utf-8 -*-
"""اختبارات وسم العامل والمعمول: كل وسم مرشح، ولا وسم حاسم."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import operator_tags as T


def test_word_operator_with_nasb_rafa():
    tags = T.tags_for_word('إِنَّ', 'ٱلنَّاسِ')
    assert tags[0][0] == 'عامل' and tags[0][2] == 'نصب / رفع' and tags[0][3] == 'WORD_OPERATOR_SENSE'


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


def test_ma_splits_by_sense_not_merged():
    # «ما» النافية تنصب وترفع، والشرطية تجزم الفعل: لا تُجمع في حالة واحدة
    rows = [t for t in T.tags_for_word('مَا', 'ٱلنَّاسِ') if t[0] == 'عامل']
    cases = {c.strip() for t in rows for c in t[2].split('/')}
    assert {'رفع', 'نصب', 'جزم'} <= cases


def test_inna_rows_are_not_duplicated():
    rows = [t for t in T.tags_for_word('إِنَّ', 'ٱلنَّاسِ') if t[0] == 'عامل']
    labels = [t[1] for t in rows]
    assert len(labels) == len(set(labels))


def test_ma_before_illa_is_negative_sense():
    rows = [t for t in T.tags_for_word('مَا', 'إِلَّا') if t[0] == 'عامل']
    assert rows and all('النفي' in t[1] for t in rows)
    assert all(t[3] == 'WORD_OPERATOR_SENSE_NEXT_ILLA' for t in rows)


def test_plural_waw_ending_keeps_both_branches():
    # كَفَرُوا: اللاحقة لم تُثبت بعد، فالكاف تبقى وجهًا متنافسًا لا تُحذف
    rows = [t for t in T.tags_for_word('كَفَرُوا') if t[0] == 'عامل']
    assert rows and all(t[3] == 'PROCLITIC_OPERATOR_BRANCHED_SUFFIX' for t in rows)


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
