"""Serialized final lexical gaps only; reuse exact prior lookup responses."""
import re

from earthquake_evidence import JOB
from mgwiki_editor.core import GuardError, lookup, now, read_json, write_json

TERMS = [('tectonic plate', 'takelaka'), ('tiltmeter', 'fitongilanana'),
         ('sonic boom', 'dona'), ('positive feedback', 'fifamafisana'),
         ('injection well', 'lavaka'), ('seismology', 'horohoron-tany'),
         ('statistical seismology', 'antontanisa'), ('stochastic modeling', 'kisendrasendra'),
         ('P-wave', 'onja'), ('S-wave', 'onja')]


if __name__ == '__main__':
    evidence = JOB/'evidence'
    cache = {}
    for path in evidence.glob('lookup-*.json'):
        d = read_json(path)
        cache[(d.get('edition'), d.get('word'))] = d
    for english, malagasy in TERMS:
        for edition, word in [('en', english), ('mg', malagasy)]:
            path = evidence/f'lookup-final-{edition}-{re.sub(r"[^a-z0-9]+", "-", english.lower())}.json'
            if path.exists():
                continue
            if (edition, word) in cache:
                data = cache[(edition, word)]
            else:
                try:
                    data = lookup(edition, word)
                except GuardError as exc:
                    if any(s in str(exc).lower() for s in ('cooldown', 'deferred', 'circuit', 'rate', 'overload')):
                        raise
                    data = {'status': 'failed', 'edition': edition, 'word': word,
                            'recorded_at': now(), 'error': str(exc)}
                cache[(edition, word)] = data
            write_json(path, data)
    print('Ten final lexical pairs checked or reused; failed lookups retained honestly.')
