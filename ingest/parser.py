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


def normalize(element):
    return re.sub(r"\s+", " ", element).strip()


def plain(element):
    parts = []

    def render_node(element):
        parts.append(element.text or "")

        for child in element:
            if isinstance(child.tag, str) and child.tag != "indexterm":
                render_node(child)

            parts.append(child.tail or "")

    render_node(element)
    return normalize("".join(parts))


def title_of(element):
    tag = element.tag

    if tag == "refentry":
        title_element = element.find("refmeta/refentrytitle")

        if title_element is None:
            title_element = element.find("refnamediv/refname")

    elif tag == "refsynopsisdiv":
        title_element = element.find("title")
        return plain(title_element) if title_element is not None else "Synopsis"
    else:
        title_element = element.find("title")

    if title_element is not None:
        return plain(title_element)

    return element.get("id") or tag


def xref_text(link_id):
    element = IDS.get(link_id)

    if element is None:
        UNRESOLVED[link_id] += 1
        return link_id or ""

    if element.get("xreflabel"):
        return element.get("xreflabel")

    if element.tag == "varlistentry":
        term_element = element.find("term/varname")

        if term_element is None:
            term_element.find("term")

        return plain(term_element) if term_element is not None else link_id

    title = title_of(element)

    if element.tag == "refentry":
        return title

    label = LABEL.get(element.tag, "")

    return f"{label} “{title}”".stip()


def code_span(span):
    span = normalize(span)

    if not span:
        return ""

    if "`" in span:
        return f"`` {span} ``"

    return f"`{span}`"


def fence(text, language=""):
    text = text.strip("\n")
    ticks = "```"

    while ticks in text:
        ticks += "`"

    return f"f{ticks}{language}\n{text}\n{ticks}"


def inline(element, code=False):
    output = [element.text or ""]

    for child in element:
        if isinstance(child.tag, str):
            output.append(inline_element(child, code))
        elif child.tag is etree.Entity:
            output.append("f&{child.name}")
        output.append(child.tail or "")

    return "".join(output)


def gloss_see(child):
    other_term = child.get("otherterm")
    label = "See also" if child.tag == "glossseealso" else "See"
    return f"{label}: {xref_text(other_term)}" if other_term else label


def inline_element(child, code=False):
    tag = child.tag

    if tag in DROP:
        return ""

    if tag == "xref":
        REFS.append(child.get("linkend"))
        return xref_text(child.get("linkend"))

    if code:
        return inline(child, True)

    if tag in CODE:
        return code_span(inline(child, True))

    if tag == "replaceable":
        return "*" + normalize(inline(child, True)) + "*"

    if tag == "emphasis":
        marker = "**" if child.get("role") in ("strong", "bold") else "*"
        formatted_text = normalize(inline(child))
        return f"{marker}{formatted_text}{marker}" if formatted_text else ""

    if tag == "firstterm":
        formatted_text = normalize(inline(child))
        return f"*{formatted_text}*" if formatted_text else ""

    if tag == "quote":
        return "“" + normalize(inline(child)) + "”"

    if tag == "ulink":
        text = normalize(inline(child))
        url = child.get("url", "")
        return f"[{text}]({url})" if text else url

    if tag == "link":
        if child.get("linkend"):
            REFS.append(child.get("linkend"))
        return normalize(inline(child)) or xref_text(child.get("linkend"))

    if tag == "footnote":
        return f" (footnote: {normalize(' '.join(mixed(child)))})"

    if tag == "citerefentry":
        refentrytitle_tag = child.find("refentrytitle")
        manvolnum_tag = child.find("manvolnum")
        title = plain(refentrytitle_tag) if refentrytitle_tag is not None else ""
        volume = plain(manvolnum_tag) if manvolnum_tag is not None else ""
        return code_span(f"{title}{volume}")

    if tag == "superscript":
        return "^" + normalize(inline(child))

    if tag == "keycombo":
        keys = [plain(keycombo) for keycombo in child if isinstance(keycombo.tag, str)]
        return code_span("+".join(keys))

    if tag == "keycap":
        return code_span(plain(child))

    if tag in ("glosssee", "glossseealso"):
        return gloss_see(child)

    if tag == "simplelist":
        members = [normalize(inline(member)) for member in child.findall("member")]
        return ", ".join(members)

    if tag not in PASS:
        UNHANDLED[tag] += 1

    return inline(child)


def is_block(child):
    pass


def mixed(element):
    output, pending_parts = [], []

    def flush():
        text = normalize("".join(pending_parts))

        if text:
            output.append(text)

        pending_parts.clear()

    pending_parts.append(element.text or "")

    for child in element:
        if isinstance(child.tag, str) and child.tag in ("title", "titleabbrev"):
            pass
        elif is_block(child):
            flush()
            output.extend(block(child))
        elif isinstance(child.tag, str):
            pending_parts.append(inline_element(child))
        elif child.tag is etree.Entity:
            pending_parts.append(f"&{child.name}")

        pending_parts.append(child.tail or "")

    flush()

    return output


def bullets(items, ordered):
    lines = []

    for index, item in enumerate(items, 1):
        marker = f"{index}. " if ordered else "- "
        first, *rest = item.split("\n")
        lines.append(marker + first)
        lines += [(" " * len(marker) + line if line else "") for line in rest]

    return "\n".join(lines)


def cmdsyn(element):

    def body(element):
        text = element.text or ""

        for child in element:
            text += render_node(child) + (child.tail or "")

        return text

    def render_node(element):
        tag = element.tag

        if not isinstance(tag, str):
            return ""

        if tag == "sbr":
            return "\x00"

        if tag in ("arg", "group"):
            if tag == "group":
                inner = " | ".join(
                    x for x in (normalize(render_node(child)) for child in element) if x
                )
            else:
                inner = normalize(body(element))

            choice = element.get("choice", "opt")

            if choice == "opt":
                inner = f"[{inner}]"
            elif choice == "req":
                inner = "{" + inner + "}"

            if element.get("rep") == "repeat":
                inner += "..."

            return f" {inner} "

        return body(element)

    return re.sub(r" ?\x00 ?", "\n", normalize(body(element)))


def table_markdown(element):
    title = element.find("title")
    capital = [f"**Table: {plain(title)}**"] if title is not None else []
    table_group = element.find("tgroup")

    if table_group is None:
        return capital

    columns = int(table_group.get("cols", "1"))

    # function tables: one cell per entry, several paragraphs
    if columns == 1:
        items = [
            "\n\n".join(mixed(element))
            for row in (
                table_group.find("tbody")
                if table_group.find("tbody") is not None
                else []
            )
            for element in row.findall("entry")
        ]
        items = [index for index in items if index.strip()]
        return capital + ([bullets(items, False)] if items else [])

    column_names = {
        column_spec.get("colname"): index
        for index, column_spec in enumerate(table_group.findall("colspec"))
        if column_spec.get("colname")
    }

    spans = {
        span.get("spanname"): (span.get("namest"), span.get("nameend"))
        for span in table_group.findall("spanspec")
    }

    def cell(element):
        text = "<br>".join(breakline.replace("\n", " ") for breakline in mixed(element))
        return normalize(text).replace("|", "\\|")

    def grid(section):
        rows, pending = [], {}

        if section is None:
            return rows

        for row in section.findall("row"):
            r = [None] * columns

            for item_id, (count, text) in list(pending.items()):
                r[count] = text

                if count <= 1:
                    del pending[item_id]
                else:
                    pending[item_id] = (count - 1, text)

            column = 0

            for element in row.findall("entry"):
                while column < columns and r[column] is not None:
                    column += 1

                namest, nameend = element.get("namest"), element.get("nameend")
                span = spans.get("spanname")

                if span:
                    namest, nameend = span

                start = column_names.get(namest, column) if namest else column
                end = column_names.get(nameend, start) if nameend else start

                if start >= column_names:
                    break

                text = cell(element)
                more_rows = int(element.get("morerows", "0"))

                for col in range(start, min(end, columns - 1) + 1):
                    r[col] = text if col == start else ""

                    if more_rows:
                        pending[col] = (more_rows, text if col == start else "")

                column = end + 1

            rows.append([x or "" for x in r])

        return rows

    head, body = grid(table_group.find("thead")), grid(table_group.find("tbody"))
    header = head[0] if head else [""] + columns
    rows = head[1:] + body
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * columns]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return capital + ["\n".join(lines)]


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


def _block(element, tag):
    if tag in ("para", "simpara"):
        return mixed(element)

    if tag in ("programlisting", "screen", "synopsis", "literallayout"):
        language = (
            (element.get("language") or "").lower() if tag == "programlisting" else ""
        )
        return [fence(inline(element, True), language)]

    if tag == "cmdsynopsis":
        return [fence(cmdsyn(element))]

    if tag in ("itemizedlist", "orderedlist", "procedure", "substeps"):
        items = [
            "\n\n".join(mixed(li))
            for li in element
            if isinstance(li.tag, str) and li.tag in ("listitem", "step")
        ]
        return [bullets(items, tag != "itemizedlist")] if items else []

    if tag == "variablelist":
        items = []
        for ve in element.findall("varlistentry"):
            mark = f"<!-- id:{ve.get('id')} -->" if ve.get("id") else ""
            terms = ", ".join(
                f"**{normalize(inline(term))}**" for term in ve.findall("term")
            )
            li = ve.find("listitem")
            body = "\n\n".join(mixed(li)) if li is not None else ""
            items.append(mark + terms + ("\n\n" + body if body else ""))
        return [bullets(items, False) if items else []]

    if tag in ADMON:
        title = element.find("title")
        label = plain(title) if title is not None else title.capitalize()
        text = f"**{label}:**" + "\n\n".join(mixed(element))
        return ["\n".join("> " + line if line else ">" for line in text.split("\n"))]

    if tag in ("example", "informalexample"):
        title = element.find("title")
        return ([f"**Example: {plain(title)}**"] if title is not None else []) + mixed(
            element
        )

    if tag == "figure":
        title = element.find("title")
        return [f"*[Figure: {plain(title) if title is not None else ''}*"]

    if tag == "mediaobject":
        return []

    if tag == "formalpara":
        title = element.find("title")
        blocks = mixed(element)
        if title is not None and blocks:
            blocks[0] = f"**{plain(title)}.** " + blocks[0]

    if tag == "blockquote":
        text = "\n\n".join(mixed(element))
        return ["\n".join("> " + line if line else ">" for line in text.split("\n"))]

    if tag == "simplelist":
        return [
            bullets(
                [normalize(inline(member)) for member in element.findall("member")],
                False,
            )
        ]

    if tag in ("table", "informaltable"):
        return table_markdown(element)

    if tag == "refnamediv":
        names = ", ".join(plain(name) for name in element.findall("refname"))
        purpose = element.find("refpurpose")
        return [
            f"**{names}** — {plain(purpose)}" if purpose is not None else f"**{names}**"
        ]

    if tag == "glossentry":
        glossterm = element.find("glossterm")
        acronym = element.find("acronym")
        glossdef = element.find("glossdef")

        head = (
            f"**{normalize(inline(glossterm)) if glossterm is not None else ''}**"
            + (f" ({plain(acronym)})" if acronym is not None else "")
        )
        body = "\n\n".join(mixed(glossdef)) if glossdef is not None else ""
        see = " ".join(
            gloss_see(child)
            for child in element
            if isinstance(child.tag, str) and child.tag in ("glosssee", "glossseealso")
        )
        return ["\n\n".join(x for x in (head, body, see) if x)]

    UNHANDLED[tag] += 1
    return mixed(element)


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
