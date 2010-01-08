#ifndef OffsetStringHostMacroColumn_h
#define OffsetStringHostMacroColumn_h

#include "nagios.h"
#include "OffsetStringMacroColumn.h"

class OffsetStringHostMacroColumn : public OffsetStringMacroColumn
{
public:
    OffsetStringHostMacroColumn(string name, string description, int offset, int indirect_offset = -1) :
	OffsetStringMacroColumn(name, description, offset, indirect_offset) {};
    host *getHost(void *data);
    service *getService(void *data);
};

#endif // OffsetStringHostMacroColumn_h

