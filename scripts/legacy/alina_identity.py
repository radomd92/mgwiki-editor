"""Read only the source's Malagasy interlanguage identity through guarded Wiki."""
import json
from mgwiki_editor.core import Wiki

if __name__ == "__main__":
    wiki = Wiki()
    data = wiki.site("en").simple_request(
        action="query", prop="langlinks", titles="One Thousand and One Nights",
        lllang="mg", formatversion=2,
    ).submit()
    print(json.dumps(data, ensure_ascii=False))
