# -*- coding: utf-8 -*-
"""
تصنيف مشتق/مبني من أشكال المقاطع:
  الكلمة مشتقة إذا احتوى شكلها الصوتي على صامتين متتاليين (CC)، وإلا فهي مبنية.
  الشكل الصوتي = تسلسل C/V من أشكال المقاطع بالترتيب (VV تُعدّ حركتين).
"""


def skeleton(shapes):
    """أشكال المقاطع ← تسلسل C و V."""
    sk = []
    for sh in shapes:
        for ch in sh:
            sk.append('C' if ch == 'C' else 'V')
    return ''.join(sk)


def classify(shapes):
    return 'مشتق' if 'CC' in skeleton(shapes) else 'مبني'


if __name__ == '__main__':
    cases = [
        (['CVC'], 'مبني', 'مِن'),
        (['CV', 'CVV'], 'مبني', 'هَذَا'),
        (['CV', 'CV', 'CV'], 'مبني', 'كَتَبَ'),
        (['CVC', 'CV'], 'مشتق', 'بِسْمِ'),
        (['CVCC'], 'مشتق', 'حَقْقْ'),
        (['CVVC', 'CV'], 'مشتق', 'ءِنْنَ'),
        (['CVC', 'CVC', 'CV', 'CV'], 'مشتق', 'ٱلْحَمْدُ'),
    ]
    bad = 0
    for shapes, want, word in cases:
        got = classify(shapes)
        ok = got == want
        bad += not ok
        print('OK ' if ok else 'BAD', word, shapes, '->', got, '' if ok else f'(want {want})')
    print('ALL OK' if not bad else f'{bad} FAILURES')
