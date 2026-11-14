// Package scan provides read-only, stdlib-only analysis of large job artifacts.
package scan

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

var (
	headingRe   = regexp.MustCompile(`(?m)^[ \t]*={1,6}[ \t]*(.*?)[ \t]*={1,6}[ \t]*$`)
	linkRe      = regexp.MustCompile(`\[\[([^\[\]]+?)\]\]`)
	templateRe  = regexp.MustCompile(`\{\{[ \t]*([^{}|]+)`)
	urlRe       = regexp.MustCompile(`https?://[^\s<>\]|}]+`)
	refRe       = regexp.MustCompile(`(?i)<ref\b([^>]*)>`)
	nameRe      = regexp.MustCompile(`(?i)\bname\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))`)
	groupRe     = regexp.MustCompile(`(?i)\bgroup\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))`)
	wordRe      = regexp.MustCompile(`[\p{L}\p{N}]+`)
	interwikiRe = regexp.MustCompile(`^[a-z]{2,3}(?:-[a-z0-9]+)*:`)
)

// Inventory is a conservative raw-markup summary, not a parser or editorial review.
type Inventory struct {
	Schema       int            `json:"schema"`
	Path         string         `json:"path"`
	Bytes        int            `json:"bytes"`
	Lines        int            `json:"lines"`
	Words        int            `json:"words"`
	Headings     []string       `json:"headings"`
	LinkTargets  map[string]int `json:"link_targets"`
	Files        map[string]int `json:"files"`
	Categories   []string       `json:"categories"`
	Templates    map[string]int `json:"templates"`
	URLs         []string       `json:"urls"`
	References   []RefCount     `json:"references"`
	AnonymousRef int            `json:"anonymous_references"`
	Limits       string         `json:"limits"`
}

// RefCount preserves exact reference group/name counts.
type RefCount struct {
	Group string `json:"group"`
	Name  string `json:"name"`
	Count int    `json:"count"`
}

// CompareResult reports set differences, not approval or semantic matching.
type CompareResult struct {
	Schema             int            `json:"schema"`
	Source             string         `json:"source"`
	Draft              string         `json:"draft"`
	SourceBytes        int            `json:"source_bytes"`
	DraftBytes         int            `json:"draft_bytes"`
	MissingFiles       map[string]int `json:"missing_files"`
	ExtraFiles         map[string]int `json:"extra_files"`
	MissingSourceURLs  []string       `json:"missing_source_urls"`
	ExtraURLs          []string       `json:"extra_urls"`
	MissingLinkTargets []string       `json:"missing_link_targets"`
	ExtraLinkTargets   []string       `json:"extra_link_targets"`
	MissingReferences  []RefKey       `json:"missing_reference_names"`
	ExtraReferences    []RefKey       `json:"extra_reference_names"`
	Limits             string         `json:"limits"`
}

// RefKey identifies a named reference without revealing its body.
type RefKey struct {
	Group string `json:"group"`
	Name  string `json:"name"`
}

// FileRecord is one regular file in a summary scan.
type FileRecord struct {
	Path   string `json:"path"`
	Bytes  int64  `json:"bytes"`
	SHA256 string `json:"sha256"`
}

// DuplicateGroup lists byte-identical files.
type DuplicateGroup struct {
	Bytes int64    `json:"bytes"`
	SHA   string   `json:"sha256"`
	Files []string `json:"files"`
}

// Summary reports sizes, extensions and duplicate artifacts in a directory.
type Summary struct {
	Schema      int              `json:"schema"`
	Root        string           `json:"root"`
	FileCount   int              `json:"file_count"`
	TotalBytes  int64            `json:"total_bytes"`
	ByExtension map[string]int   `json:"by_extension"`
	Largest     []FileRecord     `json:"largest"`
	Duplicates  []DuplicateGroup `json:"duplicate_groups"`
	Skipped     []string         `json:"skipped"`
	Limits      string           `json:"limits"`
}

// Hit is one bounded text-search match.
type Hit struct {
	Path    string `json:"path"`
	Line    int    `json:"line"`
	Snippet string `json:"snippet"`
}

// SearchResult is a bounded literal search, never regex or instruction execution.
type SearchResult struct {
	Schema       int    `json:"schema"`
	Root         string `json:"root"`
	Query        string `json:"query"`
	FilesScanned int    `json:"files_scanned"`
	MatchFiles   int    `json:"match_files"`
	TotalMatches int    `json:"total_matches"`
	Hits         []Hit  `json:"hits"`
	Truncated    bool   `json:"truncated"`
	Limits       string `json:"limits"`
}

func normalizeTarget(value string) string {
	value = strings.TrimSpace(value)
	if i := strings.Index(value, "|"); i >= 0 {
		value = value[:i]
	}
	if i := strings.Index(value, "#"); i >= 0 {
		value = value[:i]
	}
	return strings.ReplaceAll(strings.TrimSpace(value), "_", " ")
}

func isFileTarget(target string) bool {
	lower := strings.ToLower(target)
	for _, prefix := range []string{"file:", "image:", "media:", "sary:"} {
		if strings.HasPrefix(lower, prefix) {
			return true
		}
	}
	return false
}

func isCategoryTarget(target string) bool {
	lower := strings.ToLower(target)
	return strings.HasPrefix(lower, "sokajy:") || strings.HasPrefix(lower, "category:")
}

func isArticleTarget(target string) bool {
	return target != "" && !strings.HasPrefix(target, ":") &&
		!isFileTarget(target) && !isCategoryTarget(target) &&
		!interwikiRe.MatchString(target)
}

func attrValue(re *regexp.Regexp, attrs string) string {
	match := re.FindStringSubmatch(attrs)
	if match == nil {
		return ""
	}
	for _, value := range match[1:] {
		if value != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

// InventoryFile inspects raw wikitext using conservative regular expressions.
func InventoryFile(path string) (Inventory, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return Inventory{}, err
	}
	text := string(raw)
	result := Inventory{
		Schema:      1,
		Path:        path,
		Bytes:       len(raw),
		Lines:       strings.Count(text, "\n") + 1,
		Words:       len(wordRe.FindAllString(text, -1)),
		Headings:    []string{},
		LinkTargets: map[string]int{},
		Files:       map[string]int{},
		Templates:   map[string]int{},
		Categories:  []string{},
		URLs:        []string{},
		References:  []RefCount{},
		Limits: "Raw regex inventory only. Templates are not expanded; links/files/categories " +
			"spanning lines, parser functions and semantic context require Python review.",
	}
	for _, match := range headingRe.FindAllStringSubmatch(text, -1) {
		if heading := strings.TrimSpace(match[1]); heading != "" {
			result.Headings = append(result.Headings, heading)
		}
	}
	categories := map[string]bool{}
	for _, match := range linkRe.FindAllStringSubmatch(text, -1) {
		target := normalizeTarget(match[1])
		if target == "" {
			continue
		}
		result.LinkTargets[target]++
		if isFileTarget(target) {
			name := target[strings.Index(target, ":")+1:]
			result.Files[strings.TrimSpace(name)]++
		}
		if isCategoryTarget(target) {
			categories[target] = true
		}
	}
	for category := range categories {
		result.Categories = append(result.Categories, category)
	}
	sort.Strings(result.Categories)
	for _, match := range templateRe.FindAllStringSubmatch(text, -1) {
		name := strings.TrimSpace(match[1])
		if name != "" {
			result.Templates[name]++
		}
	}
	urls := map[string]bool{}
	for _, url := range urlRe.FindAllString(text, -1) {
		urls[strings.TrimSuffix(url, ".")] = true
	}
	for url := range urls {
		result.URLs = append(result.URLs, url)
	}
	sort.Strings(result.URLs)
	refs := map[RefKey]int{}
	for _, match := range refRe.FindAllStringSubmatch(text, -1) {
		attrs := strings.TrimSuffix(strings.TrimSpace(match[1]), "/")
		name := attrValue(nameRe, attrs)
		if name == "" {
			result.AnonymousRef++
			continue
		}
		refs[RefKey{Group: attrValue(groupRe, attrs), Name: name}]++
	}
	for key, count := range refs {
		result.References = append(result.References, RefCount{Group: key.Group, Name: key.Name, Count: count})
	}
	sort.Slice(result.References, func(i, j int) bool {
		if result.References[i].Group != result.References[j].Group {
			return result.References[i].Group < result.References[j].Group
		}
		return result.References[i].Name < result.References[j].Name
	})
	return result, nil
}

func refKeys(inventory Inventory) map[RefKey]bool {
	keys := map[RefKey]bool{}
	for _, ref := range inventory.References {
		keys[RefKey{Group: ref.Group, Name: ref.Name}] = true
	}
	return keys
}

func sortedDiff(left, right map[string]bool) []string {
	values := []string{}
	for value := range left {
		if !right[value] {
			values = append(values, value)
		}
	}
	sort.Strings(values)
	return values
}

// CompareFiles reports exact raw-markup differences between two files.
func CompareFiles(sourcePath, draftPath string) (CompareResult, error) {
	source, err := InventoryFile(sourcePath)
	if err != nil {
		return CompareResult{}, err
	}
	draft, err := InventoryFile(draftPath)
	if err != nil {
		return CompareResult{}, err
	}
	missingFiles := map[string]int{}
	for name, count := range source.Files {
		if draft.Files[name] < count {
			missingFiles[name] = count - draft.Files[name]
		}
	}
	extraFiles := map[string]int{}
	for name, count := range draft.Files {
		if source.Files[name] < count {
			extraFiles[name] = count - source.Files[name]
		}
	}
	urls := func(values []string) map[string]bool {
		set := map[string]bool{}
		for _, value := range values {
			set[value] = true
		}
		return set
	}
	sourceLinks := map[string]bool{}
	for target := range source.LinkTargets {
		if isArticleTarget(target) {
			sourceLinks[target] = true
		}
	}
	draftLinks := map[string]bool{}
	for target := range draft.LinkTargets {
		if isArticleTarget(target) {
			draftLinks[target] = true
		}
	}
	sourceRefs := refKeys(source)
	draftRefs := refKeys(draft)
	missingRefs, extraRefs := []RefKey{}, []RefKey{}
	for key := range sourceRefs {
		if !draftRefs[key] {
			missingRefs = append(missingRefs, key)
		}
	}
	for key := range draftRefs {
		if !sourceRefs[key] {
			extraRefs = append(extraRefs, key)
		}
	}
	sort.Slice(missingRefs, func(i, j int) bool {
		if missingRefs[i].Group != missingRefs[j].Group {
			return missingRefs[i].Group < missingRefs[j].Group
		}
		return missingRefs[i].Name < missingRefs[j].Name
	})
	sort.Slice(extraRefs, func(i, j int) bool {
		if extraRefs[i].Group != extraRefs[j].Group {
			return extraRefs[i].Group < extraRefs[j].Group
		}
		return extraRefs[i].Name < extraRefs[j].Name
	})
	return CompareResult{
		Schema:             1,
		Source:             sourcePath,
		Draft:              draftPath,
		SourceBytes:        source.Bytes,
		DraftBytes:         draft.Bytes,
		MissingFiles:       missingFiles,
		ExtraFiles:         extraFiles,
		MissingSourceURLs:  sortedDiff(urls(source.URLs), urls(draft.URLs)),
		ExtraURLs:          sortedDiff(urls(draft.URLs), urls(source.URLs)),
		MissingLinkTargets: sortedDiff(sourceLinks, draftLinks),
		ExtraLinkTargets:   sortedDiff(draftLinks, sourceLinks),
		MissingReferences:  missingRefs,
		ExtraReferences:    extraRefs,
		Limits: "Exact raw-markup set comparison only. Translated link targets normally differ; " +
			"review them, do not count them as loss. No translation, identity, target validity, " +
			"citation support, image licensing or omission authorization is verified.",
	}, nil
}

func hashFile(path string) (string, int64, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", 0, err
	}
	defer file.Close()
	hash := sha256.New()
	size, err := io.Copy(hash, file)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(hash.Sum(nil)), size, nil
}

// SummarizeDir hashes regular files, reports large artifacts and duplicate bytes.
func SummarizeDir(root string) (Summary, error) {
	root, err := filepath.Abs(root)
	if err != nil {
		return Summary{}, err
	}
	result := Summary{
		Schema:      1,
		Root:        root,
		ByExtension: map[string]int{},
		Largest:     []FileRecord{},
		Duplicates:  []DuplicateGroup{},
		Skipped:     []string{},
		Limits: "Local filesystem metadata/hash scan only. Duplicate bytes are not approval; " +
			"article prose and evidence are never interpreted.",
	}
	hashes := map[string][]string{}
	sizes := map[string]int64{}
	err = filepath.WalkDir(root, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			result.Skipped = append(result.Skipped, path+": "+walkErr.Error())
			return nil
		}
		if entry.IsDir() {
			return nil
		}
		if entry.Type()&os.ModeSymlink != 0 {
			result.Skipped = append(result.Skipped, path+": symlink")
			return nil
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() {
			result.Skipped = append(result.Skipped, path+": not regular")
			return nil
		}
		hash, size, err := hashFile(path)
		if err != nil {
			result.Skipped = append(result.Skipped, path+": "+err.Error())
			return nil
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			relative = path
		}
		record := FileRecord{Path: filepath.ToSlash(relative), Bytes: size, SHA256: hash}
		result.FileCount++
		result.TotalBytes += size
		extension := strings.ToLower(filepath.Ext(path))
		if extension == "" {
			extension = "(none)"
		}
		result.ByExtension[extension]++
		result.Largest = append(result.Largest, record)
		hashes[hash] = append(hashes[hash], record.Path)
		sizes[hash] = size
		return nil
	})
	if err != nil {
		return Summary{}, err
	}
	sort.Slice(result.Largest, func(i, j int) bool {
		if result.Largest[i].Bytes != result.Largest[j].Bytes {
			return result.Largest[i].Bytes > result.Largest[j].Bytes
		}
		return result.Largest[i].Path < result.Largest[j].Path
	})
	if len(result.Largest) > 20 {
		result.Largest = result.Largest[:20]
	}
	for hash, files := range hashes {
		if len(files) < 2 || sizes[hash] == 0 {
			continue
		}
		sort.Strings(files)
		result.Duplicates = append(result.Duplicates, DuplicateGroup{
			Bytes: sizes[hash], SHA: hash, Files: files,
		})
	}
	sort.Slice(result.Duplicates, func(i, j int) bool {
		if result.Duplicates[i].Bytes != result.Duplicates[j].Bytes {
			return result.Duplicates[i].Bytes > result.Duplicates[j].Bytes
		}
		return result.Duplicates[i].SHA < result.Duplicates[j].SHA
	})
	return result, nil
}

func isTextFile(path string) bool {
	file, err := os.Open(path)
	if err != nil {
		return false
	}
	defer file.Close()
	buffer := make([]byte, 8192)
	n, err := file.Read(buffer)
	if err != nil && err != io.EOF {
		return false
	}
	for _, value := range buffer[:n] {
		if value == 0 {
			return false
		}
	}
	return true
}

// SearchDir performs a bounded, case-insensitive literal search over text files.
func SearchDir(root, query string, maxHits int) (SearchResult, error) {
	if strings.TrimSpace(query) == "" {
		return SearchResult{}, errors.New("search query must not be empty")
	}
	if maxHits <= 0 {
		maxHits = 200
	}
	if maxHits > 5000 {
		maxHits = 5000
	}
	root, err := filepath.Abs(root)
	if err != nil {
		return SearchResult{}, err
	}
	result := SearchResult{
		Schema: 1, Root: root, Query: query, Hits: []Hit{},
		Limits: "Case-insensitive literal search only. No regex, instruction execution, " +
			"semantic interpretation or evidence authority.",
	}
	needle := strings.ToLower(query)
	err = filepath.WalkDir(root, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil || entry.IsDir() || entry.Type()&os.ModeSymlink != 0 {
			return nil
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() || !isTextFile(path) {
			return nil
		}
		file, err := os.Open(path)
		if err != nil {
			return nil
		}
		result.FilesScanned++
		matchedFile := false
		lineNumber := 0
		scanner := bufio.NewScanner(file)
		scanner.Buffer(make([]byte, 64*1024), 8*1024*1024)
		for scanner.Scan() {
			lineNumber++
			line := scanner.Text()
			if !strings.Contains(strings.ToLower(line), needle) {
				continue
			}
			result.TotalMatches++
			matchedFile = true
			if len(result.Hits) < maxHits {
				snippet := strings.TrimSpace(line)
				if len(snippet) > 240 {
					snippet = snippet[:240]
				}
				relative, relErr := filepath.Rel(root, path)
				if relErr != nil {
					relative = path
				}
				result.Hits = append(result.Hits, Hit{
					Path: filepath.ToSlash(relative), Line: lineNumber, Snippet: snippet,
				})
			} else {
				result.Truncated = true
			}
		}
		_ = file.Close()
		if matchedFile {
			result.MatchFiles++
		}
		return nil
	})
	if err != nil {
		return SearchResult{}, err
	}
	return result, nil
}
