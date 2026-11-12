"""Article-independent section operations; filesystem fixtures only, no network."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError, digest, read_json, write_json
from mgwiki_editor.workflow import assemble_sections, coverage_report, heading_ranges, plan_sections


@pytest.fixture
def job(tmp_path: Path) -> Path:
    """Include local content and review/source-issue history that must survive unchanged."""
    directory = tmp_path / "job"
    directory.mkdir()
    (directory / "source.wiki").write_text(
        "Lead.<ref name=shared>Original metadata</ref>\n"
        "== Body ==\nText.<ref name=shared />\n"
        "=== Detail ===\nMore.\n== References ==\n<references />\n", encoding="utf-8",
    )
    for name, text in {
        "existing.wiki": "Local facts. [[Sokajy:Keep|Sort]]",
        "sandbox.wiki": "Prior sandbox.", "draft.wiki": "Do not overwrite draft.",
        "notes.wiki": "# Existing notes\nHistory retained.",
        "source-issues.md": "# ISS-001\nOpen source disagreement; nonblocking.\n",
    }.items():
        (directory / name).write_text(text, encoding="utf-8")
    write_json(directory / "review.json", {"checked": False})
    write_json(directory / "vocabulary.json", [{"original": "memo"}])
    return directory


def complete_workers(job: Path) -> None:
    """Use exact source copies as structural handoffs, not claimed Malagasy translations."""
    for row in read_json(job / "section-plan.json"):
        directory = job / row["directory"]
        shutil.copyfile(directory / "source.wiki", directory / "section.wiki")
        (directory / "notes.wiki").write_text("# Handoff\nReview pending.\n", encoding="utf-8")
        write_json(directory / "vocabulary.json", [])


def root_bytes(job: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in job.iterdir() if p.is_file()}


def test_plan_heading_coverage_and_no_shared_mutation(job: Path) -> None:
    before = root_bytes(job)
    result = plan_sections(job)
    assert result["sections"] == 3
    plan = read_json(job / "section-plan.json")
    assert [r["id"] for r in plan] == ["00-lead", "01-body", "02-references"]
    assert b"".join((job / row["directory"] / "source.wiki").read_bytes()
                    for row in plan) == before["source.wiki"]
    assert all((job / name).read_bytes() == data for name, data in before.items())
    assert read_json(job / "section-inputs.json")["artifacts"]["source.wiki"] == digest(
        before["source.wiki"],
    )


@pytest.mark.parametrize("source", [
    "Only lead; no headings.", "== First ==\nBody.\n",
    "Lead.\r\n== One ==\r\nBody.\r\n", "Lead.\n== One ==\nNo trailing newline",
    "<nowiki>\n== Not a heading ==\n</nowiki>\n== Real ==\nBody\n",
    "{{Box|\n== Nested ==\n}}\n== Real ==\nBody\n",
])
def test_heading_plan_preserves_all_bytes(job: Path, source: str) -> None:
    (job / "source.wiki").write_bytes(source.encode("utf-8"))
    plan_sections(job)
    plan = read_json(job / "section-plan.json")
    assert b"".join((job / row["directory"] / "source.wiki").read_bytes()
                    for row in plan) == source.encode("utf-8")


def test_grouping_merges_adjacent_short_sections_without_losing_bytes(job: Path) -> None:
    before = (job / "source.wiki").read_bytes()
    result = plan_sections(job, group_max_bytes=4000)
    plan = read_json(job / "section-plan.json")
    assert result["source_sections"] == 3
    assert result["sections"] < result["source_sections"]
    assert [r["id"] for r in plan] == ["00-lead"]
    assert plan[0]["headings"] == ["lead", "Body", "References"]
    assert plan[0]["merged_ids"] == ["00-lead", "01-body", "02-references"]
    assert plan[0]["start"] == 1
    assert b"".join((job / row["directory"] / "source.wiki").read_bytes()
                    for row in plan) == before
    assert b"== Body ==" in (job / plan[0]["directory"] / "source.wiki").read_bytes()


def test_grouping_zero_keeps_one_assignment_per_heading(job: Path) -> None:
    assert plan_sections(job, group_max_bytes=0)["sections"] == 3
    assert [r["id"] for r in read_json(job / "section-plan.json")] == [
        "00-lead", "01-body", "02-references"]
    assert all("merged_ids" not in r for r in read_json(job / "section-plan.json"))


def test_grouping_respects_size_limit_and_assembly(job: Path) -> None:
    (job / "source.wiki").write_text(
        "Lead.\n== A ==\n" + "a" * 3000 + "\n== B ==\n" + "b" * 3000 + "\n", encoding="utf-8")
    result = plan_sections(job, group_max_bytes=3500)
    plan = read_json(job / "section-plan.json")
    assert result["sections"] == 2
    assert [r["merged_ids"] for r in plan] == [["00-lead", "01-a"], ["02-b"]]
    assert all(r["group_bytes"] <= 3500 for r in plan)
    assert b"".join((job / r["directory"] / "source.wiki").read_bytes()
                    for r in plan) == (job / "source.wiki").read_bytes()


def test_grouped_plan_assembles_through_existing_gates(job: Path) -> None:
    plan_sections(job, group_max_bytes=5000)
    complete_workers(job)
    result = assemble_sections(job)
    assert result["status"] == "candidate_only"
    assert result["sections"] == 1
    integrated = read_json(job / "assembly/integrated-section-plan.json")
    assert [row["id"] for row in integrated] == ["00-lead"]
    assert (job / "assembly/draft.wiki").read_bytes() == (job / "source.wiki").read_bytes()


@pytest.mark.parametrize("value", [-1, 50001])
def test_grouping_rejects_out_of_range_limit(job: Path, value: int) -> None:
    before = root_bytes(job)
    with pytest.raises(GuardError):
        plan_sections(job, group_max_bytes=value)
    assert root_bytes(job) == before
    assert not (job / "sections").exists()


def test_broker_refuses_grouped_plan(job: Path, monkeypatch, capsys) -> None:
    from mgwiki_editor import cli, control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    monkeypatch.setattr(control, "client",
                        lambda *a: {"ok": True, "result": {"run": job.name, "intent": "translate"}})
    assert cli.main(["sections-plan", "--job", str(job), "--group-max-bytes", "4000"]) == 1
    assert "ungrouped" in capsys.readouterr().err


def test_heading_level_and_nested_heading_detection() -> None:
    text = "Lead\n== Body ==\nText\n=== Detail ===\nMore\n"
    assert len(heading_ranges(text, 2)) == 2
    assert len(heading_ranges(text, 3)) == 3
    with pytest.raises(GuardError, match="Heading level"):
        heading_ranges(text, 0)


@pytest.mark.parametrize("ranges", [
    [], {}, [{"id": "../escape", "start": 1, "end": 7}],
    [{"id": "one", "start": 2, "end": 7}],
    [{"id": "one", "start": 1, "end": 6}],
    [{"id": "one", "start": 1, "end": 8}],
    [{"id": "one", "start": True, "end": 7}],
    [{"id": "one", "start": 1, "end": 2}, {"id": "one", "start": 3, "end": 7}],
    [{"id": "one", "start": 1, "end": 3}, {"id": "two", "start": 3, "end": 7}],
])
def test_invalid_custom_ranges_write_nothing(job: Path, tmp_path: Path, ranges) -> None:
    path = tmp_path / "ranges.json"
    write_json(path, ranges)
    before = root_bytes(job)
    with pytest.raises(GuardError):
        plan_sections(job, ranges=path)
    assert root_bytes(job) == before
    assert not (job / "sections").exists()


def test_custom_ranges(job: Path, tmp_path: Path) -> None:
    path = tmp_path / "ranges.json"
    write_json(path, [{"id": "all", "start": 1, "end": 7, "heading": "Full scope"}])
    plan_sections(job, ranges=path)
    assert (job / "sections/all/source.wiki").read_bytes() == (job / "source.wiki").read_bytes()


@pytest.mark.parametrize("collision", [
    "section-plan.json", "section-inputs.json", "source-inventory.json", "sections/00-lead",
])
def test_plan_collisions_preflight_all_outputs(job: Path, collision: str) -> None:
    path = job / collision
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Keep me.", encoding="utf-8")
    with pytest.raises(GuardError, match="exists"):
        plan_sections(job)
    assert path.read_text() == "Keep me."
    assert not (job / "sections/01-body").exists()


def test_plan_refuses_symlink_parent(job: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (job / "sections").symlink_to(outside, target_is_directory=True)
    with pytest.raises(GuardError, match="symlink"):
        plan_sections(job)
    assert list(outside.iterdir()) == []


def test_assemble_new_candidate_leaves_root_artifacts_unchanged(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    before = root_bytes(job)
    result = assemble_sections(job)
    assert result["status"] == "candidate_only"
    assert root_bytes(job) == before
    assert (job / "assembly/draft.wiki").read_text().count("Original metadata") == 1
    assert "## 01-body" in (job / "assembly/section-handoffs.md").read_text()
    assert read_json(job / "assembly/assembly.json")["editorial_review"] == "pending"
    with pytest.raises(GuardError, match="exists"):
        assemble_sections(job)


@pytest.mark.parametrize("fragment", [
    " preformatted line\n", "\n  preformatted line\n\n", "line with trailing spaces  \n",
    "<pre>  exact indentation  </pre>\r\n",
])
def test_single_section_assembly_keeps_significant_whitespace(job: Path, fragment: str) -> None:
    (job / "source.wiki").write_bytes(fragment.encode("utf-8"))
    plan_sections(job)
    complete_workers(job)
    assemble_sections(job)
    assert (job / "assembly/draft.wiki").read_bytes() == fragment.encode("utf-8")


def test_multiple_section_assembly_only_adds_separators(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    fragments = [" first preformatted line  \n", " second block  ", "\n third block\n\n"]
    for row, fragment in zip(read_json(job / "section-plan.json"), fragments, strict=True):
        (job / row["directory"] / "section.wiki").write_text(fragment, encoding="utf-8")
    assemble_sections(job)
    draft = (job / "assembly/draft.wiki").read_text()
    for fragment in fragments:
        assert fragment in draft


def test_plan_survives_job_move(job: Path, tmp_path: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    moved = tmp_path / "relocated"
    job.rename(moved)
    assert assemble_sections(moved)["sections"] == 3


@pytest.mark.parametrize("name", ["source.wiki", "existing.wiki", "sandbox.wiki"])
def test_assembly_rejects_changed_snapshot(job: Path, name: str) -> None:
    plan_sections(job)
    complete_workers(job)
    (job / name).write_text("Changed", encoding="utf-8")
    with pytest.raises(GuardError, match="input changed"):
        assemble_sections(job)
    assert not (job / "assembly").exists()


def test_assembly_rejects_changed_fragment_source(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    (job / "sections/00-lead/source.wiki").write_text("Changed", encoding="utf-8")
    with pytest.raises(GuardError, match="Section source changed"):
        assemble_sections(job)


@pytest.mark.parametrize("artifact", ["section.wiki", "notes.wiki", "vocabulary.json"])
def test_assembly_missing_handoff_preserves_successes(job: Path, artifact: str) -> None:
    plan_sections(job)
    complete_workers(job)
    before = (job / "sections/00-lead/section.wiki").read_bytes()
    (job / "sections/01-body" / artifact).unlink()
    with pytest.raises(GuardError, match="Missing"):
        assemble_sections(job)
    assert (job / "sections/00-lead/section.wiki").read_bytes() == before
    assert not (job / "assembly").exists()


@pytest.mark.parametrize("artifact", ["section.wiki", "notes.wiki"])
def test_assembly_empty_handoff(job: Path, artifact: str) -> None:
    plan_sections(job)
    complete_workers(job)
    (job / "sections/01-body" / artifact).write_text(" \n", encoding="utf-8")
    with pytest.raises(GuardError, match="Empty section or handoff"):
        assemble_sections(job)


@pytest.mark.parametrize("status", ["blocked", "failed"])
def test_assembly_blocked_section(job: Path, status: str) -> None:
    plan_sections(job)
    complete_workers(job)
    rows = read_json(job / "section-plan.json")
    rows[1]["status"] = status
    write_json(job / "section-plan.json", rows)
    with pytest.raises(GuardError, match="incomplete"):
        assemble_sections(job)


@pytest.mark.parametrize("artifact", ["proposal.json", "receipt.json"])
def test_assembly_never_retries_prepared_or_attempted_job(job: Path, artifact: str) -> None:
    plan_sections(job)
    complete_workers(job)
    write_json(job / artifact, {"status": "unconfirmed"})
    with pytest.raises(GuardError, match="fresh job"):
        assemble_sections(job)


def test_assembly_rejects_unsafe_output(job: Path, tmp_path: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    with pytest.raises(GuardError, match="inside the job"):
        assemble_sections(job, output=tmp_path / "outside")


def test_assembly_preserves_dangling_output_symlink(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    output = job / "candidate"
    output.symlink_to(job / "missing", target_is_directory=True)
    with pytest.raises(GuardError, match="exists"):
        assemble_sections(job, output=output)
    assert output.is_symlink()
    assert not (job / "missing").exists()


def test_section_source_symlink_keeps_handoff_directory(job: Path, tmp_path: Path) -> None:
    ranges = tmp_path / "ranges.json"
    write_json(ranges, [{"id": "all", "start": 1, "end": 7}])
    plan_sections(job, ranges=ranges)
    complete_workers(job)
    source = job / "sections/all/source.wiki"
    source.unlink()
    source.symlink_to(job / "source.wiki")
    assert assemble_sections(job)["sections"] == 1


@pytest.mark.parametrize("artifact", ["proposal.json", "receipt.json"])
def test_planning_preserves_prepared_or_attempted_job(job: Path, artifact: str) -> None:
    write_json(job / artifact, {"status": "unconfirmed"})
    before = root_bytes(job)
    with pytest.raises(GuardError, match="fresh job"):
        plan_sections(job)
    assert root_bytes(job) == before


@pytest.mark.parametrize("inputs", [[], {"schema": 1, "artifacts": []}, {}])
def test_malformed_input_manifest_fails_before_output(job: Path, inputs) -> None:
    plan_sections(job)
    complete_workers(job)
    write_json(job / "section-inputs.json", inputs)
    with pytest.raises(GuardError, match="input manifest"):
        assemble_sections(job)
    assert not (job / "assembly").exists()


def test_worker_vocabulary_evidence_rebased_without_status_promotion(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    evidence = job / "evidence"
    evidence.mkdir()
    write_json(evidence / "lookup.json", {"status": "not_found"})
    record = {"source_term": "unknown", "source_sense": "specific sense", "status": "unresolved",
              "evidence_files": ["../../evidence/lookup.json", "source.wiki"]}
    write_json(job / "sections/00-lead/vocabulary.json", {"terms": [record]})
    assemble_sections(job)
    result = read_json(job / "assembly/worker-vocabulary.json")[0]
    assert result["status"] == "unresolved"
    assert result["source_sense"] == "specific sense"
    assert result["evidence_files"] == [
        "evidence/lookup.json", "sections/00-lead/notes.wiki",
        "sections/00-lead/section.wiki", "sections/00-lead/source.wiki",
    ]
    assert "evidence/lookup.json" in read_json(job / "assembly/assembly.json")["inputs"]


@pytest.mark.parametrize("records", [
    {"unexpected": []}, ["not a record"], [{"evidence_files": "source.wiki"}],
    [{"evidence_files": ["missing.json"]}], [{"evidence_files": ["/etc/hosts"]}],
    [{"evidence_files": ["../../../outside.json"]}],
])
def test_worker_bad_vocabulary_fails_before_any_output(job: Path, records) -> None:
    plan_sections(job)
    complete_workers(job)
    write_json(job / "sections/00-lead/vocabulary.json", records)
    with pytest.raises(GuardError):
        assemble_sections(job)
    assert not (job / "assembly").exists()


@pytest.mark.parametrize("text", [
    "Text <ref name=undefined />",
    "<ref name=duplicate>One</ref><ref name=duplicate>Two</ref>",
])
def test_assembly_rejects_broken_references(job: Path, text: str) -> None:
    plan_sections(job)
    complete_workers(job)
    (job / "sections/01-body/section.wiki").write_text(text, encoding="utf-8")
    with pytest.raises(GuardError, match="named references"):
        assemble_sections(job)


def test_assembly_opt_in_citation_conversion(job: Path) -> None:
    plan_sections(job)
    complete_workers(job)
    path = job / "sections/01-body/section.wiki"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("{{cite book|title=Original|author17=Last author|custom=Keep}}")
    assemble_sections(job, native_citations=True)
    text = (job / "assembly/draft.wiki").read_text()
    assert "author17: Last author" in text and "custom: Keep" in text
    assert read_json(job / "assembly/citation-conversions.json")[0]["source"].startswith(
        "{{cite book",
    )


def test_coverage_reports_differences_not_approval(job: Path) -> None:
    (job / "source.wiki").write_text(
        "[[File:One.jpg|caption]][[File:One.jpg|again]]\n"
        "<gallery>\nFile:Two.svg|caption\n</gallery>\n"
        "{{Box|image=Three.png}} https://example.invalid/reference", encoding="utf-8",
    )
    draft = job / "draft.wiki"
    draft.write_text("[[File:One.jpg|caption]][[File:Extra.jpg]]", encoding="utf-8")
    result = coverage_report(job, draft)
    assert result["missing_files"] == {"One.jpg": 1, "Two.svg": 1}
    assert result["extra_files"] == {"Extra.jpg": 1}
    assert result["missing_source_urls"] == ["https://example.invalid/reference"]
    assert result["source"]["template_file_candidates"][0]["value"] == "Three.png"
    assert result["status"] == "review_required"


def test_offline_cli_never_constructs_wiki(job: Path, monkeypatch, capsys) -> None:
    def forbidden():
        raise AssertionError("Offline workflow must not instantiate Wiki")

    monkeypatch.setattr(cli, "Wiki", forbidden)
    assert cli.main(["sections-plan", "--job", str(job)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "planned"
    complete_workers(job)
    output = job / "candidate"
    assert cli.main(["sections-assemble", "--job", str(job), "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "candidate_only"
    assert cli.main(["coverage", "--job", str(job), "--draft", str(output / "draft.wiki"),
                     "--output", str(job / "coverage.json")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "review_required"
    assert (job / "coverage.json").is_file()
