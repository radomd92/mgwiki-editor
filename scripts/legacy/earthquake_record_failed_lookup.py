"""Reuse actual prior 503 evidence without repeating the failed dictionary request."""
from urllib.parse import quote

from earthquake_evidence import JOB
from mgwiki_editor.core import read_json, write_json


if __name__ == '__main__':
    record = read_json(JOB/'evidence/resumed-overload.json')
    item = record['failed_lookup']
    output = JOB/'evidence'/item['expected_output']
    if not output.exists():
        prior = read_json(JOB/'evidence/lookup-en-earthquake.json')
        origin = prior['url'].split('/wiktionary-pages/', 1)[0]
        write_json(output, {
            'status': 'failed', 'edition': item['edition'], 'word': item['word'],
            'url': origin+'/wiktionary-pages/'+item['edition']+'/'+quote(item['word'], safe=''),
            'recorded_at': record['recorded_at'], 'error': record['error'],
            'http_status': record['http_status'], 'entries': [],
            'evidence_origin': 'Recorded failed lookup, reconstructed from existing overload receipt and raw log; not a new lookup or dictionary miss.',
            'source_files': ['evidence/resumed-overload.json', 'resumed-evidence.log'],
        })
        print('Prior 503 retained as failed lookup; no request sent.')
