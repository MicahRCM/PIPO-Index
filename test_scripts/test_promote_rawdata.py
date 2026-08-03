#!/usr/bin/env python3
"""Sanity checks for the RawData CDS promotion (data_pipeline/promote_rawdata.py).

Verifies the promoted institutions_master.csv against the pre-promotion backup and
the preview, and confirms SUSPECT-join CDS values were suppressed.
Run from repo root:  python3 test_scripts/test_promote_rawdata.py
"""
import csv, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(REPO, 'data', 'institutions_master.csv')
PREVIEW = os.path.join(REPO, 'data', 'institutions_master_with_cds.csv')
VALID = os.path.join(REPO, 'data', 'rawdata_join_validation.csv')
BACKUP = ('/private/tmp/claude-501/-Users-peacespherical-Documents-GitHub-'
          'PIPO-Index/66fc5bde-feb6-4ef6-987c-4063571951cb/scratchpad/'
          'institutions_master.pre_rawdata.csv')

CDS_IDX = list(range(50, 69))


def load(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def main():
    fails = []
    m = load(MASTER)
    b = load(BACKUP)
    p = load(PREVIEW)

    # 1. shape
    if len(m) != 48077:
        fails.append(f'master row count {len(m)} != 48077')
    if len(m[0]) != 69:
        fails.append(f'master col count {len(m[0])} != 69')
    if len(m) != len(b) or len(m) != len(p):
        fails.append('row counts differ across master/backup/preview')

    # 2. first 50 cols unchanged vs backup (existing data preserved exactly)
    if sum(1 for i in range(len(m)) if m[i][:50] != b[i][:50]):
        fails.append('first 50 columns changed vs backup')

    # 3. header = backup header + 19 CDS fields (order preserved)
    if m[0][:50] != b[0]:
        fails.append('header first 50 not equal to backup header')

    # 4. suspects fully blanked
    suspects = set()
    with open(VALID, newline='') as f:
        for r in csv.DictReader(f):
            if r['verdict'] == 'SUSPECT':
                suspects.add(r['unitid'])
    iu = m[0].index('unitid')
    if any(any(row[i] != '' for i in CDS_IDX)
           for row in m[1:] if row[iu].strip() in suspects):
        fails.append('a SUSPECT unitid still has non-blank CDS values')

    # 5. non-suspect rows equal preview exactly (CDS carried through unchanged)
    bad = 0
    for row_m, row_p in zip(m[1:], p[1:]):
        if row_m[iu].strip() in suspects:
            continue
        if row_m[50:69] != row_p[50:69]:
            bad += 1
    if bad:
        fails.append(f'{bad} non-suspect rows differ from preview CDS')

    print(f'suspects={len(suspects)}  master={len(m)-1}x{len(m[0])}')
    if fails:
        print('FAIL:')
        for x in fails:
            print('  -', x)
        sys.exit(1)
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
