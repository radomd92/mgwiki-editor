"""Serial read-only terminology evidence through the project gateway."""
import json
from pathlib import Path

from mgwiki_editor.core import GuardError, lookup, now

J = Path('runs/alina-iraika-20261105')
TERMS = [
 ('frame story','tantara'), ('recension','dika'), ('critical edition','fanitsiana'),
 ('foreshadowing','fambara'), ('cliffhanger','fitantarana'),
 ('self-fulfilling prophecy','faminaniana'), ('ghoul','faty'), ('jinn','jiny'),
 ('vizier','viziry'), ('qahramana','mpitantana'), ('leitwortstil','famerimberenana'),
 ('thematic patterning','lohahevitra'), ('unreliable narrator','mpitantantara'),
 ('suspense','fihenjanana'), ('burlesque','hatsikana'), ('erotica','firaisana'),
 ('bowdlerize','fanesorana'), ('prose','lahatsoratra'), ('couplet','andalana'),
 ('quatrain','tononkalo'), ('science fiction','siansa'), ('fantasy','mahagaga'),
 ('dramatic visualization','famaritana'), ('retrocausality','antony'),
 ('automaton','milina'), ('primitive communism','fiaraha-monina'),
 ('abjad','abidy'), ('manhwa','tantara an-tsary'), ('manga','sary'),
 ('tempera','loko'), ('woodcut','sokitra'), ('pastiche','tahaka'),
 ('brass','varahina'), ('jackal','alika'), ('major','tonalite'),
 ('prolepsis','fitantarana'), ('millboard','baoritra'), ('anatomy','firafitra'),
]


def main():
    failures=0
    for en,mg in TERMS:
        for lang,word in [('en',en),('mg',mg)]:
            path=J/('lookup-'+lang+'-'+word.replace(' ','-')+'.json')
            if path.exists():
                continue
            try:
                data=lookup(lang,word)
            except GuardError as exc:
                data={'edition':lang,'word':word,'status':'lookup_failed','error':str(exc),'retrieved_at':now()}
                failures+=1
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            print(lang,word,data['status'],flush=True)
            if failures>=3:
                return


if __name__=='__main__':
    main()
