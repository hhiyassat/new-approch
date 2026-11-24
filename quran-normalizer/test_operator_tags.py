# -*- coding: utf-8 -*-
"""اختبارات وسم العامل والمعمول: كل وسم مرشح، ولا وسم حاسم."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import operator_tags as T


def test_word_operator_with_nasb_rafa():
    tags = T.tags_for_word('إِنَّ', 'ٱلنَّاسِ')
    assert tags[0][0] == 'عامل' and tags[0][2] == 'نصب / رفع' and tags[0][3] == 'WORD_OPERATOR_VOCALIZED'


def test_proclitic_jarr_operator_is_diagnostic_only():
    tags = T.tags_for_word('بِمَآ')
    assert tags and all(t[5] == 'DIAGNOSTIC_ONLY' and t[3] == 'PROCLITIC_DIAGNOSTIC' for t in tags)


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
    assert rows and all('نفي' in t[1] for t in rows)
    assert all(t[3] == 'WORD_OPERATOR_SENSE_NEXT_ILLA' for t in rows)


def test_plural_waw_ending_keeps_both_branches():
    # كَفَرُوا: السابقة تشخيصية فقط، ولا تُعدّ عاملًا بالجدول الرئيسي
    rows = [t for t in T.tags_for_word('كَفَرُوا') if t[0] == 'عامل']
    assert rows and all(t[5] == 'DIAGNOSTIC_ONLY' for t in rows)


def test_waw_and_fa_are_never_proclitic_operators():
    # معيار ١: الواو والفاء لا تُرشّحان عاملًا؛ «وَلَدَانِ» و«فَالِقُ» بلا وسم
    assert T.tags_for_word('وَلَدَانِ') == []
    assert T.tags_for_word('فَالِقُ') == []


def test_merged_boundary_blocks_proclitic_candidate():
    # معيار ١: الحرف الملتحم بما بعده في المقطع لا يُرشَّح قبل إثبات حدّه
    for w in ('لِّلۡمُتَّقِينَ', 'بِٱلۡغَيۡبِ'):
        rows = T.tags_for_word(w)
        assert rows and all(t[5] == 'DIAGNOSTIC_ONLY' for t in rows), w


def test_function_is_undecided_without_article_evidence():
    # معيار ٢: الشكل CV وحده لا يعيّن الوظيفة
    rows = T.tags_for_word('بِمَآ')
    assert rows and all(t[7] == 'UNDECIDED' for t in rows)


def test_unreadable_operand_suspends_the_relation():
    # معيار ٣: إذا تعذّرت هوية الطرف الآخر تُعلَّق العلاقة ولا تُخمَّن
    rows = [t for t in T.tags_for_word('إِنَّ', 'يُؤۡمِنُونَ') if t[0] == 'معمول']
    assert rows and all(t[5] == 'SUSPENDED_OPERAND_UNREADABLE' for t in rows)


def test_kana_uu_is_not_proven_cv():
    # «كَانُوا» أول مقطعها CVV: لا يُعدّ حدًّا مثبتًا، ويبقى مؤجلًا لا محذوفًا
    rows = T.tags_for_word('كَانُوا')
    assert rows and all(t[3] == 'PROCLITIC_DIAGNOSTIC' and t[5] == 'DIAGNOSTIC_ONLY' for t in rows)
    assert rows[0][6] == 'FIRST_SYLLABLE_CVV'


def test_deferred_rows_are_kept_not_dropped():
    # «بِٱلۡغَيۡبِ» و«لِّلۡمُتَّقِينَ»: الحد ملتحم، فتبقى صفوفًا مؤجلة بالسبب
    for w in ('بِٱلۡغَيۡبِ', 'لِّلۡمُتَّقِينَ'):
        rows = T.tags_for_word(w)
        assert rows and all(t[5] == 'DIAGNOSTIC_ONLY' and t[6] in ('MERGED_WITH_FOLLOWING', 'NO_CLEAN_SYLLABLES') for t in rows), w


def test_min_kasra_is_jarr_and_fatha_is_conditional():
    # «مِنَ» بالكسرة جار، و«مَنْ» بالفتحة شرطية: الشكل يميّز الوجه
    jar = [t[2] for t in T.tags_for_word('مِنْ') if t[0] == 'عامل']
    cond = [t[2] for t in T.tags_for_word('مَنْ') if t[0] == 'عامل']
    assert jar and all(c == 'جر' for c in jar)
    assert cond and all('جزم' in c for c in cond)


def test_operand_identity_cells_are_present():
    rows = [t for t in T.tags_for_word('بِمَآ') if t[0] == 'معمول']
    assert rows and rows[0][8] != ''


def test_quranic_small_sukun_counts_as_sukun():
    # «مِنۡ» بالسكون الصغير القرآني تطابق «مِنْ» بالشكل
    assert T.vsig('مِنۡ') == T.vsig('مِنْ')
    assert [t for t in T.tags_for_word('مِنۡ') if t[0] == 'عامل' and t[8] == 'WORD_OPERATOR_VOCALIZED']


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
