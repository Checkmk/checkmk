#!/usr/bin/python
# Put this file into share/check_mk/web/plugins/wato. It will create a rules
# for modbus checks and a rule in the configuration of the special agents.

register_check_parameters(
  subgroup_environment,
  "modbus_value",
  _("Modbus Performance Values"),
  Tuple(
     elements = [
         Integer(title = _("Warning if above")),
         Integer(title = _("Critical if above"))
        ]
  ),
  TextAscii( title = _("Value Name") ),
  None
)


register_rule(group,
    "special_agents:modbus",
    Tuple(
        title = _("Check Modbus devices"),
        help = _( "Configure the Server Address and the ids you want to query from the device"
                  "Please refer to the documentation of the device to find out which ids you want"),
        elements = [
           Integer( title = _("Port Number"), default_value=502 ),
           ListOf(
               Tuple(
                   elements = [
                     Integer( title=_("Counter ID") ),
                     DropdownChoice(
                       title = _("Number of words"),
                       choices = [
                          ( 1 , _("1 Word") ),
                          ( 2, _("2 Words") ),
                       ]
                     ),
                     DropdownChoice(
                       title = _("Value type"),
                       choices = [
                          ( "counter" , _("Its a counter value") ),
                          ( "gauge", _("Its a gauge value") ),
                       ]
                     ),
                     TextAscii( title = _("Counter Description")),
                   ]
               )
           )
        ]
    ),
    match = "first")


