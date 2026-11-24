# -*- coding: utf-8 -*-
"""
تشغيل وسم العامل والمعمول على ملف المصحف (أو سورة).
الاستعمال: python3 run_operator_tags.py <quran_hafs.tsv> <out_dir> [--sura N]
الخرج: operator_tags.tsv — صف لكل وسم: الكلمة، الوسم، المعامل، الحالة المتوقعة، الدليل، الكلمة المرتبطة، الحالة (دائمًا CANDIDATE).
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura
import operator_tags as T


def main(argv):
    args = list(argv); sura = None
    if '--sura' in args:
        i = args.index('--sura'); sura = args[i + 1]; del args[i:i + 2]
    if len(args) != 2:
        print(__doc__); return 2
    src, out_dir = args
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    with open(src, encoding='utf-8') as f:
        for rec in csv.reader(f, delimiter='\t'):
            if len(rec) < 3 or not rec[0].isdigit():
                continue
            if sura is not None and rec[0] != str(sura):
                continue
            words = join_split_maqsura(rec[2].split())
            for pos, w in enumerate(words, start=1):
                nxt = words[pos] if pos < len(words) else None
                for tag, op, case, evidence, operand, relation, boundary, function in T.tags_for_word(w, nxt):
                    rows.append([rec[0], rec[1], pos, f'{rec[0]}:{rec[1]}:{pos}', w, tag, op, case,
                                 evidence, operand, relation, boundary, function])
    with open(os.path.join(out_dir, 'operator_tags.tsv'), 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f, delimiter='\t')
        header = ['سورة', 'آية', 'ترتيب_الكلمة', 'معرف_الوقوع', 'الكلمة', 'الوسم', 'العامل', 'الحالة_المتوقعة',
                  'الدليل', 'الكلمة_المرتبطة', 'حالة_العلاقة', 'حد_الوحدة', 'حالة_الوظيفة']
        wr.writerow(header)
        bad = [r for r in rows if len(r) != len(header)]
        if bad:
            raise SystemExit('عدم تطابق الأعمدة')
        wr.writerows(rows)
    from collections import Counter
    print(dict(Counter(r[5] for r in rows)), 'rows', len(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
