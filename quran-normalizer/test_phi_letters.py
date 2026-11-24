# -*- coding: utf-8 -*-
"""اختبار قاعدة φ: ئ و اْ تُحذف مع حركتهما عند فشل البناء فقط، ولا يقبل النموذج الصورة الأصلية، وما لا يُعالَج يبقى فشلًا ظاهرًا."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate import build_cells
import check_operator_rows as C

L = C.load_phi()

def test_gate_still_rejects_original_forms():
    for w in ('مِاْئَةَ', 'مِئَةَ'):
        try:
            build_cells(w)
        except ValueError:
            continue
        raise AssertionError(f'النموذج يجب ألا يبني {w} مباشرة')

def test_stripped_forms_build_and_match_skeleton():
    assert C.strip_phi('مِاْئَةَ', L) == C.strip_phi('مِئَةَ', L) == 'مِةَ'
    assert len(build_cells(C.strip_phi('مِاْئَةَ', L))) == 2
    assert len(build_cells(C.strip_phi('مِاْئَتَيۡنِۚ', L))) == 4

def test_decomposed_hamza_on_yaa_is_stripped():
    dec = 'مِا\u0652\u064a\u064e\u0654\u0629\u0650'   # م ِ ا ْ ي َ ٔ ة ِ
    assert C.strip_phi(dec, L) == 'مِةِ'

def test_word_equivalence_is_only_for_its_word():
    used = []
    cells = C.cells_for('مَجۡرٜىٰهَا', L, C.load_subs(), used)
    assert len(cells) == len(build_cells('مَجۡرِىهَا')) == 4
    assert used == [('مَجۡرٜىٰهَا', 'مَجۡرِىهَا')]
    try:
        C.cells_for('مَجۡرىٰهَا', L, C.load_subs(), [])   # كلمة أخرى لا تنالها القاعدة
    except ValueError:
        return
    raise AssertionError('التكافؤ لا يُعمَّم على كلمات أخرى')

def test_tagger_reads_phi_form_the_same_way():
    import operator_tags as O
    ids, ok = O._cell_ids('مِاْئَةِ')
    assert ok and len(ids.split()) == 2
    ids2, ok2 = O._cell_ids('مَجۡرٜىٰهَا')
    assert ok2 and len(ids2.split()) == 4

def test_unlisted_failure_stays_visible():
    used = []
    try:
        C.cells_for('مَجۡرٜىٰهَا', L, {}, used)   # بلا استبدال ى→ي يبقى الفشل ظاهرًا
    except ValueError:
        assert used == []
        return
    raise AssertionError('حرف غير مدعوم لا يُعالج بالحذف، ويجب أن يبقى ظاهرًا')

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
