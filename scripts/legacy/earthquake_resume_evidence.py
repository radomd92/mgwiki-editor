"""Single paced coordinator worker resumes pinned metadata and lexical checks."""
import re

from earthquake_evidence import JOB, main as original_evidence
from earthquake_supplement import main as supplemental_evidence
from mgwiki_editor.core import GuardError, lookup, now, read_json, write_json

EXTRA_TERMS = [
    ('elastic rebound', 'fiverenana'), ('fault plane', 'velarana'),
    ('dip-slip', 'fitongilanana'), ('oblique slip', 'mitongilana'),
    ('megathrust', 'fifanosihana'), ('brittle', 'vaky'), ('ductile', 'miova'),
    ('rupture', 'fahavakisana'), ('friction', 'fikikisana'),
    ('conduction', 'fifindrana'), ('convection', 'fivezivezena'),
    ('stress drop', 'fihenana'), ('dip', 'fitongilanana'),
    ('mainshock', 'lehibe'), ('earthquake storm', 'andiana'),
    ('seismicity', 'fihetsehana'), ('surface-wave magnitude', 'magnitioda'),
    ('accelerometer', 'fandrefesana'), ('amplitude', 'velatra'),
    ('P wave', 'onja'), ('S wave', 'onja'), ('surface wave', 'onja'),
    ('density', 'lanja'), ('elasticity', 'fiverenana'), ('seismogram', 'rakitra'),
    ('ground acceleration', 'hafainganam-pihetsika'),
    ('site amplification', 'fanamafisana'), ('masonry', 'biriky'),
    ('seismic risk', 'loza'), ('seismic hazard', 'loza'),
    ('seismotectonics', 'tektônika'), ('helioseismology', 'fihovitrovitra'),
    ('catfish', 'trondro'), ('supernova', 'fipoahana'),
    ('starquake', 'fihovitrovitra'), ('tremor', 'firohondrohona'),
    ('temblor', 'horohoron-tany'), ('plague', 'pesta'),
]


def main():
    supplemental_evidence()
    original_evidence()
    e = JOB/'evidence'
    index = {}
    for f in e.glob('lookup-*.json'):
        data = read_json(f)
        index[(data.get('edition'), data.get('word'))] = data
    for english, malagasy in EXTRA_TERMS:
        for edition, word in [('en', english), ('mg', malagasy)]:
            out = e/f'lookup-extra-{edition}-{re.sub(r"[^a-z0-9]+", "-", english.lower())}.json'
            if out.exists():
                continue
            if (edition, word) in index:
                result = index[(edition, word)]
            else:
                try:
                    result = lookup(edition, word)
                except GuardError as exc:
                    if any(s in str(exc).lower() for s in ('cooldown', 'deferred', 'circuit', 'rate', 'overload')):
                        raise
                    result = {'status': 'failed', 'edition': edition, 'word': word,
                              'retrieved_at': now(), 'error': str(exc)}
                index[(edition, word)] = result
            write_json(out, result)
    print('All planned resumed evidence requests completed; no external citation URL accessed.')


if __name__ == '__main__':
    main()
