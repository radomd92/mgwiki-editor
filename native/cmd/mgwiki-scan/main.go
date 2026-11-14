// mgwiki-scan is a read-only native accelerator for large local job artifacts.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"mgwiki-editor/native/internal/scan"
)

func writeJSON(value any, pretty bool) error {
	encoder := json.NewEncoder(os.Stdout)
	if pretty {
		encoder.SetIndent("", "  ")
	}
	return encoder.Encode(value)
}

func fail(err error) {
	encoder := json.NewEncoder(os.Stderr)
	_ = encoder.Encode(map[string]string{"error": err.Error()})
	os.Exit(1)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: mgwiki-scan inventory|compare|summary|search [flags]")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "inventory":
		flags := flag.NewFlagSet("inventory", flag.ExitOnError)
		pretty := flags.Bool("pretty", false, "indent JSON")
		_ = flags.Parse(os.Args[2:])
		if flags.NArg() != 1 {
			fmt.Fprintln(os.Stderr, "usage: mgwiki-scan inventory [-pretty] FILE")
			os.Exit(2)
		}
		result, err := scan.InventoryFile(flags.Arg(0))
		if err != nil {
			fail(err)
		}
		if err := writeJSON(result, *pretty); err != nil {
			fail(err)
		}
	case "compare":
		flags := flag.NewFlagSet("compare", flag.ExitOnError)
		pretty := flags.Bool("pretty", false, "indent JSON")
		_ = flags.Parse(os.Args[2:])
		if flags.NArg() != 2 {
			fmt.Fprintln(os.Stderr, "usage: mgwiki-scan compare [-pretty] SOURCE DRAFT")
			os.Exit(2)
		}
		result, err := scan.CompareFiles(flags.Arg(0), flags.Arg(1))
		if err != nil {
			fail(err)
		}
		if err := writeJSON(result, *pretty); err != nil {
			fail(err)
		}
	case "summary":
		flags := flag.NewFlagSet("summary", flag.ExitOnError)
		pretty := flags.Bool("pretty", false, "indent JSON")
		_ = flags.Parse(os.Args[2:])
		if flags.NArg() != 1 {
			fmt.Fprintln(os.Stderr, "usage: mgwiki-scan summary [-pretty] DIRECTORY")
			os.Exit(2)
		}
		result, err := scan.SummarizeDir(flags.Arg(0))
		if err != nil {
			fail(err)
		}
		if err := writeJSON(result, *pretty); err != nil {
			fail(err)
		}
	case "search":
		flags := flag.NewFlagSet("search", flag.ExitOnError)
		pretty := flags.Bool("pretty", false, "indent JSON")
		maxHits := flags.Int("max-hits", 200, "maximum returned hits (1-5000)")
		_ = flags.Parse(os.Args[2:])
		if flags.NArg() != 2 {
			fmt.Fprintln(os.Stderr, "usage: mgwiki-scan search [-pretty] [-max-hits N] DIRECTORY QUERY")
			os.Exit(2)
		}
		result, err := scan.SearchDir(flags.Arg(0), flags.Arg(1), *maxHits)
		if err != nil {
			fail(err)
		}
		if err := writeJSON(result, *pretty); err != nil {
			fail(err)
		}
	default:
		fmt.Fprintln(os.Stderr, "usage: mgwiki-scan inventory|compare|summary|search [flags]")
		os.Exit(2)
	}
}
