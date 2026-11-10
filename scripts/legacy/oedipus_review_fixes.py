"""Apply coordinator's final source-comparison findings, before preparation."""
import json
from pathlib import Path

JOB = Path('runs/oedipus-20261105')


def main():
    path = JOB / 'draft.wiki'
    text = path.read_text(encoding='utf-8')
    for old, new in [
        ("fitambaran' ny faniriana tsy tsapa mitondra ny anarany (na fanirian' ny zaza lahy",
         "fitambaran' ny faniriana tsy tsapa mitondra ny anaran' i Œdipe (na faniriana tsy tsapan' ny zaza lahy"),
        ("Nampaka an' i Tiresias i Œdipe, ary nampitandrina azy io mba tsy hitady izay namono an' i Laius.",
         "Nampaka an' i Tiresias i Œdipe. Nampitandrina an' i Œdipe kosa i Tiresias mba tsy hitady izay namono an' i Laius."),
        ("tamin' ny taonjato voalohany taorian' i Kristy Misy fahasamihafana",
         "tamin' ny taonjato voalohany taorian' i Kristy. Misy fahasamihafana"),
    ]:
        if old not in text:
            raise RuntimeError('Expected review context is missing')
        text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')
    vocab_path = JOB / 'vocabulary.json'
    entries = json.loads(vocab_path.read_text(encoding='utf-8'))
    for entry in entries:
        if entry['source_term'] == 'neck amphora / red-figure':
            entry['evidence_files'] += ['evidence/lookup-en-red-figure.json', 'evidence/lookup-mg-red-figure.json']
            entry['reason'] += ' Both additional red-figure lookups failed HTTP 502, not dictionary misses; descriptive sary mena preserves the source caption without adding a fabrication-technique claim.'
        if entry['source_term'] == 'satyr play':
            entry['evidence_files'] += ['evidence/lookup-en-satyr.json', 'evidence/lookup-mg-satyr.json']
        if entry['source_term'] == 'folkloristics':
            entry['evidence_files'] += ['evidence/lookup-en-folklore.json', 'evidence/lookup-mg-folklore.json']
    vocab_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as stream:
        stream.write("\n== Fanitsiana hita tamin’ ny famakiana ny dika natambatra ==\n")
        stream.write("Natao mazava fa i Tiresias no mampitandrina an’ i Œdipe fa tsy ny mifamadika amin’ izany (source 44). Nosoloina anaran’ i Œdipe ny mpisolo anarana mety hampifangaro ny anaran’ ny teôrian’ i Freud sy ny anaran’ ilay mpanjaka. Naverina ny teboka faran’ ny fehezanteny momba ny taonjato voalohany rehefa nosoratana feno ny taor. J.K. Ny endrika paper titles sy citation prose dia nodinihina; tsy novaina ny tena lohateny, mpanoratra, URL na daty bibliografika.\n")
    print('Final source-comparison fixes applied')


if __name__ == '__main__':
    main()
