#!/usr/bin/env python3
#
# Call with pytest. Requires XKB_CONFIG_ROOT to be set

import os
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET


def _xkb_config_root():
    path = os.getenv('XKB_CONFIG_ROOT')
    assert path is not None, 'Environment variable XKB_CONFIG_ROOT must be set'
    print(f'Using XKB_CONFIG_ROOT={path}')

    xkbpath = Path(path)
    assert (xkbpath / 'rules').exists(), f'{path} is not an XKB installation'
    return xkbpath


@pytest.fixture
def xkb_config_root():
    return _xkb_config_root()


def iterate_layouts_variants(rules_xml):
    '''
    Return an iterator of type (layout, variant) for each element in the XML
    file.
    '''
    tree = ET.parse(rules_xml)
    root = tree.getroot()
    for layout in root.iter('layout'):
        yield layout, None

        for variant in layout.iter('variant'):
            yield layout, variant


def pytest_generate_tests(metafunc):
    # for any test_foo function with an argument named rules_xml,
    # make it the list of XKB_CONFIG_ROOT/rules/*.xml files.
    if 'rules_xml' in metafunc.fixturenames:
        rules_xml = list(_xkb_config_root().glob('rules/*.xml'))
        assert rules_xml
        metafunc.parametrize('rules_xml', rules_xml)
    # for any test_foo function with an argument named layout,
    # make it a Layout wrapper class for all layout(variant) combinations
    elif 'layout' in metafunc.fixturenames:
        rules_xml = list(_xkb_config_root().glob('rules/*.xml'))
        assert rules_xml
        layouts = []
        for f in rules_xml:
            for l, v in iterate_layouts_variants(f):
                layouts.append(Layout(f, l, v))
        metafunc.parametrize('layout', layouts)



class Layout:
    '''
    Wrapper class for layout/variants - both ConfigItems are available but
    the properties automatically pick the variant (if it exists) or the
    layout otherwise.
    '''
    def __init__(self, rulesfile, layout, variant=None):
        self.rulesfile = rulesfile
        self.layout = ConfigItem.from_elem(layout)
        self.variant = ConfigItem.from_elem(variant) if variant else None
        if variant:
            self.name = f"{self.layout.name}({self.variant.name})"
        else:
            self.name = f"{self.layout.name}"

    def _fetch(self, name):
        parent = self.variant or self.layout
        elements = parent.findall(name)
        if elements is None:
            return None
        elif len(elements) > 1:
            return elements
        else:
            return elements[0]

    @property
    def iso3166(self):
        return (self.variant or self.layout).iso3166

    @property
    def iso639(self):
        return (self.variant or self.layout).iso639


def prettyxml(element):
    return ET.tostring(element).decode('utf-8')


class ConfigItem:
    def __init__(self, name, shortDescription=None, description=None):
        self.name = name
        self.shortDescription = shortDescription
        self.description = description
        self.iso639 = []
        self.iso3166 = []

    @classmethod
    def _fetch_subelement(cls, parent, name):
        sub_element = parent.findall(name)
        if sub_element is not None and len(sub_element) == 1:
            return sub_element[0]
        else:
            return None

    @classmethod
    def _fetch_subelement_text(cls, parent, name):
        sub_element = parent.findall(name)
        return [e.text for e in sub_element]

    @classmethod
    def _fetch_text(cls, parent, name):
        sub_element = cls._fetch_subelement(parent, name)
        if sub_element is None:
            return None
        return sub_element.text

    @classmethod
    def from_elem(cls, elem):
        try:
            ci_element = cls._fetch_subelement(elem, 'configItem')
            name = cls._fetch_text(ci_element, 'name')
            assert name is not None
            # shortDescription and description are optional
            sdesc = cls._fetch_text(ci_element, 'shortDescription')
            desc = cls._fetch_text(ci_element, 'description')
            ci = ConfigItem(name, sdesc, desc)

            langlist = cls._fetch_subelement(ci_element, 'languageList')
            if langlist:
                ci.iso639 = cls._fetch_subelement_text(langlist, 'iso639Id')

            langlist = cls._fetch_subelement(ci_element, 'languageList')
            if langlist:
                ci.iso639 = cls._fetch_subelement_text(langlist, 'iso639Id')

            countrylist = cls._fetch_subelement(ci_element, 'countryList')
            if countrylist:
                ci.iso3166 = cls._fetch_subelement_text(countrylist, 'iso3166')

            return ci
        except AssertionError as e:
            endl = "\n"  # f{} cannot contain backslashes
            e.args = (f'\nFor element {prettyxml(elem)}\n{endl.join(e.args)}',)
            raise


def test_duplicate_layouts(rules_xml):
    tree = ET.parse(rules_xml)
    root = tree.getroot()
    layouts = {}
    for layout in root.iter('layout'):
        ci = ConfigItem.from_elem(layout)
        assert ci.name not in layouts, f'Duplicate layout {ci.name}'
        layouts[ci.name] = True

        variants = {}
        for variant in layout.iter('variant'):
            vci = ConfigItem.from_elem(variant)
            assert vci.name not in variants, \
                f'{rules_xml}: duplicate variant {ci.name}({vci.name}):\n{prettyxml(variant)}'
            variants[vci.name] = True


def test_duplicate_models(rules_xml):
    tree = ET.parse(rules_xml)
    root = tree.getroot()
    models = {}
    for model in root.iter('model'):
        ci = ConfigItem.from_elem(model)
        assert ci.name not in models, f'Duplicate model {ci.name}'
        models[ci.name] = True


def test_iso3166(layout):
    pycountry = pytest.importorskip('pycountry')
    country_codes = [c.alpha_2 for c in pycountry.countries]
    for code in layout.iso3166:
        assert code in country_codes, \
            f'{layout.rulesfile}: unknown country code "{code}" in {layout.name}'


def test_iso639(layout):
    pycountry = pytest.importorskip('pycountry')

    # A list of languages not in pycountry, so we need to special-case them
    special_langs = [
        'ber',  # Berber languages (collective), https://iso639-3.sil.org/code/ber
        'btb',  # Beti (Cameroon), https://iso639-3.sil.org/code/btb
        'fox',  # Formosan languages (collective), https://iso639-3.sil.org/code/fox
        'phi',  # Philippine languages (collective), https://iso639-3.sil.org/code/phi
        'ovd',  # Elfdalian, https://iso639-3.sil.org/code/ovd
    ]
    language_codes = [c.alpha_3 for c in pycountry.languages] + special_langs
    for code in layout.iso639:
        assert code in language_codes, \
            f'{layout.rulesfile}: unknown language code "{code}" in {layout.name}'
