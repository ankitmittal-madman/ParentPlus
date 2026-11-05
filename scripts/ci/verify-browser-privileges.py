#!/usr/bin/env python3
"""Fail closed unless the privileged namespace bootstrap dropped all privileges."""
import os
from pathlib import Path


def valid_drop(fields, expected_uid, expected_gid):
    try:
        uids = [int(value) for value in fields['Uid'].split()]
        gids = [int(value) for value in fields['Gid'].split()]
        caps = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')
        return (expected_uid > 0 and expected_gid > 0 and len(uids) == len(gids) == 4
                and all(value == expected_uid for value in uids)
                and all(value == expected_gid for value in gids)
                and not fields['Groups'].strip()
                and all(int(fields[name].strip(), 16) == 0 for name in caps)
                and fields['NoNewPrivs'].strip() == '1')
    except (KeyError, ValueError, TypeError):
        return False


def main():
    try:
        expected_uid = int(os.environ['PARENTPLUS_VERIFY_DROPPED_UID'])
        expected_gid = int(os.environ['PARENTPLUS_VERIFY_DROPPED_GID'])
        fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    except (KeyError, ValueError, OSError):
        raise SystemExit('STOP: privileged bootstrap verification failed')
    if not valid_drop(fields, expected_uid, expected_gid):
        raise SystemExit('STOP: privileged bootstrap verification failed')


if __name__ == '__main__':
    main()
