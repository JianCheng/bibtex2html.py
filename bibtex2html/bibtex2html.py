#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Description: Convert bibtex to html.

Usage:
  bibtex2html.py <bibfile> <htmlfile> [-v <verbose>]  [--conf <conffile>] [-i <input>] [--outbib <outbibfile>] [--nc]
  bibtex2html.py (-h | --help)

Options:

  -h --help                Show this screen.
  -v --verbose <verbose>   Verbose level. [default: 0]

  -c --conf <conffile>     Configuration file.
  -i --input <input>       Input cmd parameters which can override some parameters in -c.
  --outbib <outbibfileb>   Output .bib file with cleaned and selected bib entries
  --nc                     No citation. Don't use google scholar. Same as -i "{'show_citation':'no', 'show_total_citation':False}"

Examples:

bibtex2html.py papers.bib papers.html
bibtex2html.py papers.bib papers.html -c papers_conf.ini
bibtex2html.py papers.bib papers.html -c papers_conf.ini --nc
bibtex2html.py papers.bib papers.html -c papers_conf.ini --outbib out.bib
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type'}"
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type_year', 'bulleted_list':'ol_reversed'}"
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type', 'css_file': 'style.css'}"
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type', 'selection_and': {'author': ['Jian Cheng'], 'year':[2010,2013] }}"

bibtex2html.py papers.bib papers -c group_conf.ini
bibtex2html.py papers.bib papers -c group_conf.ini --nc

Author(s): Jian Cheng (jian.cheng.1983@gmail.com)
"""

from __future__ import print_function
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    from urllib import FancyURLopener
    import ConfigParser as configparser
else:
    from urllib.request import FancyURLopener
    import configparser
    import functools

    def unicode(ss):
        return ss

import re, os, io
import shutil
import datetime
import codecs
import textwrap

from bs4 import BeautifulSoup

import bibtexparser

from docopt import docopt

import ast


# output html encoding
#  encoding = 'UTF-8'
#  encoding = 'ISO-8859-1'


params = {}
params['title'] = u'Publication List'
params['css_file'] = ''
params['encoding'] = 'UTF-8'

#  style of paper list ('type', 'year', 'type_year')
params['show_paper_style'] = 'type'

params['journal_shortname_highlighted'] = [u'TMI', u'HBM', u'MIA', u'MedIA', u'TIP', u'TPAMI', u'IJCV', u'MRM']
params['journal_fullname_highlighted'] = [u'Nature Methods', u'NeuroImage', u'Medical Image Analysis', u'IEEE Transactions on Medical Imaging',
                               u'IEEE Transactions on Pattern Analysis and Machine Intelligence', u'Medical Physics', u'Magnetic Resonance in Medicine',
                               u'SIAM Journal on Imaging Sciences']
params['conference_shortname_highlighted'] = [u'MICCAI', u'IPMI', u'CVPR', u'NIPS', u'ICCV', u'ECCV']
params['author_names_highlighted'] = []

# used for selection, select entries from bib file
params['selection_and'] = {}
params['selection_or'] = {}

params['outbibfile'] = ''

# show the number of papers in specific journals and conferences
params['show_count_number'] = True
# counted publisher (conferences are determined by conference_shortname_highlighted)
params['count_publisher'] = [
    [u'Nature Methods'],
    [u'TMI', u'IEEE Transactions on Medical Imaging'],
    [u'MedIA', u'MIA', u'Medical Image Analysis'],
    [u'TPAMI', u'IEEE Transactions on Pattern Analysis and Machine Intelligence'],
    [u'IJCV', u'International Journal of Computer Vision'],
    [u'NeuroImage'],
    [u'HBM', u'Human Brain Mapping'],
    [u'TIP', u'IEEE Transactions on Image Processing'],
    [u'MRM', 'Magnetic Resonance in Medicine'],
    [u'Medical Physics'],
]

params['show_citation_types'] = [u'article', u'inproceedings', u'phdthesis', u'inbook']

params['author_group'] = {}

#  'no', 'scholar.js' 'bs'
params['show_citation'] = 'no'
# show total citation by googlescholarID using bs
params['show_total_citation'] = False
# obtained by googlescholarID by using bs
params['dict_title'] = {} # dict of papers:  {title: [citations, url]}
params['google_scholar_out'] = ()

params['show_page_title'] = True

#  params['googlescholarID'] = u"'BARqXQ0AAAAJ'"
params['googlescholarID'] = u''
params['show_citation_before_years'] = 1
#  params['scholar.js'] = 'scholar.js'
params['scholar.js'] = 'https://kha.li/dist/scholar/scholar-0.1.1.min.js'

params['use_icon'] = False
#  params['icon_path'] = u'.'
params['icon_pdf'] = ''
params['icon_www'] = ''
params['icon_size'] = '16px'

#  open link in a new tab
#  params['target_link'] = u'_blank'
params['target_link'] = u'_self'
# target attr for citations
params['target_link_citation'] = u'_blank'


#  If false, show multiple lines
params['single_line'] = True

#  Use ordered list if 'ol', unordered list if 'ul'
params['bulleted_list'] = 'ol'

params['show_abstract'] = True
params['show_bibtex'] = True
params['use_bootstrap_dialog'] = True

# default conference paper type
params['type_conference_paper'] = [u'inproceedings']
# default conference abstract type
params['type_conference_abstract'] = [u'conference']

# bibtex download fields
params['bibtex_fields_download'] = ['arxiv', 'project', 'slides', 'poster', 'video', 'code', 'software', 'data', 'media']
# bibtex note fields
params['bibtex_fields_note'] = ['note', 'hlnote', 'hlnote2']
# show bibtex with given fields
params['bibtex_show_list'] = ['author', 'title', 'journal', 'booktitle', 'year', 'volume', 'number', 'pages', 'month', 'publisher', 'organization', 'school', 'address', 'edition',
                              'editor', 'institution', 'chapter', 'series', 'pdf', 'doi', 'url', 'hal_id', 'eprint', 'archiveprefix', 'primaryclass']

# print signs for first authors, corresponding authors.
params['show_author_sign'] = False
params['author_sign'] = {'author_first': '#', 'author_corresponding': '*'}

# add <br> after each item
params['add_blank_line_after_item'] = False
# customized bootstrap if provided
params['bootstrap_css'] = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css'


# regular expression for \emph{...{...}*...}
emph = re.compile(u'''
            \\\\emph{                       # \emph{
            (?P<emph_text>([^{}]*{[^{}]*})*.*?)  # (...{...})*...
            }''', re.VERBOSE)               # }


def remove_empty_lines(strIn):
    '''Remove empty lines from a string'''
    return os.linesep.join([s for s in strIn.splitlines() if s.strip()])


def is_author_selected(entry, names, select_field=''):
    '''Return true if the author list of the entry is selected.

    Parameters
    ----------
        entry        :   bibtex entry
        names        :   selected author names
        select_field :   'first': first author;  'corresponding': corresponding author; '': first or corresponding author

    Returns
    -------
        is_selected : boolean
    '''

    author_names = entry['author'].split(', ')
    k = 'author_' + select_field
    if select_field=='first':
        if author_names[0] in names:
            return True
        elif k in entry:
            authorFirst_names = entry[k].split(', ')
            for name in authorFirst_names:
                if name in names:
                    return True
        return False
    elif select_field=='corresponding':
        if not k in entry:
            return False
        else:
            authorCorr_names = entry[k].split(', ')
            for name in authorCorr_names:
                if name in names:
                    return True
        return False
    elif select_field=='':
        return is_author_selected(entry, names, 'first') or is_author_selected(entry, names, 'corresponding')
    else:
        raise ValueError("Wrong select_field ('first', 'corresponding', or '')!")


def cmp_by_type(y, x):
    '''sort entry by type'''

    if x['ENTRYTYPE']!=y['ENTRYTYPE']:
        if y['ENTRYTYPE']=='phdthesis': return -1
        if y['ENTRYTYPE'] in ['inbook', 'book'] and x['ENTRYTYPE'] not in ['phdthesis']: return -1
        if y['ENTRYTYPE']=='article' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook']: return -1
        if y['ENTRYTYPE']=='inproceedings' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook', 'article']: return -1
        if y['ENTRYTYPE']=='conferences' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook', 'article', 'inproceedings']: return -1
        return 1
    else:
        if x['ENTRYTYPE']=='article':
            x_hl, y_hl = False, False
            for word in params['journal_shortname_highlighted']:
                if x['journal'].find('(%s)' % word)>=0: x_hl=True
                if y['journal'].find('(%s)' % word)>=0: y_hl=True
            for word in params['journal_fullname_highlighted_lower']:
                if not x_hl and x['journal'].lower().find(word)>=0: x_hl=True
                if not y_hl and y['journal'].lower().find(word)>=0: y_hl=True
            if x_hl and not y_hl:  return 1
            if not x_hl and y_hl:  return -1
        elif x['ENTRYTYPE'] in params['type_conference_paper']:
            x_hl, y_hl = False, False
            for word in params['conference_shortname_highlighted']:
                if x['booktitle'].find(word+"'")>=0: x_hl=True
                if y['booktitle'].find(word+"'")>=0: y_hl=True
            if x_hl and not y_hl:  return 1
            if not x_hl and y_hl:  return -1

        #  same type, both types are highlighted or not highlighted
        if len(params['author_names_highlighted']):
            x_hl = is_author_selected(x, params['author_names_highlighted'])
            y_hl = is_author_selected(y, params['author_names_highlighted'])
            if x_hl and not y_hl:  return 1
            if not x_hl and y_hl:  return -1

        return 1


def cmp_by_year(y, x):
    '''sort entry by year'''

    if x['year'].isdigit() and y['year'].isdigit():
        return int(x['year']) - int(y['year']) if int(x['year']) != int(y['year']) else cmp_by_type(y,x)
    elif x['year'].isdigit() and not y['year'].isdigit():
        return -1
    elif not x['year'].isdigit() and y['year'].isdigit():
        return 1
    else:
        return 1


def highlight_author(entry, out_path=''):
    """return a string with highlighted author"""

    authors = entry['author'].split(', ')

    authors_new = []
    for p in authors:
        if len(params['author_group']):
            if p in params['author_group'].keys():
                author_split = p.rsplit(' ', 1)
                if len(author_split)!=2:
                    raise ValueError('author_split should have 2 elements for first and last name')
                # last-first.html
                author_file = os.path.join(params['author_group_Author'], author_split[1] + '-' + author_split[0].replace(' ', '-')+'.html')
                author_file = os.path.relpath(author_file, os.path.dirname(out_path))
                authors_new.append('<a target="%s" href="%s"><b>%s</b></a>' % (params['target_link'], author_file, p));
            else:
                authors_new.append(p);
        else:
            if p in params['author_names_highlighted']:
                authors_new.append('<b>%s</b>' % p);
            else:
                authors_new.append(p);

    if params['show_author_sign']:
        authorFirst_names = entry['author_first'].split(', ') if 'author_first' in entry else []
        authorCorr_names = entry['author_corresponding'].split(', ') if 'author_corresponding' in entry else []
        if len(authorFirst_names) or len(authorCorr_names):
            for i, name in enumerate(authors):
                if name in authorFirst_names:
                    authors_new[i] = authors_new[i] + params['author_sign']['author_first']
                if name in authorCorr_names:
                    authors_new[i] = authors_new[i] + params['author_sign']['author_corresponding']

    return ', '.join(authors_new)


def highlight_publisher(publisher):
    """return a string with highlighted jounrls and conferences"""

    words_highlighted = params['journal_shortname_highlighted'] + params['conference_shortname_highlighted']

    if publisher.lower() in params['journal_fullname_highlighted_lower']:
        return '<b>%s</b>' % publisher
    else:
        dem_1 = publisher.find('(')
        if dem_1>=0:
            dem_2 = publisher.find(')')
            dem_3 = publisher.find("'")
            dem = dem_2 if dem_3<0 else dem_3
            if publisher[dem_1+1:dem] in words_highlighted:
                return '%s<b>%s</b>%s' % (publisher[:dem_1+1], publisher[dem_1+1:dem], publisher[dem:])
            else:
                return publisher
        else:
            return publisher


def get_title_citation_url(scholarID):
    '''get a dictionary {title: [citations, url]}, total citations, h-index from a given googlescholar id'''

    if scholarID==None or scholarID==u'':
        raise ValueError("no googlescholarID")

    openurl = FancyURLopener().open
    url0 = u'https://scholar.google.com/citations?user=%s&hl=en' % scholarID
    url = url0 + u'&view_op=list_works&sortby=pubdate&cstart=0&pagesize=1000'
    soup = BeautifulSoup(openurl(url).read(), "lxml")

    #  title: [citations, url]
    soup_all_gsc_a_at = soup.findAll("a", { "class" : "gsc_a_at" })
    title = [unicode(u''.join(i.findAll(text=True))).strip() for i in soup_all_gsc_a_at]
    title_url = [u'https://scholar.google.com/%s' % i['href'] for i in soup_all_gsc_a_at]
    citations = [unicode(u''.join(i.findAll(text=True))).strip() for i in soup.findAll("a", { "class" : "gsc_a_ac" })]

    dict_out={}
    for i, name in enumerate(title):
        dict_out[name.lower()] = [citations[i] if citations[i]!=u'' else u'0', title_url[i]]

    #  (total_citations, h-index, str_out)
    career = soup.findAll("td", { "class" : "gsc_rsb_std" }, text=True)
    citations = unicode(career[0].get_text())
    hindex = unicode(career[2].get_text())

    str_out = '''<p><big>&#8226;&nbsp;<b>Total Citations</b>: <a target="%s" href='%s'>%s</a> &#8226;&nbsp;  <b>H-Index</b>: <a target="%s" href='%s'>%s</a></big></p>''' % (params['target_link_citation'], url0, citations, params['target_link_citation'], url0, hindex)

    return dict_out, citations, hindex, str_out


def get_arxivID_from_entry(entry):
    '''get arxiv id'''

    id = ''
    if 'eprint' in entry or 'arxiv' in entry:
        word = 'eprint' if 'eprint' in entry else 'arxiv'
        w = entry[word].lower()
        pos = w.find('arxiv:')
        if pos>=0:
            id = w[pos+6:]

    elif 'journal' in entry:
        journal = entry['journal'].lower()
        words = journal.split()
        for w in words:
            pos = w.find('arxiv:')
            if pos>=0:
                id = w[pos+6:]
                return id

    return id


def get_arxivlink_from_entry(entry):
    '''get arxiv link'''

    return 'https://arxiv.org/abs/%s' % get_arxivID_from_entry(entry)


def get_pdflink_from_entry(entry):
    '''get pdf link from bib entry (keys: pdf, hal_id)'''

    if 'pdf' in entry and entry['pdf']!='':
        return entry['pdf']
    elif get_arxivID_from_entry(entry)!='':
        return 'https://arxiv.org/pdf/%s.pdf' % get_arxivID_from_entry(entry)
    elif 'hal_id' in entry:
        return 'https://hal.archives-ouvertes.fr/%s/document' % entry['hal_id']
    else:
        return ''


def get_wwwlink_from_entry(entry):
    '''get website link from bib entry (keys: url, www, doi, hal_id)'''

    if 'url' in entry and entry['url']!='':
        return entry['url']
    elif 'www' in entry:
        return entry['www']
    elif 'doi' in entry:
        return 'https://dx.doi.org/%s' % entry['doi']
    elif get_arxivID_from_entry(entry)!='':
        return 'https://arxiv.org/abs/%s' % get_arxivID_from_entry(entry)
    elif 'hal_id' in entry:
        return 'https://hal.archives-ouvertes.fr/%s' % entry['hal_id']
    else:
        return ''


def get_journal_from_entry(entry):
    '''get journal from entry (keys: journal, eprint)'''

    if 'journal' in entry and entry['journal']!='':
        return entry['journal']
    elif 'eprint' in entry:
        return entry['eprint']
    else:
        return ''


def add_empty_fields_in_entry(entry):
    '''add some fields using other fields'''

    #  add pdf_link from other keys
    if not 'pdf' in entry or entry['pdf']=='':
        pdf_link = get_pdflink_from_entry(entry)
        if pdf_link!='':
            entry['pdf'] = pdf_link

    #  add url from other keys
    if not 'url' in entry or entry['url']=='':
        www_link = get_wwwlink_from_entry(entry)
        if www_link!='':
            entry['url'] = www_link

    #  add journal from other keys
    if not 'journal' in entry or entry['journal']=='':
        journal = get_journal_from_entry(entry)
        if journal!='':
            entry['journal'] = journal


def get_bibtex_from_entry(entry, comma_to_and=False):
    '''Get bibtex string from an entry. Remove some non-standard fields.'''

    entry2 = entry.copy()

    add_empty_fields_in_entry(entry2)

    if comma_to_and:
        authors = entry2['author'].split(', ')
        entry2['author'] = ' and '.join(authors)

    entry_standard = {}
    keep_list = ['ENTRYTYPE', 'ID']
    for i_str in entry2.keys():
        if i_str in params['bibtex_show_list'] or i_str in keep_list:
            entry_standard[i_str] = entry2[i_str]

    bibdata = bibtexparser.bibdatabase.BibDatabase()
    bibdata.entries = [entry_standard]
    bibstr = bibtexparser.dumps(bibdata)
    bibstr = remove_empty_lines(bibstr)

    if params['verbose']>=2:
        print('bibstr=%s' % bibstr)

    return bibstr


def get_publisher_shortname_from_entry(entry):
    '''Get shortname for journals or conferences from an entry'''

    pub = ''
    if 'journal' in entry:
        pub = entry['journal']
    elif 'booktitle' in entry:
        pub = entry['booktitle']

    dem_1 = pub.find('(')
    if dem_1>=0:
        dem_2 = pub.find(')')
        dem_3 = pub.find("'")
        dem = dem_2 if dem_3<0 else dem_3
        return pub[dem_1+1:dem]
    else:
        pub_lower = pub.lower()
        for cp in params['count_publisher']:
            if len(cp)==1:
                if cp[0].lower() == pub_lower:
                    return cp[0]
            else:
                for ii in range(1, len(cp)):
                    if cp[ii].lower() == pub_lower:
                        return cp[0]

    return pub


def _get_count_name_number(entries):
    '''get a name list and a list of count numbers from entries'''

    count_name = []
    for name in params['count_publisher']:
        if type(name)==list:
            count_name.append(name[0])
        else:
            count_name.append(name)
    count_number = [0]*len(count_name)

    for e in entries:
        name = get_publisher_shortname_from_entry(e)
        for i, name1 in enumerate(count_name):
            if name.lower()==name1.lower():
                count_number[i] += 1

    count_number2 = []
    count_name2 = []
    for name, number in zip(count_name, count_number):
        if number:
            count_name2.append(name)
            count_number2.append(number)

    return count_name2, count_number2


def get_publisher_countnumber_from_entries(entries):
    '''Get count numbers from entries for specific journals (conferences).

    Parameters
    ----------
        entries :   list of entries

    Returns
    -------
        count_name : list of journal (or conference) names
        count_number: list of numbers
        count_str :  output string in html format
    '''

    count_name, count_number = _get_count_name_number(entries)

    if sum(count_number):
        count_str_list=['<p>&#8226;&nbsp;']
        for name, num in zip(count_name, count_number):
            if num>0:
                str_count = '''<b>%s</b> (%s) &#8226;&nbsp;''' % (name, num)
                count_str_list.append(str_count)
        count_str_list.append('</p>')

        return count_name, count_number, ''.join(count_str_list)

    else:
        return [], [], '<p>&nbsp;</p>'


def is_entry_selected_by_key(entry, k, v):
    '''return true if entry is selected by a given key and value list

    Parameters
    ----------
        entry :    a bib entry
        k :        key (string)
        v :        value list (string list)

    Returns
    -------
        output : True if it is selected
    '''

    if k == 'year':
        return int(entry[k]) in v
    elif k in 'author':
        author_names = entry[k].split(', ')
        for name in v:
            if name in author_names:
                return True
        return False
    elif k=='author_first':
        return is_author_selected(entry, v, 'first')
    elif k =='author_corresponding':
        return is_author_selected(entry, v, 'corresponding')
    else:
        raise ValueError('Wrong selection keys!')

    return True


def is_entry_selected(entry, selection_and=None, selection_or=None):
    '''return true if entry is selected

    Parameters
    ----------
        entry          :  a bib entry
        selection_and  :  dict with conditions (and operator)
        selection_or   :  dict with conditions (or operator)

    Returns
    -------
        output : True if it is selected
    '''

    if selection_and is None:
        selection_and = params['selection_and']
    if selection_or is None:
        selection_or = params['selection_or']

    if not selection_and and not selection_or:
        return True
    if selection_and and selection_or:
        raise ValueError('selection_and and selection_or cannot be used together')

    if selection_and:
        for k, v in selection_and.items():
            if not is_entry_selected_by_key(entry, k, v):
                return False
        return True
    elif selection_or:
        for k, v in selection_or.items():
            if is_entry_selected_by_key(entry, k, v):
                return True
        return False
    else:
        raise Exception('Wrong logic here')


def get_anchor_name(name):
    '''get anchor from a string'''

    if name.isdigit():
        return 'year'+ name
    else:
        return name.lower().replace(' ', '-')


def get_bulleted_list_str():
    '''get html string for bulleted list'''

    if params['bulleted_list']=='ol':
        return '<ol>', '</ol>'
    elif params['bulleted_list']=='ul':
        return '<ul>', '</ul>'
    elif params['bulleted_list']=='ol_reversed':
        return '<ol reversed>', '</ol>'
    else:
        raise ValueError("Wrong params['bulleted_list']. Must be 'ol', 'ul', 'ol_reversed'")


def get_html_prelog(out_path=''):
    '''get prelog in html.'''

    css_file = os.path.relpath(params['css_file'], os.path.dirname(out_path)) if params['css_file'] and os.path.exists(params['css_file']) else ''
    bootstrap_css_file = os.path.relpath(params['bootstrap_css'], os.path.dirname(out_path)) if params['bootstrap_css'] and os.path.exists(params['bootstrap_css']) else params['bootstrap_css']

    # html prelog
    # modify according to your needs
    prelog = """<!DOCTYPE HTML
        PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "https://www.w3.org/TR/html4/strict.dtd">
    <head>
    <meta http-equiv=Content-Type content="text/html; charset=%s">
    <title>%s</title>

    <script type="text/javascript" src="https://code.jquery.com/jquery-2.2.0.min.js"></script>
    <link rel="stylesheet" href="%s">
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <script type="text/javascript" src="%s"></script>


    <script type="text/javascript">
        function toggle(showHideDiv, switchTextDiv)
        {
        var ele = document.getElementById(showHideDiv);
        var text = document.getElementById(switchTextDiv);
        if(ele.style.display == "block")
        {
            ele.style.display = "none";
        }
        else
        {
            ele.style.display = "block";
        }
        }
    </script>

    <link rel="stylesheet" type="text/css" href="%s">
    <style type="text/css">
    </style>

    </head>
    <body>


    <div id="content">
    <br>
    """ % (params['encoding'], params['title'], bootstrap_css_file, params['scholar.js'] if params['show_citation']=='scholar.js' else '', css_file)

    return prelog


def get_html_disclaimer():
    '''return str of disclaimer'''

    import time, getpass

    log_sign = ''
    if params['show_author_sign']:
        log_sign='\n<p>%s denotes co-first authors. %s denotes corresponding authors.</p> \n' % (params['author_sign']['author_first'], params['author_sign']['author_corresponding'])


    log_disclaimer = """
<br><br /><br><br />
<u><strong>Disclaimer:</strong></u><br /><br />
<p><em>
This material is presented to ensure timely dissemination of
scholarly and technical work. Copyright and all rights therein
are retained by authors or by other copyright holders.
All person copying this information are expected to adhere to
the terms and constraints invoked by each author's copyright.
In most cases, these works may not be reposted
without the explicit permission of the copyright holder.

</em></p>

%s

Last modifiled:  %s

<br />Author: %s

<br><br />

<p>This document was translated from bibtex by
<a href="https://github.com/JianCheng/bibtex2html.py"><em>bibtex2html.py</em></a>
</p>

""" % (log_sign, time.strftime("%Y-%m-%d, %H:%M:%S"), getpass.getuser())

    return log_disclaimer



def clean_entry(entry):
    '''Clean up an entry'''

    for k, v in entry.items():

        # remove leading and trailing whitespace
        v = v.strip()
        #  print k,v

        # replace special characters - add more if necessary
        v = v.replace('\\AE', u'Æ')
        v = v.replace('\\O',  u'Ø')
        v = v.replace('\\AA', u'Å')
        v = v.replace('\\ae', u'æ')
        v = v.replace('\\o',  u'ø')
        v = v.replace('\\aa', u'å')
        v = v.replace('\\\'a', '&aacute;')
        v = v.replace('\\\'e', '&eacute;')
        v = v.replace('\\c{c}' , '&ccedil;')

        # fix \emph in title
        if k == 'title':
            v = re.sub(emph, '<I>\g<emph_text></I>', v)

        # remove "{" and "}"
        if k != 'abstract':
            v = v.replace('{', '')
            v = v.replace('}', '')
            v = v.replace('"', '')

        # remove trailing comma and dot
        if len(v)>0:
            if v[-1] == ',':
                v = v[:-1]

        # fix author
        if k == 'author' or k == 'author_first' or k == 'author_corresponding':

            # split into list of authors
            authors = v.split(' and ')

            # strip each author ;)
            authors = [a.strip() for a in authors]

            # make blanks non-breakable
            authors = [a.replace(' ', '&nbsp;') for a in authors]

            # reverse first and surname
            for i, a in enumerate(authors):
                #print a + "\n"
                #surname =
                namearray = a.split('&nbsp;')
                surname = namearray[0]
                if surname.find(',') >=0:
                    surname = surname.replace(',', '')
                    firstname = ' '.join(namearray[1:])
                    authors[i] = firstname + " " + surname
                else:
                    authors[i] = ' '.join(namearray)

            v = ", ".join(authors[:])

        # fix pages
        if k == 'pages':
            v = v.replace('--', '&ndash;')
            v = v.replace('-',  '&ndash;')

        entry[k] = v;


def get_entry_output(entry, out_path=''):
    """Get output html string for a bib entry

    Parameters
    ----------
        entry    :   a bib entry
        out_oath :   a path for output file

    Returns
    -------
        output : string in html format for the bib entry
    """

    # --- Start list ---
    out=['\n<li>\n']

    # --- author ---
    if 'author' in entry:
        out.append('<span class="author">%s</span>,' % highlight_author(entry, out_path))
        if not params['single_line']:
            out.append('<br>')

        out.append('\n')

    # --- chapter ---
    chapter = False
    if 'chapter' in entry:
        chapter = True
        out.append('<span class="title">"%s"</span>,' % entry['chapter'])
        if not params['single_line']:
            out.append('<br>')

    # --- title ---
    if not(chapter):
        out.append('<span class="title">"%s"</span>,' % entry['title'])
        if not params['single_line']:
            out.append('<br>')

    # -- if book chapter --
    if chapter:
        out.append('in: %s, %s' % (entry['title'], entry['publisher']))

    if entry['ENTRYTYPE']=='book':
        out.append(entry['publisher'])

    out.append('\n')

    # --- journal or similar ---
    if 'journal' in entry:
        out.append('<span class="publisher">%s</span>' % highlight_publisher(entry['journal']))
    elif 'booktitle' in entry:
        out.append('<span class="publisher">')
        if entry['ENTRYTYPE'] in params['type_conference_paper']:
            out.append(highlight_publisher(entry['booktitle']))
        else:
            out.append(entry['booktitle'])
        out.append('</span>')
    elif 'eprint' in entry:
        out.append('<span class="publisher">%s</span>' % highlight_publisher(entry['eprint']))
    elif entry['ENTRYTYPE'] == 'phdthesis':
        out.append('PhD thesis, %s' % entry['school'])
    elif entry['ENTRYTYPE'] == 'techreport':
        out.append('Tech. Report, %s' % entry['number'])

    # --- volume, pages, notes etc ---
    #  print(entry)
    if 'volume' in entry:
        out.append(', vol. %s' % entry['volume'])
    if 'number' in entry and entry['ENTRYTYPE']!='techreport':
        out.append(', no. %s' % entry['number'])
    if 'pages' in entry:
        out.append(', pp. %s' % entry['pages'])
    #  elif 'note' in entry:
    #      if journal or chapter: out.append(', ')
    #      out.append(entry['note'])
    if 'month' in entry:
        out.append(', %s' % entry['month'])

    # --- year ---
    out.append(', <span class="year">%s</span>' % entry['year'])

    # final period
    out.append('.\n')

    if not params['single_line']:
        out.append('<br>')

    # --- Links ---

    if not params['single_line']:
        out.append('<div class="publilinks">\n')

    #  pdf
    pdf_link = get_pdflink_from_entry(entry)
    if pdf_link!='':
        if params['use_icon'] and params['icon_pdf']:
            icon_pdf_file = params['icon_pdf'] if len(params['author_group'])==0 else params['author_group_icon_pdf']
            icon_pdf_file = os.path.relpath(icon_pdf_file, os.path.dirname(out_path))
            out.append('<a target="%s" href="%s"><img src="%s" alt="[pdf]" style="width: %s; height: %s;"></a>' % (params['target_link'], pdf_link, icon_pdf_file, params['icon_size'], params['icon_size']))
        else:
            out.append('[<a target="%s" href="%s">pdf</a>]' % (params['target_link'], pdf_link))
        out.append('&nbsp;')

    #  url, www, doi, hal_id
    href_link = get_wwwlink_from_entry(entry)
    if href_link!='':
        out.append('\n')
        if not params['use_icon']:
            out.append('[')
        out.append('<a target="%s" href="%s">' % (params['target_link'], href_link))
        if params['use_icon'] and params['icon_www']:
            icon_www_file = params['icon_www'] if len(params['author_group'])==0 else params['author_group_icon_www']
            icon_www_file = os.path.relpath(icon_www_file, os.path.dirname(out_path))
            out.append('<img src="%s" alt="[www]" style="width: %s; height: %s;"></a>' % (icon_www_file, params['icon_size'], params['icon_size']))
        else:
            out.append('link</a>')
        if not params['use_icon']:
            out.append(']')
        out.append('&nbsp;')

    bibid = entry['ID']
    bibid = bibid.replace(':', u'-')
    bibid = bibid.replace('.', u'-')
    show_abstract = params['show_abstract'] and 'abstract' in entry and entry['abstract']!=''
    show_bibtex = params['show_bibtex']

    # bibtex
    if show_bibtex:
        out.append('\n')
        if params['use_bootstrap_dialog']:
            out.append('''[<a type="button" data-toggle="modal" data-target="#bib-%s">bibtex</a>]&nbsp;''' % (bibid) )
        else:
            out.append('''[<a id="blk-%s" href="javascript:toggle('bib-%s', 'blk-%s');">bibtex</a>]&nbsp;''' % (bibid, bibid, bibid) )

    #  abstract
    if show_abstract:
        out.append('\n')
        if params['use_bootstrap_dialog']:
            out.append('''[<a type="button" data-toggle="modal" data-target="#abs-%s">abstract</a>]&nbsp;''' % (bibid) )
        else:
            out.append('''[<a id="alk-%s" href="javascript:toggle('abs-%s', 'alk-%s');">abstract</a>]&nbsp;''' % (bibid, bibid, bibid) )

    #  download fields
    for i_str in params['bibtex_fields_download']:
        if i_str in entry and entry[i_str]!='':
            out.append('\n')
            out.append('''[<a target="%s" href="%s">%s</a>]&nbsp;''' % (params['target_link'], entry[i_str] if i_str!='arxiv' else get_arxivlink_from_entry(entry), i_str) )

    #  citation
    if entry['ENTRYTYPE'] in params['show_citation_types'] and int(entry['year']) <= params['show_citation_year']:
        if params['show_citation']=='no':
            pass
        elif params['show_citation']=='scholar.js':
            out.append('\n[citations: <span class="scholar" name="%s" with-link="true" target="%s"></span>]&nbsp;' % (entry['title'], params['target_link_citation']) )
        elif params['show_citation']=='bs':
            if entry['title'].lower() in params['dict_title']:
                citations_url = params['dict_title'][entry['title'].lower()]
                out.append('\n[citations: <a target="%s" href="%s">%s</a>]&nbsp;' % (params['target_link_citation'], citations_url[1], citations_url[0]) )
        else:
            raise ValueError('wrong show_citation')

    #  note
    for i_str in params['bibtex_fields_note']:
        if i_str in entry and entry[i_str]!='':
            out.append('\n(<span class="%s">%s</span>)&nbsp;' % (i_str if i_str!='note' else 'hlnote0', entry[i_str]))

    out.append('\n')
    if not params['single_line']:
        out.append('</div>')

    if show_bibtex:
        out.append('\n')
        bibstr = get_bibtex_from_entry(entry, comma_to_and=True)
        if params['use_bootstrap_dialog']:
            out.append('''<div class="modal fade" id="bib-%s" role="dialog"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal">&times;</button><h4 class="modal-title">Bibtex</h4></div><div class="modal-body"> \n<pre>%s</pre> </div><div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Close</button></div></div></div></div>''' % (bibid, bibstr))
        else:
            out.append('''<div class="bibtex" id="bib-%s" style="display: none;">\n<pre>%s</pre></div>''' % (bibid, bibstr))

    #  abstract
    if show_abstract:
        out.append('\n')
        if params['use_bootstrap_dialog']:
            out.append('''<div class="modal fade" id="abs-%s" role="dialog"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal">&times;</button><h4 class="modal-title">Abstract</h4></div><div class="modal-body"> \n<pre>%s</pre> </div><div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Close</button></div></div></div></div>''' % (bibid, "\n".join(textwrap.wrap(entry['abstract'],68))))
        else:
            out.append('''<div class="abstract" id="abs-%s" style="display: none;">%s</div>''' % (bibid, entry['abstract']))

    # Terminate the list entry
    out.append('\n</li>')

    if params['add_blank_line_after_item']:
        out.append('<br>')

    out.append('\n')

    return ''.join(out)


def get_categories_of_entries(bib_entries):
    '''get list of caregories of entries, section names, section tags'''

    # lists according to publication type
    preprintlist = []
    booklist = []
    bookchapterlist = []
    journallist = []
    conflist = []
    abstractlist = []
    techreportlist = []
    thesislist = []
    misclist = []

    # Iterate over the entries
    for e in bib_entries:

        if 'eprint' in e:
            preprintlist.append(e)
        elif (e['ENTRYTYPE']=="book"):
            booklist.append(e)
        elif (e['ENTRYTYPE']=="inbook"):
            bookchapterlist.append(e)
        elif (e['ENTRYTYPE']=="article"):
            journallist.append(e)
        elif (e['ENTRYTYPE'] in params['type_conference_paper']):
            conflist.append(e)
        elif (e['ENTRYTYPE'] in params['type_conference_abstract']):
            abstractlist.append(e)
        elif (e['ENTRYTYPE']=="techreport"):
            techreportlist.append(e)
        elif (e['ENTRYTYPE']=="phdthesis"):
            thesislist.append(e)
        else:
            misclist.append(e)

    # write list of sections, papers
    paperlists = [preprintlist, booklist, bookchapterlist, journallist, conflist, abstractlist, techreportlist, thesislist, misclist]
    seclist = ['Preprints', 'Books', 'Book Chapters', 'Journal Articles', 'Conference Articles', 'Conference Abstracts', 'Research Reports', 'Theses', 'Miscellaneous']
    secline = ['Preprints', 'Books', 'Book Chapters', 'Journals', 'Conferences', 'Abstracts', 'Research Reports', 'Theses', 'Miscellaneous']

    return paperlists, seclist, secline


def write_entries_by_type(bib_entries, show_total_citation=False):
    '''write bib_entries by types (journal, conference, etc.)'''

    # create the html file with opted encoding
    f1 = codecs.open(params['htmlfile_type'], 'w', encoding=params['encoding'])

    # write the initial part of the file
    f1.write(get_html_prelog(params['htmlfile_type']))

    if len(params['author_group']):
        f1.write('''<br />
<a href="../index.html"><strong> BACK TO INDEX </strong></a>
<br /><br />\n\n''')

    if params['show_page_title']:
        f1.write('<h1>%s</h1>\n\n' % params['title']);

    if show_total_citation:
        f1.write('%s\n\n' % params['google_scholar_out'][2])

    if params['show_count_number']:
        _, _, count_str = get_publisher_countnumber_from_entries(bib_entries)
        f1.write('%s\n\n' % count_str)

    # write list of sections, papers
    paperlists, seclist, secline = get_categories_of_entries(bib_entries)

    # write list of sections
    if len(params['author_group'])==0:
        str_year = '''<span style="font-size: 20px;"><a href="%s"><b>Sorted by year</b></a></span> &#8226;&nbsp;''' % os.path.basename(params['htmlfile_year']) if params['htmlfile_year'] else ''
        f1.write('<p><big>&#8226;&nbsp;%s' % str_year)
    for papers, sec, secl in zip(paperlists, seclist, secline):
        strTmp = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name(sec), secl) if papers else ''
        f1.write(strTmp)
    f1.write( '</big></p>\n\n' )

    ol_1, ol_2 = get_bulleted_list_str()
    # write list according to publication type
    for papers, sec in zip(paperlists, seclist):
        if papers:
            f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name(sec), sec));
            f1.write('\n%s\n' % ol_1)
            if PY2:
                papers = sorted(papers, cmp=cmp_by_year)
            else:
                papers = sorted(papers, key=functools.cmp_to_key(cmp_by_year))
            for e in papers:
                f1.write(get_entry_output(e, params['htmlfile_type']))
            f1.write('\n%s\n\n\n' % ol_2)

    if len(params['author_group']):
        f1.write(get_html_disclaimer())

    f1.write(params['afterlog'])
    f1.close()

    print('Convert %s to %s' % (params['bibfile'], params['htmlfile_type']))


def write_entries_by_year(bib_entries, show_total_citation=False):
    '''write bib_entries by types (journal, conference, etc.)'''

    year_entries_dict = {}
    for e in bib_entries:
        if e['year'] in year_entries_dict:
            year_entries_dict[e['year']].append(e)
        else:
            year_entries_dict[e['year']]=[e]

    #  print 'year_entries_dict=', year_entries_dict

    # create the html file with opted encoding
    f1 = codecs.open(params['htmlfile_year'], 'w', encoding=params['encoding'])

    # write the initial part of the file
    f1.write(get_html_prelog(params['htmlfile_year']))

    if params['show_page_title']:
        f1.write('<h1>%s</h1>\n\n' % params['title']);

    if show_total_citation:
        f1.write('%s\n\n' % params['google_scholar_out'][2])

    if params['show_count_number']:
        _, _, count_str = get_publisher_countnumber_from_entries(bib_entries)
        f1.write('%s\n\n' % count_str)

    ol_1, ol_2 = get_bulleted_list_str()
    if year_entries_dict:
        years = sorted(year_entries_dict.keys(), reverse=True)

        str_type = '''<span style="font-size: 20px;"><a href="%s"><b>Sorted by type</b></a></span> &#8226;&nbsp;''' % os.path.basename(params['htmlfile_type']) if params['htmlfile_type'] else ''
        f1.write('<p><big>&#8226;&nbsp;%s' % str_type)
        for y in years:
            f1.write('''<span style="font-size: 20px;"><a href="%s#year%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_year']), y, y) )
        f1.write('</big></p>\n\n')

        for y in years:
            #  print 'y0=', y
            #  print 'y1=', year_entries_dict[y]
            f1.write('\n<h2><a name="year%s"></a>%s</h2>\n' % (y,y));
            f1.write('\n%s\n' % ol_1)
            papers = year_entries_dict[y]
            if PY2:
                papers = sorted(papers, cmp=cmp_by_type)
            else:
                papers = sorted(papers, key=functools.cmp_to_key(cmp_by_type))
            for e in papers:
                f1.write(get_entry_output(e, params['htmlfile_year']))
            f1.write('\n%s\n\n\n' % ol_2)

    f1.write(params['afterlog'])
    f1.close()

    print('Convert %s to %s' % (params['bibfile'], params['htmlfile_year']))


def write_entries_group(bib_entries):
    '''write bib_entries by types in a group (journal, conference, etc.)'''

    # copy icons
    icons_folder = os.path.join(params['htmlfile_group'], 'Icons')
    params['author_group_Icons'] = icons_folder
    if not os.path.exists(icons_folder):
        os.mkdir(icons_folder)
    if params['icon_www']:
        params['author_group_icon_www'] = os.path.join(icons_folder, os.path.basename(params['icon_www']))
        shutil.copyfile(params['icon_www'], params['author_group_icon_www'])
    if params['icon_pdf']:
        params['author_group_icon_pdf'] = os.path.join(icons_folder, os.path.basename(params['icon_pdf']))
        shutil.copyfile(params['icon_pdf'], params['author_group_icon_pdf'])

    # copy css file
    static_folder = os.path.join(params['htmlfile_group'], 'Static')
    params['author_group_Static'] = static_folder
    if not os.path.exists(static_folder):
        os.mkdir(static_folder)
    if params['css_file'] and os.path.exists(params['css_file']):
        params['author_group_css'] = os.path.join(static_folder, os.path.basename(params['css_file']))
        shutil.copyfile(params['css_file'], params['author_group_css'])
        params['css_file'] = params['author_group_css']
    if params['bootstrap_css'] and os.path.exists(params['bootstrap_css']):
        params['author_group_bootstrap_css'] = os.path.join(static_folder, os.path.basename(params['bootstrap_css']))
        shutil.copyfile(params['bootstrap_css'], params['author_group_bootstrap_css'])
        params['bootstrap_css'] = params['author_group_bootstrap_css']

    title = params['title']

    # write entries selected by authors
    _write_entries_group_author(bib_entries)
    params['dict_title'] = params['dict_title_group']

    # write complete-bibliography.html
    params['title'] = title
    _write_entries_group_complete(bib_entries)

    # write complete-bibliography.bib
    biblio_folder = os.path.join(params['htmlfile_group'], 'Bibliography')
    params['outbibfile'] = os.path.join(biblio_folder, 'complete-bibliography.bib')
    write_entries_to_bibfile(bib_entries)

    # write entries selected by publication venues
    _write_entries_group_venue(bib_entries)

    # write entries selected by years
    _write_entries_group_year(bib_entries)

    # write entries selected by categories
    _write_entries_group_category(bib_entries)

    # write index.html
    params['title'] = title
    _write_entries_group_index(bib_entries)


def _write_entries_group_index(bib_entries):
    '''write bib_entries to a index.html file.'''

    html_file = os.path.join(params['htmlfile_group'], 'index.html')

    # create the html file with opted encoding
    f1 = codecs.open(html_file, 'w', encoding=params['encoding'])

    # write the initial part of the file
    f1.write(get_html_prelog(html_file))

    if params['show_page_title']:
        f1.write('<h1>%s</h1>\n\n' % params['title']);

    #  if params['show_count_number']:
    #      _, _, count_str = get_publisher_countnumber_from_entries(bib_entries)
    #      f1.write('%s\n\n' % count_str)


    # selection by year
    f1.write("""
<table width="100%">
 <tr><td><h2>Selection by year</h2></td></tr>
</table>
""" )

    year_entries_dict = {}
    for e in bib_entries:
        if e['year'] in year_entries_dict:
            year_entries_dict[e['year']].append(e)
        else:
            year_entries_dict[e['year']]=[e]

    years = sorted(year_entries_dict.keys(), reverse=True)
    f1.write('\n\n<br /><table align="center" cellpadding="4" cellspacing="2">\n')
    for ii in range(len(years)):
        if ii%9 and ii!=0:
            f1.write('<td><a href="Year/%s.html">%s</a></td>\n' % (years[ii], years[ii]))
        else:
            if ii:
                f1.write('</tr>\n')
            f1.write('<tr align="left" valign="top">\n<td><a href="Year/%s.html">%s</a></td>\n' % (years[ii], years[ii]))
    f1.write('</tr>\n </table><br />\n\n')


    # selection by category
    seclist = ['Preprints', 'Books', 'Book Chapters', 'Journal Articles', 'Conference Articles', 'Conference Abstracts', 'Research Reports', 'Theses', 'Miscellaneous']
    file_names = [os.path.join(params['author_group_Category'], get_anchor_name(secName)+'.html') for secName in seclist]
    categories_print = ['']*len(file_names)
    for ii in range(len(file_names)):
        if os.path.exists(file_names[ii]):
            categories_print[ii] = '<td><a href="%s">%s</a></td>' % (os.path.relpath(file_names[ii], os.path.dirname(html_file)), seclist[ii])

    categories_print = [cat for cat in categories_print if cat!='']
    if len(categories_print)<9:
        categories_print += ['']*(9-len(categories_print))

    f1.write("""
<table width="100%%">
 <tr><td><h2>Selection by category</h2></td></tr>
</table>


<br /><table align="center" cellpadding="4" cellspacing="2">
<tr align="left" valign="top">
%s
%s
%s
</tr>
<tr align="left" valign="top">
%s
%s
%s
</tr>
<tr align="left" valign="top">
%s
%s
%s
</tr>
</table><br />\n\n\n
"""% tuple(cat for cat in categories_print))
    #  f1.write('\n\n\n')


    # selection by venue
    f1.write("""
<table width="100%%">
 <tr><td><h2>Selection by selected venues</h2></td></tr>
</table>


<table align="center" cellpadding="3" cellspacing="1">
<tr align="left" valign="top">\n""")


    count_name, count_number = _get_count_name_number(bib_entries)
    for ii in range(len(count_name)):
        f1.write('<td><a href="Venue/%s.html"><b>%s</b> (%s)</a></td>\n' % (count_name[ii], count_name[ii], count_number[ii]) )

        if not (ii+1)%3:
            f1.write('</tr>\n<tr align="left" valign="top">\n')

    f1.write('''</tr>
</table>
<br />\n\n\n''')



    # selection by author
    author_list=[None]*26
    for author in params['author_group'].keys():
        author_split = author.rsplit(' ', 1)
        jj = ord(author_split[1][0].lower()) - ord('a')
        if author_list[jj] is None:
            author_list[jj]=[author]
        else:
            author_list[jj].append(author)

    f1.write("""
<table width="100%%">
 <tr><td><h2>Selection by author</h2></td></tr>
</table>


<br /><table align="center" cellpadding="4" cellspacing="4">
<tr align="center">\n""")

    for ii in range(26):
        out_str = chr(65+ii)
        if author_list[ii] is not None:
            out_str = '<a href="#AUTH%s">%s</a>' % (out_str, out_str)
        f1.write('<td><b>%s</b></td>\n' %  out_str)
        if not (ii+1)%13:
            f1.write('</tr>\n<tr align="center">\n')

    f1.write('</table><br />\n\n\n')

    f1.write('<table align="center" cellpadding="3" cellspacing="1">\n')
    for ii in range(26):
        if author_list[ii] is not None:

            out_str = chr(65+ii)
            f1.write('<tr align="left" valign="top">\n<td>%s</td>\n' % out_str)

            for jj in range(len(author_list[ii])):

                str_tag = '<a name="AUTH%s"></a>' % out_str
                author_split = author_list[ii][jj].rsplit(' ', 1)
                str_author = author_split[1] + '-' + author_split[0].replace(' ', '-')+'.html'
                f1.write('<td>%s<a href="Author/%s">%s <strong>%s</strong></a></td>\n' % (str_tag if jj==0 else '', str_author, author_split[0], author_split[1]) )

                if not (jj+1)%4:
                    f1.write('</tr>\n<tr align="left" valign="top">\n')

    f1.write('''</tr>
</table>
<br />\n\n\n''')

    # write Complete bibliography
    f1.write("""
<table width="100%%">
 <tr><td><h2>Complete bibliography</h2></td></tr>
</table>


<br /><table align="center" cellpadding="4" cellspacing="2">
<tr align="left" valign="top">
<td><a href="Bibliography/complete-bibliography.html">Complete bibliography as a single HTML page</a>
</td>
</tr>
<tr align="left" valign="top">
<td><a href="Bibliography/complete-bibliography.bib">Complete bibliography as a single BIBTEX file</a>
</td>
</tr>
</table><br />\n\n\n""")


    f1.write(get_html_disclaimer())

    # afterlog
    f1.write(params['afterlog'])
    f1.close()

    print('Convert %s to %s' % (params['bibfile'], html_file))



def _write_entries_group_year(bib_entries):
    '''write bib_entries by types for different years.'''

    year_folder = os.path.join(params['htmlfile_group'], 'Year')
    params['author_group_Year'] = year_folder
    if not os.path.exists(year_folder):
        os.mkdir(year_folder)

    year_entries_dict = {}
    for e in bib_entries:
        if e['year'] in year_entries_dict:
            year_entries_dict[e['year']].append(e)
        else:
            year_entries_dict[e['year']]=[e]

    #  print 'year_entries_dict=', year_entries_dict

    for year, entries in year_entries_dict.items():

        html_file = os.path.join(year_folder, str(year)+'.html')
        params['htmlfile_type'] = html_file
        params['title'] = 'Publications of Year %s' % year

        write_entries_by_type(entries, show_total_citation=False)


def _write_entries_group_venue(bib_entries):
    '''write bib_entries by types for different publication venue.'''

    folder = os.path.join(params['htmlfile_group'], 'Venue')
    params['author_group_Venue'] = folder
    if not os.path.exists(folder):
        os.mkdir(folder)

    count_name, count_number = _get_count_name_number(bib_entries)

    venue_entries_dict = {}
    for e in bib_entries:
        name_e = get_publisher_shortname_from_entry(e)
        if name_e and name_e in count_name:
            if name_e in venue_entries_dict:
                venue_entries_dict[name_e].append(e)
            else:
                venue_entries_dict[name_e]=[e]

    for venue, e_list in venue_entries_dict.items():
        html_file = os.path.join(folder, venue+'.html')
        params['htmlfile_type'] = html_file
        params['title'] = 'Publications in %s' % venue

        write_entries_by_type(e_list, show_total_citation=False)


def _write_entries_group_author(bib_entries):
    '''write bib_entries by types for different authors.'''

    author_folder = os.path.join(params['htmlfile_group'], 'Author')
    params['author_group_Author'] = author_folder
    if not os.path.exists(author_folder):
        os.mkdir(author_folder)

    params['dict_title_group'] = {}
    for author, value in params['author_group'].items():

        author_split = author.rsplit(' ', 1)
        if len(author_split)!=2:
            raise ValueError('author_split should have 2 elements for first and last name')
        # last-first.html
        html_file = os.path.join(author_folder, author_split[1] + '-' + author_split[0].replace(' ', '-')+'.html')
        params['htmlfile_type'] = html_file
        params['title'] = 'Publications of %s' % author

        entries_selected=[]
        for e in bib_entries:
            if is_entry_selected(e, selection_and={'author': [author]}):
                entries_selected.append(e)

        if len(value):
            for k, v in value.items():
                if k.lower()=='scholarid':
                    params['googlescholarID'] = v
                else:
                    params['googlescholarID'] = ''
        else:
            params['googlescholarID'] = ''

        if params['show_citation']=='bs' and params['googlescholarID']:
            out_scholar = get_title_citation_url(params['googlescholarID'])
            params['dict_title'] = out_scholar[0]
            params['google_scholar_out'] = out_scholar[1:]
            params['dict_title_group'].update(out_scholar[0])

        write_entries_by_type(entries_selected, show_total_citation=params['show_total_citation'] and params['googlescholarID'])


def _write_entries_group_complete(bib_entries):
    '''write bib_entries by types in complete-bibliography.html (journal, conference, etc.)'''

    biblio_folder = os.path.join(params['htmlfile_group'], 'Bibliography')
    params['author_group_Bibliography'] = biblio_folder
    if not os.path.exists(biblio_folder):
        os.mkdir(biblio_folder)

    params['htmlfile_type'] = os.path.join(biblio_folder, 'complete-bibliography.html')

    write_entries_by_type(bib_entries, show_total_citation=False)


def _write_entries_group_category(bib_entries):
    '''write bib_entries by types in in different categories (journal, conference, etc.)'''

    folder = os.path.join(params['htmlfile_group'], 'Category')
    params['author_group_Category'] = folder
    if not os.path.exists(folder):
        os.mkdir(folder)

    # write list of sections, papers
    paperlists, seclist, _ = get_categories_of_entries(bib_entries)

    for ii in range(len(paperlists)):
        if len(paperlists[ii]):

            html_file = os.path.join(folder, get_anchor_name(seclist[ii])+'.html')
            params['htmlfile_type'] = html_file
            params['title'] = 'Publications of %s' % seclist[ii]

            write_entries_by_type(paperlists[ii], show_total_citation=False)


def write_entries_to_bibfile(bib_entries):
    '''write entries into a bib file'''

    f1 = codecs.open(params['outbibfile'], 'w', encoding=params['encoding'])

    for entry in bib_entries:
        bibstr = get_bibtex_from_entry(entry, comma_to_and=True)
        f1.write(bibstr)
        f1.write('\n\n')
    f1.close()

    print('Write %s (cleaned and selected) to %s' % (params['bibfile'], params['outbibfile']))


def main():

    args = docopt(__doc__, version='1.0')

    _bibfile = args['<bibfile>']
    _htmlfile = args['<htmlfile>']
    _verbose = int(args['--verbose'])
    _conffile = args['--conf']
    _input = args['--input']
    _outbibfile = args['--outbib']

    if _verbose>=1:
        print(args)

    params['verbose'] = _verbose


    config = configparser.SafeConfigParser()
    if args['--conf']:
        param_str = 'params'
        config.read(_conffile)
        #  print config.items(param_str)

        #  strings, lists, dicts
        for name_str in ['title', 'css_file', 'googlescholarID', 'scholar.js', 'show_citation', 'author_sign', 'author_group', \
                         'author_names_highlighted', 'conference_shortname_highlighted', 'journal_shortname_highlighted', \
                         'journal_fullname_highlighted','show_citation_types', 'show_abstract', 'show_bibtex', 'icon_pdf', 'icon_www', 'icon_size', \
                         'target_link', 'target_link_citation', 'type_conference_paper', 'type_conference_abstract', 'encoding', \
                         'bibtex_fields_download', 'bibtex_fields_note', 'show_paper_style', 'bootstrap_css', 'count_publisher', 'selection_and', 'selection_or', 'bulleted_list']:
            if config.has_option(param_str, name_str):
                params[name_str] = ast.literal_eval(config.get(param_str,name_str))

        #  booleans
        for name_str in ['use_icon', 'single_line', 'use_bootstrap_dialog', 'add_blank_line_after_item', 'show_page_title', 'show_count_number', 'show_total_citation', 'show_author_sign']:
            if config.has_option(param_str, name_str):
                params[name_str] = config.getboolean(param_str, name_str)

        #  integer
        for name_str in ['show_citation_before_years']:
            if config.has_option(param_str, name_str):
                params[name_str] = config.getint(param_str, name_str)

    if args['--input']:
        paramsInput = ast.literal_eval(_input)
        for k, v in paramsInput.items():
            params[k] = v

    if args['--nc']:
        params['show_total_citation'] = False
        params['show_citation'] = 'no'

    # use lower words in some keys
    #  params['journal_fullname_highlighted'] = [name.lower() for name in params['journal_fullname_highlighted'] ]
    params['show_paper_style'] = params['show_paper_style'].lower()

    # use different output html file for different types
    if len(params['author_group']):
        file_name , file_ext = os.path.splitext(_htmlfile)
        if not os.path.exists(file_name):
            os.mkdir(file_name)

        params['htmlfile_group'] = file_name

    else:
        if params['show_paper_style']=='type':
            params['htmlfile_type'] = _htmlfile
            params['htmlfile_year'] = ''
        elif params['show_paper_style']=='year':
            params['htmlfile_type'] = ''
            params['htmlfile_year'] = _htmlfile
        elif params['show_paper_style']=='year_type' or params['show_paper_style']=='type_year':
            file_name , file_ext = os.path.splitext(_htmlfile)
            params['htmlfile_type'] = '%s_by_type%s' %(file_name, file_ext)
            params['htmlfile_year'] = '%s_by_year%s' %(file_name, file_ext)
        else:
            raise ValueError('wrong show_paper_style')

    params['bibfile'] = _bibfile
    if _outbibfile:
        params['outbibfile'] = _outbibfile

    #  add conferences
    params['count_publisher'] = params['count_publisher'] + params['conference_shortname_highlighted']

    if _verbose>=1:
        print('params = %s' % params )


    params['journal_fullname_highlighted_lower'] = [name.lower() for name in params['journal_fullname_highlighted'] ]
    current_year = datetime.date.today().year
    params['show_citation_year'] = current_year - params['show_citation_before_years']

    if params['show_citation']!='bs' and params['show_total_citation']:
        raise ValueError("show_total_citation==True needs show_citation=='bs'")

    params['author_group_authors'] = list(params['author_group'].keys())


    # html afterlog
    if params['show_citation']=='scholar.js' and 'googlescholarID' in params:
        afterlog = """
        <br>
            <script type="text/javascript">
            Scholar.load("%s");
            </script>
        </div>
        </body>
        </html>
        """ % (params['googlescholarID'])
    else:
        afterlog = """
        <br>
        </div>
        </body>
        </html>
        """

    params['afterlog'] = afterlog

    with io.open(_bibfile, 'r', encoding='utf8') as bibtex_file:
        bibtex_str = bibtex_file.read()

    # read bibtex file
    bib_database = bibtexparser.loads(bibtex_str)
    bib_entries = bib_database.entries


    entries_selected=[]
    for e in bib_entries:
        if _verbose>=2:
            print ('e before clean=', e)

        #  clean entry for output
        clean_entry(e)

        #  fill some empty fields
        add_empty_fields_in_entry(e)

        if _verbose>=2:
            print ('e after clean =', e)

        if is_entry_selected(e):
            if len(params['author_group'])==0 or len(params['author_group'])>0 and is_entry_selected(e, selection_or={'author': params['author_group_authors']}):
                entries_selected.append(e)


    if len(params['author_group']):

        write_entries_group(entries_selected)

    else:
        if params['show_citation']=='bs':
            out_scholar = get_title_citation_url(params['googlescholarID'])
            params['dict_title'] = out_scholar[0]
            params['google_scholar_out'] = out_scholar[1:]

        if params['show_paper_style']=='type':
            write_entries_by_type(entries_selected, params['show_total_citation']);
        elif params['show_paper_style']=='year':
            write_entries_by_year(entries_selected, params['show_total_citation']);
        elif params['show_paper_style']=='year_type' or params['show_paper_style']=='type_year':
            write_entries_by_type(entries_selected, params['show_total_citation']);
            write_entries_by_year(entries_selected, params['show_total_citation']);

        if params['outbibfile']:
            write_entries_to_bibfile(entries_selected)


if __name__ == '__main__':
    main()

