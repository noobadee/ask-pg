#!/usr/bin/env python3
"""postgres-full.xml (resolved DocBook) -> Markdown units (units.jsonl + md/*.md)."""

import argparse, json, re
from collections import Counter
from pathlib import Path
from lxml import etree

CODE = {
    "literal",
    "command",
    "function",
    "type",
    "varname",
    "option",
    "parameter",
    "structfield",
    "structname",
    "filename",
    "application",
    "envar",
    "token",
    "symbol",
    "classname",
    "returnvalue",
    "systemitem",
    "userinput",
    "computeroutput",
    "prompt",
    "constant",
}

PASS = {
    "acronym",
    "productname",
    "phrase",
    "abbrev",
    "citetitle",
    "glossterm",
    "firstname",
    "surname",
    "email",
    "date",
    "year",
    "holder",
    "publishername",
    "pubdate",
    "isbn",
    "edition",
    "address",
    "author",
    "corpauthor",
    "title",
    "secondary",
    "tertiary",
    "lineannotation",
    "trademark",
    "symbol",
    "pagenums",
    "volumenums",
    "pubnumber",
    "confgroup",
    "conftitle",
    "confdates",
    "biblioset",
    "seealso",
    "see",
    "attribution",
}

DROP = {"indexterm", "anchor", "co"}

BLOCKS = {
    "para",
    "simpara",
    "itemized",
    "orderedlist",
    "variablelist",
    "programlisting",
    "screen",
    "synopsis",
    "cmdsynopsis",
    "literallayout",
    "table",
    "informaltable",
    "note",
    "tip",
    "warning",
    "caution",
    "important",
    "example",
    "informalexample",
    "figure",
    "mediaobject",
    "procedure",
    "substeps",
    "formalparablockquote",
    "calloutlist",
    "glosslist",
    "glossentry",
    "refnamediv",
}

ADMON = {"note", "tip", "warning", "caution", "important"}

SECT = {
    "sect1",
    "sect2",
    "sect3",
    "sect4",
    "sect5",
    "section",
    "simplesect",
    "refsect1",
    "refsect2",
    "refsect3",
    "refsynopsisdiv",
}

SKIP = {
    "title",
    "titleabbrev",
    "subtitle",
    "indexterm",
    "refmeta",
    "bookinfo",
    "anchor",
}

MARK = {
    "varlistentry",
    "table",
    "informaltable",
    "example",
    "glossentry",
    "figure",
} | SECT

UNIT = {"sect1", "refentry"}

CONTAINER = {"part", "chapter", "appendix", "preface", "reference", "bibliography"}

TITLED = UNIT | CONTAINER | {"sec2", "sect3"}

PAGE = UNIT | CONTAINER

LABEL = {
    "chapter": "Chapter",
    "apendix": "Appendix",
    "part": "Part",
    "table": "Table",
    "example": "Example",
    "figure": "Figure",
    "sect1": "Section",
    "sec2": "Section",
    "sec3": "Section",
    "sect4": "Section",
    "refsect1": "Section",
    "refsect2": "Section",
}

IDS, REFS, UNHANDLED, UNRESOLVED = {}, [], Counter(), Counter()


def section_blocks(element, level):
    output = []
    for character in element:
        if not isinstance(character, str) or character.tag in SKIP:
            continue
        # output += section(character, level) if character.tag in SECT else block(character)


def main():
    # ARGUMENT FORMAT
    # python parser.py <xml-filepath> <output-directory> --major <major-version> --version <minor-version>
    # e.g., python parser.py postgresql.xml out --major 18 --version 18.6
    argument_parse = argparse.ArgumentParser()
    argument_parse.add_argument("xml")
    argument_parse.add_argument("outdir")
    argument_parse.add_argument("--major", default="18")
    argument_parse.add_argument("--version", default="18.6")
    arguments = argument_parse.parse_args()

    parser = etree.XMLParser(
        load_dtd=False, no_network=True, resolve_entities=False, huge_tree=True
    )
    root = etree.parse(arguments.xml, parser).getroot()

    IDS.update(
        {
            element.get("id"): element
            for element in root.iter(etree.Element)
            if element.get("id")
        }
    )

    base = f"https://www.postgresql.org/docs/{arguments.major}"

    # Creates an output directory (and an md subdirectory inside it) if they don’t already exist,
    # and stores the base path in out for later use.
    output_directory = Path(arguments.outdir)
    (output_directory / "md").mkdir(parents=True, exist_ok=True)

    stats, num_of_characters, seen = Counter(), 0, set()

    # with open(output_directory / "units.jsonl", "w", encoding="utf-8") as file:
    #     for element in root.iter(*(UNIT | CONTAINER)):
    #         universal_id = element.get("id")

    #         if not universal_id or universal_id in seen:
    #             continue

    #         REFS.clear()

    #         body = intro_blocks(element) if element.tag in CONTAINER else section_blocks(element, 2)

    # print(f"CODE: {len(CODE)}")
    # print(f"PASS: {len(PASS)}")
    # print(f"DROP: {len(DROP)}")
    # print(f"BLOCKS: {len(BLOCKS)}")
    # print(f"ADMON: {len(ADMON)}")
    # print(f"SECT: {len(SECT)}")
    # print(f"SKIP: {len(SKIP)}")
    # print(f"MARK: {len(MARK)}")
    # print(f"UNIT: {len(UNIT)}")
    # print(f"CONTAINER: {len(CONTAINER)}")
    # print(f"TITLED: {len(TITLED)}")
    # print(f"PAGE: {len(PAGE)}")
    # print(f"LABEL: {len(LABEL)}")


if __name__ == "__main__":
    main()
