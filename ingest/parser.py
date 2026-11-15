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


def title_of(element):
    pass


def mixed(element):
    pass


def fence(text, language=""):
    pass


def inline(element, code=False):
    pass


def cmdsyn(element):
    pass


# It is the entry point for converting a non-section element into Markdown
# Example output:
#   ["<!-- id:foo -->"] element has an id and its tag is in MARK
#   [] otherwise
def block(element):
    tag = element.tag

    if not isinstance(tag, str) or tag in SKIP:
        return []

    mark = (
        [f"<!-- id:{element.get('id')} -->"]
        if element.get("id") and tag in MARK
        else []
    )

    return mark + _block(element, tag)


# def _block(element, tag):
#     if tag in ("para", "simpara"):
#         return mixed(element)

#     if tag in ("programlisting", "screen", "synopsis", "literallayout"):
#         language = (
#             (element.get("language") or "").lower() if tag == "programlisting" else ""
#         )
#         return [fence(inline(element, True), language)]

#     if tag == "cmdsynopsis":
#         return [fence(cmdsyn(element))]


# It renders one section element as Markdown
# The output is a list of Markdown strings
# Example output (when combined with section_blocks):
#   <!-- id:install -->
#   ## Installation
#   ...paragraph blocks...
#   ### Prerequisites
#   ...blocks...
def section(element, level):
    output = [f"<!-- id:{element.get('id')} -->"] if element.get("id") else []
    output.append("#" * min(level, 6) + " " + title_of(element))
    return output + section_blocks(element, level + 1)


# Converts the children of a section-like element into a flat list of blocks
# at a given heading level
def section_blocks(element, level):
    output = []

    for child in element:
        if not isinstance(child, str) or child.tag in SKIP:
            continue
        output += section(child, level) if child.tag in SECT else block(child)

    return output


# It collects the introductory content of a container element as a flat list of blocks
# It looks only at the direct element's children
def intro_blocks(element):
    output = []

    for child in element:
        if (
            not isinstance(child.tag, str)
            or child.tag in SKIP
            or child.tag in UNIT
            or child.tag in CONTAINER
        ):
            continue
        out += (
            section_blocks(child, 2)
            if child.tag == "partintro"
            else (section(child, 2) if child.tag in SECT else block(child))
        )

    return output


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

    # Scans every element in an XML tree (lxml)
    # and registers each one that has an id attribute
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

    with open(output_directory / "units.jsonl", "w", encoding="utf-8") as file:
        for element in root.iter(*(UNIT | CONTAINER)):
            universal_id = element.get("id")

            if not universal_id or universal_id in seen:
                continue

            REFS.clear()

            body = (
                intro_blocks(element)
                if element.tag in CONTAINER
                else section_blocks(element, 2)
            )

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
