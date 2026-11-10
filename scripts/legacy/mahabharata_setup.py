"""Pin the requested article using a targeted Malagasy language-link query."""
from pathlib import Path
from mgwiki_editor.core import Wiki, initialize


class TargetedWiki(Wiki):
    def existing_title(self, language, source_title, fallback):
        data = self.site(language).simple_request(
            action="query", prop="langlinks", titles=source_title,
            lllang="mg", lllimit=1, formatversion=2,
        ).submit()
        pages = data["query"]["pages"]
        links = pages[0].get("langlinks", [])
        return links[0]["title"] if links else fallback


if __name__ == "__main__":
    state = initialize(TargetedWiki(), Path("runs/mahabharata-20261108"),
                       "en", "Mahabharata", "Mahabharata")
    for key in ("source", "existing", "sandbox"):
        print(key, state[key]["title"], state[key]["revision_id"])
