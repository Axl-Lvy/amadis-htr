# Tectonic drives the bibliography pass itself: it runs the backend biblatex
# asks for, and reruns TeX until the references settle. Nothing here calls
# bibtex or biber directly.
TECTONIC ?= tectonic
FLAGS = --keep-intermediates --synctex

.PHONY: all report report-fr slides clean

all: report report-fr slides

report: report/main.pdf
report-fr: report/main-fr.pdf
slides: slides/main.pdf

SECTIONS = $(wildcard report/sections/*.tex)
SECTIONS_FR = $(wildcard report/sections-fr/*.tex)

report/main.pdf: report/main.tex report/preamble.tex report/refs.bib \
                 report/generated/macros.tex $(SECTIONS)
	cd report && $(TECTONIC) $(FLAGS) main.tex

report/main-fr.pdf: report/main-fr.tex report/preamble.tex report/refs.bib \
                    report/generated/fr/macros.tex $(SECTIONS_FR)
	cd report && $(TECTONIC) $(FLAGS) main-fr.tex

slides/main.pdf: slides/main.tex report/preamble.tex report/generated/macros.tex
	cd slides && $(TECTONIC) $(FLAGS) main.tex

clean:
	rm -f report/main.pdf report/main-fr.pdf slides/main.pdf report/*-blx.bib slides/*-blx.bib \
	      report/*.aux report/*.bbl report/*.bcf report/*.blg report/*.log \
	      report/*.run.xml report/*.synctex.gz \
	      slides/*.aux slides/*.log slides/*.nav slides/*.out slides/*.snm \
	      slides/*.toc slides/*.synctex.gz
