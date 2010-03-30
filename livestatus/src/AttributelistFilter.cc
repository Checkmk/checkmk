#include "AttributelistFilter.h"
#include "AttributelistColumn.h"
#include "opids.h"
#include "logger.h"


/* The following operators are defined:

   modified_attributes = 6
   modified_attributes = notifications_enabled

   --> Exact match

   modified_attributes ~ 6
   modified_attributes ~ notifications_enabled

   --> Must contain at least those bits

   modified_attributes ~~ 6
   modified_attributes ~~ notifications_enabled

   --> Must contain at least one of those bits

   Also number comparisons
*/


bool AttributelistFilter::accepts(void *data)
{
    unsigned long act_value = _column->getValue(data);
    bool pass = true;
    switch (_opid) {
	case OP_EQUAL:
	    pass = act_value == _ref; break;
	case OP_GREATER:
	    pass = act_value > _ref; break;
	case OP_LESS:
	    pass = act_value < _ref; break;
	case OP_REGEX:
	    pass = (act_value & _ref) == _ref; break;
	case OP_REGEX_ICASE:
	    pass = (act_value & _ref) != 0; break;
	default:
	    logger(LG_INFO, "Sorry. Operator %d not implemented for attribute lists", _opid);
    }
    return pass != _negate;
}

