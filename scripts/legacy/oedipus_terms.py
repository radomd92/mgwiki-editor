"""Pin additional sense checks sequentially; never edit dictionary pages."""
import shutil
from pathlib import Path

from mgwiki_editor.core import GuardError, lookup, now, write_json

JOB = Path('runs/oedipus-20261105')


def main():
    evidence = JOB / 'evidence'
    for edition in ['en', 'mg']:
        origin = Path('runs/genji-en-20261105-utf8/evidence') / f'lookup-{edition}-regent.json'
        target = evidence / origin.name
        if not target.exists():
            shutil.copyfile(origin, target)
    for english, malagasy in [
        ('trilogy', 'trilojia'), ('satyr play', 'tantara'),
        ('bastard', 'zazasary'), ('adoption', 'fananganan-jaza'),
        ('fresco', 'sary'), ('amphora', 'siny'),
        ('lekythos', 'vazy'), ('pelike', 'siny'),
        ('folklore', 'lovantsofina'), ('genetic attraction', 'fisarihana'),
        ('plague', 'valanaretina'), ('seer', 'mpahita'),
        ('epiphany', 'fahafantarana'), ('brooch', 'haingo'),
        ('consort', 'vady'), ('exposure', 'famelana'),
        ('betrothal', 'fifamofoana'), ('spurious', 'sandoka'),
        ('herald', 'mpitondra hafatra'), ('red-figure', 'sary mena'),
    ]:
        for edition, word in [('en', english), ('mg', malagasy)]:
            output = evidence / f'lookup-{edition}-{english.replace(" ", "-")}.json'
            if output.exists():
                continue
            try:
                result = lookup(edition, word)
            except GuardError as exc:
                result = {'status': 'failed', 'edition': edition, 'word': word,
                          'retrieved_at': now(), 'error': str(exc)}
            write_json(output, result)
    print('Additional term evidence pinned')


if __name__ == '__main__':
    main()
