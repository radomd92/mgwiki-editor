"""Three canonical English headwords after source-spelling lookups; one worker."""
from mgwiki_editor.core import GuardError, lookup, now, read_json, write_json
from programming_plan import JOB


if __name__=='__main__':
    items=[('twos',"two's complement"),('ones',"one's complement"),('turing','Turing complete')]
    results=[]
    for ident,word in items:
        f=JOB/'evidence'/f'lookup-canonical-{ident}.json'
        if not f.exists():
            try:
                data=lookup('en',word)
            except Exception as exc:
                if any(x in str(exc).lower() for x in ['cooldown','deferred','circuit','overload','ratelimit']):
                    write_json(JOB/'evidence/dictionary-canonical-stop.json',
                        {'at':now(),'status':'deferred','word':word,'error':str(exc)})
                    raise
                if not isinstance(exc,GuardError):
                    raise
                data={'edition':'en','word':word,'status':'failed','retrieved_at':now(),'error':str(exc)}
            write_json(f,data)
        d=read_json(f)
        results.append({'word':word,'file':str(f.relative_to(JOB)),'status':d['status'],
                        'definitions':[e.get('definitions',[]) for e in d.get('entries',[])]})
    write_json(JOB/'canonical-headword-review.json',results)
    print(results)
