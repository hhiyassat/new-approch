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
    b = bare(w)
    if b.startswith('ال') and len(b) > 2:
        return True
    # سابقة واحدة (و، ف، ب، ل، ك) قبل أل
    return len(b) > 3 and b[0] in PREFIX and b[1:3] == 'ال'


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
    ]
    bad = 0
    for ws, want in tests:
        got = tag_nouns(ws)
        ok = got == want
        bad += not ok
        print('OK ' if ok else 'BAD', ws, got, '' if ok else f'(want {want})')
    print('ALL OK' if not bad else f'{bad} FAILURES')
