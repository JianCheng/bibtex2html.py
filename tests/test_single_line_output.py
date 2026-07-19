#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for single-line publication output.

Author: Jian Cheng (jian.cheng.1983@gmail.com)
Date: 2026-07-19
"""

import importlib.util
import os
import unittest


MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'bibtex2html',
    'bibtex2html.py',
)
SPEC = importlib.util.spec_from_file_location('bibtex2html_script', MODULE_PATH)
BIBTEX2HTML = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BIBTEX2HTML)


class SingleLineOutputTest(unittest.TestCase):
    """Verify that the single_line option controls visible line breaks."""

    def setUp(self):
        """Configure the generator with deterministic link output."""
        self.original_params = BIBTEX2HTML.params.copy()
        BIBTEX2HTML.params.update({
            'add_blank_line_after_item': False,
            'author_group': {},
            'author_names_highlighted': [],
            'bibtex_fields_download': ['project'],
            'bibtex_fields_note': ['note'],
            'conference_shortname_highlighted': [],
            'count_publisher': [],
            'dict_title': {'single line output': [3, 'https://example.org/citations']},
            'icon_pdf': '',
            'icon_www': '',
            'journal_fullname_highlighted_lower': [],
            'journal_shortname_highlighted': [],
            'publisher_short_full_names': [],
            'show_abstract': True,
            'show_bibtex': True,
            'show_citation': 'bs',
            'show_citation_lb': 0,
            'show_citation_types': ['article'],
            'show_citation_year': 2026,
            'target_link': '_self',
            'target_link_citation': '_blank',
            'type_conference_abstract': ['conference'],
            'type_conference_paper': ['inproceedings'],
            'use_bootstrap_dialog': False,
            'use_icon': False,
            'verbose': 0,
        })

    def tearDown(self):
        """Restore global generator parameters after each test."""
        BIBTEX2HTML.params.clear()
        BIBTEX2HTML.params.update(self.original_params)

    def test_single_line_true_keeps_links_on_publication_line(self):
        """Avoid inserting link-only newlines when single_line is enabled."""
        BIBTEX2HTML.params['single_line'] = True
        entry = {
            'ID': 'single-line',
            'ENTRYTYPE': 'article',
            'author': 'Jian Cheng',
            'journal': 'Journal',
            'title': 'Single line output',
            'year': '2026',
            'url': 'https://example.org/paper',
            'abstract': 'A short abstract.',
            'project': 'https://example.org/project',
            'note': 'selected',
        }

        output = BIBTEX2HTML.get_entry_output(entry)
        visible_output = output.split('<div class="bibtex"', 1)[0]

        self.assertNotIn('<br>', visible_output)
        self.assertIn('[<a target="_self" href="https://example.org/paper">link</a>]', visible_output)
        self.assertIn('[<a id="blk-single-line"', visible_output)
        self.assertIn('[<a id="alk-single-line"', visible_output)
        self.assertIn('[<a target="_self" href="https://example.org/project">project</a>]', visible_output)
        self.assertIn('[citations: <a target="_blank" href="https://example.org/citations">3</a>]', visible_output)
        self.assertIn('(<span class="hlnote0">selected</span>)', visible_output)
        self.assertNotIn('\n[<a id="blk-single-line"', visible_output)
        self.assertNotIn('\n[<a id="alk-single-line"', visible_output)
        self.assertNotIn('\n[<a target="_self" href="https://example.org/project">project</a>]', visible_output)
        self.assertNotIn('\n[citations:', visible_output)
        self.assertNotIn('\n(<span class="hlnote0">selected</span>)', visible_output)

    def test_single_line_false_keeps_multiline_publication_breaks(self):
        """Insert line breaks between publication text and links in multiline mode."""
        BIBTEX2HTML.params['single_line'] = False
        entry = {
            'ID': 'multi-line',
            'ENTRYTYPE': 'article',
            'author': 'Jian Cheng',
            'journal': 'Journal',
            'title': 'Single line output',
            'year': '2026',
            'url': 'https://example.org/paper',
            'abstract': 'A short abstract.',
            'project': 'https://example.org/project',
            'note': 'selected',
        }

        output = BIBTEX2HTML.get_entry_output(entry)
        visible_output = output.split('<div class="bibtex"', 1)[0]

        self.assertIn('<br>', visible_output)
        self.assertIn('\n[<a target="_self" href="https://example.org/paper">link</a>]', visible_output)
        self.assertIn('\n[<a id="blk-multi-line"', visible_output)
        self.assertIn('\n[<a id="alk-multi-line"', visible_output)
        self.assertIn('\n[<a target="_self" href="https://example.org/project">project</a>]', visible_output)
        self.assertIn('\n[citations:', visible_output)
        self.assertIn('\n(<span class="hlnote0">selected</span>)', visible_output)


if __name__ == '__main__':
    unittest.main()
