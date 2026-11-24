# -*- coding: utf-8 -*-
"""
بناء جدول المبنيات الموحّد من ملفات data/mabniyat/*.json.

الناتج:
  lexicon/mabniyat.tsv         مداخل صالحة للاستعمال كدليل فحص (exhaustive=false دائمًا)
  lexicon/mabniyat_review.tsv  مداخل وصفية أو تحتاج مراجعة، لا تُستعمل قبل حسمها
كل صف يحمل صيغته الأصلية وصيغته المجرّدة (هيكل صامتي) والمصدر والمجال والمعنى.
"""
import csv, json, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from gate import build_cells, MARKCHARS, TATWEEL, WAQF

# الحقل الذي يحمل المدخل في كل ملف، والمجال المعتمد للملف
SOURCES = {
    'coordinating_conjunctions.json': ('letter', 'عطف'),
    'conditional_letters_tools.json': ('particle', 'شرط'),
    'copulative_particle.json': ('copulative_particle', 'نواسخ'),
    'preposition_meanings.json': ('preposition', 'حرف جر'),
    'vocative_particles.json': ('particle', 'نداء'),
    'interrogative_letters_tools.json': ('tool', 'استفهام'),
    'jazm_tools.json': ('tool', 'جزم'),
    'present_naseb_tools.json': ('tool', 'نصب'),
    'letters_answers.json': ('particle', 'جواب'),
    'relative_pronouns.json': ('name', 'موصول'),
    'demonstrative_pronouns.json': ('name', 'إشارة'),
    'pronouns_classification.json': ('pronoun', 'ضمير'),
    'hidden_pronouns.json': ('form', 'ضمير مستتر'),
    'built_in_adverbs.json': ('adverb', 'ظرف'),
    'verb_name.json': ('name', 'اسم فعل'),
    'kinaya_names.json': ('name', 'كناية'),
    'compound_numbers.json': ('subject', 'عدد مركب'),
}
# مدخل يبدأ بهذه الكلمات أو يحتوي أقواسًا فهو وصف، لا صيغة
DESCRIPTIVE = ('تاء', 'هاء', 'كاف', 'ياء', 'واو', 'ألف', 'نون', 'الهاء', 'الكاف', 'ياء', 'وَاوُ', 'أَلِفُ', 'نُونُ', 'يَاءُ', 'تاء', 'الهاءُ', 'الكافُ')
SKIP_CHARS = set(MARKCHARS) | {TATWEEL, '‏', 'ْ'} | set(WAQF)
SEPARATORS = re.compile(r'\s+وَ\s+|\s+-\s+|\s+/\s+|\s*،\s*|\s*,\s*')


def skeleton(s):
    out = []
    for ch in s:
        if ch in SKIP_CHARS or ch.isspace():
            continue
        out.append({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا'}.get(ch, ch))
    return ''.join(out)


def is_descriptive(s):
    if '(' in s or ')' in s or ':' in s:
        return True
    if len(s.split()) > 4:
        return True
    return any(s.startswith(w) or s == w for w in DESCRIPTIVE)


# حروف الصيغ الصحيحة: الهمزات والمقصورة والتاء المربوطة مقبولة، وغيرها يُراجع
LETTERS = set('ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي')
GRAMMAR_TERMS = ('اعراب', 'إعراب', 'تمييز', 'الرفع', 'النصب', 'الجر', 'المفرد', 'المذكر', 'المؤنث',
                 'الجمع', 'الغائب', 'المخاطب', 'المتكلم', 'المعدود', 'المركب')


def letters_ok(s):
    return bool(skeleton(s)) and all(ch in LETTERS for ch in skeleton(s))


def is_grammar_term(s):
    return any(t in s for t in GRAMMAR_TERMS)


def rows_for(fname, field, domain):
    data = json.load(open(os.path.join(HERE, '..', 'data', 'mabniyat', fname), encoding='utf-8'))['data']
    for it in data:
        raw = str(it.get(field) or '').strip()
        if not raw:
            continue
        meaning = str(it.get('description') or it.get('meaning') or it.get('usage') or
                      it.get('category') or it.get('tool') or it.get('particle') or '').strip()
        parts = [p.strip() for p in SEPARATORS.split(raw) if p.strip()]
        for part in parts:
            cleaned = part.replace('ْ', '') if part.endswith(' ْ') or part.endswith('ْ') and len(part) <= 3 else part
            cleaned = cleaned.strip()
            if not cleaned:
                continue
            status = 'OK'
            if is_descriptive(cleaned) or is_grammar_term(cleaned):
                status = 'DESCRIPTIVE'
            elif not letters_ok(cleaned):
                status = 'REVIEW_LETTERS'
            yield dict(headword=cleaned, skeleton=skeleton(cleaned), words=len(cleaned.split()), status=status, domain=domain,
                       source=fname, raw_field=field, raw_value=raw, meaning=meaning[:200],
                       exhaustive='false', built='مبني')


def main():
    ok, review, seen = [], [], set()
    for fname, (field, domain) in sorted(SOURCES.items()):
        for r in rows_for(fname, field, domain):
            key = (r['skeleton'], r['domain'], r['status'])
            if key in seen:
                continue
            seen.add(key)
            (ok if r['status'] == 'OK' else review).append(r)
    cols = ['headword', 'skeleton', 'words', 'domain', 'built', 'source', 'raw_field', 'raw_value', 'meaning', 'exhaustive', 'status']
    for path, rows in [(os.path.join(HERE, 'mabniyat.tsv'), ok), (os.path.join(HERE, 'mabniyat_review.tsv'), review)]:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', extrasaction='ignore')
            w.writeheader(); w.writerows(rows)
    print(f'OK={len(ok)} review={len(review)}')
    from collections import Counter
    print(Counter(r['status'] for r in review))


if __name__ == '__main__':
    main()
