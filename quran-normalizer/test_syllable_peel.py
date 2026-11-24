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


def test_positional_sides_for_right_candidate():
    # الطرف الأيسر دائمًا قبل الحد: لـ«هُ» يكون اليسار نَكْتُبُ والمرشح على اليمين
    c = [c for c in _cands('نَكْتُبُهُ') if c['side'] == 'right' and c['detached_text'] == 'هُ'][0]
    assert c['left_syllables'] == ['CVC', 'CV', 'CV'] and c['right_syllables'] == ['CV']


def test_no_affix_class_blocks_detachment():
    # رَيۡبَۛ: كلا الجزأين خارج أبواب التقشير المعتمدة
    res = _cands('رَيۡبَۛ')
    assert res and all(c['final_verdict'] == 'REJECTED' for c in res)
    assert all(c['reason'].startswith('NO_AFFIX_CLASS') for c in res)


def test_gate_switch_is_the_cause():
    # تعطيل البوابة يغيّر حكم رَيۡبَۛ: الرفض سببه البوابة لا الهندسة
    import syllable_peel as S
    S.ELIGIBILITY_GATE = False
    try:
        res = _cands('رَيۡبَۛ')
        assert all(c['final_verdict'] == 'PENDING' for c in res)
    finally:
        S.ELIGIBILITY_GATE = True


def test_kaf_is_pending_not_rejected_without_article():
    # كاف التشبيه صنف مؤهل: لا تُرفض لغياب ال، وتبقى PENDING حتى تُثبت وظيفتها
    for w in ('كَفَرُوا', 'كَمَثَلِ', 'كَصَيِّبٍ'):
        k = [c for c in _cands(w) if c['side'] == 'left' and c['detached_text'] == 'كَ']
        assert k and all(c['final_verdict'] == 'PENDING' for c in k), w
        assert k[0]['reason'].startswith('KAF_FUNCTION_UNPROVEN'), w


def test_residual_is_complement_of_detached():
    for w in ('ٱلۡكِتَٰبُ', 'نَكْتُبُهُ', 'كَمَثَلِ'):
        for c in _cands(w):
            if c['final_verdict'] == 'NO_SYLLABLE_BOUNDARY':
                continue
            assert sorted(c['detached_cells'] + c['residual_cells']) == list(range(len(c['detached_cells']) + len(c['residual_cells']))), w
            assert not set(c['detached_cells']) & set(c['residual_cells']), w


def test_partition_check_rejects_overlap_and_loss():
    import syllable_peel as S
    try:
        S.check_partition(3, [0, 1], [1, 2]); raise AssertionError('يجب أن يفشل التقاطع')
    except ValueError:
        pass
    try:
        S.check_partition(3, [0], [1]); raise AssertionError('يجب أن يفشل الفقد')
    except ValueError:
        pass


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
