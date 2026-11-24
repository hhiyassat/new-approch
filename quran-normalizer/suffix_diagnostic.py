# -*- coding: utf-8 -*-
"""
تشخيص لاحقة النهاية: ترشيح داخل التمثيل دون تنفيذ فصل.

الحالات المنفصلة في المخرج:
  ORTHOGRAPHIC_ENDING   : النهاية الكتابية «وا» (مطابقة نصية فقط، لا تسمّى واو جماعة)
  REPRESENTATION_CANDIDATE: خلية المد تحمل الواو الممدودة والألف الصامتة (إحالة، لا نسخ ولا حذف)
  LICENSED_SUFFIX       : دائمًا لا شيء هنا (لا شهادة بعد)
  EXECUTED_CUT          : دائمًا لا شيء هنا (لا فصل منفّذ)
ولا يغيّر هذا الملف نموذج الخلايا ولا سياسة حدود المقاطع.
"""
from gate import build_cells, MARKCHARS, TATWEEL, WAQF, NON_PHONETIC


def _orth_skeleton(word):
    return ''.join(ch for ch in word if ch not in MARKCHARS and ch not in {TATWEEL, '\u200f'}
                   and ch not in set(WAQF) and ch not in set(NON_PHONETIC) and not ch.isspace())


def labels(orth_end, rep):
    return dict(
        ending='ORTHOGRAPHIC_WAW_ALIF_ENDING' if orth_end else 'NO_ENDING_MATCH',
        representation='REPRESENTATION_CANDIDATE' if rep else 'NONE',
        license='NOT_LICENSED',
        cut='NOT_EXECUTED',
    )


def diagnose(word):
    orth = _orth_skeleton(word)
    try:
        cells = build_cells(word)
    except ValueError as e:
        return dict(word=word, status='UNSUPPORTED_GLYPH', orthographic_ending=orth.endswith('وا'),
                    representation_candidate=False, madd_owner_cell=None, owner_type=None,
                    licensed_suffix=False, executed_cut=False, note=str(e)[:80])
    owner, owner_type = None, None
    for c in cells:
        if 'SILENT_ALIF_WAW_PLURAL' not in c.flags:
            continue
        if 'MADD_و' in c.flags:
            owner, owner_type = c.idx, 'MADD_ON_PREVIOUS_CELL'      # الواو ممدودة داخل خلية سابقة
        else:
            owner, owner_type = c.idx, 'STANDALONE_WAW_CELL'        # الواو خلية مستقلة ساكنة (علامة المدة فوقها)
    return dict(
        word=word,
        status='OK',
        orthographic_ending=orth.endswith('وا'),
        representation_candidate=owner is not None,
        madd_owner_cell=owner,
        owner_type=owner_type,
        licensed_suffix=False,
        executed_cut=False,
        note='',
        labels=labels(orth.endswith('وا'), owner is not None),
    )


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:]:
        print(diagnose(w))
