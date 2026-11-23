# -*- coding: utf-8 -*-
"""
normalize.py (جزء) — ترتيب التوحيد قبل التحليل:
  1) التعريف «ال»: قبل الشمسي تُحذف اللام، قبل القمري تبقى.
  2) الهمزة على الألف: أ/إ → ء مع بقاء حركتها.
  3) الألف الخنجرية: حامل (و/ى) + ٰ → ا (يُحذف الحامل)؛ أي ٰ أخرى → ا (الحامل يبقى).
  4) الشدة: الحرف المشدَّد → حرفان من جنسه: الأول ساكن، والثاني يحمل بقية حركاته.
  5) السكون: السكون الصغير القرآني ۡ (U+06E1) → السكون العادي ْ (U+0652)،
     وكل صامت خالٍ من الحركة يُعدّ ساكناً فيُكتب له ْ.
     مستثنى: الألف بأنواعها، والى (ى) والواو/الياء الممدودتان (حاملات المدّ).
"""
import re
from collections import Counter

LAM = 'ل'
ALIF_FORMS = 'اٱإأآ'   # ا ٱ إ أ آ
SOLAR = set('تثدذرزسشصضطظلن')
DAGGER = 'ٰ'
ALIF = 'ا'
HAMZA = 'ء'
HAMZA_ON_ALIF = 'أإ'                  # أ إ
SHADDA = 'ّ'
FATHA, DAMMA, KASRA = '\u064E', '\u064F', '\u0650'
SUKUN = 'ْ'
SMALL_SUKUN = 'ۡ'                          # ۡ القرآني
CARRIERS = 'وى'                       # و ى
# كل الحركات، بما فيها علامات القرآن الصغيرة U+06D6–U+06ED
MARK_CLASS = 'ً-ٰٟۖ-ۭ'
MARK = '[' + MARK_CLASS + ']'
VOWEL_OR_SUKUN = re.compile('[ً-ْۡ]')   # حركة أو تنوين أو سكون

_PREFIX = '[وفبلك]' + MARK + '*'
_ARTICLE = re.compile(r'(?<!\S)((?:' + _PREFIX + r'){0,2})([' + ALIF_FORMS + r']?)(' + MARK + r'*)' + LAM + MARK + r'*(.)')
_HAMZA_ON_ALIF = re.compile('[' + HAMZA_ON_ALIF + ']')
_CARRIER_DAGGER = re.compile('[' + CARRIERS + ']([ً-ٟ]*)' + DAGGER)
_DAGGER = re.compile(DAGGER)
_LETTER_MARKS = re.compile(r'([^\s' + MARK_CLASS + r'])(' + MARK + r'*)')
_BARE = re.compile(r'([^\s' + MARK_CLASS + r'])(' + MARK + r'*)')
# الحروف التي لا تُكتب لها سكون: الألفات، والى المقصورة
EXEMPT = set(ALIF_FORMS) | {'ى'}


def normalize_article(text, counts=None):
    """«ال» بعد سابقة أو في أول الكلمة: قبل الشمسي تُحذف اللام، قبل القمري تبقى."""
    if counts is None:
        counts = Counter()

    def repl(m):
        prefix, alif, alif_marks, nxt = m.group(1), m.group(2), m.group(3), m.group(4)
        if not prefix and not alif:           # لَن: ليست «ال»
            return m.group(0)
        if nxt in SOLAR:
            counts['ARTICLE_SOLAR_LAM_DELETED'] += 1
            return prefix + alif + alif_marks + nxt
        counts['ARTICLE_MOON_LAM_KEPT'] += 1
        return m.group(0)

    return _ARTICLE.sub(repl, text)


_ALIF_HAMZA = re.compile('\u0627([' + MARK_CLASS + ']*)')


def normalize_alif_hamza(text, counts=None):
    """ا تليها همزة فوق/تحت (في أي ترتيب مع الحركات) → ء مع بقية الحركات."""
    if counts is None:
        counts = Counter()

    def repl(m):
        marks = m.group(1)
        if '\u0654' not in marks and '\u0655' not in marks:
            return m.group(0)
        counts['ALIF_HAMZA_TO_HAMZA'] += 1
        return HAMZA + marks.replace('\u0654', '').replace('\u0655', '')

    return _ALIF_HAMZA.sub(repl, text)


def normalize_silent_waw_alif(text, counts=None):
    """ألف واو الجماعة في آخر الكلمة (كَفَرُواْ، خَلَوۡاْ): الألف صامتة فتُحذف."""
    if counts is None:
        counts = Counter()
    m = re.search('\u0648([' + MARK_CLASS + ']*)\u0627([' + MARK_CLASS + ']*)$', text)
    if m:
        counts['SILENT_WAW_ALIF_DELETED'] += 1
        return text[:m.start()] + '\u0648' + m.group(1) + text[m.end():]
    return text


def normalize_hamza_on_alif(text, counts=None):
    """أ وإ → ء مع بقاء حركتها (أَيُّهَا → ءَيُّهَا)."""
    if counts is None:
        counts = Counter()

    def repl(m):
        counts['HAMZA_ON_ALIF_TO_HAMZA'] += 1
        return HAMZA

    return _HAMZA_ON_ALIF.sub(repl, text)


def normalize_dagger_alif(text, counts=None):
    if counts is None:
        counts = Counter()

    def on_carrier(m):
        j = m.start() - 1
        after_sukun = False
        while j >= 0 and re.match(MARK, m.string[j]):
            if m.string[j] == SUKUN:
                after_sukun = True
            j -= 1
        if m.group(0)[0] == '\u0648' and after_sukun:
            # واو بعد سكون ينطق صامتاً (أَزۡوَٰجࣱ = ءَزْواَجُ): تبقى، وتُكتب الألف بعدها
            counts['DAGGER_WAW_CONSONANT_KEPT'] += 1
            return '\u0648' + ALIF + m.group(1)
        counts['DAGGER_ON_CARRIER_DELETED'] += 1
        return ALIF + m.group(1)

    def plain(m):
        counts['DAGGER_TO_ALIF'] += 1
        return ALIF

    text = _CARRIER_DAGGER.sub(on_carrier, text)
    return _DAGGER.sub(plain, text)


def split_shadda(text, counts=None, mushaf=False):
    """الشدة على الحرف الأول من الكلمة: في المصحف علامة إدغام تُحذف (مِّن → مِن).
    في غيره تُفك الشدة إلى حرفين. وفي سائر المواضع تُفك الشدة دائماً."""
    if counts is None:
        counts = Counter()
    first = next(_LETTER_MARKS.finditer(text), None)
    first_start = first.start() if first else -1

    def repl(m):
        base, marks = m.group(1), m.group(2)
        if SHADDA not in marks:
            return m.group(0)
        rest = marks.replace(SHADDA, '')
        if mushaf and m.start() == first_start:
            counts['IDGHAM_INITIAL_SHADDA_DELETED'] += 1
            return base + rest
        counts['SHADDA_SPLIT'] += 1
        return base + SUKUN + base + rest

    return _LETTER_MARKS.sub(repl, text)


def normalize_sukun(text, counts=None):
    """السكون القرآني → عادي؛ وكل صامت بلا حركة ولا سكون → يُكتب له سكون.
    الواو بعد ضمة والياء بعد كسرة (بلا حركة) مدّ، فتُترك."""
    if counts is None:
        counts = Counter()
    text = text.replace(SMALL_SUKUN, SUKUN)
    units = [[m.group(1), m.group(2)] for m in _BARE.finditer(text)]
    out = []
    prev_vowel = None
    for idx, (base, marks) in enumerate(units):
        next_is_alif = idx + 1 < len(units) and units[idx + 1][0] == ALIF
        if base in EXEMPT:
            out.append(base + marks)
        elif VOWEL_OR_SUKUN.search(marks):
            out.append(base + marks)
        elif base in ('\u0648', '\u064A') and marks == '' and next_is_alif:
            out.append(base + marks)            # واو/ياء صامتة قبل ألف المدّ (وَا)
        elif base == '\u0648' and prev_vowel == DAMMA:
            out.append(base + marks)            # واو المدّ
        elif base == '\u064A' and prev_vowel == KASRA:
            out.append(base + marks)            # ياء المدّ
        else:
            counts['BARE_CONSONANT_SUKUN'] += 1
            out.append(base + marks + SUKUN)
        prev_vowel = next((v for v in (FATHA, DAMMA, KASRA) if v in marks), None)
    return ''.join(out)


# ---------- علامات المصحف ----------
# تُحذف: مدّة فوق الألف، نقطة تحت، ميم سفلية (تجويد)، واوٌ وياءٌ صغيرتان (علامات مدّ)،
# التطويل، المحرف الاتجاهي، ۞ ۩ (تقسيم وسجود)
DELETE_MARKS = '\u0653\u065C\u06ED\u06E5\u06E6\u06E4\u06E7\u06E8\u06EC\u0640\u200F\u06DE\u06E9'
# مستطيل صغير عمودي: الحرف الحامل لا يُنطق فيُهمل مع علامته
SILENT_CARRIER = '\u06E0'
_SILENT_UNIT = re.compile('([^\\s' + MARK_CLASS + '])(' + MARK + '*)')
# علامات الوقف: تُحذف من النص، وتُعلَّم الكلمة بوسم نهاية جملة
WAQF_MARKS = '\u06D6\u06D7\u06D8\u06DA\u06DB\u06DC\u06E2'
# تنوين المصحف المفتوح → التنوين العادي
OPEN_TANWIN = {'\u08F0': '\u064B', '\u08F1': '\u064C', '\u08F2': '\u064D'}
_DELETE = re.compile('[' + DELETE_MARKS + ']')
_WAQF = re.compile('[' + WAQF_MARKS + ']')


def end_tag(word):
    """هل تحمل الكلمة علامة وقف (وسم نهاية جملة)؟"""
    return bool(_WAQF.search(word))


# تطويل حامل لهمزة (ـَٔ): التطويل هنا مقعد الهمزة، فيصير ءً مع حركته.
# الألف التي تليه تُحذف فقط إن تلتها خنجرية، أو ياء بلا مدّ (بلا حركة أو بخنجرية).
_TANWIN_OR_VOWEL = ('\u064E', '\u064F', '\u0650', '\u064B', '\u064C', '\u064D')


def _alif_is_silent(text, k):
    """هل الألف عند الموضع k تُحذف بعد مقعد الهمزة؟"""
    if k >= len(text):
        return False
    if text[k] == DAGGER:
        return True
    if text[k] != '\u064A':                  # ياء
        return False
    k += 1
    marks = ''
    while k < len(text) and re.match(MARK, text[k]):
        marks += text[k]
        k += 1
    return DAGGER in marks or not any(v in marks for v in _TANWIN_OR_VOWEL)


def normalize_hamza_seat(text, counts=None):
    if counts is None:
        counts = Counter()
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != '\u0640':
            out.append(text[i]); i += 1; continue
        j = i + 1
        marks = ''
        while j < n and re.match(MARK, text[j]):
            marks += text[j]; j += 1
        if '\u0654' not in marks:
            i += 1                            # تطويل بلا همزة: يُحذف لاحقاً
            continue
        counts['TATWEEL_HAMZA_SEAT'] += 1
        out.append(HAMZA + marks.replace('\u0654', ''))
        tanwin_fath = '\u064B' in marks          # ـًٔ: الألف المرافقة للتنوين صامتة
        if j < n and text[j] == ALIF and (tanwin_fath or _alif_is_silent(text, j + 1)):
            counts['SEAT_ALIF_DELETED'] += 1
            j += 1
        i = j
    return ''.join(out)


_MADDA_ALIF = re.compile('[\u0627\u0623\u0625]([' + MARK_CLASS + ']*)')


def normalize_madda_alif(text, counts=None):
    """ألف عليها مدّة (أٓ / ٱٓ): تصير ءَ (الهمزة بفتحة، والمدّ يُحذف)."""
    if counts is None:
        counts = Counter()

    def repl(m):
        marks = m.group(1)
        if '\u0653' not in marks:
            return m.group(0)
        counts['MADDA_ALIF_TO_HAMZA_FATHA'] += 1
        kept = ''.join(c for c in marks if c not in '\u0653\u0654\u0655')
        if not any(v in kept for v in '\u064E\u064F\u0650'):
            kept = '\u064E' + kept
        return HAMZA + kept

    return _MADDA_ALIF.sub(repl, text)


def normalize_quran_marks(text, counts=None):
    if counts is None:
        counts = Counter()
    text = normalize_madda_alif(text, counts)
    text = normalize_hamza_seat(text, counts)
    if _WAQF.search(text):
        counts['WAQF_END_TAG'] += 1
    def drop_silent(m):
        if SILENT_CARRIER in m.group(2):
            counts['SILENT_CARRIER_DROPPED'] += 1
            return ''
        return m.group(0)

    text = _SILENT_UNIT.sub(drop_silent, text)
    text = _WAQF.sub('', text)
    n = len(_DELETE.findall(text))
    if n:
        counts['QURAN_MARK_DELETED'] += n
    text = _DELETE.sub('', text)
    text = text.replace(SMALL_SUKUN, SUKUN)
    for k, v in OPEN_TANWIN.items():
        text = text.replace(k, v)
    return text


WASLA = '\u0671'                                  # ٱ
TANWIN_TO_VOWEL = {'\u064B': '\u064E', '\u064C': '\u064F', '\u064D': '\u0650'}   # ً ٌ ٍ → َ ُ ِ


_WASLA_INITIAL = re.compile('(?<!\\S)\u0671([' + MARK_CLASS + ']*)')
_WASLA_MID = re.compile('(?<=\\S)\u0671[' + MARK_CLASS + ']*')


def normalize_wasla(text, counts=None):
    """ٱ في أول الكلمة → ءَ. ٱ داخل الكلمة لا تُغيَّر."""
    if counts is None:
        counts = Counter()

    def repl(m):
        counts['WASLA_TO_HAMZA'] += 1
        after = m.group(1)
        return HAMZA + ('' if after else '\u064E') + after

    text = _WASLA_INITIAL.sub(repl, text)
    n = len(_WASLA_MID.findall(text))
    if n:
        counts['WASLA_MID_DELETED'] += n
    return _WASLA_MID.sub('', text)


def normalize_tanwin(text, counts=None):
    """التنوين حركة التنوين: ً ٌ ٍ → َ ُ ِ (بلا نون)."""
    if counts is None:
        counts = Counter()
    for k, v in TANWIN_TO_VOWEL.items():
        n = text.count(k)
        if n:
            counts['TANWIN_TO_VOWEL'] += n
            text = text.replace(k, v)
    return text


_DIVINE_SKELETON = re.compile(r'^[وفبلك]{0,2}[اٱإأ]?لل[ه]$')


def is_divine(word):
    """لفظ الجلالة (بأي سابقة): لا يُقطَّع ولا يُطبع."""
    skel = re.sub('[' + MARK_CLASS + '\u0640\u200F]', '', word)
    return bool(_DIVINE_SKELETON.match(skel))


def join_split_maqsura(words, counts=None):
    """ى منفصلة عن الكلمة قبلها (هُدࣰ | ى) خطأ في المصدر: تُلحق بها."""
    if counts is None:
        counts = Counter()
    out = []
    for w in words:
        core = re.sub('[' + MARK_CLASS + ']', '', w)
        if out and core == '\u0649':
            counts['SPLIT_MAQSURA_JOINED'] += 1
            out[-1] = out[-1] + w
        else:
            out.append(w)
    return out


def normalize(text, counts=None, mushaf=False):
    if counts is None:
        counts = Counter()
    if is_divine(text):
        counts['DIVINE_NAME_SKIPPED'] += 1
        return None
    text = normalize_quran_marks(text, counts)
    text = normalize_article(text, counts)
    text = normalize_alif_hamza(text, counts)
    text = normalize_wasla(text, counts)
    text = normalize_silent_waw_alif(text, counts)
    text = normalize_hamza_on_alif(text, counts)
    text = normalize_dagger_alif(text, counts)
    text = split_shadda(text, counts, mushaf=mushaf)
    text = normalize_sukun(text, counts)
    return normalize_tanwin(text, counts)


if __name__ == '__main__':
    tests = {
        'ٱلشَّمْسُ': 'ءَشْشَمْسُ',
        'ٱلْقَمَرُ': 'ءَلْقَمَرُ',
        'ٱلرَّحۡمَٰنِ': 'ءَرْرَحْمَانِ',
        'ٱلۡحَمۡدُ': 'ءَلْحَمْدُ',
        'عَلَىٰ': 'عَلَا',
        'الصَّلَوٰةَ': 'اصْصَلَاةَ',
        'ذَٰلِكَ': 'ذَالِكَ',
        'عَلَى': 'عَلَى',
        'يَٰأَيُّهَا': 'يَاءَيْيُهَا',
        'مَدَّ': 'مَدْدَ',
        'رَبٌّ': 'رَبْبُ',
        'إِنَّ': 'ءِنْنَ',
        'حَقّ': 'حَقْقْ',
        'مُّ': 'مْمُ',
        'مِّن': 'مْمِنْ',
    }
    ok = True
    for src, want in tests.items():
        got = normalize(src)
        ok &= got == want
        print('OK ' if got == want else 'BAD', src, '->', got, '' if got == want else f'(want {want})')
    c = Counter()
    normalize('ٱلشَّمْسُ ٱلْقَمَرُ عَلَىٰ الصَّلَوٰةَ يَٰأَيُّهَا', c)
    print(dict(c))
    print('ALL OK' if ok else 'FAILURES')
