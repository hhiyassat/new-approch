# -*- coding: utf-8 -*-
"""
تشغيل التوحيد والفحص والتقطيع على ملف القرآن (TSV: سورة\tآية\tنص).

الاستخدام:
    python3 run_quran.py path/to/quran_hafs.tsv [output_dir]

يكتب في output_dir (الافتراضي: المجلد الحالي):
    quran_syllables.tsv   كل كلمة مع تقطيعها وأشكال مقاطعها
    quran_failures.tsv    الكلمات التي لم تجتز الفحص
"""
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura, normalize  # noqa: E402
from check_licensed import check  # noqa: E402
from syllab import syllables  # noqa: E402


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src = argv[1]
    out_dir = argv[2] if len(argv) > 2 else '.'
    os.makedirs(out_dir, exist_ok=True)

    with open(src, encoding='utf-8') as f:
        rows = [line.rstrip('\n').split('\t') for line in f if line.strip()]

    syl_rows, fail_rows = [], []
    stats = Counter()
    for sura, ayah, text in rows:
        for word in join_split_maqsura(text.split()):
            res = syllables(word)
            if res is None:
                stats['skipped'] += 1
                syl_rows.append([sura, ayah, word, '', '', 'لا يُقطَّع'])
                continue
            parts, shapes, bad, norm = res
            n, _, problems = check(word)
            stats['words'] += 1
            if problems:
                stats['fail'] += 1
                fail_rows.append([sura, ayah, word, norm, ' | '.join(problems)])
            else:
                stats['pass'] += 1
            syl_rows.append([sura, ayah, word, norm, ' . '.join(parts),
                             ' . '.join(shapes) + (' | بقايا' if bad else '')])

    with open(os.path.join(out_dir, 'quran_syllables.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['سورة', 'آية', 'الكلمة', 'بعد التوحيد', 'المقاطع', 'الأشكال'])
        w.writerows(syl_rows)
    with open(os.path.join(out_dir, 'quran_failures.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['سورة', 'آية', 'الكلمة', 'بعد التوحيد', 'أسباب الفشل'])
        w.writerows(fail_rows)

    total = stats['words']
    pct = 100.0 * stats['pass'] / total if total else 0.0
    print(f"الكلمات المفحوصة: {total}")
    print(f"المتخطاة (لفظ الجلالة والحروف المقطعة): {stats['skipped']}")
    print(f"نجحت: {stats['pass']}  ({pct:.2f}%)")
    print(f"فشلت: {stats['fail']}")
    print(f"الملفات: {os.path.abspath(out_dir)}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
