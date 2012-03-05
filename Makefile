GEN=generate.py
PY=ni.py
#INCLUDES=/usr/include/ni/XnStatus.h /usr/include/ni/XnTypes.h XnInternalTypes.h  /usr/include/ni/XnQueries.h /usr/include/ni/XnContext.h /usr/include/ni/XnPrdNode.h /usr/include/ni/XnEnumerationErrors.h /usr/include/ni/XnUtils.h /usr/include/ni/XnPrdNodeInfoList.h /usr/include/ni/XnPropNames.h
INCLUDES=/usr/include/ni/XnStatus.h /usr/include/ni/XnTypes.h /usr/include/ni/XnQueries.h /usr/include/ni/XnContext.h /usr/include/ni/XnPrdNode.h /usr/include/ni/XnEnumerationErrors.h /usr/include/ni/XnUtils.h /usr/include/ni/XnPrdNodeInfoList.h /usr/include/ni/XnPropNames.h

all: validate

validate: $(PY)
	pyflakes $(PY)
	grep FIXME $(PY)

$(PY): Makefile $(GEN) override.py header.py footer.py $(INCLUDES)
	python $(GEN) -o $@  $(INCLUDES)
	#python $(GEN) -o $@ /usr/include/ni/*.h

clean:
	-/bin/rm $(PY)

check:
	python $(GEN) -dc $(INCLUDES)
