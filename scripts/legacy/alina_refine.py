"""Apply coordinator's targeted whole-article review corrections offline."""
import json
import re
from pathlib import Path

J=Path('runs/alina-iraika-20261105')


def main():
    p=J/'draft.wiki'
    s=p.read_text(encoding='utf-8')
    changes=[
      ('[[#Crime fiction elements|', '[[#Tantara momba ny heloka bevava|'),
      ('[[#Unreliable narrator|', '[[#Mpitantara tsy azo itokisana|'),
      ("sora-tanana siriana tamin' ny taonjato faha-14 na faha-15 ao amin' ny", "sora-tanana siriana ao amin' ny"),
      ("''jackal'' (biby iray karazana amin' ny alika)", "''jackal'' (biby dia mitovitovy amin' ny alika)"),
      ("Fonosiny amin' ny taratasy ny perany", "Fonosiny amin' ny taratasy ny perany"),
      ("Fonosiny amin' ny taratasy ny perany", "Fonosiny amin' ny taratasy ny peratra anaovany"),
      ("rima anatiny ao amin' ny", "fitovian' ny feo ao anatin' ny andalana (rima anatiny) ao amin' ny"),
      ("famirapiratan' ny", "famirapiratan' ny"),
      ("toa an' i Aladdin, Sinbad ary Ali Baba", "toa an' i [[Aladin ou la Lampe merveilleuse|Aladdin]], Sinbad ary Ali Baba"),
      ("fanontana mampitaha sy mandinika ireo sora-tanana, amin' ny", "fanontana [[Fitsikerana lahatsoratra|mampitaha sy mandinika ireo sora-tanana]], amin' ny"),
      ("ilay zandriny indrindra tamin' izy roa lahy", "ilay tanora kokoa tamin' izy roa lahy"),
      ("Ferrucio Busoni:", "Ferruccio Busoni:"),
      ("''1001 Arabian Nights (song)''", "''1001 Arabian Nights''"),
      ("Ny dia fahadimin' i Sindbad", "Ny dia fahadimin' i Sinbad"),
      ("Sindbad sy ny Lohasahan' ny Diamondra", "Sinbad sy ny Lohasahan' ny Diamondra"),
      ("firaka varahina sy fanitso", "varahina mavo"),
      ('* Roman\n', '* Rômana\n'),
      ("«The Thousand-and-Second Tale of Scheherazade»", "''The Thousand-and-Second Tale of Scheherazade''"),
      ("''La Mama Experimental Theatre Club'' (klioba La Mama momba ny teatra andrana)", "''La Mama Experimental Theatre Club'' (La Mama, toerana fanaovana teatra andrana)"),
      ("Mitranga any amin' ny hoavy afaka 1 500 taona ireo sarimihetsika, nefa manaraka akaiky kokoa ny tantara tany am-boalohany ao amin' ny ''Alina iraika amby arivo'' noho ireo dika nataon' i [[Disney]], anisan' izany ny fametrahana ny zava-mitranga any Azia.", "Mitranga any Azia, amin' ny hoavy afaka 1 500 taona, ireo sarimihetsika."),
    ]
    report=[]
    for old,new in changes:
        if old==new:
            continue
        count=s.count(old)
        if not count:
            raise RuntimeError('Expected phrase absent: '+old)
        s=s.replace(old,new)
        report.append({'old':old,'new':new,'count':count})
    # Repair doubled italics caused by preformatted source citation title fields.
    for title in ["Reviewed work(s): ''Story-Telling Techniques in the Arabian Nights'' by David Pinault", "Pasolini's Splendid Infidelities: Un/Faithful Film Versions of ''The Thousand and One Nights''"]:
        s=s.replace("''"+title+"''", "''"+title.replace("''",'')+"''")
    s=s.replace("''[http://www.al-hakawati.net/english/Stories_Tales/laila170.asp ''The Story of Gherib and his Brother Agib'']''", "''[http://www.al-hakawati.net/english/Stories_Tales/laila170.asp The Story of Gherib and his Brother Agib]''")
    p.write_text(s,encoding='utf-8')
    (J/'coordinator-corrections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
