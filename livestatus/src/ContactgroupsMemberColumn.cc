#include "nagios.h"
#include "ContactgroupsMemberColumn.h"
#include "logger.h"

bool ContactgroupsMemberColumn::isNagiosMember(void *cg, void *ctc)
{
    return is_contact_member_of_contactgroup((contactgroup *)cg, (contact *)ctc);
}

