#include "OffsetStringServiceMacroColumn.h"
#include "nagios.h"

host *OffsetStringServiceMacroColumn::getHost(void *data)
{
    service *svc = getService(data);
    if (svc)
	return svc->host_ptr;
    else
	return 0;
}

service *OffsetStringServiceMacroColumn::getService(void *data)
{
    data = shiftPointer(data);
    return (service *)data;
}


