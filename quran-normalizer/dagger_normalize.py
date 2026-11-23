# -*- coding: utf-8 -*-
"""
توحيد النص قبل التحليل (وضع المصحف وغيره).

ترتيب المراحل في normalize():
  1. علامات المصحف            normalize_quran_marks
  2. «ال»                     normalize_article
  3. همزة على الألف           normalize_alif_hamza
  4. ٱ الوصل                  normalize_wasla
  5. ألف واو الجماعة          normalize_silent_waw_alif
  6. أ/إ → ء                   normalize_hamza_on_alif
  7. الألف الخنجرية           normalize_dagger_alif
  8. الشدة                    split_shadda
  9. السكون                   normalize_sukun
 10. التنوين → حركته          normalize_tanwin

لفظ الجلالة والحروف المقطعة لا تُطبَّع (normalize تعيد None لها).
"""
import re
from collections import Counter

# ---------------------------------------------------------------- الثوابت
ALIF = '\u0627'
HAMZA = '\u0621'
LAM = '\u0644'
DAGGER = '\u0670'
SHADDA = '\u0651'
SUKUN = '\u0652'
SMALL_SUKUN = '\u06E1'              # ۡ القرآني
FATHA, DAMMA, KASRA = '\u064E', '\u064F', '\u0650'
TATWEEL = '\u0640'
RLM = '\u200F'
TANWIN_FATH = '\u064B'

ALIF_FORMS = '\u0627\u0671\u0625\u0623\u0622'   # ا ٱ إ أ آ
HAMZA_ON_ALIF = '\u0623\u0625'                  # أ إ
CARRIERS = '\u0648\u0649'                       # و ى
SOLAR = set('تثدذرزسشصضطظلن')
RELATIVE_PRONOUNS = {'الذي', 'الذين', 'التي', 'اللذان', 'اللذين', 'اللتان', 'اللتين',
                    'اللاتي', 'اللواتي', 'اللائي', 'الذا', 'الذى'}
MUQATTAAT = {'حم', 'طسم', 'الم', 'الر', 'المر', 'المص', 'كهيعص', 'طه', 'يس', 'طس',
             'ص', 'ق', 'ن', 'عسق'}

# كل الحركات، بما فيها علامات القرآن الصغيرة U+06D6–U+06ED
MARK_CLASS = '\u064B-\u065F\u0670\u06D6-\u06ED'
MARK = '[' + MARK_CLASS + ']'
BASE = '[^\\s' + MARK_CLASS + ']'               # حرف أساسي
VOWEL_OR_SUKUN = re.compile('[\u064B-\u0652\u06E1]')

# علامات تُحذف من النص
DELETE_MARKS = '\u0653\u065C\u06ED\u06E5\u06E6\u06E4\u06E7\u06E8\u06EC\u0640\u200F\u06DE\u06E9'
SILENT_CARRIER = '\u06E0'                       # الحامل معه لا يُنطق
WAQF_MARKS = '\u06D6\u06D7\u06D8\u06DA\u06DB\u06DC\u06E2'   # تُحذف وتُعلَّم بوسم نهاية جملة
OPEN_TANWIN = {'\u08F0': '\u064B', '\u08F1': '\u064C', '\u08F2': '\u064D'}
TANWIN_TO_VOWEL = {'\u064B': FATHA, '\u064C': DAMMA, '\u064D': KASRA}

_DELETE = re.compile('[' + DELETE_MARKS + ']')
_WAQF = re.compile('[' + WAQF_MARKS + ']')
_SILENT_UNIT = re.compile('(' + BASE + ')(' + MARK + '*)')

# ---------------------------------------------------------------- الأنماط
_ARTICLE_PREFIX = '(?:[وفبلك]' + MARK + '*|ء' + MARK + '*(?=[ا]))'
_ARTICLE = re.compile(
    r'(?<!\S)((?:' + _ARTICLE_PREFIX + r'){0,2})([' + ALIF_FORMS + r']?)(' + MARK + r'*)'
    + LAM + MARK + r'*(.)')
_ALIF_HAMZA = re.compile(ALIF + '(' + MARK + '*)')
_HAMZA_ON_ALIF = re.compile('[' + HAMZA_ON_ALIF + ']')
_WASLA_INITIAL = re.compile('(?<!\\S)\u0671(' + MARK + '*)')
_WASLA_MID = re.compile('(?<=\\S)\u0671' + MARK + '*')
_CARRIER_DAGGER = re.compile('[' + CARRIERS + ']([\u064B-\u065F]*)' + DAGGER)
_DAGGER = re.compile(DAGGER)
_LETTER_MARKS = re.compile('(' + BASE + ')(' + MARK + '*)')
_MADDA_ALIF = re.compile('[\u0627\u0623\u0625](' + MARK + '*)')
_IDGHAM_SUKUN_CLOSE_PAIR = re.compile('([تد])[' + SMALL_SUKUN + SUKUN + ']([تد])(?=' + MARK + '*' + SHADDA + ')')
_IDGHAM_BARE_PAIR = re.compile('([تد])(?!' + MARK + ')([تد])(?=' + MARK + '*' + SHADDA + ')')
_INITIAL_LAM = re.compile('(?<!\\S)' + LAM + '[' + SMALL_SUKUN + SUKUN + '](' + TATWEEL + ')?')
_SAME_LETTER_SHADDA = re.compile('(' + BASE + ')' + SUKUN + '?(?=\\1' + MARK + '*' + SHADDA + ')')
_SAME_LETTER_SUKUN = re.compile('(' + BASE + ')' + SUKUN + '(?=\\1' + SUKUN + ')')
_SILENT_ALIF_BEFORE_HAMZA = re.compile(ALIF + SUKUN + '(?=\u0626|\u064A' + MARK + '*[\u0621\u0654])')
_CAR_WAW_DAGGER_END = re.compile('\u0648' + DAGGER + '(' + MARK + '*)' + ALIF + '(' + MARK + '*)$')
_CAR_WAW_END = re.compile('\u0648(' + MARK + '*)' + ALIF + '(' + MARK + '*)$')
_TATWEEL_SEAT = re.compile(TATWEEL + '(' + MARK + '*)')
_DIVINE = re.compile(r'^[وفبلكت]{0,2}[ءاٱإأآ]{0,2}لل[ه]$')

EXEMPT = set(ALIF_FORMS) | {'\u0649'}
_TANWIN_OR_VOWEL = (FATHA, DAMMA, KASRA, '\u064B', '\u064C', '\u064D')


# ---------------------------------------------------------------- المراحل
def normalize_article(text, counts):
    """«ال» بعد سابقة أو في أول الكلمة: قبل الشمسي تُحذف اللام، قبل القمري تبقى."""
    if _skeleton(text).replace('ٱ', 'ا').replace('إ', 'ا').replace('أ', 'ا') in RELATIVE_PRONOUNS:
        counts['ARTICLE_EXCEPTION_RELATIVE'] += 1     # الذي: اسم موصول، لا «ال» تعريف
        return text
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


def normalize_alif_hamza(text, counts):
    """ا تليها همزة فوق/تحت (في أي ترتيب مع الحركات) → ء مع بقية الحركات."""
    def repl(m):
        marks = m.group(1)
        if '\u0654' not in marks and '\u0655' not in marks:
            return m.group(0)
        counts['ALIF_HAMZA_TO_HAMZA'] += 1
        return HAMZA + marks.replace('\u0654', '').replace('\u0655', '')
    return _ALIF_HAMZA.sub(repl, text)


def normalize_wasla(text, counts):
    """ٱ في أول الكلمة → ءَ. ٱ داخل الكلمة تُحذف."""
    def repl(m):
        counts['WASLA_TO_HAMZA'] += 1
        after = m.group(1)
        return HAMZA + ('' if after else FATHA) + after
    text = _WASLA_INITIAL.sub(repl, text)
    n = len(_WASLA_MID.findall(text))
    if n:
        counts['WASLA_MID_DELETED'] += n
    return _WASLA_MID.sub('', text)


def normalize_silent_waw_alif(text, counts):
    """ألف واو الجماعة في آخر الكلمة (كَفَرُواْ، خَلَوۡاْ) صامتة فتُحذف."""
    m0 = _CAR_WAW_DAGGER_END.search(text)
    if m0:
        counts['WAW_DAGGER_SILENT_ALIF_END'] += 1
        return text[:m0.start()] + ALIF
    m = _CAR_WAW_END.search(text)
    if m:
        counts['SILENT_WAW_ALIF_DELETED'] += 1
        return text[:m.start()] + '\u0648' + m.group(1) + text[m.end():]
    return text


def normalize_hamza_on_alif(text, counts):
    """أ وإ → ء مع بقاء حركتها (أَيُّهَا → ءَيُّهَا)."""
    def repl(m):
        counts['HAMZA_ON_ALIF_TO_HAMZA'] += 1
        return HAMZA
    return _HAMZA_ON_ALIF.sub(repl, text)


def normalize_dagger_alif(text, counts):
    """الألف الخنجرية: حامل (و/ى) + ٰ → ا؛ الواو الصامتة (بعد سكون أو مدّ، أو غير متبوعة بتاء مربوطة) تبقى."""
    def on_carrier(m):
        j = m.start() - 1
        after_sukun = after_long = False
        while j >= 0 and re.match(MARK, m.string[j]):
            if m.string[j] == SUKUN:
                after_sukun = True
            if m.string[j] == DAGGER:
                after_long = True
            j -= 1
        k = m.end()
        while k < len(m.string) and re.match(MARK, m.string[k]):
            k += 1
        followed_by_taa = k < len(m.string) and m.string[k] == '\u0629'
        if m.group(0)[0] == '\u0648' and not followed_by_taa:
            counts['DAGGER_WAW_CONSONANT_KEPT'] += 1
            return '\u0648' + (m.group(1) or FATHA) + ALIF
        counts['DAGGER_ON_CARRIER_DELETED'] += 1
        return ALIF + m.group(1)

    def plain(m):
        counts['DAGGER_TO_ALIF'] += 1
        return ALIF

    text = _CARRIER_DAGGER.sub(on_carrier, text)
    return _DAGGER.sub(plain, text)


def split_shadda(text, counts, mushaf=False):
    """الشدة: في المصحف على أول الكلمة علامة إدغام تُحذف؛ وفي غيرها تُفكّ إلى حرفين."""
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


def normalize_sukun(text, counts):
    """السكون القرآني → عادي؛ كل صامت بلا حركة ولا سكون يُكتب له سكون.
    الألف والى مستثنيتان، والواو بعد ضمة والياء بعد كسرة مدّ، والصامت قبل ألف يأخذ فتحة."""
    text = text.replace(SMALL_SUKUN, SUKUN)
    units = [(m.group(1), m.group(2)) for m in _LETTER_MARKS.finditer(text)]
    out = []
    prev_vowel = None
    for idx, (base, marks) in enumerate(units):
        next_is_alif = idx + 1 < len(units) and units[idx + 1][0] == ALIF
        if base in EXEMPT or VOWEL_OR_SUKUN.search(marks):
            out.append(base + marks)
        elif marks == '' and next_is_alif:
            out.append(base + FATHA)
        elif base == '\u0648' and prev_vowel == DAMMA:
            out.append(base + marks)
        elif base == '\u064A' and prev_vowel == KASRA:
            out.append(base + marks)
        else:
            counts['BARE_CONSONANT_SUKUN'] += 1
            out.append(base + marks + SUKUN)
        prev_vowel = next((v for v in (FATHA, DAMMA, KASRA) if v in marks), None)
    return ''.join(out)


def normalize_tanwin(text, counts):
    """التنوين حركة التنوين: ً ٌ ٍ → َ ُ ِ."""
    for k, v in TANWIN_TO_VOWEL.items():
        n = text.count(k)
        if n:
            counts['TANWIN_TO_VOWEL'] += n
            text = text.replace(k, v)
    return text


# ---------------------------------------------------------------- مراحل المصحف
def _seat_alif_silent(text, k):
    """هل الألف عند k تُحذف بعد مقعد الهمزة؟"""
    if k >= len(text):
        return False
    if text[k] == DAGGER:
        return True
    if text[k] != '\u064A':
        return False
    k += 1
    marks = ''
    while k < len(text) and re.match(MARK, text[k]):
        marks += text[k]
        k += 1
    return DAGGER in marks or not any(v in marks for v in _TANWIN_OR_VOWEL)


def normalize_hamza_seat(text, counts):
    """التطويل الحامل لهمزة (ـَٔ) يصير ءً مع حركته؛ الألف بعده تُحذف إن كانت صامتة."""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != TATWEEL:
            out.append(text[i]); i += 1; continue
        j = i + 1
        marks = ''
        while j < n and re.match(MARK, text[j]):
            marks += text[j]; j += 1
        if '\u0654' not in marks:
            i += 1
            continue
        counts['TATWEEL_HAMZA_SEAT'] += 1
        out.append(HAMZA + marks.replace('\u0654', ''))
        tanwin_fath = TANWIN_FATH in marks
        if j < n and text[j] == ALIF and (tanwin_fath or _seat_alif_silent(text, j + 1)):
            counts['SEAT_ALIF_DELETED'] += 1
            j += 1
        i = j
    return ''.join(out)


def normalize_madda_alif(text, counts):
    """ألف عليها مدّة (أٓ): تصير ءَ."""
    def repl(m):
        marks = m.group(1)
        if '\u0653' not in marks:
            return m.group(0)
        counts['MADDA_ALIF_TO_HAMZA_FATHA'] += 1
        kept = ''.join(c for c in marks if c not in '\u0653\u0654\u0655')
        if not any(v in kept for v in (FATHA, DAMMA, KASRA)):
            kept = FATHA + kept
        return HAMZA + kept
    return _MADDA_ALIF.sub(repl, text)


def _idgham_pairs(text, counts):
    """إدغام ت/د: الأول ساكناً (صريحاً أو بلا علامة) قبل مشددة من الآخر تُدغم."""
    def sub(m):
        a, b = m.group(1), m.group(2)
        if a == b:
            return m.group(0)
        counts['IDGHAM_SUKUN_CLOSE' if m.group(0)[1] in (SMALL_SUKUN, SUKUN) else 'IDGHAM_BARE_CLOSE'] += 1
        return b
    text = _IDGHAM_SUKUN_CLOSE_PAIR.sub(sub, text)
    return _IDGHAM_BARE_PAIR.sub(sub, text)


def normalize_quran_marks(text, counts):
    text = _INITIAL_LAM.sub(
        lambda m: LAM + (FATHA if m.group(1) else KASRA) + (m.group(1) or ''), text)
    text = _idgham_pairs(text, counts)
    text = text.replace('\u0622', ALIF)
    text = normalize_madda_alif(text, counts)
    text = normalize_hamza_seat(text, counts)
    if _WAQF.search(text):
        counts['WAQF_END_TAG'] += 1
    text = _SILENT_UNIT.sub(_drop_silent(counts), text)
    text = _WAQF.sub('', text)
    n = len(_DELETE.findall(text))
    if n:
        counts['QURAN_MARK_DELETED'] += n
    text = _DELETE.sub('', text)
    text = text.replace(SMALL_SUKUN, SUKUN)
    text = _SAME_LETTER_SHADDA.sub('', text)
    text = _SAME_LETTER_SUKUN.sub('', text)
    text = _SILENT_ALIF_BEFORE_HAMZA.sub('', text)
    for k, v in OPEN_TANWIN.items():
        text = text.replace(k, v)
    return text


def _drop_silent(counts):
    def repl(m):
        if SILENT_CARRIER in m.group(2):
            counts['SILENT_CARRIER_DROPPED'] += 1
            return ''
        return m.group(0)
    return repl


# ---------------------------------------------------------------- واجهة عامة
def end_tag(word):
    """هل تحمل الكلمة علامة وقف (وسم نهاية جملة)؟"""
    return bool(_WAQF.search(word))


def _skeleton(word):
    return re.sub('[' + MARK_CLASS + TATWEEL + RLM + ']', '', word)


def is_divine(word):
    """لفظ الجلالة بأي سابقة: لا يُقطَّع ولا يُطبع."""
    return bool(_DIVINE.match(_skeleton(word)))


def is_constant(word):
    """الحروف المقطعة في أوائل السور: ثوابت لا تُقطَّع ولا تُطبع."""
    return _skeleton(word) in MUQATTAAT


def join_split_maqsura(words, counts=None):
    """ى منفصلة عن الكلمة قبلها (هُدࣰ | ى) خطأ في المصدر: تُلحق بها."""
    counts = Counter() if counts is None else counts
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
    """يعيد النص الموحَّد، أو None للفظ الجلالة (مستثنى). الحروف المقطعة لا تُستثنى."""
    counts = Counter() if counts is None else counts
    if is_divine(text):
        counts['DIVINE_NAME_SKIPPED'] += 1  # لفظ الجلالة: لا يُطبَّع ولا يُقطَّع
        return None
    if is_constant(text):
        counts['MUQATTAAT'] += 1            # لا تُستثنى: تُطبَّع وتُقطَّع مثل غيرها
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


_SELF_TESTS = {
    'ٱلشَّمْسُ': 'ءَشْشَمْسُ', 'ٱلْقَمَرُ': 'ءَلْقَمَرُ', 'ٱلرَّحۡمَٰنِ': 'ءَرْرَحْمَانِ',
    'ٱلۡحَمۡدُ': 'ءَلْحَمْدُ', 'عَلَىٰ': 'عَلَا', 'الصَّلَوٰةَ': 'اصْصَلَاةَ',
    'ذَٰلِكَ': 'ذَالِكَ', 'عَلَى': 'عَلَى', 'يَٰأَيُّهَا': 'يَاءَيْيُهَا',
    'سَمَٰوَٰتࣲ': 'سَمَاوَاتِ', 'صَلَوٰةَ': 'صَلَاةَ', 'أَزۡوَٰجࣱ': 'ءَزْوَاجُ',
    'ٱلصَّوَٰعِقِ': 'ءَصْصَوَاعِقِ', 'مِاْئَةَ': 'مِئَةَ', 'مَدَّ': 'مَدْدَ',
    'رَبٌّ': 'رَبْبُ', 'إِنَّ': 'ءِنْنَ', 'حَقّ': 'حَقْقْ', 'مُّ': 'مُ', 'مِّن': 'مِنْ',
}

if __name__ == '__main__':
    failed = 0
    for src, want in _SELF_TESTS.items():
        got = normalize(src, mushaf=True)
        if got != want:
            failed += 1
        print('OK ' if got == want else 'BAD', src, '->', got, '' if got == want else f'(want {want})')
    print('ALL OK' if failed == 0 else f'{failed} FAILURES')
