"""Serialized read-only terminology evidence with recent local lookup reuse."""
from pathlib import Path
import re
import shutil
from mgwiki_editor.core import lookup, read_json, write_json, now

JOB=Path('runs/mahabharata-20261108')
PAIRS=[
 ('redaction','fanitsiana'),('interpolation','fanampiana'),('frame story','tantara'),
 ('bard','mpitantara'),('archetype','niandohana'),('stemma codicum','tetiarana'),
 ('recension','dikan-teny'),('critical edition','fanontana'),('sacrifice','sorona'),
 ('sarpasattra','bibilava'),('ashvamedha','soavaly'),('Brahmana','soratra'),
 ('Pancharatra','fampianarana'),('shastra','fampianarana'),('kavya','tononkalo'),
 ('historicity','tantara'),('archaeoastronomy','astronomia'),('genealogy','tetiarana'),
 ('celibacy','tokan-tena'),('swayamvara','fanambadiana'),('niyoga','fiterahana'),
 ('renunciate','fialana'),('jaundiced','mavo'),('mantra','raikipitenenana'),
 ('boon','fitahiana'),('lac','dity'),('ghee','dibera'),('suta','kalesy'),
 ('alms','fiantrana'),('polyandry','fanambadiana'),('loaded dice','fitaka'),
 ('pilgrimage','fivahiniana'),('Kshatriya','mpiady'),('chivalry','fitsipika'),
 ('proportionality','fifandanjana'),('vulgate','dikan-teny'),
 ('transcreation','fandikana'),('abridgment','fanafohezana'),('patronage','fanohanana'),
 ('hagiography','tantara'),('canon','soratra'),('chakravartin','mpanjaka'),
 ('Tirthankara','mpampianatra'),('karma','asa'),('moksha','fanafahana'),
 ('Shramana','mpitoka-monina'),('possession','fanahy'),('conglomerate','orinasa'),
 ('dharmayuddha','ady'),('war of succession','fifandimbiasana'),
 ('compositional layers','sosona'),('parva','fizarana'),
 ('sutra','fitsipika'),('rishi','olon-kendry'),('svarga','lanitra'),
 ('khila','fanampiny'),('ochre','volontany'),('brahmin','mpisorona'),
 ('public domain',"zon'ny mpamorona"),('hermitage','fonenana'),('dhoti','lamba'),
 ('barbed','farango'),('pitch accent','lantom-peo'),('classics','sivilizasiôna'),
 ('jaundice','jôndisy'),
]


def slug(word):
    return re.sub(r'[^a-z0-9]+','-',word.lower()).strip('-')


if __name__=='__main__':
    cache={}
    for p in sorted(Path('runs').glob('**/lookup-*.json')):
        if p.is_relative_to(JOB): continue
        try: data=read_json(p)
        except (ValueError,OSError): continue
        edition=data.get('edition'); word=data.get('word')
        if edition and word and data.get('status') in {'found','missing','no_matching_language'}:
            cache.setdefault((edition,word.casefold()),p)
    requests=[]; seen=set()
    for en,mg in PAIRS:
        for edition,word in [('en',en),('mg',mg)]:
            key=(edition,word.casefold())
            if key in seen: continue
            seen.add(key)
            dest=JOB/'evidence'/f'lookup-{edition}-{slug(word)}.json'
            reused=None
            if not dest.exists():
                prior=cache.get(key)
                if prior:
                    shutil.copyfile(prior,dest); reused=str(prior)
                else:
                    try: data=lookup(edition,word)
                    except Exception as exc:
                        data=dict(edition=edition,word=word,status='lookup_failed',retrieved_at=now(),
                                  error=type(exc).__name__,message=str(exc))
                    write_json(dest,data)
            data=read_json(dest)
            requests.append(dict(edition=edition,word=word,evidence_file=str(dest.relative_to(JOB)),
                                 status=data.get('status'),reused_from=reused))
            print(edition,word,data.get('status'),flush=True)
            # A Wikimedia cooldown/circuit is not bypassed by moving to another term.
            if data.get('status')=='lookup_failed' and any(x in data.get('message','').lower() for x in ['cooldown','deferred','circuit','429','503','maxlag','ratelimited']):
                write_json(JOB/'terminology-request-index.json',requests)
                raise SystemExit('Deferred by shared request guard; retained completed lookups.')
    write_json(JOB/'terminology-request-index.json',requests)
