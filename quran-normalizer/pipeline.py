# -*- coding: utf-8 -*-
"""
خط المعالجة: النص المكتوب → الخلايا → المقاطع → الفحوص → التصنيف (مشتق/مبني).
المشتق والمبني يُحسبان بعد التقطيع فقط، ولا يدخلان في أي مرحلة قبله.
"""
from gate import build_cells, syllabify
from classify_derived import classify


def stage_cells(word):
    """النص المكتوب ← خلايا الحرف والحركة (يرفع ValueError على رمز غير مدعوم)."""
    return build_cells(word)


def stage_syllables(cells):
    """الخلايا ← المقاطع مع حدودها، والبقايا غير المقطّعة."""
    return syllabify(cells)


def stage_checks(sylls, residue):
    """الفحوص: كل مقطع مرخّص، ولا بقايا. تُعيد قائمة الأخطاء (فارغة إن نجحت)."""
    errors = [f'بقية: {t[1]}' for t in residue]
    errors += [f"{s['shape']}: {s['reason']}" for s in sylls if not s['valid']]
    return errors


def stage_classify(sylls):
    """بعد التقطيع فقط: مشتق إذا احتوى الشكل صامتين متتاليين، وإلا مبني."""
    return classify([s['shape'] for s in sylls])


def run(word):
    cells = stage_cells(word)
    sylls, residue = stage_syllables(cells)
    errors = stage_checks(sylls, residue)
    result = {'word': word, 'shapes': [s['shape'] for s in sylls], 'errors': errors}
    if errors:
        result['status'] = 'REJECTED'
        return result
    result['status'] = 'OK'
    result['kind'] = stage_classify(sylls)
    return result


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:] or ['مِن']:
        print(run(w))
