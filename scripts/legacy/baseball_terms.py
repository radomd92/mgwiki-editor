"""Sequential read-only sense checks; exact cached evidence is reused."""
import re
from pathlib import Path

from mgwiki_editor.core import GuardError, lookup, now, write_json

JOB=Path('runs/baseball-20261106')
WORDS="""bat|fielder|baserunner|designated hitter|shortstop|tag|playoff|doubleheader|home plate|diamond|foul line|fair territory|foul territory|infield|outfield|pitcher's mound|rubber|mitt|webbing|cork|knob|infielder|outfielder|basepath|first baseman|second baseman|third baseman|left fielder|center fielder|right fielder|umpire|batter's box|batter-runner|putout|safe|hit|single|double|triple|grand slam|error|dead ball|flyout|tag up|stolen base|pitch|strike zone|strikeout|walk|hit by pitch|ground out|force out|tag out|double play|triple play|dugout|plate appearance|caught stealing|batting order|substitution|roster|position player|starting pitcher|relief pitcher|closer|bullpen|utility player|pinch hitter|breaking ball|pitchout|shift|ground ball|hit and run|contact hitter|sacrifice bunt|scoring position|squeeze play|sacrifice fly|codification|antecedent|dead-ball era|spitball|power hitter|farm system|Hispanic|reserve clause|free agency|wild card|interleague|amateur|rally|draw|line drive|partnership|wicket|artificial turf|warning track|pull hitter|box score|official scorer|at bat|fielder's choice|runs batted in|batting average|save|on deck|innings pitched|winning percentage|earned run average|assist|total chances|fielding average|intentional walk|on-base percentage|total bases|on-base plus slugging|walks plus hits per inning pitched|wins above replacement|replacement-level player|white-collar|blue-collar|nativize|primetime|draft|varsity|euphemism|clutch|vaudeville|parody|musical|beat|canon|nonfiction|trade card|trading card|fantasy baseball|tee|heritage""".split('|')
CANDIDATES=['kibay','toby','fihodinana','mpanipy','mpikapoka','mpisambotra','mpiaro',
            'mpihazakazaka','fanesorana','isa','kapoka','fanipazana','baolina',
            'fandikan-dalàna','antontanisa','sterôida','fialamboly',
            'faritra','fahadisoana','fandresena','paikady','mpitsara','mpanazatra',
            'fonon-tanana','bosoa','tahiry','fanahafana','ligy','matihanina',
            'soatoavina','fanoharana','safidy','fitsipika']


def main():
    evidence=JOB/'evidence'
    pairs=[('en',w) for w in WORDS]+[('mg',w) for w in CANDIDATES]
    import sys
    start=int(sys.argv[1]) if len(sys.argv)>1 else 0
    stop=int(sys.argv[2]) if len(sys.argv)>2 else len(pairs)
    existing={}
    import json
    for p in evidence.glob('lookup-*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        existing[(d.get('edition'),d.get('word'))]=p
    for edition,word in pairs[start:stop]:
        if (edition,word) in existing:
            continue
        path=evidence/f'lookup-{edition}-extra-{re.sub(r"[^a-z0-9]+","-",word)}.json'
        try:
            data=lookup(edition,word)
        except GuardError as exc:
            if any(x in str(exc).lower() for x in ('cooldown','deferred','circuit','rate','overload')):
                raise
            data={'status':'failed','word':word,'edition':edition,'retrieved_at':now(),'error':str(exc)}
        write_json(path,data)
    print('Completed term slots',start,stop,'of',len(pairs))


if __name__=='__main__':
    main()
