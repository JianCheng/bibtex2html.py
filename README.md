
# bibtex2html.py

[bibtex2html.py](https://github.com/JianCheng/bibtex2html.py) coverts a bibtex file into an html file.
It considers additional fields (e.g., note, code, etc.) in bibtex. 
It also can show corresponding google scholar citations related with bibtex entries by parsing the google scholar profile. 


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

* Generate paper lists by type and by year using a configuration file. It requires access to google scholar.

```
./bibtex2html/bibtex2html.py examples/papers.bib examples/papers.html -c examples/papers.ini 
```

* Do not show paper citations if you cannot access google scholar. Override options in configuration file.

```
./bibtex2html/bibtex2html.py examples/papers.bib examples/papers.html -c examples/papers.ini -i "{'show_citation':'no', 'show_total_citation':False}"
```


* Generate paper list by type with a selected first author and selected years.

```
./bibtex2html/bibtex2html.py examples/papers.bib examples/papers.html -c examples/papers.ini -i "{'show_paper_style':'type', 'selection_and': {'author_first': ['Jian Cheng'], 'year':[2010,2013] }}"
```
