#include "AttributelistColumn.h"
#include "AttributelistFilter.h"
#include "Query.h"
#include "strutil.h"
#include "logger.h"

struct al_entry {
    const char *name;
    unsigned long bitvalue;
};

struct al_entry al_entries[] = {
    { "notifications_enabled",            MODATTR_NOTIFICATIONS_ENABLED      },
    { "active_checks_enabled",            MODATTR_ACTIVE_CHECKS_ENABLED      },
    { "passive_checks_enabled",           MODATTR_PASSIVE_CHECKS_ENABLED     },
    { "event_handler_enabled",            MODATTR_EVENT_HANDLER_ENABLED      },
    { "flap_detection_enabled",           MODATTR_FLAP_DETECTION_ENABLED     },
    { "failure_prediction_enabled",       MODATTR_FAILURE_PREDICTION_ENABLED },
    { "performance_data_enabled",         MODATTR_PERFORMANCE_DATA_ENABLED   },
    { "obsessive_handler_enabled",        MODATTR_OBSESSIVE_HANDLER_ENABLED  },
    { "event_handler_command",            MODATTR_EVENT_HANDLER_COMMAND      },
    { "check_command",                    MODATTR_CHECK_COMMAND              },
    { "normal_check_interval",            MODATTR_NORMAL_CHECK_INTERVAL      },
    { "retry_check_interval",             MODATTR_RETRY_CHECK_INTERVAL       },
    { "max_check_attempts",               MODATTR_MAX_CHECK_ATTEMPTS         },
    { "freshness_checks_enabled",         MODATTR_FRESHNESS_CHECKS_ENABLED   },
    { "check_timeperiod",                 MODATTR_CHECK_TIMEPERIOD           },
    { "custom_variable",                  MODATTR_CUSTOM_VARIABLE            },
    { "notification_timeperiod",          MODATTR_NOTIFICATION_TIMEPERIOD    },
    { 0, 0 }
};

unsigned long AttributelistColumn::getValue(void *data)
{
   data = shiftPointer(data);
   if (!data) return 0;

   return *(unsigned long *)((char *)data + _offset);
}

void AttributelistColumn::output(void *data, Query *query)
{
    unsigned long mask = getValue(data);
    if (_show_list) {
	unsigned i = 0;
	bool first = true;
	query->outputBeginSublist();
	while (al_entries[i].name) {
	    if (mask & al_entries[i].bitvalue) {
		if (!first)
		    query->outputSublistSeparator();
		else
		    first = false;
		query->outputString(al_entries[i].name);
	    }
	    i++;
	}
	query->outputEndSublist();
    }
    else {
	query->outputUnsignedLong(mask);
    }
}

string AttributelistColumn::valueAsString(void *data)
{
    unsigned long mask = getValue(data);
    char s[16];
    snprintf(s, 16, "%lu", mask);
    return string(s);
}

Filter *AttributelistColumn::createFilter(int opid, char *value)
{
    unsigned long ref = 0;
    if (isdigit(value[0]))
	ref = strtoul(value, 0, 10);
    else {
	char *scan = value;
	char *t;
	while (t = next_token(&scan)) {
	    unsigned i = 0;
	    while (al_entries[i].name) {
		if (!strcmp(t, al_entries[i].name)) {
		    ref |= al_entries[i].bitvalue;
		    break;
		}
		i ++;
	    }
	    if (!al_entries[i].name) {
		logger(LG_INFO, "Ignoring invalid value '%s' for attribute list", t);
	    }
	}
    }
    return new AttributelistFilter(this, opid, ref);
}

