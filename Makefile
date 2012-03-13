GEN=generate.py
PY=ni.py
PREFIX=/usr/include
#INCLUDES=$(PREFIX)/ni/XnStatus.h $(PREFIX)/ni/XnTypes.h XnInternalTypes.h  $(PREFIX)/ni/XnQueries.h $(PREFIX)/ni/XnContext.h $(PREFIX)/ni/XnPrdNode.h $(PREFIX)/ni/XnEnumerationErrors.h $(PREFIX)/ni/XnUtils.h $(PREFIX)/ni/XnPrdNodeInfoList.h $(PREFIX)/ni/XnPropNames.h
INCLUDES=$(PREFIX)/ni/XnStatus.h $(PREFIX)/ni/XnTypes.h $(PREFIX)/ni/XnQueries.h $(PREFIX)/ni/XnModuleInterface.h $(PREFIX)/ni/XnContext.h $(PREFIX)/ni/XnPrdNode.h $(PREFIX)/ni/XnEnumerationErrors.h $(PREFIX)/ni/XnUtils.h $(PREFIX)/ni/XnPrdNodeInfoList.h $(PREFIX)/ni/XnPropNames.h

all: validate

validate: $(PY)
	pyflakes $(PY)
	grep FIXME $(PY)

$(PY): Makefile $(GEN) override.py header.py footer.py $(INCLUDES)
	python $(GEN) -o $@  $(INCLUDES)

clean:
	-/bin/rm $(PY)

check:
	python $(GEN) -dc $(INCLUDES)
