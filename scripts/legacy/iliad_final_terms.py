"""Final read-only technical vocabulary checks, serial and bounded."""
import re
from mgwiki_editor.core import lookup, now, write_json, GuardError
from iliad_more_terms import JOB

PAIRS=[('editio princeps','fanontana'),('chivalric romance','tantara'),('librettist','tononkira'),('papyrus','papiry'),('accusative','fameno'),('historicity','tantara'),('dogma','foto-pinoana'),('introspection','fandinihana'),('basileus','andriana'),('aspis','ampinga'),('sakos','ampinga'),('white-ground','lafika'),('facsimile','dika'),('miniseries','tantara mitohy'),('postmodernism','literatiora')]

def main():
 for en,mg in PAIRS:
  for edition,word in [('en',en),('mg',mg)]:
   p=JOB/'evidence'/('lookup-'+edition+'-final-'+re.sub('[^a-z0-9]+','-',en)+'.json')
   if p.exists():continue
   try:result=lookup(edition,word)
   except GuardError as e:
    result=dict(status='failed',edition=edition,word=word,retrieved_at=now(),error=str(e))
    write_json(p,result)
    if any(x in str(e).lower() for x in ('cooldown','overload','deferred','429','503')):raise
   write_json(p,result)
 print('Final sense checks:',len(PAIRS))

if __name__=='__main__':main()
