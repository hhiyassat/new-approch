# -*- coding: utf-8 -*-
"""فاحص صفوف الوسم: يتحقق أن كل علاقة تُشير إلى الطرف المقصود، وأن خلايا كل طرف تفسَّر داخل وقوعه.
الاستعمال: python3 check_operator_rows.py <operator_tags.tsv> <quran_hafs.tsv>
يخرج برمز غير صفر عند أي مخالفة، ويطبع عددها."""
import csv, sys, os, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura
from gate import build_cells

PHI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'spelling', 'phi_letters.json')

def load_phi(path=PHI_PATH):
    with open(path, encoding='utf-8') as f:
        return json.load(f)['letters']

def load_subs(path=PHI_PATH):
    with open(path, encoding='utf-8') as f:
        return json.load(f).get('word_equivalences', {})

def _marks_from(word, j):
    k = j
    while k < len(word) and unicodedata.category(word[k]) == 'Mn':
        k += 1
    return k

def strip_phi(word, letters):
    # ئ المفكّكة: ي تتبعها علاماتها، وفيها همزة U+0654 في أي موضع بين علاماتها
    out, i = [], 0
    while i < len(word):
        hit = next((L for L in letters if word.startswith(L, i)), None)
        if hit:
            i += len(hit)
            i = _marks_from(word, i)
            continue
        if word[i] == '\u064a':
            k = _marks_from(word, i + 1)
            if '\u0654' in word[i + 1:k]:
                i = k          # يحذف الحرف مع علاماته كلها
                continue
        out.append(word[i]); i += 1
    return ''.join(out)

def cells_for(word, letters, subs, used):
    try:
        return build_cells(word)
    except ValueError:
        if word in subs:                 # تكافؤ مرخّص لكلمة بعينها
            fb = subs[word]
        else:
            fb = strip_phi(word, letters)
        if fb != word:
            cells = build_cells(fb)   # يرفع الخطأ إن بقي الفشل
            used.append((word, fb))
            return cells
        raise

def main(tags_path, quran_path):
    letters = load_phi()
    subs = load_subs()
    used = []
    rows = list(csv.reader(open(tags_path, encoding='utf-8'), delimiter='\t'))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}
    words = {}
    with open(quran_path, encoding='utf-8') as f:
        for rec in csv.reader(f, delimiter='\t'):
            if len(rec) >= 3 and rec[0].isdigit():
                for pos, w in enumerate(join_split_maqsura(rec[2].split()), 1):
                    words[f'{rec[0]}:{rec[1]}:{pos}'] = w
    violations = []
    for x in data:
        occ, word = x[idx['معرف_الوقوع']], x[idx['الكلمة']]
        tag, evidence = x[idx['الوسم']], x[idx['الدليل']]
        related = x[idx['معرف_الطرف_المرتبط']]
        cells = x[idx['خلايا_الطرف']]
        if evidence.startswith('PROCLITIC'):
            if related != occ:
                violations.append(('PROCLITIC_NOT_SELF', occ, word, related))
            continue
        if evidence.startswith(('WORD_OPERATOR', 'ADJACENT')):
            s, a, p = occ.split(':')
            nxt = f'{s}:{a}:{int(p) + 1}'
            if nxt in words:
                if related != nxt:
                    violations.append(('RELATED_NOT_NEXT', occ, word, related))
                if tag == 'معمول' and cells:
                    try:
                        n_cells = len(cells_for(words[nxt], letters, subs, used))
                    except ValueError as e:
                        violations.append(('OPERAND_UNBUILDABLE', occ, words[nxt], str(e)[:60]))
                    else:
                        got = len(cells.split())
                        if got != n_cells:
                            violations.append(('OPERAND_CELLS_MISMATCH', occ, words[nxt], f'{got}!={n_cells}'))
            elif related:
                violations.append(('RELATED_WITHOUT_NEXT', occ, word, related))
    print(f'rows={len(data)} violations={len(violations)} phi_stripped_operands={len(used)}')
    for w, st in sorted(set(used)):
        print('PHI_STRIPPED', w, '->', st)
    for v in violations[:20]:
        print(v)
    return 1 if violations else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
