# -*- coding: utf-8 -*-
"""
تشغيل التقشير المرخّص على ملف المصحف (أو على سورة واحدة).

الاستعمال:
    python3 run_peel.py <quran_hafs.tsv> <out_dir> [--sura N]

الخرج:
    peel_words.tsv : صف لكل وقوع كلمة وتحليل تقشير (سورة، آية، الكلمة، القاعدة، الحكم، السبب، الحدود، الوحدات)
    peel_summary.txt : إحصاءات الأحكام حسب القاعدة
الكلمات الإلهية تُستثنى كما في run_quran.py؛ والكلمات التي تفشل في بناء الخلايا تُسجَّل.
"""
import csv, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dagger_normalize import join_split_maqsura, is_divine
from gate import build_cells
from peel import analyze


def _units_text(a):
    return ' | '.join(f"{u['candidate_role']}:{u['text']}" for u in a['units'][1:])


def _cuts(a):
    return ','.join(str(b['cut_at_cell']) for b in a['boundary_checks'] if 'cut_at_cell' in b)


def _syl(sylls):
    return ' . '.join(f"{s['shape']}[{','.join(str(i) for i in s['cell_ids'])}]" for s in sylls)


def _evidence(a):
    bc = [b for b in a['boundary_checks'] if 'left_syllables' in b]
    left = ' || '.join(_syl(b['left_syllables']) for b in bc)
    right = ' || '.join(_syl(b['residual_syllables']) for b in bc)
    shadda = ','.join(str(b['shadda_origin']) for b in bc)
    sukun = ','.join(f"{s['cell_id']}:{s['origin']}" for b in bc for s in b['internal_sukun_origin'])
    cov = ','.join(f"{e['char']}:{e['status']}" for e in a['source_coverage'])
    return [left, right, shadda, sukun, cov]


def main(argv):
    args = list(argv)
    sura = None
    if '--sura' in args:
        i = args.index('--sura'); sura = args[i + 1]; del args[i:i + 2]
    method = 'peel'                     # الافتراضي: المسار القديم بالحروف، للمقارنة
    if '--method' in args:
        i = args.index('--method'); method = args[i + 1]; del args[i:i + 2]
    if method not in ('peel', 'syllable'):
        print('method must be peel or syllable'); return 2
    if method == 'syllable':
        import syllable_peel as SP
    if len(args) != 2:
        print(__doc__); return 2
    src, out_dir = args
    os.makedirs(out_dir, exist_ok=True)
    rows, stats = [], collections.Counter()
    with open(src, encoding='utf-8') as f:
        rd = csv.reader(f, delimiter='\t')
        for rec in rd:
            if len(rec) < 3 or not rec[0].isdigit():
                continue
            s, ayah, text = rec[0], rec[1], rec[2]
            if sura is not None and s != str(sura):
                continue
            for pos, word in enumerate(join_split_maqsura(text.split()), start=1):
                stats['words'] += 1
                occ = f'{s}:{ayah}:{pos}'
                if is_divine(word):
                    stats['divine_skipped'] += 1
                    continue
                if method == 'syllable':
                    try:
                        sp = SP.propose(word)
                    except ValueError as e:
                        stats['cells_error'] += 1
                        continue
                    for c in sp['candidates']:
                        stats[c['final_verdict']] += 1
                        rows.append([s, ayah, pos, occ, word, 'SYLLABLE', c['final_verdict'], c['reason'],
                                     c['candidate_id'], c['side'], c['detached_text'], c['geometry_verdict'],
                                     ' '.join(c['left_syllables']), ' '.join(c['right_syllables'])] + [''] * 3)
                    if not sp['candidates']:
                        stats['no_candidate'] += 1
                    continue
                try:
                    cells = build_cells(word)
                except ValueError as e:
                    stats['cells_error'] += 1
                    rows.append([s, ayah, pos, occ, word, '', 'ERROR', str(e)[:80], '', '', '', '', '', '', ''])
                    continue
                analyses = analyze(word, cells=cells, source_id=f'quran-hafs:{s}:{ayah}',
                                   occurrence_id=occ, original_text=word)
                if not analyses:
                    stats['no_candidate'] += 1
                    rows.append([s, ayah, pos, occ, word, '', 'NO_CANDIDATE', 'لا اقتراح تقشير؛ غيابه ليس رفضًا',
                                 '', '', '', '', '', '', ''])
                    continue
                for a in analyses:
                    stats[a['verdict']] += 1
                    stats[f"{a['rule']['rule_id']}:{a['verdict']}"] += 1
                    rows.append([s, ayah, pos, occ, word, a['rule']['rule_id'], a['verdict'], a['reason'],
                                 _cuts(a), _units_text(a)] + _evidence(a))
    with open(os.path.join(out_dir, 'peel_words.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['سورة', 'آية', 'ترتيب_الكلمة_في_الآية', 'معرف_الوقوع', 'الكلمة', 'القاعدة', 'الحكم', 'السبب',
                    'الحدود', 'الوحدات', 'مقاطع_الطرف_الأيسر_للحد', 'مقاطع_الطرف_الأيمن_للحد', 'أصل_الشدة', 'أصل_الساكن_الداخلي',
                    'تغطية_المصدر_الاستثناءات'])
        w.writerows(rows)
    lines = [f"{k}: {v}" for k, v in sorted(stats.items())]
    with open(os.path.join(out_dir, 'peel_summary.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
