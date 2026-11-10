"""Fresh English Genji job; guarded sequential Wikimedia operations only."""
from pathlib import Path
import shutil

from mgwiki_editor.core import Wiki, initialize


class TargetedWiki(Wiki):
    def existing_title(self, language, source_title, fallback):
        data = self.site(language).simple_request(
            action="query", prop="langlinks", titles=source_title,
            lllang="mg", lllimit=1, formatversion=2,
        ).submit()
        for page in data["query"]["pages"]:
            for link in page.get("langlinks", []):
                if link["lang"] == "mg":
                    return link["title"]
        return fallback


if __name__ == "__main__":
    # Explicitly requested removal, limited to identified earlier Genji work.
    for name in ("genji-ja-20261104", "genji-ja-20261104-sections"):
        path = Path("runs") / name
        if path.is_dir():
            shutil.rmtree(path)
    for name in (
        "genji_chapter08_evidence.py", "genji_evidence.py", "genji_job.py",
        "genji_merge.py", "genji_parenthetical_evidence.py", "genji_pending.py",
        "genji_plan.py", "genji_targeted_evidence.py",
    ):
        Path(name).unlink(missing_ok=True)
    state = initialize(
        TargetedWiki(), Path("runs/genji-en-20261105-utf8"),
        "en", "The Tale of Genji", "Tantaran'i Genji",
    )
    print(state["destination"])
    for name in ("source", "existing", "sandbox"):
        print(name, state[name]["title"], state[name]["revision_id"])
