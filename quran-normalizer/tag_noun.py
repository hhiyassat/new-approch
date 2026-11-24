# -*- coding: utf-8 -*-
"""
وسم الاسم (مرحلة بعد التصنيف):
  تُوسم الكلمة «اسماً» إذا:
    1) بدأت بأل التعريف (ال / ٱل)، أو بسابقة عطف/جر قبلها أل (وَٱلـ، فَٱلـ، بِٱلـ، لِلـ، كَٱلـ)،
    2) أو سبقها حرف جر مستقل في الجملة.
  وما عدا ذلك لا يُوسم اسماً بهذه المرحلة.
"""
import re

MK = re.compile('[ً-ٰٟـۖ-ࣰۭ-ࣲ‏]')
JARR = {'من', 'إلى', 'عن', 'على', 'في', 'رب', 'حتى', 'مذ', 'منذ', 'خلا', 'حاشا', 'عدا', 'ب', 'ل', 'ك'}
PREFIX = {'و', 'ف', 'ب', 'ل', 'ك'}


def bare(w):
    s = MK.sub('', w or '')
    return s.replace('ٱ', 'ا').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ـ', '').strip()


def starts_with_article(w):
    """أل التعريف في أول الكلمة، أو بعد سابقة أو سابقتين (وَ، فَ، بِ، لِ، كَ، وَبِ، فَبِ، وَكَ...).
    ويشمل لِلـ: اللام الجارة ثم لام التعريف المدغمة."""
    b = bare(w)
    for k in (0, 1, 2):
        if len(b) > k + 2 and all(c in PREFIX for c in b[:k]) and b[k:k + 2] == 'ال':
            return True
    # لِلـ: لام جارة ثم لام (لام التعريف مع الحرف الشمسي مكتوبة بالشدة)
    if len(b) > 2 and b[0] == 'ل' and b[1] == 'ل':
        return True
    return False


def tag_nouns(words):
    """قائمة كلمات ← قائمة أوسمة: 'اسم' أو ''."""
    tags = []
    for i, w in enumerate(words):
        prev = bare(words[i - 1]) if i > 0 else ''
        if starts_with_article(w) or (prev and prev in JARR):
            tags.append('اسم')
        else:
            tags.append('')
    return tags


if __name__ == '__main__':
    tests = [
        (['ٱلشَّمْسُ'], ['اسم']),
        (['وَٱلنَّاسِ'], ['اسم']),
        (['بِٱللَّهِ'], ['اسم']),
        (['فِي', 'ٱلۡأَرۡضِ'], ['', 'اسم']),
        (['مِنَ', 'ٱلنَّاسِ'], ['', 'اسم']),
        (['يَعۡلَمُونَ'], ['']),
        (['كَتَبَ', 'زَيۡدٌ'], ['', '']),
        (['وَبِٱللَّهِ'], ['اسم']),
        (['فَبِٱلۡحَقِّ'], ['اسم']),
        (['لِلنَّاسِ'], ['اسم']),
        (['كَٱلَّذِي'], ['اسم']),
        (['وَٱلَّذِينَ'], ['اسم']),
        (['لِيَقۡطَعۡ'], ['']),
        (['بِيَدِهِ'], ['']),
    ]
    bad = 0
    for ws, want in tests:
        got = tag_nouns(ws)
        ok = got == want
        bad += not ok
        print('OK ' if ok else 'BAD', ws, got, '' if ok else f'(want {want})')
    print('ALL OK' if not bad else f'{bad} FAILURES')
