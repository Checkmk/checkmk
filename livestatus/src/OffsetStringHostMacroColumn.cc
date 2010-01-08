#include "OffsetStringHostMacroColumn.h"
#include "nagios.h"

host *OffsetStringHostMacroColumn::getHost(void *data)
{
    data = shiftPointer(data);
    return (host *)data;
}

service *OffsetStringHostMacroColumn::getService(void *data)
{
    return 0;
}


