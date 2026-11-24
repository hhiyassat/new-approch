# -*- coding: utf-8 -*-
"""ربط التطبيع بالتقشير: لكل كلمة، أحداث التطبيع (سجل counts) ونتيجة التقشير على الكلمة الأصلية، وتصنيف التطابق.
لا يغيّر هذا الربط أي حكم تقشير؛ الحكم يبقى لـ peel.analyze وحده.
الاستعمال: python3 run_linked.py <quran_hafs.tsv> <out_dir> [--sura N]
الخرج: linked_words.tsv"""
import csv, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura, is_divine, normalize
from gate import build_cells
from peel import analyze

ARTICLE_EVENTS = ('ARTICLE_SOLAR_LAM_DELETED', 'ARTICLE_MOON_LAM_KEPT')

def link_word(word):
    counts = Counter()
    norm = normalize(word, counts=counts, mushaf=True)
    art_norm = any(k in counts for k in ARTICLE_EVENTS)
    try:
        analyses = analyze(word, cells=build_cells(word), source_id='linked', occurrence_id='linked',
                           original_text=word)
    except ValueError as e:
        return norm, dict(counts), 'ERROR', str(e)[:60], art_norm, False
    art_peel = any(a['rule']['rule_id'].startswith('ART') and a['verdict'] == 'LICENSED' for a in analyses)
    verdicts = ';'.join(sorted({a['verdict'] for a in analyses})) or 'NO_CANDIDATE'
    return norm, dict(counts), verdicts, '', art_norm, art_peel

def agreement(art_norm, art_peel):
    if art_norm and art_peel: return 'AGREE_ARTICLE'
    if art_norm: return 'NORM_ONLY_ARTICLE'
    if art_peel: return 'PEEL_ONLY_ARTICLE'
    return 'NONE'

def main(argv):
    args = list(argv); sura = None
    if '--sura' in args:
        i = args.index('--sura'); sura = args[i + 1]; del args[i:i + 2]
    if len(args) != 2:
        print(__doc__); return 2
    src, out_dir = args
    os.makedirs(out_dir, exist_ok=True)
    header = ['سورة', 'آية', 'ترتيب', 'معرف_الوقوع', 'الكلمة', 'التطبيع', 'أحداث_التطبيع', 'حكم_التقشير', 'سبب_خطأ', 'التطابق']
    rows, stats = [], Counter()
    with open(src, encoding='utf-8') as f:
        for rec in csv.reader(f, delimiter='\t'):
            if len(rec) < 3 or not rec[0].isdigit(): continue
            s, ayah, text = rec[0], rec[1], rec[2]
            if sura is not None and s != str(sura): continue
            for pos, word in enumerate(join_split_maqsura(text.split()), 1):
                if is_divine(word):
                    stats['divine_skipped'] += 1; continue
                occ = f'{s}:{ayah}:{pos}'
                norm, ev, verdicts, err, art_n, art_p = link_word(word)
                agr = agreement(art_n, art_p)
                stats[agr] += 1
                rows.append([s, ayah, pos, occ, word, norm or '', ';'.join(f'{k}={v}' for k, v in sorted(ev.items())),
                             verdicts, err, agr])
    with open(os.path.join(out_dir, 'linked_words.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t'); w.writerow(header); w.writerows(rows)
    lines = [f'{k}: {v}' for k, v in sorted(stats.items())]
    open(os.path.join(out_dir, 'linked_summary.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
