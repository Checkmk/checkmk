#include "OffsetStringMacroColumn.h"
#include "AndingFilter.h"
#include "Query.h"
#include "logger.h"
#include "nagios.h"
#include "nagios/macros.h"
extern char     *macro_user[MAX_USER_MACROS];

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
    // host macros
    if (!strcmp(macroname, "HOSTNAME"))
	return hst->name;
    else if (!strcmp(macroname, "HOSTDISPLAYNAME"))
	return hst->display_name;
    else if (!strcmp(macroname, "HOSTALIAS"))
	return hst->alias;
    else if (!strcmp(macroname, "HOSTADDRESS"))
	return hst->address;
    else if (!strcmp(macroname, "HOSTOUTPUT"))
	return hst->plugin_output;
    else if (!strcmp(macroname, "LONGHOSTOUTPUT"))
	return hst->long_plugin_output;
    else if (!strcmp(macroname, "HOSTPERFDATA"))
	return hst->perf_data;
    else if (!strcmp(macroname, "HOSTCHECKCOMMAND"))
	return hst->host_check_command;

    else if (!strncmp(macroname, "_HOST", 5)) // custom macro
	return expandCustomVariables(macroname + 5, hst->custom_variables);

    // service macros
    else if (svc) {
	if (!strcmp(macroname, "SERVICEDESC"))
	    return svc->description;
	else if (!strcmp(macroname, "SERVICEDISPLAYNAME"))
	    return svc->display_name;
	else if (!strcmp(macroname, "SERVICEOUTPUT"))
	    return svc->plugin_output;
	else if (!strcmp(macroname, "LONGSERVICEOUTPUT"))
	    return svc->long_plugin_output;
	else if (!strcmp(macroname, "SERVICEPERFDATA"))
	    return svc->perf_data;
	else if (!strcmp(macroname, "SERVICECHECKCOMMAND"))
	    return svc->service_check_command;
	else if (!strncmp(macroname, "_SERVICE", 8)) // custom macro
	    return expandCustomVariables(macroname + 8, svc->custom_variables);
    }

    // USER macros
    if (!strncmp(macroname, "USER", 4)) {
	int n = atoi(macroname + 4);
	if (n > 0 && n <= MAX_USER_MACROS) {
	    return macro_user[n - 1];
	}
    }
    
    return 0;
}


const char *OffsetStringMacroColumn::expandCustomVariables(const char *varname, customvariablesmember *custvars)
{
    while (custvars)
    {
	if (!strcasecmp(varname, custvars->variable_name))
	    return custvars->variable_value;
	custvars = custvars->next;
    }
    return 0;
} 
