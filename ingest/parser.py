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

    # for element in root.iter():
    #     if element.get("id"):
    #         print(element)

    # IDS.update({})
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
