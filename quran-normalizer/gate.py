# -*- coding: utf-8 -*-
"""
بوابة العوامل والمبنيات (SLG/NABT) على النص المكتوب:
  الخلايا المكتوبة → المقاطع المرخّصة → تركيب المقاطع وحدّها → الوجوه → شاهد التعيين → الحكم.

المصدر الوحيد لكل شيء في هذه الوحدة:
  - تعريف الخلية وترقيمها:         CARRIERS, MARK_INDEX, atom()
  - أشكال المقاطع وقواعد الحد:      SIX, FINAL_ONLY, syllabify()
  - المرشحون والشواهد:              LEXICON (بذرة من قائمة الاختبارات، غير مستنفدة)
  - القرار:                         decide()

المدخل النص المكتوب كما هو. لا تُسقط همزة وصل ولا لام، ولا تُضاف حركة غير مكتوبة
دون وسمها UNMARKED. النطق المشتق في normalize() لا يدخل هنا.
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------- الخلايا
CARRIERS = 'ءبتثجحخدذرزسشصضطظعغفقكلمنهوية'      # 29 حاملاً (الألف حرف مدّ لا حامل)
assert len(CARRIERS) == 29
FATHA, DAMMA, KASRA, SUKUN = 'َ', 'ُ', 'ِ', 'ْ'
MARK_INDEX = {FATHA: 0, DAMMA: 1, KASRA: 2, SUKUN: 3}   # الحالات الأربع
VOWEL_OF = {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}
TANWIN_OF = {'ً': 'a', 'ٌ': 'u', 'ٍ': 'i'}
SHADDA, DAGGER, SMALL_SUKUN = 'ّ', 'ٰ', 'ۡ'
MARKCHARS = set(MARK_INDEX) | set(TANWIN_OF) | {SHADDA, DAGGER, SMALL_SUKUN}
ALIF = 'ا'
WASLA = 'ٱ'
HAMZA_ALIF = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء'}
MADD_OF = {'و': 'u', 'ي': 'i'}                              # حرف المدّ بعد الحركة المطابقة


def atom(carrier, state):
    """منظومة 116: 4·c + m، حيث c فهرس الحامل وm حالة الحركة."""
    return 4 * CARRIERS.index(carrier) + state


@dataclass
class Cell:
    idx: int
    carrier: str
    vowel: str = None           # a / u / i أو None
    sukun: bool = False
    long: int = 0               # 2 إذا كان معها مدّ مكتوب
    shadda: str = None          # 'first' / 'second' إذا نتجت عن فكّ شدة
    tanwin: bool = False
    span: tuple = (0, 0)        # موضع الحرف في النص الأصلي
    flags: list = field(default_factory=list)

    @property
    def atom(self):
        if self.vowel:
            return atom(self.carrier, MARK_INDEX[{'a': FATHA, 'u': DAMMA, 'i': KASRA}[self.vowel]])
        return atom(self.carrier, MARK_INDEX[SUKUN])

    def identity(self):
        return (self.carrier, self.vowel, self.sukun, self.long)


def build_cells(word):
    """النص المكتوب → خلايا. يرفع خطأ على أي رمز غير معروف (لا تخمين)."""
    cells, i, n = [], 0, len(word)
    while i < n:
        ch = word[i]
        if ch in MADD_OF and i + 1 <= n:
            # واو/ياء بلا حركة بعد الحركة المطابقة = مدّ
            nxt_marks = _marks_after(word, i + 1)[0]
            if not nxt_marks and cells and cells[-1].vowel == MADD_OF[ch] and not cells[-1].long:
                cells[-1].long = 2
                cells[-1].flags.append('MADD_' + ch)
                i += 1
                continue
        if ch == ALIF or ch == DAGGER:
            if cells and cells[-1].vowel == 'a' and not cells[-1].long:
                cells[-1].long = 2
                cells[-1].flags.append('MADD_ALIF')
                i += 1
                continue
            if not cells and ch == ALIF:
                # ألف مكتوبة في أول الكلمة (ال، ا...): حامل ء بفتحة مستنتجة، موسومة
                c = Cell(0, 'ء', vowel='a', span=(i, i + 1))
                c.flags += ['ALIF_INITIAL', 'INFERRED_VOWEL']
                cells.append(c)
                i += 1
                continue
            raise ValueError(f'ألف بلا حامل عند الموضع {i} في {word!r}')
        if ch == WASLA or ch in HAMZA_ALIF:
            carrier = 'ء'
            marks, j = _marks_after(word, i + 1)
            c = _cell_from_marks(len(cells), carrier, marks, (i, j))
            c.flags.append('WASLA' if ch == WASLA else 'HAMZA_ON_ALIF')
            if ch == WASLA and not cells and not marks:
                # همزة الوصل في أول الكلمة بلا حركة مكتوبة: الحركة مستنتجة وموسومة
                # (فتحة مع «ال»، وكسرة في غيرها)، والصامت لا يبقى بلا مقطع
                c.vowel = 'a' if word.startswith('ٱل') else 'i'
                c.sukun = False
                c.flags = [f for f in c.flags if f != 'UNMARKED'] + ['INFERRED_VOWEL']
            if ch == 'آ':
                c.long = 2
                c.flags.append('MADDA')
            cells.append(c)
            i = j
            continue
        if ch in CARRIERS:
            marks, j = _marks_after(word, i + 1)
            if SHADDA in marks:
                first = Cell(len(cells), ch, sukun=True, shadda='first', span=(i, j))
                rest = [m for m in marks if m != SHADDA]
                second = _cell_from_marks(len(cells) + 1, ch, rest, (i, j))
                second.shadda = 'second'
                second.flags.append('SHADDA_SPLIT')
                cells += [first, second]
            else:
                cells.append(_cell_from_marks(len(cells), ch, marks, (i, j)))
            i = j
            continue
        raise ValueError(f'رمز غير مدعوم {ch!r} عند {i} في {word!r}')
    for c in cells:
        if c.carrier == 'ء' and c.vowel is None and not c.sukun:
            c.flags.append('UNMARKED')
    return cells


def _marks_after(word, j):
    marks = []
    while j < len(word) and word[j] in MARKCHARS:
        marks.append(word[j])
        j += 1
    return marks, j


def _cell_from_marks(idx, carrier, marks, span):
    c = Cell(idx, carrier, span=span)
    for m in marks:
        if m in TANWIN_OF:
            c.vowel = TANWIN_OF[m]
            c.tanwin = True
        elif m in VOWEL_OF_MARKS:
            c.vowel = VOWEL_OF_MARKS[m]
        elif m in (SUKUN, SMALL_SUKUN):
            c.sukun = True
    if c.vowel is None and not c.sukun:
        c.sukun = True
        c.flags.append('UNMARKED')          # حركة غير مكتوبة: تُوسم استنتاجاً
    return c


VOWEL_OF_MARKS = {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}

# ---------------------------------------------------------------- المقاطع
SIX = ('CV', 'CVV', 'CVC', 'CVVC', 'CVCC', 'CVVCC')
FINAL_ONLY = ('CVCC', 'CVVCC')


def _tokens(cells):
    toks = []
    for c in cells:
        if c.vowel:
            toks.append(('C', c.idx, c))
            toks.append(('VV' if c.long else 'V', c.idx, c))
        else:
            toks.append(('C', c.idx, c))
    return toks


def syllabify(cells):
    """→ (المقاطع, البقايا). كل مقطع: شكله وخلاياه ومجاله وحدّه وسبب قبوله."""
    toks = _tokens(cells)
    sy, residue = [], []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t[0] != 'C' or i + 1 >= n or toks[i + 1][0] not in ('V', 'VV'):
            if t[0] == 'C' and sy:
                sy[-1]['coda'].append(t[1]); i += 1; continue
            residue.append(t); i += 1; continue
        nuc = toks[i + 1]
        cur = {'onset': t[1], 'nuc': nuc[0], 'coda': []}
        j, cons = i + 2, []
        while j < n and toks[j][0] == 'C':
            cons.append(toks[j][1]); j += 1
        if j < n and toks[j][0] in ('V', 'VV'):
            cur['coda'] = cons[:-1]; nxt = j - 1
        else:
            cur['coda'] = cons; nxt = j
        sy.append(cur); i = nxt
    out = []
    for k, s in enumerate(sy):
        cell_ids = [s['onset']] + [x for x in s['coda']]
        shape = 'C' + ('VV' if s['nuc'] == 'VV' else 'V') + 'C' * len(s['coda'])
        last = k == len(sy) - 1
        nxt_onset = sy[k + 1]['onset'] if not last else None
        # الاستثناء: نصف الشدة المكتوبة وحده قفل، بعده الصامت التالي نفسه؛ لا قفل قبله
        geminate = (len(s['coda']) == 1 and nxt_onset is not None
                    and cells[nxt_onset].carrier == cells[s['coda'][-1]].carrier)
        ok_shape = shape in SIX
        ok_final = last or shape not in FINAL_ONLY or geminate
        span = (cells[cell_ids[0]].span[0], cells[cell_ids[-1]].span[1])
        out.append({
            'shape': shape,
            'cells': cell_ids,
            'span': span,
            'valid': ok_shape and ok_final,
            'reason': ('مقطع مرخّص' if ok_shape and ok_final else
                       'شكل غير مرخّص' if not ok_shape else
                       'CVCC/CVVCC وسط الكلمة بلا شدة مكتوبة'),
            'geminate_coda': geminate,
        })
    return out, residue


# ---------------------------------------------------------------- المرشحون (بذرة)
# مدخل معجمي: الكتابة المرجعية، والصنف، والبناء، والوظيفة، ومصدر الشاهد.
# لا تُعد هذه القائمة مستنفدة، فلا يصدر عنها ترخيص قطعي.
LEXICON = [
    dict(word='لَيْتَ', cls='حرف', built='مبني', role='عامل', witness='باب الحروف المشبهة بالفعل', exhaustive=False),
    dict(word='لَيْسَ', cls='فعل', built='مبني', role=None, witness='فعل ماضٍ ناقص مبني', exhaustive=False),
    dict(word='بَيْتَ', cls='اسم', built='معرب', role=None, witness='اسم في استعماله الموافق', exhaustive=False),
    dict(word='مَا', cls='حرف', built='مبني', role=None, witness='حرف نافٍ', exhaustive=False),
    dict(word='مَا', cls='اسم', built='مبني', role=None, witness='اسم موصول', exhaustive=False),
    dict(word='قَدْ', cls='حرف', built='مبني', role=None, witness='حرف تحقيق', exhaustive=False),
    dict(word='قَدْ', cls='اسم', built='مبني', role=None, witness='اسم فعل', exhaustive=False),
    dict(word='مِنْ', cls='حرف', built='مبني', role='عامل', witness='حرف جر', exhaustive=False),
    dict(word='الَّذِي', cls='اسم', built='مبني', role=None, witness='اسم موصول', exhaustive=False),
    dict(word='إِلَيَّ', cls='حرف', built='مبني', role='عامل', witness='حرف جر مع ياء المتكلم', exhaustive=False),
]


def _key(word):
    return tuple((c.carrier, c.vowel, c.sukun, c.long) for c in build_cells(word))


def decide(word):
    """يعيد القرار مع كل المراحل. كل حقل يُستمد من المرحلة التي قبله."""
    cells = build_cells(word)
    sylls, residue = syllabify(cells)
    boundary_ok = not residue and all(s['valid'] for s in sylls)
    res = {'word': word, 'cells': [(c.idx, c.carrier, c.vowel, c.long, c.shadda, c.flags) for c in cells],
           'syllables': [(s['shape'], s['span'], s['valid'], s['reason']) for s in sylls],
           'residue': residue}
    if not boundary_ok:
        bad = [s for s in sylls if not s['valid']]
        res.update(status='REJECTED', reason=bad[0]['reason'] if bad else 'بقايا', candidates=[])
        return res
    key = _key(word)
    cands = [e for e in LEXICON if _key(e['word']) == key]
    res['candidates'] = [dict(cls=e['cls'], built=e['built'], role=e['role'], witness=e['witness']) for e in cands]
    if not cands:
        res.update(status='NO_CANDIDATE', reason='غياب من قائمة غير مستنفدة ليس دليل رفض')
    elif len({e['cls'] for e in cands}) == 1 and len(cands) == 1:
        res.update(status='PENDING', reason='وجه واحد، ولم يثبت استنفاد البدائل')
    else:
        res.update(status='PENDING', reason='أكثر من وجه، والبدائل محفوظة')
    return res
