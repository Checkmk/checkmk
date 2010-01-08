#include "OffsetStringMacroColumn.h"
#include "AndingFilter.h"
#include "Query.h"
#include "logger.h"
#include "nagios.h"

string OffsetStringMacroColumn::valueAsString(void *data)
{
    char *raw = getValue(data);
    host *hst = getHost(data);
    service *svc = getService(data);


    // search for macro names, beginning with $
    string result = "";
    char *scan = raw;

    while (*scan) {
	char *dollar = strchr(scan, '$');
	if (!dollar) {
	    result += scan;
	    break;
	}
	result += string(scan, dollar - scan);
	char *otherdollar = strchr(dollar + 1, '$');
	if (!otherdollar) { // unterminated macro, do not expand
	    result += scan;
	    break;
	}
	string macroname = string(dollar + 1, otherdollar - dollar - 1);
	const char *replacement = expandMacro(macroname.c_str(), hst, svc);
	if (replacement)
	    result += replacement;
	else
	    result += string(dollar, otherdollar - dollar + 1); // leave macro unexpanded
	scan = otherdollar + 1;
    }
    return result;
}


void OffsetStringMacroColumn::output(void *data, Query *query)
{
    string s = valueAsString(data);
    query->outputString(s.c_str());
}

Filter *OffsetStringMacroColumn::createFilter(int opid, char *value)
{
    logger(LG_INFO, "Sorry. No filtering on macro columns implemented yet");
    return new AndingFilter(); // always true
}

const char *OffsetStringMacroColumn::expandMacro(const char *macroname, host *hst, service *svc)
{
    if (!strcmp(macroname, "HOSTNAME"))
	return hst->name;
    else if (!strcmp(macroname, "SERVICEDESC"))
	if (svc)
	    return svc->description;
	else
	    return "";
    return 0;
}

