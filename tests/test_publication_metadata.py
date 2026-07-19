#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for publication metadata attributes.

Author: Jian Cheng (jian.cheng.1983@gmail.com)
Date: 2026-07-18
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


class PublicationMetadataTest(unittest.TestCase):
    """Verify machine-readable metadata generated for publication entries."""

    def setUp(self):
        """Configure the generator parameters used by metadata helpers."""
        BIBTEX2HTML.params['author_names_highlighted'] = ['Jian Cheng']
        BIBTEX2HTML.params['count_publisher'] = [
            ['TMI', 'IEEE Transactions on Medical Imaging'],
            'MICCAI',
        ]
        BIBTEX2HTML.params['publisher_short_full_names'] = [
            ['TMI', 'IEEE Transactions on Medical Imaging'],
        ]
        BIBTEX2HTML.params['conference_shortname_highlighted'] = ['MICCAI']
        BIBTEX2HTML.params['journal_shortname_highlighted'] = ['TMI']
        BIBTEX2HTML.params['journal_fullname_highlighted_lower'] = [
            'ieee transactions on medical imaging',
        ]
        BIBTEX2HTML.params['show_citation_year'] = 0
        BIBTEX2HTML.params['show_bibtex'] = False
        BIBTEX2HTML.params['type_conference_paper'] = ['inproceedings']
        BIBTEX2HTML.params['type_conference_abstract'] = ['conference']
        BIBTEX2HTML.params['selected_paper_ids'] = []

    def test_journal_metadata_and_roles(self):
        """Return normalized metadata for a selected journal article."""
        entry = {
            'ID': 'cheng:2026.test',
            'ENTRYTYPE': 'article',
            'author': 'A. Author, Jian Cheng',
            'author_corresponding': 'Jian Cheng',
            'journal': 'IEEE Transactions on Medical Imaging (TMI)',
            'title': 'A test',
            'year': '2026',
        }

        metadata = BIBTEX2HTML.get_entry_metadata(entry)

        self.assertEqual(metadata['bib_id'], 'cheng-2026-test')
        self.assertEqual(metadata['publication_type'], 'journal')
        self.assertEqual(metadata['venue'], 'IEEE Transactions on Medical Imaging')
        self.assertEqual(metadata['venue_short'], 'TMI')
        self.assertTrue(metadata['selected_venue'])
        self.assertEqual(metadata['selected_venue_order'], 0)
        self.assertEqual(metadata['highlighted_author_roles'], 'corresponding')

    def test_first_author_and_special_character_escaping(self):
        """Return first-author metadata and safely escape HTML attributes."""
        entry = {
            'ID': 'special',
            'ENTRYTYPE': 'inproceedings',
            'author': 'Jian Cheng, A. Author',
            'booktitle': 'Research & Development "Workshop"',
            'title': 'A test',
            'year': '2025',
        }

        metadata = BIBTEX2HTML.get_entry_metadata(entry)

        self.assertEqual(metadata['publication_type'], 'conference')
        self.assertEqual(metadata['highlighted_author_roles'], 'first')
        self.assertEqual(
            BIBTEX2HTML.escape_html_attribute(metadata['venue']),
            'Research &amp; Development &quot;Workshop&quot;',
        )

    def test_existing_html_entity_is_normalized_before_escaping(self):
        """Avoid double escaping an existing HTML entity in metadata."""
        self.assertEqual(
            BIBTEX2HTML.escape_html_attribute(
                'Universit&eacute; Nice & "Research"'
            ),
            'Université Nice &amp; &quot;Research&quot;',
        )

    def test_selected_venue_without_separate_short_name(self):
        """Keep the venue name as its short name when configured that way."""
        BIBTEX2HTML.params['count_publisher'].append(['eLife'])
        BIBTEX2HTML.params['publisher_short_full_names'].append(['eLife'])
        entry = {
            'ID': 'elife',
            'ENTRYTYPE': 'article',
            'author': 'Jian Cheng',
            'journal': 'eLife',
            'title': 'A test',
            'year': '2024',
        }

        metadata = BIBTEX2HTML.get_entry_metadata(entry)

        self.assertEqual(metadata['venue'], 'eLife')
        self.assertEqual(metadata['venue_short'], 'eLife')
        self.assertTrue(metadata['selected_venue'])

    def test_publication_type_categories(self):
        """Return stable public categories for representative BibTeX entries."""
        cases = [
            ({'ENTRYTYPE': 'misc', 'eprint': 'arXiv:1234'}, 'preprint'),
            ({'ENTRYTYPE': 'book'}, 'book'),
            ({'ENTRYTYPE': 'inbook'}, 'book-chapter'),
            ({'ENTRYTYPE': 'article'}, 'journal'),
            ({'ENTRYTYPE': 'inproceedings'}, 'conference'),
            ({'ENTRYTYPE': 'conference'}, 'conference-abstract'),
            ({'ENTRYTYPE': 'techreport'}, 'research-report'),
            ({'ENTRYTYPE': 'phdthesis'}, 'thesis'),
            ({'ENTRYTYPE': 'misc'}, 'miscellaneous'),
        ]

        for entry, expected in cases:
            self.assertEqual(BIBTEX2HTML.get_publication_type(entry), expected)

    def test_missing_optional_fields(self):
        """Return empty metadata for an entry without author, year, or venue."""
        entry = {
            'ID': 'authorless',
            'ENTRYTYPE': 'misc',
            'title': 'An entry without optional fields',
        }

        metadata = BIBTEX2HTML.get_entry_metadata(entry)

        self.assertEqual(metadata['year'], '')
        self.assertEqual(metadata['venue'], '')
        self.assertEqual(metadata['venue_short'], '')
        self.assertFalse(metadata['selected_venue'])
        self.assertEqual(metadata['highlighted_author_roles'], '')

    def test_entry_output_without_author(self):
        """Generate a complete publication item when author is omitted."""
        entry = {
            'ID': 'authorless-output',
            'ENTRYTYPE': 'misc',
            'title': 'An authorless publication',
            'year': '2025',
        }

        output = BIBTEX2HTML.get_entry_output(entry)

        self.assertIn('data-highlighted-author-roles=""', output)
        self.assertIn('<span class="title">"An authorless publication"</span>', output)
        self.assertNotIn('<span class="author">', output)

    def test_thesis_output_marks_visible_venue(self):
        """Wrap a thesis school for client-side Venue highlighting."""
        entry = {
            'ID': 'thesis',
            'ENTRYTYPE': 'phdthesis',
            'author': 'Jian Cheng',
            'school': 'Universit&eacute; Nice',
            'title': 'A thesis',
            'year': '2012',
        }

        output = BIBTEX2HTML.get_entry_output(entry)

        self.assertIn('data-venue="Université Nice"', output)
        self.assertIn(
            'PhD thesis, <span class="publication-venue">'
            'Universit&eacute; Nice</span>',
            output,
        )

    def test_entry_output_contains_escaped_metadata_and_body(self):
        """Write escaped metadata attributes without changing publication text."""
        entry = {
            'ID': 'special:entry.test',
            'ENTRYTYPE': 'inproceedings',
            'author': 'Jian Cheng, A. Author',
            'booktitle': 'Research & Development "Workshop"',
            'title': 'A visible title',
            'year': '2025',
        }
        BIBTEX2HTML.params['selected_paper_ids'] = ['other', 'special:entry.test']

        output = BIBTEX2HTML.get_entry_output(entry)
        opening_tag = output.split('\n', 2)[1]

        self.assertIn('class="publication-item"', opening_tag)
        self.assertIn('data-bib-id="special-entry-test"', opening_tag)
        self.assertIn('data-entry-type="inproceedings"', opening_tag)
        self.assertIn('data-publication-type="conference"', opening_tag)
        self.assertIn('data-selected-paper="true"', opening_tag)
        self.assertIn('data-selected-paper-order="1"', opening_tag)
        self.assertIn('data-year="2025"', opening_tag)
        self.assertIn(
            'data-venue="Research &amp; Development &quot;Workshop&quot;"',
            opening_tag,
        )
        self.assertIn('data-highlighted-author-roles="first"', opening_tag)
        self.assertIn('<span class="title">"A visible title"</span>', output)
        self.assertIn('<span class="author">', output)

    def test_selected_paper_metadata_uses_exact_bibtex_id(self):
        """Match selected papers by the original case-sensitive BibTeX ID."""
        BIBTEX2HTML.params['selected_paper_ids'] = ['first', 'cheng:TMI2021']
        entry = {
            'ID': 'cheng:TMI2021',
            'ENTRYTYPE': 'article',
            'title': 'A selected paper',
        }

        metadata = BIBTEX2HTML.get_entry_metadata(entry)

        self.assertTrue(metadata['selected_paper'])
        self.assertEqual(metadata['selected_paper_order'], 1)

        entry['ID'] = 'cheng:tmi2021'
        metadata = BIBTEX2HTML.get_entry_metadata(entry)
        self.assertFalse(metadata['selected_paper'])
        self.assertEqual(metadata['selected_paper_order'], -1)

    def test_selected_paper_validation_rejects_duplicates_and_missing_ids(self):
        """Reject ambiguous or unavailable selected paper configuration."""
        entries = [{'ID': 'known'}]
        BIBTEX2HTML.params['selected_paper_ids'] = ['known', 'known']
        with self.assertRaisesRegex(ValueError, 'Duplicate selected_paper_ids: known'):
            BIBTEX2HTML.validate_selected_paper_ids(entries)

        BIBTEX2HTML.params['selected_paper_ids'] = ['known', 'missing']
        with self.assertRaisesRegex(ValueError, 'not found.*missing'):
            BIBTEX2HTML.validate_selected_paper_ids(entries)

        BIBTEX2HTML.params['selected_paper_ids'] = ['known']
        self.assertIsNone(BIBTEX2HTML.validate_selected_paper_ids(entries))


if __name__ == '__main__':
    unittest.main()
