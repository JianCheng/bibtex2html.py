#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Description: Convert bibtex to html.

Usage:
  bibtex2html.py <bibfile> <htmlfile> [-v <verbose>]  [--conf <conffile>] [-i <input>]
  bibtex2html.py (-h | --help)

Options:

  -h --help                Show this screen.
  -v --verbose <verbose>   Verbose level. [default: 0]

  -c --conf <conffile>     Configuration file.
  -i --input   <input>     Input cmd parameters which can override some parameters in -c.

Examples:
bibtex2html.py papers.bib papers.html -c papers_conf.ini
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type'}"
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type', 'css_file': 'style.css'}"
bibtex2html.py papers.bib papers.html -c papers_conf.ini -i "{'show_paper_style':'type', 'selection_and': {'author': ['Jian Cheng'], 'year':[2010,2013] }}"

Author(s): Jian Cheng (jian.cheng.1983@gmail.com)
"""


import re, os, io
import datetime
import codecs
import textwrap

import bibtexparser
from docopt import docopt

import ConfigParser
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

# show the number of papers in specific journals and conferences
params['show_count_number'] = True
# counted publisher (conferences are determined by conference_shortname_highlighted)
params['count_publisher'] = [
    [u'Nature Methods'],
    [u'TMI', u'IEEE Transactions on Medical Imaging'],
    [u'MIA', u'MedIA', u'Medical Image Analysis'],
    [u'TPAMI', u'IEEE Transactions on Pattern Analysis and Machine Intelligence'],
    [u'IJCV', u'International Journal of Computer Vision'],
    [u'NeuroImage'],
    [u'HBM', u'Human Brain Mapping'],
    [u'TIP', u'IEEE Transactions on Image Processing'],
    [u'MRM', 'Magnetic Resonance in Medicine'],
    [u'Medical Physics'],
]

params['show_citation_types'] = [u'article', u'inproceedings', u'phdthesis', u'inbook']

params['show_citation'] = False
params['show_page_title'] = True

#  params['googlescholarID'] = u"'BARqXQ0AAAAJ'"
params['show_citation_before_years'] = 1
#  params['scholar.js'] = 'scholar.js'
params['scholar.js'] = 'http://kha.li/dist/scholar/scholar-0.1.1.min.js'

params['use_icon'] = False
#  params['icon_path'] = u'.'
params['icon_pdf'] = ''
params['icon_www'] = ''

#  open link in a new tab
#  params['target_link'] = u'_blank'
params['target_link'] = u'_self'
# target attr for citations
params['target_link_citation'] = u'_blank'


#  If false, show multiple lines
params['single_line'] = False

params['show_abstract'] = True
params['show_bibtex'] = True
params['use_bootstrap_dialog'] = True

# default conference paper type
params['type_conference_paper'] = [u'inproceedings']
# default conference abstract type
params['type_conference_abstract'] = [u'conference']

# bibtex download fields
params['bibtex_fields_download'] = ['project', 'slides', 'poster', 'video', 'code', 'software', 'data', 'media']
# bibtex note fields
params['bibtex_fields_note'] = ['note', 'hlnote', 'hlnote2']
# show bibtex with given fields
params['bibtex_show_list'] = ['author', 'title', 'journal', 'booktitle', 'year', 'volume', 'number', 'pages', 'month', 'publisher', 'organization', 'school', 'address', 'edition',
                              'editor', 'institution', 'chapter', 'series', 'pdf', 'doi', 'url', 'hal_id', 'eprint', 'archiveprefix', 'primaryclass']

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


def cmp_by_year(y, x):
    '''sort entry by year'''

    if x['year'].isdigit() and y['year'].isdigit():
        return int(x['year']) - int(y['year'])
    elif x['year'].isdigit() and not y['year'].isdigit():
        return -1
    elif not x['year'].isdigit() and y['year'].isdigit():
        return 1
    else:
        return 1


def cmp_by_type(y, x):
    '''sort entry by type'''

    if x['ENTRYTYPE']!=y['ENTRYTYPE']:
        if y['ENTRYTYPE']=='phdthesis': return -1
        if y['ENTRYTYPE'] in ['inbook', 'book'] and x['ENTRYTYPE'] not in ['phdthesis']: return -1
        if y['ENTRYTYPE']=='article' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook']: return -1
        if y['ENTRYTYPE']=='inproceedings' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook', 'article']: return -1
        if y['ENTRYTYPE']=='conferences' and x['ENTRYTYPE'] not in ['phdthesis', 'book', 'inbook', 'article', 'inproceedings']: return -1
    elif x['ENTRYTYPE']=='article':
        x_hl = False
        y_hl = False
        for word in params['journal_shortname_highlighted']:
            if x['journal'].find('(%s)' % word)>=0: x_hl=True
            if y['journal'].find('(%s)' % word)>=0: y_hl=True
        for word in params['journal_fullname_highlighted_insensitive']:
            if not x_hl and x['journal'].find(word)>=0: x_hl=True
            if not y_hl and y['journal'].find(word)>=0: y_hl=True
        if x_hl and not y_hl:  return 1
        if not x_hl and y_hl:  return -1
    elif x['ENTRYTYPE'] in params['type_conference_paper']:
        x_hl = False
        y_hl = False
        for word in params['conference_shortname_highlighted']:
            if x['booktitle'].find(word+"'")>=0: x_hl=True
            if y['booktitle'].find(word+"'")>=0: y_hl=True
        #  print x['booktitle'], y['booktitle'], x_hl, y_hl
        if x_hl and not y_hl:  return 1
        if not x_hl and y_hl:  return -1

    return 1


def highlight_author(author, params):
    """return a string with highlighted author"""

    authors = author.split(', ')
    authors_new = []
    for p in authors:
        if p in params['author_names_highlighted']:
            authors_new.append('<b>%s</b>' % p);
        else:
            authors_new.append(p);
    return ', '.join(authors_new)


def highlight_publisher(publisher, params):
    """return a string with highlighted jounrls and conferences"""

    words_highlighted = params['journal_shortname_highlighted'] + params['conference_shortname_highlighted']

    words = publisher.split(' ')
    if len(words)==1 or publisher.lower() in params['journal_fullname_highlighted_insensitive']:
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


def get_arxivID_from_entry(entry):
    '''get arxiv id'''

    id = ''
    if entry.has_key('journal'):
        journal = entry['journal'].lower()
        words = journal.split()
        for w in words:
            pos = w.find('arxiv:')
            if pos>=0:
                id = w[pos+6:]
                return id

    elif entry.has_key('eprint'):
        w = entry['eprint'].lower()
        pos = w.find('arxiv:')
        if pos>=0:
            id = w[pos+6:]

    return id


def get_pdflink_from_entry(entry):
    '''get pdf link from bib entry (keys: pdf, hal_id)'''

    if entry.has_key('pdf'):
        return entry['pdf']
    elif entry.has_key('hal_id'):
        return 'https://hal.archives-ouvertes.fr/%s/document' % entry['hal_id']
    elif get_arxivID_from_entry(entry)!='':
        return 'https://arxiv.org/pdf/%s.pdf' % get_arxivID_from_entry(entry)
    else:
        return ''


def get_wwwlink_from_entry(entry):
    '''get website link from bib entry (keys: url, www, doi, hal_id)'''

    if entry.has_key('url'):
        return entry['url']
    elif entry.has_key('www'):
        return entry['www']
    elif entry.has_key('doi'):
        return 'https://dx.doi.org/%s' % entry['doi']
    elif entry.has_key('hal_id'):
        return 'https://hal.archives-ouvertes.fr/%s' % entry['hal_id']
    elif get_arxivID_from_entry(entry)!='':
        return 'https://arxiv.org/abs/%s' % get_arxivID_from_entry(entry)
    else:
        return ''


def get_bibtex_from_entry(entry):
    '''Get bibtex string from an entry. Remove some non-standard fields.'''

    entry2 = entry.copy()

    #  add pdf_link from other keys
    if not entry2.has_key('pdf'):
        pdf_link = get_pdflink_from_entry(entry2)
        if pdf_link!='':
            entry2['pdf'] = pdf_link

    #  add url from other keys
    if not entry2.has_key('url'):
        www_link = get_wwwlink_from_entry(entry2)
        if www_link!='':
            entry2['url'] = www_link

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
    if entry.has_key('journal'):
        pub = entry['journal']
    elif entry.has_key('booktitle'):
        pub = entry['booktitle']

    dem_1 = pub.find('(')
    if dem_1>=0:
        dem_2 = pub.find(')')
        dem_3 = pub.find("'")
        dem = dem_2 if dem_3<0 else dem_3
        return pub[dem_1+1:dem]

    return pub


def get_publisher_countnumber_from_entries(entries):
    '''Get count numbers from entries'''

    count_name = []
    for name in params['count_publisher']:
        if type(name)==list:
            count_name.append(name[0])
        else:
            count_name.append(name)
    count_number = [0]*len(count_name)

    for e in entries:
        name = get_publisher_shortname_from_entry(e)
        for i in xrange(len(count_name)):
            if name.lower()==count_name[i].lower():
                count_number[i] = count_number[i]+1

    return count_name, count_number


def is_entry_selected_by_key(entry, k, v):
    '''return true if entry is selected'''

    if k == 'year':
        return int(entry[k]) in v
    elif k in 'author':
        author_names = entry[k].split(', ')
        for name in v:
            if name in author_names:
                return True
        return False
    elif k=='author_first':
        author_names = entry['author'].split(', ')
        if author_names[0] in v:
            return True
        elif entry.has_key(k):
            authorFirst_names = entry[k].split(', ')
            for name in authorFirst_names:
                if name in v:
                    return True
        return False
    elif k =='author_corresponding':
        if not entry.has_key(k):
            return False
        else:
            authorCorr_names = entry[k].split(', ')
            for name in authorCorr_names:
                if name in v:
                    return True
    else:
        raise('Wrong selection keys!')

    return True


def is_entry_selected(entry):
    '''return true if entry is selected'''

    if len(params['selection_and'])==0 and len(params['selection_or'])==0:
        return True
    if len(params['selection_and'])>0 and len(params['selection_or'])>0:
        raise('selection_and and selection_or cannot be used together')

    if len(params['selection_and'])>0:
        for k, v in params['selection_and'].items():
            if not is_entry_selected_by_key(entry, k, v):
                return False
        return True
    elif len(params['selection_or'])>0:
        for k, v in params['selection_or'].items():
            if is_entry_selected_by_key(entry, k, v):
                return True
        return False
    else:
        raise('Wrong logic here')


def get_anchor_name(name):
    '''get anchor from a string'''
    if name.isdigit():
        return 'year'+ name
    else:
        return name.lower().replace(' ', '-')


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


def write_entry(entry, fid, params):
    """Write entry to html file"""

    # --- Start list ---
    fid.write('\n')
    fid.write('<li>\n')

    # --- author ---
    if entry.has_key('author'):
        fid.write('<span class="author">')
        fid.write(highlight_author(entry['author'], params))
        fid.write('</span>,')

        if not params['single_line']:
            fid.write('<br>')

        fid.write('\n')

    # --- chapter ---
    chapter = False
    if entry.has_key('chapter'):
        chapter = True
        fid.write('<span class="title">"')
        fid.write(entry['chapter'])
        fid.write('"</span>,')
        if not params['single_line']:
            fid.write('<br>')

    # --- title ---
    if not(chapter):
        fid.write('<span class="title">"')
        fid.write(entry['title'])
        fid.write('"</span>,')
        if not params['single_line']:
            fid.write('<br>')

    # -- if book chapter --
    if chapter:
        fid.write('in: ')
        #  fid.write('<i>')
        fid.write(entry['title'])
        #  fid.write('</i>')
        fid.write(', ')
        fid.write(entry['publisher'])

    if entry['ENTRYTYPE']=='book':
        fid.write(entry['publisher'])

    fid.write('\n')

    # --- journal or similar ---
    if entry.has_key('journal'):
        fid.write('<span class="publisher">')
        fid.write(highlight_publisher(entry['journal'], params))
        fid.write('</span>')
    elif entry.has_key('booktitle'):
        fid.write('<span class="publisher">')
        if entry['ENTRYTYPE'] in params['type_conference_paper']:
            fid.write(highlight_publisher(entry['booktitle'], params))
        else:
            fid.write(entry['booktitle'])
        fid.write('</span>')
    elif entry['ENTRYTYPE'] == 'phdthesis':
        fid.write('PhD thesis, ')
        fid.write(entry['school'])
    elif entry['ENTRYTYPE'] == 'techreport':
        fid.write('Tech. Report, ')
        fid.write(entry['number'])

    # --- volume, pages, notes etc ---
    #  print(entry)
    if entry.has_key('volume'):
        fid.write(', Vol. ')
        fid.write(entry['volume'])
    if (entry.has_key('number') and entry['ENTRYTYPE']!='techreport'):
        fid.write(', No. ')
        fid.write(entry['number'])
    if entry.has_key('pages'):
        fid.write(', p.')
        fid.write(entry['pages'])
    #  elif entry.has_key('note'):
    #      if journal or chapter: fid.write(', ')
    #      fid.write(entry['note'])
    if entry.has_key('month'):
        fid.write(', ')
        fid.write(entry['month'])

    # --- year ---
    fid.write('<span class="year">')
    #fid.write(', ');
    fid.write(', ');
    fid.write(entry['year'])
    fid.write('</span>')
    #fid.write(',\n')

    # final period
    fid.write('.')
    fid.write('\n')

    if not params['single_line']:
        fid.write('<br>')

    # --- Links ---

    if not params['single_line']:
        fid.write('''<div class="publilinks">''')
        fid.write('\n')
    #  pdf
    pdf_link = get_pdflink_from_entry(entry)
    if not params['use_icon'] or pdf_link=='':
        fid.write('[')
    if pdf_link!='':
        fid.write('<a target="%s" href="%s">' % (params['target_link'], pdf_link))
        if params['use_icon'] and params['icon_pdf']:
            fid.write('<img align="middle" border="0" src="%s" alt="[pdf]"></a>' % (params['icon_pdf']))
        else:
            fid.write('pdf</a>')
    else:
        fid.write('pdf')
    if not params['use_icon'] or pdf_link=='':
        fid.write(']')
    fid.write('&nbsp;')

    #  url, www, doi, hal_id
    href_link = get_wwwlink_from_entry(entry)
    if href_link!='':
        fid.write('\n')
        if not params['use_icon']:
            fid.write('[')
        fid.write('<a target="%s" href="%s">' % (params['target_link'], href_link))
        if params['use_icon'] and params['icon_www']:
            fid.write('<img align="middle" border="0" src="%s" alt="[www]"></a>' % (params['icon_www']))
        else:
            fid.write('link</a>')
        if not params['use_icon']:
            fid.write(']')
        fid.write('&nbsp;')


    bibid0 = entry['ID']
    bibid = bibid0.replace(':', u'-')
    show_abstract = params['show_abstract'] and entry.has_key('abstract') and entry['abstract']!=''
    show_bibtex = params['show_bibtex']

    # bibtex
    if show_bibtex:
        fid.write('\n')
        if params['use_bootstrap_dialog']:
            fid.write('''[<a type="button" data-toggle="modal" data-target="#bib-%s">bibtex</a>]&nbsp;''' % (bibid) )
        else:
            fid.write('''[<a id="blk-%s" href="javascript:toggle('bib-%s', 'blk-%s');">bibtex</a>]&nbsp;''' % (bibid, bibid, bibid) )

    #  abstract
    if show_abstract:
        fid.write('\n')
        if params['use_bootstrap_dialog']:
            fid.write('''[<a type="button" data-toggle="modal" data-target="#abs-%s">abstract</a>]&nbsp;''' % (bibid) )
        else:
            fid.write('''[<a id="alk-%s" href="javascript:toggle('abs-%s', 'alk-%s');">abstract</a>]&nbsp;''' % (bibid, bibid, bibid) )

    #  download fields
    for i_str in params['bibtex_fields_download']:
        if entry.has_key(i_str) and entry[i_str]!='':
            fid.write('\n')
            fid.write('''[<a target="%s" href="%s">%s</a>]&nbsp;''' % (params['target_link'], entry[i_str], i_str) )

    #  citation
    if params['show_citation'] and entry['ENTRYTYPE'] in params['show_citation_types'] and int(entry['year']) <= params['show_citation_year']:
        fid.write('\n')
        fid.write('[citations: <span class="scholar" name="%s" with-link="true" target="%s"></span>]&nbsp;' % (entry['title'], params['target_link_citation']) )

    #  note
    for i_str in params['bibtex_fields_note']:
        if entry.has_key(i_str) and entry[i_str]!='':
            fid.write('\n')
            fid.write('(<span class="%s">%s</span>)&nbsp;' % (i_str if i_str!='note' else 'hlnote0', entry[i_str]))

    fid.write('\n')
    if not params['single_line']:
        fid.write('</div>')

    if show_bibtex:
        fid.write('\n')
        bibstr = get_bibtex_from_entry(entry)
        if params['use_bootstrap_dialog']:
            fid.write('''<div class="modal fade" id="bib-%s" role="dialog"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal">&times;</button><h4 class="modal-title">Bibtex</h4></div><div class="modal-body"> \n<pre>%s</pre> </div><div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Close</button></div></div></div></div>''' % (bibid, bibstr))
        else:
            fid.write('''<div class="bibtex" id="bib-%s" style="display: none;">\n<pre>%s</pre></div>''' % (bibid, bibstr))

    #  abstract
    if show_abstract:
        fid.write('\n')
        if params['use_bootstrap_dialog']:
            fid.write('''<div class="modal fade" id="abs-%s" role="dialog"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal">&times;</button><h4 class="modal-title">Abstract</h4></div><div class="modal-body"> \n<pre>%s</pre> </div><div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Close</button></div></div></div></div>''' % (bibid, "\n".join(textwrap.wrap(entry['abstract'],68))))
        else:
            fid.write('''<div class="abstract" id="abs-%s" style="display: none;">%s</div>''' % (bibid, entry['abstract']))

    # Terminate the list entry
    fid.write('\n</li>')

    if params['add_blank_line_after_item']:
        fid.write('<br>')
    fid.write('\n')


def write_entries_by_type(bib_entries):
    '''write bib_entries by types (journal, conference, etc.)'''

    # create the html file with opted encoding
    f1 = codecs.open(params['htmlfile_type'], 'w', encoding=params['encoding'])

    # write the initial part of the file
    f1.write(params['prelog'])

    if params['show_page_title']:
        f1.write('<h1>%s</h1>\n\n' % params['title']);

    if params['show_count_number']:
        count_name, count_number = get_publisher_countnumber_from_entries(bib_entries)
        f1.write('<p>&#8226;&nbsp;')
        for i in xrange(len(count_name)):
            if count_number[i]>0:
                str_count = '''<b>%s</b> (%s) &#8226;&nbsp;''' % (count_name[i], count_number[i])
                f1.write(str_count)
        f1.write('</p>\n\n')

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

        #  if _verbose>=2:
        #      print 'e before clean 2=', e

        arxiv_id = get_arxivID_from_entry(e)
        if arxiv_id!='':
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


    # write list of sections
    str_year       = '''<span style="font-size: 20px;"><a href="%s"><b>Sorted by year</b></a></span> &#8226;&nbsp;''' % os.path.basename(params['htmlfile_year']) if params['htmlfile_year'] else ''

    str_preprint   = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Preprints'), 'Preprints') if len(preprintlist) else ''
    str_book       = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Books'), 'Books') if len(booklist) else ''
    str_chapter    = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Book Chapters'), 'Book Chapters') if len(bookchapterlist) else ''
    str_journal    = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Journal Articles'), 'Journals') if len(journallist) else ''
    str_conference = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Conference Articles'), 'Conferences') if len(conflist) else ''
    str_abstract   = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Conference Abstracts'), 'Abstracts') if len(abstractlist) else ''
    str_report     = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Research Reports'), 'Research Reports') if len(techreportlist) else ''
    str_thesis     = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Theses'), 'Theses') if len(thesislist) else ''
    str_misc       = '''<span style="font-size: 20px;"><a href="%s#%s"><b>%s</b></a></span> &#8226;&nbsp;''' % (os.path.basename(params['htmlfile_type']), get_anchor_name('Miscellaneous Papers'), 'Miscellaneous Papers') if len(misclist) else ''

    f1.write('''
    <p><big>&#8226;&nbsp;%s%s%s%s%s%s%s%s%s%s</big></p>
    ''' % (str_preprint, str_year, str_book, str_chapter, str_journal, str_conference, str_abstract, str_report, str_thesis, str_misc)
    )

    # write list according to publication type
    if len(preprintlist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Preprints'), 'Preprints'));
        f1.write('\n<ol>\n')
        preprintlist = sorted(preprintlist, cmp=cmp_by_year)
        for e in preprintlist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(booklist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Books'), 'Books'));
        f1.write('\n<ol>\n')
        booklist = sorted(booklist, cmp=cmp_by_year)
        for e in booklist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(bookchapterlist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Book Chapters'), 'Book Chapters'));
        f1.write('\n<ol>\n')
        bookchapterlist = sorted(bookchapterlist, cmp=cmp_by_year)
        for e in bookchapterlist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(journallist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Journal Articles'), 'Journal Articles'));
        f1.write('\n<ol>\n')
        journallist = sorted(journallist, cmp=cmp_by_year)
        for e in journallist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(conflist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Conference Articles'), 'Conference Articles'));
        f1.write('\n<ol>\n')
        conflist = sorted(conflist, cmp=cmp_by_year)
        for e in conflist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(abstractlist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Conference Abstracts'), 'Conference Abstracts'));
        f1.write('\n<ol>\n')
        abstractlist = sorted(abstractlist, cmp=cmp_by_year)
        for e in abstractlist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(techreportlist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Research Reports'), 'Research Reports'));
        f1.write('\n<ol>\n')
        techreportlist = sorted(techreportlist, cmp=cmp_by_year)
        for e in techreportlist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(thesislist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Theses'), 'Theses'));
        f1.write('\n<ol>\n')
        thesislist = sorted(thesislist, cmp=cmp_by_year)
        for e in thesislist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    if len(misclist):
        f1.write('<h2><a name="%s"></a>%s</h2>' % (get_anchor_name('Miscellaneous Papers'), 'Miscellaneous Papers'));
        f1.write('\n<ol>\n')
        misclist = sorted(misclist, cmp=cmp_by_year)
        for e in misclist:
            write_entry(e, f1, params)
        f1.write('\n</ol>\n\n\n')

    f1.write(params['afterlog'])
    f1.close()

    print('Covert %s to %s' % (params['bibfile'], params['htmlfile_type']))


def write_entries_by_year(bib_entries):
    '''write bib_entries by types (journal, conference, etc.)'''

    year_entries_dict = {}
    for e in bib_entries:
        if year_entries_dict.has_key(e['year']):
            year_entries_dict[e['year']].append(e)
        else:
            year_entries_dict[e['year']]=[e]

    #  print 'year_entries_dict=', year_entries_dict

    # create the html file with opted encoding
    f1 = codecs.open(params['htmlfile_year'], 'w', encoding=params['encoding'])

    # write the initial part of the file
    f1.write(params['prelog'])

    if params['show_page_title']:
        f1.write('<h1>%s</h1>\n\n' % params['title']);

    if params['show_count_number']:
        count_name, count_number = get_publisher_countnumber_from_entries(bib_entries)
        f1.write('<p>&#8226;&nbsp;')
        for i in xrange(len(count_name)):
            if count_number[i]>0:
                str_count = '''<b>%s</b> (%s) &#8226;&nbsp;''' % (count_name[i], count_number[i])
                f1.write(str_count)
        f1.write('</p>\n\n')

    if len(year_entries_dict):
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
            f1.write('\n<ol>\n')
            papers = year_entries_dict[y]
            papers = sorted(papers, cmp=cmp_by_type)
            for e in papers:
                write_entry(e, f1, params)
            f1.write('\n</ol>\n\n\n')


    f1.write(params['afterlog'])
    f1.close()

    print('Covert %s to %s' % (params['bibfile'], params['htmlfile_year']))


def main():

    args = docopt(__doc__, version='1.0')


    _bibfile = args['<bibfile>']
    _htmlfile = args['<htmlfile>']
    _verbose = int(args['--verbose'])
    _conffile = args['--conf']
    _input = args['<input>']

    if _verbose>=1:
        print(args)

    params['verbose'] = _verbose


    config = ConfigParser.SafeConfigParser()
    if args['--conf']:
        param_str = 'params'
        config.read(_conffile)
        #  print config.items(param_str)

        #  strings, lists, dicts
        for name_str in ['title', 'css_file', 'googlescholarID', 'scholar.js', \
                         'author_names_highlighted', 'conference_shortname_highlighted', 'journal_shortname_highlighted', \
                         'journal_fullname_highlighted','show_citation_types', 'show_abstract', 'show_bibtex', 'icon_pdf', 'icon_www', \
                         'target_link', 'target_link_citation', 'type_conference_paper', 'type_conference_abstract', 'encoding', \
                         'bibtex_fields_download', 'bibtex_fields_note', 'show_paper_style', 'bootstrap_css', 'count_publisher', 'selection_and', 'selection_or']:
            if config.has_option(param_str, name_str):
                params[name_str] = ast.literal_eval(config.get(param_str,name_str))

        #  booleans
        for name_str in ['show_citation', 'use_icon', 'single_line', 'use_bootstrap_dialog', 'add_blank_line_after_item', 'show_page_title', 'show_count_number']:
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

    # use lower words in some keys
    #  params['journal_fullname_highlighted'] = [name.lower() for name in params['journal_fullname_highlighted'] ]
    params['show_paper_style'] = params['show_paper_style'].lower()

    # use different output html file for different types
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
        raise('wrong show_paper_style')

    params['bibfile'] = _bibfile

    #  add conferences
    params['count_publisher'] = params['count_publisher'] + params['conference_shortname_highlighted']

    if _verbose>=1:
        print('params = %s' % params )


    params['journal_fullname_highlighted_insensitive'] = [name.lower() for name in params['journal_fullname_highlighted'] ]
    current_year = datetime.date.today().year
    params['show_citation_year'] = current_year - params['show_citation_before_years']


    # html prelog
    # modify according to your needs
    prelog = """<!DOCTYPE HTML
        PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
    <head>
    <meta http-equiv=Content-Type content="text/html; charset=%s">
    <title>%s</title>

    <script type="text/javascript" src="http://code.jquery.com/jquery-2.2.0.min.js"></script>
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
    """ % (params['encoding'], params['title'], params['bootstrap_css'], params['scholar.js'], params['css_file'])


    # html afterlog
    if params.has_key('googlescholarID'):
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

    params['prelog'] = prelog
    params['afterlog'] = afterlog

    with io.open(_bibfile, 'r', encoding='utf8') as bibtex_file:
        bibtex_str = bibtex_file.read()

    # read bibtex file
    bib_database = bibtexparser.loads(bibtex_str)
    bib_entries = bib_database.entries


    entries_selected=[]
    for e in bib_entries:
        if _verbose>=2:
            print 'e before clean=', e
        clean_entry(e)
        if _verbose>=2:
            print 'e after clean =', e

        if is_entry_selected(e):
            entries_selected.append(e)


    if params['show_paper_style']=='type':
        write_entries_by_type(entries_selected);
    elif params['show_paper_style']=='year':
        write_entries_by_year(entries_selected);
    elif params['show_paper_style']=='year_type' or params['show_paper_style']=='type_year':
        write_entries_by_type(entries_selected);
        write_entries_by_year(entries_selected);


if __name__ == '__main__':
    main()

