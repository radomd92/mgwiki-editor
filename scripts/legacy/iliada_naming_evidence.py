"""Serialized guarded Wikipedia reads for ancient proper-name identities."""
from pathlib import Path

from mgwiki_editor.core import Wiki, read_json, write_json

JOB = Path('runs/iliada-naming-20261106')
NAMES = [
    'Homer', 'Achilles', 'Hector', 'Agamemnon', 'Mycenae', 'Patroclus',
    'Chryseis', 'Briseis', 'Chryses (priest of Apollo)', 'Apollo', 'Myrmidons',
    'Odysseus', 'Thetis', 'Zeus', 'Athena', 'Thersites', 'Priam',
    'Paris (mythology)', 'Menelaus', 'Helen of Troy', 'Sparta', 'Aphrodite',
    'Hera', 'Pandarus', 'Diomedes', 'Aeneas', 'Ares', 'Glaucus (soldier)',
    'Bellerophon', 'Hecuba', 'Andromache', 'Astyanax', 'Ajax the Great',
    'Ajax the Lesser', 'Phoenix (son of Amyntor)', 'Dolon (mythology)',
    'Nestor (mythology)', 'Poseidon', 'Amphimachus I of Elis',
    'Idomeneus of Crete', 'Polydamas (Iliad)', 'Hephaestus',
    'Sarpedon (Trojan War hero)', 'Cebriones', 'Euphorbos', 'Antilochus of Pylos',
    'Automedon', 'Scamander', 'Deiphobus', 'Hermes', 'Hypnos', 'Thanatos',
    'Calchas', 'Leto', 'Aeacus', 'Menoetius', 'Cronus', 'Dardanus (son of Zeus)',
    'Hebe (mythology)', 'Atreus', 'Herodotus', 'Hesiod', 'Thucydides', 'Plato',
    'Aristonicus of Alexandria', 'Didymus Chalcenterus', 'Aelius Herodianus',
    'Nicanor Stigmatias', 'Phereclus', 'Telamon', 'Teucer', 'Simoeisius',
    'Anthemion', 'Simoeis', 'Othryades', 'Aeschylus', 'Troilus', 'Cressida',
    'Cassandra', 'Clytemnestra', 'Hermione (mythology)', 'Statius', 'Ovid', 'Virgil',
    'Mount Olympus', 'Thrace', 'Pompeii', 'Iliad', 'Odyssey', 'Argos',
]


def main():
    wiki = Wiki()
    directory = JOB / 'naming-evidence'
    directory.mkdir(exist_ok=True)
    for start in range(0, len(NAMES), 45):
        path = directory / f'en-fr-{start:03d}.json'
        if not path.exists():
            data = wiki.site('en').simple_request(
                action='query', prop='langlinks', titles='|'.join(NAMES[start:start + 45]),
                lllang='fr', lllimit='max', formatversion=2,
            ).submit()
            write_json(path, data)
        for page in read_json(path).get('query', {}).get('pages', []):
            print(page['title'], '=>', [x.get('title', x.get('*')) for x in page.get('langlinks', [])])
    mapping = read_json(JOB / 'link-map.json')
    targets = sorted({mapping[n]['mg'] for n in NAMES if n in mapping and mapping[n]['mg'] and '\ufffd' not in mapping[n]['mg']})
    path = directory / 'mg-name-pages.json'
    if not path.exists():
        data = wiki.site('mg').simple_request(
            action='query', prop='revisions', titles='|'.join(targets),
            rvprop='ids|timestamp|content', rvslots='main', formatversion=2,
        ).submit()
        write_json(path, data)
    print('Malagasy pages:', targets)


if __name__ == '__main__':
    main()
