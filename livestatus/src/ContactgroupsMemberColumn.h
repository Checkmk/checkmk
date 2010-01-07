#ifndef ContactgroupsMemberColumn_h
#define ContactgroupsMemberColumn_h

#include "config.h"
#include "ContactsColumn.h"

class ContactgroupsMemberColumn : public ContactsColumn
{
public:
    ContactgroupsMemberColumn(string name, string description, int indirect_offset)
	: ContactsColumn(name, description, indirect_offset) {};
    int type() { return COLTYPE_LIST; };
    bool isNagiosMember(void *data, void *member);
};

#endif // ContactgroupsMemberColumn_h

