"""Create the initial job vocabulary memo with grounded records."""
import json
from pathlib import Path

job = Path("runs/biol-sex-20261114")


def rec(source_term, domain, source_sense, english_definition, malagasy_definition,
        chosen_expression, evidence_files, status="verified", origin="dictionary",
        alternatives=None, reason=""):
    return {
        "source_term": source_term,
        "source_language": "en",
        "domain": domain,
        "source_sense": source_sense,
        "english_definition": english_definition,
        "definition_origin": origin,
        "malagasy_definition": malagasy_definition,
        "chosen_expression": chosen_expression,
        "evidence_files": evidence_files,
        "alternatives_rejected": alternatives or [],
        "status": status,
        "reason": reason,
    }


records = [
    rec(
        "biological sex", "article title / biology", "sex as a biological trait",
        "The biological category of an organism as male or female, based on the type of gametes produced.",
        "Ny sokajy biôlôjikan' ny zavamananaina ho lahy na vavy, mifototra amin' ny karazana gameta amokarany.",
        "Lahy sy vavy ara-biôlôjika",
        ["evidence-title-candidates.json", "evidence-link-targets.json",
         "evidence/read-mg-lehilahy.json", "evidence/read-mg-fananahana.json",
         "evidence/read-final-title.json"],
        reason="Title chosen from verified local title absence, en redirect names Sexes/Male and female, local biological usage of lahy sy vavy, and local adjectival ara-biôlôjika. Rejected Firaisana ara-nofo (sexual intercourse) and Fananahana (reproduction).",
    ),
    rec(
        "sex", "biology", "biological category, not sexual activity",
        "A category into which sexually-reproducing organisms are divided on the basis of their reproductive roles; the system of such categories.",
        "Sokajy anasokajiana ny zavamananaina miteraka ara-nofo araka ny anjara asany eo amin' ny fananahana; io rafitra io.",
        "lahy sy vavy ara-biôlôjika; maha-lahy sy maha-vavy ara-biôlôjika",
        ["evidence/lookups-en/000-en-98d44e13f455d916.json", "evidence-title-candidates.json",
         "evidence/read-mg-fananahana.json", "evidence/read-mg-lehilahy.json"],
        reason="Dictionary sense 1 is the biological category; local usage distinguishes it from firaisana ara-nofo (sexual intercourse).",
    ),
    rec(
        "gamete", "biology / reproduction", "haploid reproductive cell",
        "A reproductive cell (such as a sperm or egg) that fuses with another such cell at fertilization.",
        "Sela fananahana (toy ny tsirinaina na ny atody) izay mitsaihana amin' ny sela fananahana hafa amin' ny fitsaihana.",
        "gameta (na sela fananahana)",
        ["evidence/lookups-en/001-en-d485da920b54719a.json", "evidence/read-mg-gametofita.json"],
        reason="Local Gametôfita uses gameta and fitsaihana; dictionary confirms the haploid reproductive-cell sense.",
    ),
    rec(
        "zygote", "biology / reproduction", "cell formed by gamete fusion",
        "The cell formed by the fusion of a male and a female gamete.",
        "Ny sela vokatry ny fitsaihan' ny gameta lahy sy ny gameta vavy.",
        "zigôty (na sela vao noforonina tamin' ny fitsaihana)",
        ["evidence/lookups-en/002-en-d8be86c985bdd293.json"],
        reason="Descriptive Malagasy gloss; zigôty is the established local scientific transcription in mg embryophyte articles.",
    ),
    rec(
        "hermaphrodite", "biology / reproduction", "organism producing both gamete types",
        "An organism that produces both male and female gametes.",
        "Zavamananaina mamokatra gameta lahy sy gameta vavy.",
        "hermafrôdita (na zavamananaina manana taovam-pananahana lahy sy vavy)",
        ["evidence/lookups-en/003-en-4392a0c582e4caff.json"],
        reason="Cautious transcription plus explanatory gloss; no verified one-word Malagasy equivalent found.",
    ),
    rec(
        "anisogamy", "biology / reproduction", "fusion of dissimilar gametes",
        "Sexual reproduction involving the fusion of gametes of different sizes or shapes.",
        "Fananahana ara-nofo misy fitsaihan' ny gameta samy hafa habe na endrika.",
        "anisôgamia (gameta samy hafa habe)",
        ["evidence/lookups-en/004-en-8ccc3b1a86336fb6.json"],
        reason="Transcription plus explanatory gloss; dictionary sense confirmed.",
    ),
    rec(
        "isogamy", "biology / reproduction", "fusion of similar gametes",
        "Sexual reproduction involving gametes of similar morphology.",
        "Fananahana ara-nofo misy gameta mitovy endrika sy habe.",
        "isôgamia (gameta mitovy habe)",
        ["evidence/lookups-en/005-en-11f2a32624122117.json"],
        reason="Transcription plus explanatory gloss; dictionary sense confirmed.",
    ),
    rec(
        "diploid", "genetics", "two chromosome sets",
        "Of a cell, having a pair of each type of chromosome, one from each parent.",
        "Misy krômôzôma roa isaky ny karazana, ka ny iray avy amin' ny ray aman-dreny tsirairay.",
        "diplôida",
        ["evidence/lookups-en/006-en-08cae05f5643b4e9.json", "evidence/read-mg-gametofita.json"],
        reason="Local Gametôfita uses diplôida; dictionary confirms the two-set sense.",
    ),
    rec(
        "haploid", "genetics", "one chromosome set",
        "Having a single set of unpaired chromosomes, as a typical gamete does.",
        "Manana andiana krômôzôma tokana tsy mifanambady, toy ny gameta mahazatra.",
        "haplôida",
        ["evidence/lookups-en/007-en-5a3da2311b35427e.json", "evidence/read-mg-gametofita.json"],
        reason="Local Gametôfita uses haplôida; dictionary confirms the single-set sense.",
    ),
    rec(
        "meiosis", "genetics / cell biology", "reduction division producing gametes",
        "A cell division that produces haploid gametes with new combinations of genes.",
        "Fizarana sela mamokatra gameta haplôida misy fitambaran' ny fototarazo vaovao.",
        "meiôzy",
        ["evidence/lookups-en/008-en-3fcf87977becbf13.json"],
        reason="Established local scientific transcription (mg Eukaryota search result); dictionary confirms the biological sense.",
    ),
    rec(
        "gonochorism", "biology / sexual systems", "separate sexes in a species",
        "The situation in which individuals of a species are of one of at least two distinct sexes and retain that sex throughout life.",
        "Toe-javatra misy zavamananaina samy manana ny maha-lahy na maha-vavy azy ary mitoetra mandritra ny fiainany.",
        "gonôkôrisma (fisarahana ho lahy sy vavy)",
        ["evidence/lookups-en/009-en-457163eab8c15047.json"],
        reason="Transcription plus explanatory gloss; dictionary sense confirmed.",
    ),
    rec(
        "phenotype", "genetics", "observable characteristics",
        "Any observable characteristic of an organism, including morphology, development, biochemistry, physiology or behavior.",
        "Izay toetra hita na refesina amin' ny zavamananaina, toy ny endrika, ny fitomboana, ny simia, ny fizôlôjia na ny fitondran-tena.",
        "fenôtaipy (na toetra hita ivelany)",
        ["evidence/lookups-en/010-en-3edbdb5e0adae73b.json"],
        reason="Transcription plus descriptive gloss; dictionary sense confirmed.",
    ),
    rec(
        "chromosome", "genetics / cell biology", "DNA-protein structure carrying genes",
        "A linear arrangement of condensed DNA and associated proteins that contains the genetic material of an organism.",
        "Firafitry ny asidra dezôksiribôniokleika miforitra sy ny prôteinina mifandray aminy, mitahiry ny fototarazo.",
        "krômôzôma",
        ["evidence/lookups-en/011-en-a4a48f5e8ce80ee3.json", "evidence/read-mg-lehilahy.json"],
        reason="Local Lehilahy uses krômôzôma; dictionary confirms the DNA/protein sense.",
    ),
]
(job / "vocabulary.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("records", len(records), "bytes", (job / "vocabulary.json").stat().st_size)
