# Tectonic drives the bibliography pass itself: it runs the backend biblatex
# asks for, and reruns TeX until the references settle. Nothing here calls
# bibtex or biber directly.
TECTONIC ?= tectonic
FLAGS = --keep-intermediates --synctex

.PHONY: all report report-fr clean

all: report report-fr

report: report/main.pdf
report-fr: report/main-fr.pdf

SECTIONS = $(wildcard report/sections/*.tex)
SECTIONS_FR = $(wildcard report/sections-fr/*.tex)

report/main.pdf: report/main.tex report/preamble.tex report/refs.bib \
                 report/generated/macros.tex $(SECTIONS)
	cd report && $(TECTONIC) $(FLAGS) main.tex

report/main-fr.pdf: report/main-fr.tex report/preamble.tex report/refs.bib \
                    report/generated/fr/macros.tex $(SECTIONS_FR)
	cd report && $(TECTONIC) $(FLAGS) main-fr.tex

clean:
	rm -f report/main.pdf report/main-fr.pdf report/*-blx.bib \
	      report/*.aux report/*.bbl report/*.bcf report/*.blg report/*.log \
	      report/*.run.xml report/*.synctex.gz
