"""Small coordinator integration edits, never a new article generation."""
from pathlib import Path
import mwparserfromhell as mw

JOB=Path('runs/iliad-en-20261106')

def main():
 p=JOB/'draft.wiki';s=p.read_text(encoding='utf-8')
 replacements={
  "Ny '''''Iliasy''''' (''Iliad''":"Ny '''''Iliasy''''' na '''''Iliady''''' (''Iliad''",
  "=== Fiandohan' ny tantara (boky 1–4) ===":"=== Fiandohan' ny tantara (boky faha-1–4) ===",
  "=== Faharesen' ny Grika (Boky 8–15) ===":"=== Faharesen' ny Grika (boky faha-8–15) ===",
  "==== Haja sy fanajana: timē ====":"==== Haja sy fanajana: ''timē'' ====",
  "==== Fihoaram-pefy noho ny avonavona: hybris ====":"==== Fihoaram-pefy noho ny avonavona: ''hybris'' ====",
  "=== Hatezerana (mēnis) ===":"=== Hatezerana (''mēnis'') ===",
  "Sarintanin' i [[Grisia]] araka ny fitantaran' i Homer":"Sarintanin' i [[Grisia]] araka ny fitantaran' i [[Hômerôsy|Homer]]",
  "Rehefa avy naka hevitra tao amin' ny toerana fangatahana valin' ny andriamanitra tao Dodona i Herodotus":"Rehefa avy naka hevitra tao amin' ny toerana fangatahana valin' ny andriamanitra tao Dodona i [[Herôdôtôsy|Herodotus]]",
  "tamin' ny Andron' ny Vy, izany hoe tamin' ny andron' i Homer":"tamin' ny [[Andron' ny Vy]], izany hoe tamin' ny andron' i Homer",
 }
 for a,b in replacements.items():
  if a not in s:print('Already adapted or context differs:',a)
  else:s=s.replace(a,b,1)
 code=mw.parse(s)
 for comment in list(code.filter_comments()):
  try:code.replace(comment,'')
  except ValueError:pass
 p.write_text(str(code),encoding='utf-8')
 print('Coordinator integration refinements written')

if __name__=='__main__':main()
