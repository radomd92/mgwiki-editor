package scan

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeFile(t *testing.T, path, text string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(text), 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestInventoryCountsRawMarkup(t *testing.T) {
	path := filepath.Join(t.TempDir(), "draft.wiki")
	writeFile(t, path, "'''X''' [[A|a]] [[File:F.jpg|thumb]] [[Sokajy:C]]\n"+
		"{{Box|v=1}} <ref name=\"r\">body</ref> <ref name=r /> https://e.org\n== H ==\n")
	result, err := InventoryFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if result.Files["F.jpg"] != 1 {
		t.Fatalf("files = %#v", result.Files)
	}
	if len(result.Categories) != 1 || result.Categories[0] != "Sokajy:C" {
		t.Fatalf("categories = %#v", result.Categories)
	}
	if result.LinkTargets["A"] != 1 || result.LinkTargets["Sokajy:C"] != 1 {
		t.Fatalf("links = %#v", result.LinkTargets)
	}
	if result.Templates["Box"] != 1 {
		t.Fatalf("templates = %#v", result.Templates)
	}
	if len(result.References) != 1 || result.References[0].Name != "r" || result.References[0].Count != 2 {
		t.Fatalf("references = %#v", result.References)
	}
	if len(result.Headings) != 1 || result.Headings[0] != "H" {
		t.Fatalf("headings = %#v", result.Headings)
	}
	if len(result.URLs) != 1 || result.URLs[0] != "https://e.org" {
		t.Fatalf("urls = %#v", result.URLs)
	}
}

func TestCompareReportsSetDifferences(t *testing.T) {
	dir := t.TempDir()
	source := filepath.Join(dir, "source.wiki")
	draft := filepath.Join(dir, "draft.wiki")
	writeFile(t, source, "[[A]] [[File:One.jpg]] <ref name=\"keep\">x</ref> https://a.example\n")
	writeFile(t, draft, "[[B]] [[File:Two.jpg]] <ref name=\"extra\">y</ref> https://b.example\n")
	result, err := CompareFiles(source, draft)
	if err != nil {
		t.Fatal(err)
	}
	if result.MissingFiles["One.jpg"] != 1 || result.ExtraFiles["Two.jpg"] != 1 {
		t.Fatalf("files = %#v %#v", result.MissingFiles, result.ExtraFiles)
	}
	if len(result.MissingReferences) != 1 || result.MissingReferences[0].Name != "keep" {
		t.Fatalf("missing refs = %#v", result.MissingReferences)
	}
	if len(result.ExtraReferences) != 1 || result.ExtraReferences[0].Name != "extra" {
		t.Fatalf("extra refs = %#v", result.ExtraReferences)
	}
	if len(result.MissingLinkTargets) != 1 || result.MissingLinkTargets[0] != "A" {
		t.Fatalf("missing links = %#v", result.MissingLinkTargets)
	}
	if len(result.MissingSourceURLs) != 1 || !strings.Contains(result.MissingSourceURLs[0], "a.example") {
		t.Fatalf("missing urls = %#v", result.MissingSourceURLs)
	}
}

func TestSummaryFindsDuplicateArtifacts(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "a.json"), "same")
	writeFile(t, filepath.Join(dir, "b.json"), "same")
	writeFile(t, filepath.Join(dir, "empty1"), "")
	writeFile(t, filepath.Join(dir, "empty2"), "")
	result, err := SummarizeDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	if result.FileCount != 4 || result.TotalBytes != 8 {
		t.Fatalf("counts = %d %d", result.FileCount, result.TotalBytes)
	}
	if len(result.Duplicates) != 1 || len(result.Duplicates[0].Files) != 2 {
		t.Fatalf("duplicates = %#v", result.Duplicates)
	}
	if len(result.Largest) == 0 || result.Largest[0].Path != "a.json" {
		t.Fatalf("largest = %#v", result.Largest)
	}
}

func TestSearchIsBoundedAndLiteral(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "a.wiki"), "Alpha\nTERM here\nterm again\n")
	result, err := SearchDir(dir, "term", 1)
	if err != nil {
		t.Fatal(err)
	}
	if result.TotalMatches != 2 || len(result.Hits) != 1 || !result.Truncated {
		t.Fatalf("search = %#v", result)
	}
	if result.Hits[0].Line != 2 || result.MatchFiles != 1 {
		t.Fatalf("hit = %#v", result.Hits[0])
	}
}

func TestSearchRejectsEmptyQuery(t *testing.T) {
	if _, err := SearchDir(t.TempDir(), "  ", 10); err == nil {
		t.Fatal("expected empty-query error")
	}
}
