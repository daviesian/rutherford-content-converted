MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

pdf: $(TARGETS)

%.eps: %.svg
	inkscape -z -E $@ $<

%.eps: %.jpg
	convert $< $@

%.dvi: %.tex        
	TEXINPUTS=$(MAKEFILE_DIR)../resources/common:${TEXINPUTS} latex $<
	while grep 'Rerun to get ' $*.log ; do TEXINPUTS=$(MAKEFILE_DIR)../resources/common:${TEXINPUTS} latex $<; done

%.ps: %.dvi
	dvips -o $@ $<

%.pdf: %.ps
	ps2pdf $< $@

clean:
	rm -f *.log *.pdf *.aux *.dvi *~ figures/*.eps

.DELETE_ON_ERROR:
