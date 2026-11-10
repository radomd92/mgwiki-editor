"""Initialize Baseball using a language-filtered interlanguage API query."""
from pathlib import Path

from mgwiki_editor.core import Wiki, initialize


class FocusedWiki(Wiki):
    def existing_title(self, language, source_title, fallback):
        data = self.site(language).simple_request(
            action="query", prop="langlinks", titles=source_title,
            lllang="mg", lllimit="max", formatversion=2,
        ).submit()
        links = data["query"]["pages"][0].get("langlinks", [])
        return links[0]["title"] if links else fallback


if __name__ == "__main__":
    state = initialize(
        FocusedWiki(), Path("runs/baseball-20261106"), "en", "Baseball", "Baseball",
    )
    print({key: (state[key]["title"], state[key]["revision_id"]) for key in
           ("source", "existing", "sandbox")})
