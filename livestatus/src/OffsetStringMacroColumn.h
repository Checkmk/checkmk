#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "nagios.h"
#include "OffsetStringColumn.h"

class OffsetStringMacroColumn : public OffsetStringColumn
{
    int _offset;
public:
    OffsetStringMacroColumn(string name, string description, int offset, int indirect_offset = -1) :
	OffsetStringColumn(name, description, offset, indirect_offset) {};
    // reimplement several functions from StringColumn

    string valueAsString(void *data);
    void output(void *data, Query *);
    Filter *createFilter(int opid, char *value);

    // overriden by host and service macro columns
    virtual host *getHost(void *) = 0;
    virtual service *getService(void *) = 0;
private:
    const char *expandMacro(const char *macroname, host *hst, service *svc);
};

#endif // OffsetStringMacroColumn_h

