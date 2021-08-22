
# bibtex2html.py

[bibtex2html.py](https://github.com/JianCheng/bibtex2html.py) converts a bibtex file into an html file or a group of html files.
It considers additional fields (e.g., note, code, etc.) in bibtex. 
It also can show corresponding google scholar citations related with bibtex entries by parsing the google scholar profile. 
The group mode was inspired by [bibtex2html](http://www-sop.inria.fr/members/Gregoire.Malandain/codes/bibtex2html.html) by Dr. Gregoire Malandain. 


## Dependancies

Dependencies can be satisfied by running `pip install -r requirements.txt`


## Install 

* Use `pip`:

```
sudo pip install bibtex2html.py
```

* Or download latest codes from github

```
git clone https://github.com/JianCheng/bibtex2html.py
cd  bibtex2html.py
pip install -r requirements.txt
```


## Examples

#### To generate an html file 

* Generate paper lists by type and by year using a configuration file. It requires access to google scholar.

```
cd examples
bibtex2html.py papers.bib papers.html -c papers.ini 
```

* Do not show paper citations if you cannot access google scholar. Override options in configuration file.

```
bibtex2html.py papers.bib papers.html -c papers.ini --nc
```
Or

```
bibtex2html.py papers.bib papers.html -c papers.ini -i "{'show_citation':'no', 'show_total_citation':False}"
```


* Generate paper list by type with a selected first author and selected years.

```
bibtex2html.py papers.bib papers.html -c papers.ini -i "{'show_paper_style':'type', 'selection_and': {'author_first': ['Jian Cheng'], 'year':[2010,2013] }}"
```

#### To generate a group of html files

* Use `author_group` option to specify a group of people, then generate html files for the group.

```
cd examples
bibtex2html.py papers_group.bib papers -c papers_group.ini 
```
It outputs files in the folder `papers`.

* Do not show paper citations if you cannot access google scholar. Override options in configuration file.

```
bibtex2html.py papers_group.bib papers -c papers_group.ini --nc
```
