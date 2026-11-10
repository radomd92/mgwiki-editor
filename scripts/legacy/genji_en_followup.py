"""Coordinator-only targeted Wikipedia metadata; no external-link access."""
from pathlib import Path

from mgwiki_editor.core import Wiki, now, write_json

JOB = Path("runs/genji-en-20261105-utf8")


def run():
    wiki = Wiki()
    groups = [
        ("names-intros-1.json", ["Jun'ichirō Tanizaki", "Fumiko Enchi", "Seiko Tanabe",
          "Jakucho Setouchi", "Osamu Hashimoto", "Yasunari Kawabata", "Kōzaburō Yoshimura",
          "Tetsuji Takechi", "Waki Yamato", "Gisaburō Sugii"]),
        ("names-intros-2.json", ["Miyako Maki", "Miki Minoru", "Osamu Dezaki", "Rio Asumi",
          "Machiko Midorikawa", "Suematsu Kenchō", "Yosano Akiko", "Tosa Mitsuoki",
          "J. Ingram Bryan", "Tokuhei Yamagishi"]),
    ]
    for name, titles in groups:
        output = JOB / "evidence" / name
        if output.exists():
            continue
        data = wiki.site("en").simple_request(
            action="query", titles="|".join(titles), prop="extracts",
            exintro=True, explaintext=True, exlimit="max", redirects=True, formatversion=2,
        ).submit()
        write_json(output, {"retrieved_at": now(), "scope": "lead extracts only", "response": data})
    output = JOB / "evidence" / "reference-expansions.json"
    if not output.exists():
        text = "\nGENJI_BREAK\n".join([
            "{{Zenkoku Accent Jiten|p=224}}", "{{Shinmeikai Nihongo Accent Jiten 2nd Edition|p=275}}",
            "{{NKBD}}", "{{Commons category}}", "{{Wikisource|ja|源氏物語}}",
            "{{gutenberg|no=66057|name=The Tale of Genji}}",
            "{{librivox book|title=Genji Monogatari (The Tale of Genji)|author=Murasaki Shikibu}}",
        ])
        data = wiki.site("en").simple_request(
            action="expandtemplates", title="The Tale of Genji", text=text,
            prop="wikitext", formatversion=2,
        ).submit()
        write_json(output, {"retrieved_at": now(), "input": text, "response": data})
    output = JOB / "evidence" / "citation-context.json"
    if not output.exists():
        data = wiki.site("en").simple_request(
            action="query", titles="Nihon Koten Bungaku Taikei|J. Ingram Bryan|Tokuhei Yamagishi",
            prop="revisions", rvprop="ids|content", rvslots="main", formatversion=2,
        ).submit()
        write_json(output, {"retrieved_at": now(), "response": data})
    print("Targeted metadata pinned")


if __name__ == "__main__":
    run()
