#!/usr/bin/env bash
# يشغّل كل المجموعات، ويخرج برمز غير صفر عند أي فشل داخل أي مجموعة.
set -u
cd "$(dirname "$0")"
status=0
for t in test_operator_tags.py test_syllable_peel.py test_peel.py test_pipeline.py gate_test.py test_suffix_diagnostic.py test_phi_letters.py; do
  python3 "$t" > "/tmp/run_all_$t.log" 2>&1
  code=$?
  echo "$t exit=$code $(tail -1 "/tmp/run_all_$t.log")"
  if [ "$code" -ne 0 ]; then status=1; fi
done
exit $status
