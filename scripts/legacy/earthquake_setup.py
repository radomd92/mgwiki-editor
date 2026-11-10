"""Pin Earthquake with verified Malagasy interlanguage title and reused source."""
import json
from pathlib import Path

from mgwiki_editor.core import Wiki, initialize


if __name__ == "__main__":
    wiki = Wiki()
    # The source has no mg langlink. Local search confirms this spelling.
    target = "Horohoron-tany"
    source = json.loads(Path("/tmp/opencode/earthquake-source.json").read_text())
    existing = json.loads(Path("/tmp/opencode/earthquake-existing-hyphen.json").read_text())

    class PinnedWiki(Wiki):
        def snapshot(self, language, page_title, *, sandbox=False):
            if language == "en" and page_title == "Earthquake" and not sandbox:
                return source
            if language == "mg" and page_title == target and not sandbox:
                return existing
            return super().snapshot(language, page_title, sandbox=sandbox)

    wiki.__class__ = PinnedWiki
    state = initialize(wiki, Path("runs/earthquake-20261108"), "en", "Earthquake",
                       target, existing_title=target)
    print({key: (state[key]["title"], state[key]["revision_id"])
           for key in ("source", "existing", "sandbox")})
