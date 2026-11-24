# -*- coding: utf-8 -*-
"""فاحص صفوف الوسم: يتحقق أن كل علاقة تُشير إلى الطرف المقصود، وأن خلايا كل طرف تفسَّر داخل وقوعه.
الاستعمال: python3 check_operator_rows.py <operator_tags.tsv> <quran_hafs.tsv>
يخرج برمز غير صفر عند أي مخالفة، ويطبع عددها."""
import csv, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura
from gate import build_cells

def main(tags_path, quran_path):
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
                    n_cells = len(build_cells(words[nxt]))
                    got = len(cells.split())
                    if got != n_cells:
                        violations.append(('OPERAND_CELLS_MISMATCH', occ, words[nxt], f'{got}!={n_cells}'))
            elif related:
                violations.append(('RELATED_WITHOUT_NEXT', occ, word, related))
    print(f'rows={len(data)} violations={len(violations)}')
    for v in violations[:20]:
        print(v)
    return 1 if violations else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
