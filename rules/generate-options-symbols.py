#!/usr/bin/env python3
#
# This file is formatted with python black
#
# This file parses the base.xml and base.extras.xml file and prints out the option->symbols
# mapping compatible with the rules format. See the meson.build file for how this is used.

import argparse
import sys
import xml.etree.ElementTree as ET

from typing import Iterable
from dataclasses import dataclass
from pathlib import Path

XKB_CONFIG_ROOT: "XkbConfigRoot"

skip = (
    # Special type that exists but doesn't really exist
    "custom:types",
    # These are all defined in 0036-layoutoption_symbols.part
    "misc:apl",
    "misc:typo",
    "lv3:ralt_alt",
    "grp:toggle",
    "grp:alts_toggle",
    "grp:alt_altgr_toggle",
    "grp:alt_space_toggle",
    "grp:win_space_toggle",
    "grp:ctrl_space_toggle",
    "grp:rctrl_rshift_toggle",
    "grp:shifts_toggle",
)


def error(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    print("Aborting now")
    sys.exit(1)


@dataclass
class Directive:
    option: "Option"
    filename: str
    section: str

    @property
    def name(self) -> str:
        return self.option.name

    def __str__(self) -> str:
        return f"{self.filename}({self.section})"


@dataclass
class DirectiveSet:
    option: "Option"
    keycodes: Directive | None
    compat: Directive | None
    geometry: Directive | None
    symbols: Directive | None
    types: Directive | None

    @property
    def is_empty(self) -> bool:
        return all(
            x is None
            for x in (
                self.keycodes,
                self.compat,
                self.geometry,
                self.symbols,
                self.types,
            )
        )

    def for_section(self, section: str) -> Directive | None:
        return {
            "xkb_keycodes": self.keycodes,
            "xkb_compatibility": self.compat,
            "xkb_geometry": self.geometry,
            "xkb_symbols": self.symbols,
            "xkb_types": self.types,
        }[section]


@dataclass
class XkbConfigRoot:
    keycodes: Path
    compat: Path
    geometry: Path
    symbols: Path
    types: Path

    @property
    def directories(self) -> Iterable[Path]:
        yield self.keycodes
        yield self.compat
        yield self.geometry
        yield self.symbols
        yield self.types

    @property
    def section_headers(self) -> Iterable[str]:
        for h in [
            "xkb_keycodes",
            "xkb_compatibility",
            "xkb_geometry",
            "xkb_symbols",
            "xkb_types",
        ]:
            yield h

    @classmethod
    def for_basedir(cls, basedir: Path) -> "XkbConfigRoot":
        return cls(
            keycodes=basedir / "keycodes",
            compat=basedir / "compat",
            geometry=basedir / "geometry",
            symbols=basedir / "symbols",
            types=basedir / "types",
        )


@dataclass
class Option:
    """
    Wrapper around a single option -> symbols rules file entry. Has the properties
    name and directive where the directive consists of the XKB symbols file name
    and corresponding section, usually composed in the rules file as:
        name = +directive
    """

    name: str

    def __lt__(self, other) -> bool:
        return self.name < other.name

    @property
    def directive(self) -> Directive:
        f, s = self.name.split(":")
        return Directive(self, f, s)


def resolve_option(option: Option) -> DirectiveSet:
    directives: dict[str, Directive | None] = {
        s: None for s in XKB_CONFIG_ROOT.section_headers
    }
    directive = option.directive
    filename, section = directive.filename, directive.section
    for subdir, section_header in zip(
        XKB_CONFIG_ROOT.directories, XKB_CONFIG_ROOT.section_headers
    ):
        if not (subdir / filename).exists():
            # Some of our foo:bar entries map to a baz_vndr/foo file
            for vndr in subdir.glob("*_vndr"):
                vndr_path = vndr / filename
                if vndr_path.exists():
                    filename = vndr_path.relative_to(subdir).as_posix()
                    break
            else:
                continue

        # Now check if the target file actually has that section
        f = subdir / filename
        with open(f) as fd:
            found = any(f'{section_header} "{section}"' in line for line in fd)
            if found:
                directives[section_header] = Directive(option, filename, section)

    return DirectiveSet(
        option=option,
        keycodes=directives["xkb_keycodes"],
        compat=directives["xkb_compatibility"],
        geometry=directives["xkb_geometry"],
        symbols=directives["xkb_symbols"],
        types=directives["xkb_types"],
    )


def options(rules_xml) -> Iterable[Option]:
    """
    Yields all Options from the given XML file
    """
    tree = ET.parse(rules_xml)
    root = tree.getroot()

    def fetch_subelement(parent, name):
        sub_element = parent.findall(name)
        if sub_element is not None and len(sub_element) == 1:
            return sub_element[0]
        return None

    def fetch_text(parent, name):
        sub_element = fetch_subelement(parent, name)
        if sub_element is None:
            return None
        return sub_element.text

    def fetch_name(elem):
        try:
            ci_element = (
                elem
                if elem.tag == "configItem"
                else fetch_subelement(elem, "configItem")
            )
            name = fetch_text(ci_element, "name")
            assert name is not None
            return name
        except AssertionError as e:
            endl = "\n"  # f{} cannot contain backslashes
            e.args = (
                f"\nFor element {ET.tostring(elem).decode('utf-8')}\n{endl.join(e.args)}",
            )
            raise

    for option in root.iter("option"):
        yield Option(fetch_name(option))


def main():
    global XKB_CONFIG_ROOT

    parser = argparse.ArgumentParser(description="Generate the evdev keycode lists.")
    parser.add_argument(
        "--xkb-config-root",
        help="The XKB base directory",
        default=Path("."),
        type=Path,
    )
    parser.add_argument(
        "--rules-section",
        choices=["xkb_symbols", "xkb_compatibility", "xkb_types"],
        help="The rules section to generate",
        default="xkb_symbols",
    )
    parser.add_argument(
        "files", nargs="+", help="The base.xml and base.extras.xml files"
    )
    ns = parser.parse_args()

    XKB_CONFIG_ROOT = XkbConfigRoot.for_basedir(ns.xkb_config_root)

    all_options = []
    for f in ns.files:
        os = list(options(f))
        all_options.extend(os)

    directives = (resolve_option(o) for o in sorted(all_options) if o.name not in skip)

    def check_and_map(directive):
        assert (
            not directive.is_empty
        ), f"Option {directive.option} does not resolve to any section"

        return directive.for_section(ns.rules_section)

    filtered = (
        x
        for x in filter(
            lambda y: y is not None,
            map(check_and_map, directives),
        )
    )

    header = {
        "xkb_symbols": "symbols",
        "xkb_compatibility": "compat",
        "xkb_types": "types",
    }[ns.rules_section]

    print(f"! option                         = {header}")
    for d in filtered:
        assert d is not None
        print(f"  {d.name:30s} = +{d}")

    if ns.rules_section == "xkb_types":
        print(f"  {'custom:types':30s} = +custom")


if __name__ == "__main__":
    main()
