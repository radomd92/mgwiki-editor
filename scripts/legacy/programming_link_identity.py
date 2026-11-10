"""Finish two short local-topic identity checks through the single Wiki gateway."""
from mgwiki_editor.core import Wiki, now, read_json, write_json
from programming_plan import JOB


if __name__=='__main__':
    wiki=Wiki()
    work=[('final-local-identity.json','mg',dict(prop='info|extracts',titles='PHP|Tranonkala',
        exintro=1,explaintext=1,exlimit='max',formatversion=2)),
          ('final-type-safety.json','en',dict(prop='langlinks',titles='Type safety',
        lllang='mg',lllimit='max',formatversion=2))]
    for filename,language,params in work:
        f=JOB/'evidence'/filename
        if not f.exists():
            result=wiki.site(language).simple_request(action='query',**params).submit()
            write_json(f,{'retrieved_at':now(),'response':result})
        print(filename,read_json(f))
