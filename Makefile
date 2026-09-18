# Tectonic drives the bibliography pass itself: it runs the backend biblatex
# asks for, and reruns TeX until the references settle. Nothing here calls
# bibtex or biber directly.
TECTONIC ?= tectonic
FLAGS = --keep-intermediates --synctex

.PHONY: all report slides clean

all: report slides

report: report/main.pdf
slides: slides/main.pdf

report/main.pdf: report/main.tex report/preamble.tex report/refs.bib report/generated/macros.tex
	cd report && $(TECTONIC) $(FLAGS) main.tex

slides/main.pdf: slides/main.tex report/preamble.tex report/generated/macros.tex
	cd slides && $(TECTONIC) $(FLAGS) main.tex

clean:
	rm -f report/main.pdf slides/main.pdf \
	      report/*.aux report/*.bbl report/*.bcf report/*.blg report/*.log \
	      report/*.run.xml report/*.synctex.gz \
	      slides/*.aux slides/*.log slides/*.nav slides/*.out slides/*.snm \
	      slides/*.toc slides/*.synctex.gz
