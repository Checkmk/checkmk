#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import mkeventd

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

# main_config_file = defaults.check_mk_configdir + "/mkeventd.mk"
config_dir       = defaults.default_config_dir + "/mkeventd.d/wato/"
if defaults.omd_root:
    status_file      = defaults.omd_root + "/var/mkeventd/status"

# Include rule configuration into backup/restore/replication. Current
# status is not backed up.
if mkeventd_enabled:
    replication_paths.append(( "dir", "mkeventd", config_dir ))
    backup_paths.append(( "dir", "mkeventd", config_dir ))

#.
#   .--ValueSpecs----------------------------------------------------------.
#   |        __     __    _            ____                                |
#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___           |
#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|          |
#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \          |
#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/          |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   | Declarations of the structure of rules and actions                   |
#   '----------------------------------------------------------------------'
substitute_help = _("""
The following placeholdes will be substituted by value from the actual event:
<table class=help>
<tr><td class=tt>$ID$</td><td>Event ID</td></tr>
<tr><td class=tt>$COUNT$</td><td>Number of occurrances</td></tr>
<tr><td class=tt>$TEXT$</td><td>Message text</td></tr>
<tr><td class=tt>$FIRST$</td><td>Time of the first occurrance (time stamp)</td></tr>
<tr><td class=tt>$LAST$</td><td>Time of the most recent occurrance</td></tr>
<tr><td class=tt>$COMMENT$</td><td>Event comment/td></tr>
<tr><td class=tt>$SL$</td><td>Service Level</td></tr>
<tr><td class=tt>$HOST$</td><td>Host name (as sent by syslog)</td></tr>
<tr><td class=tt>$CONTACT$</td><td>Contact information</td></tr>
<tr><td class=tt>$APPLICATION$</td><td>Syslog tag / Application</td></tr>
<tr><td class=tt>$PID$</td><td>Process ID of the origin process</td></tr>
<tr><td class=tt>$PRIORITY$</td><td>Syslog Priority</td></tr>
<tr><td class=tt>$FACILITY$</td><td>Syslog Facility</td></tr>
<tr><td class=tt>$RULE_ID$</td><td>ID of the rule</td></tr>
<tr><td class=tt>$STATE$</td><td>State of the event (0/1/2/3)</td></tr>
<tr><td class=tt>$PHASE$</td><td>Phase of the event (always open)</td></tr>
<tr><td class=tt>$OWNER$</td><td>Owner of the event</td></tr>
<tr><td class=tt>$MATCH_GROUPS$</td><td>Text groups from regular expression match, separated by spaces/td></tr>
<tr><td class=tt>$MATCH_GROUP_1$</td><td>Text of the first match group from expression match</td></tr>
<tr><td class=tt>$MATCH_GROUP_2$</td><td>Text of the second match group from expression match</td></tr>
<tr><td class=tt>$MATCH_GROUP_3$</td><td>Text of the third match group from expression match (and so on...)</td></tr> 
</table>
"""
)

class ActionList(ListOf):
    def __init__(self, vs, **kwargs): 
        ListOf.__init__(self, vs, **kwargs) 

    def validate_value(self, value, varprefix):
        ListOf.validate_value(self, value, varprefix)
        action_ids = [ v["id"] for v in value ]
        rules = load_mkeventd_rules()
        for rule in rules:
            for action_id in rule.get("actions", []):
                if action_id not in action_ids:
                    raise MKUserError(varprefix, _("You are missing the action with the ID <b>%s</b>, "
                       "which is still used in some rules.") % action_id)

    
vs_mkeventd_actions = \
    ActionList(
        Foldable(
          Dictionary(
            title = _("Action"),
            optional_keys = False,
            elements = [
              (   "id", 
                  ID(
                      title = _("Action ID"),
                      help = _("A unique ID of this action that is used as an internal "
                               "reference in the configuration. Changing the ID is not "
                               "possible if still rules refer to this ID."),
                      allow_empty = False,
                      size = 12,
                  )
              ),
              (   "title",
                  TextUnicode(
                      title = _("Title"),
                      help = _("A descriptive title of this action."),
                      allow_empty = False,
                      size = 64,
                  )
              ),
              (   "disabled",
                  Checkbox(
                      title = _("Disable"),
                      label = _("Current disable execution of this action"),
                  )
              ),
              (   "hidden",
                  Checkbox(
                      title = _("Hide from Status GUI"),
                      label = _("Do not offer this action as a command on open events"),
                      help = _("If you enabled this option, then this action will not "
                               "be available as an interactive user command. It is usable "
                               "as an ad-hoc action when a rule fires, nevertheless."),
                 ),
              ),
              (   "action",
                  CascadingDropdown(
                      title = _("Type of Action"),
                      help = _("Choose the type of action to perform"),
                      choices = [
                          ( "email",
                            _("Send Email"),
                            Dictionary(
                              optional_keys = False,
                              elements = [
                                 (   "to",
                                     TextAscii(
                                         title = _("Recipient Email address"),
                                         allow_empty = False,
                                     ),
                                 ),
                                 (   "subject",
                                     TextUnicode(
                                         title = _("Subject"),
                                         allow_empty = False,
                                         size = 64,
                                     ),
                                 ),
                                 (   "body",
                                     TextAreaUnicode(
                                         title = _("Body"),
                                         help = _("Text-body of the email to send. ") + substitute_help,
                                         cols = 64,
                                         rows = 10,
                                     ),
                                 ),
                              ]
                            )
                        ),
                        ( "script",
                          _("Execute Shell Script"),
                          Dictionary(
                            optional_keys = False,
                            elements = [
                               ( "script",
                                 TextAreaUnicode(
                                   title = _("Script body"),
                                   help = _("This script will be executed using the BASH shell. ") + substitute_help,
                                   cols = 64,
                                   rows = 10,
                                 )
                               ),
                            ]
                          )
                        ),
                      ]
                  ),
              ),
            ],
          ),
          title_function = lambda value: not value["id"] and _("New Action") or (value["id"] + " - " + value["title"]), 
        ),
    title = _("Actions (Emails &amp Scripts)"),
    help = _("Configure that possible actions that can be performed when a "
             "rule triggers and also manually by a user."),
    totext = _("%d actions"),
    )


class RuleState(MonitoringState):
    def __init__(self, **kwargs):
        MonitoringState.__init__(self, **kwargs)
        self._choices.append((-1, _("(set by syslog)")))

vs_mkeventd_rule = Dictionary(
    title = _("Rule Properties"),
    elements = [
        ( "id",
          ID(
            title = _("Rule ID"),
            help = _("A unique ID of this rule. Each event will remember the rule "
                     "it was classified with by its rule ID."),
            allow_empty = False,
            size = 12,
        )),
        ( "description",
          TextUnicode(
            title = _("Description"),
            help = _("You can use this description for commenting your rules. It "
                     "will not be attached to the event this rule classifies."),
            size = 64,
        )),
        ( "disabled",
          Checkbox(
            title = _("Rule activation"),
            help = _("Disabled rules are kept in the configuration but are not applied."),
            label = _("do not apply this rule"),
          )
        ),
        ( "drop",
          Checkbox(
            title = _("Drop Message"),
            help = _("With this option all messages matching this rule will be silently dropped."),
            label = _("Silently drop messages, do no actions"),
          )
        ),
        ( "state",
          RuleState(
            title = _("State"),
            help = _("The monitoring state that this event will trigger."),
            default_value = -1,
        )),
        ( "sl",
          DropdownChoice(
            title = _("Service Level"),
            choices = mkeventd.service_levels,
            prefix_values = True,
          ),
        ),
        ( "actions", 
          ListChoice(
            title = _("Actions"),
            help = _("Actions to automatically perform when this event occurs"),
            choices = mkeventd.action_choices,
          )
        ),
        ( "count",
          Dictionary(
              title = _("Count messages in defined interval"),
              help = _("With this option you can make the rule being executed not before "
                       "the matching message is seen a couple of times in a defined "
                       "time interval. Also counting activates the aggregation of messages "
                       "that result from the same rule into one event, even if <i>count</i> is "
                       "set to 1."),
              optional_keys = False,
              columns = 2,
              elements = [
                  ( "count",
                      Integer(
                        title = _("Count until triggered"),
                        help = _("That many times the message must occur until an event is created"),
                        minvalue = 1,
                      ),
                  ),
                  ( "period",
                      Age(
                        title = _("Time period for counting"),
                        help = _("If in this time range the configured number of time the rule is "
                                 "triggered, an event is being created. If the required count is not reached "
                                 "then the count is reset to zero."),
                        default_value = 86400,
                      ),
                  ),
                  ( "algorithm",
                    DropdownChoice(
                        title = _("Algorithm"),
                        help = _("Select how the count is computed. The algorithm <i>Interval</i> will count the "
                                 "number of messages from the first occurrance and reset this counter as soon as "
                                 "the interval is elapsed or the maximum count has reached. The token bucket algorithm "
                                 "does not work with intervals but simply decreases the current count by one for "
                                 "each partial time interval. Please refer to the online documentation for more details."),
                        choices = [
                            ( "interval",    _("Interval")),
                            ( "tokenbucket", _("Token Bucket")),
                            ( "dynabucket", _("Dynamic Token Bucket")),
                        ],
                        default_value = "interval")
                  ),
                  ( "count_ack",
                    Checkbox(
                        label = _("Continue counting when event is <b>acknowledged</b>"),
                        help = _("Otherwise counting will start from one with a new event for "
                                 "the next rule match."),
                        default_value = False,
                    )
                  ),
                  ( "separate_host",
                    Checkbox(
                        label = _("Force separate events for different <b>hosts</b>"),
                        help = _("When aggregation is turned on and the rule matches for "
                                 "two different hosts then these two events will be kept "
                                 "separate if you check this box."),
                        default_value = True,
                    ),
                  ),
                  ( "separate_application",
                    Checkbox(
                        label = _("Force separate events for different <b>applications</b>"),
                        help = _("When aggregation is turned on and the rule matches for "
                                 "two different applications then these two events will be kept "
                                 "separate if you check this box."),
                        default_value = True,
                    ),
                  ),
                  ( "separate_match_groups",
                    Checkbox(
                        label = _("Force separate events for different <b>match groups</b>"),
                        help = _("When you use subgroups in the regular expression of your "
                                 "match text then you can have different values for the matching "
                                 "groups be reflected in different events."),
                        default_value = True,
                    ),
                  ),
             ],
           )
        ),
        ( "expect",
          Dictionary(
             title = _("Expect regular messages"),
             help = _("With this option activated you can make the Event Console monitor "
                      "that a certain number of messages are <b>at least</b> seen within "
                      "each regular time interval. Otherwise an event will be created. "
                      "The options <i>week</i>, <i>two days</i> and <i>day</i> refer to "
                      "periodic intervals aligned at 00:00:00 on the 1st of January 1970. "
                      "You can specify a relative offset in hours in order to re-align this "
                      "to any other point of time."),
             optional_keys = False,
             columns = 2,
             elements = [
               ( "interval",
                 CascadingDropdown(
                     title = _("Interval"),
                     html_separator = "&nbsp;",
                     choices = [
                         ( 7*86400, _("week"),
                           Integer(
                               label = _("Timezone offset"),
                               unit = _("hours"),
                               default_value = 0,
                               minvalue = - 167,
                               maxvalue = 167,
                            )
                         ),
                         ( 2*86400, _("two days"),
                           Integer(
                               label = _("Timezone offset"),
                               unit = _("hours"),
                               default_value = 0,
                               minvalue = - 47,
                               maxvalue = 47,
                            )
                         ),
                         ( 86400, _("day"),
                           DropdownChoice(
                               label = _("in timezone"),
                               choices = [
                                  ( -12, _("UTC -12 hours") ),
                                  ( -11, _("UTC -11 hours") ),
                                  ( -10, _("UTC -10 hours") ),
                                  ( -9, _("UTC -9 hours") ),
                                  ( -8, _("UTC -8 hours") ),
                                  ( -7, _("UTC -7 hours") ),
                                  ( -6, _("UTC -6 hours") ),
                                  ( -5, _("UTC -5 hours") ),
                                  ( -4, _("UTC -4 hours") ),
                                  ( -3, _("UTC -3 hours") ),
                                  ( -2, _("UTC -2 hours") ),
                                  ( -1, _("UTC -1 hour") ),
                                  ( 0, _("UTC") ),
                                  ( 1, _("UTC +1 hour") ),
                                  ( 2, _("UTC +2 hours") ),
                                  ( 3, _("UTC +3 hours") ),
                                  ( 4, _("UTC +4 hours") ),
                                  ( 5, _("UTC +5 hours") ),
                                  ( 6, _("UTC +8 hours") ),
                                  ( 7, _("UTC +7 hours") ),
                                  ( 8, _("UTC +8 hours") ),
                                  ( 9, _("UTC +9 hours") ),
                                  ( 10, _("UTC +10 hours") ),
                                  ( 11, _("UTC +11 hours") ),
                                  ( 12, _("UTC +12 hours") ),
                              ],
                              default_value = 0,
                          )
                        ),
                        ( 3600, _("hour") ),
                        (  900, _("15 minutes") ),
                        (  300, _("5 minutes") ),
                        (   60, _("minute") ), 
                        (   10, _("10 seconds") ), 
                    ],
                    default_value = 3600,
                 )
               ),
               ( "count",
                 Integer(
                     title = _("Number of expected messages in each interval"),
                     minvalue = 1,
                 )
              ),
              ( "merge",
                DropdownChoice(
                    title = _("Merge with open event"),
                    help = _("If there already exists an open event because of absent "
                             "messages according to this rule, you can optionally merge "
                             "the new incident with the exising event or create a new "
                             "event for each interval with absent messages."),
                    choices = [
                        ( "open", _("Merge if there is an open un-acknowledged event") ),
                        ( "acked", _("Merge even if there is an acknowledged event") ),
                        ( "never", _("Create a new event for each incident - never merge") ),
                    ],
                    default_value = "open",
                )
              ),
            ])
        ),
        ( "delay",
          Age(
            title = _("Delay event creation"),
            help = _("The creation of an event will be delayed by this time period. This "
                     "does only make sense for events that can be cancelled by a negative "
                     "rule."))
        ),
        ( "livetime",
          Tuple(
              title = _("Limit event livetime"),
              help = _("If you set a livetime of an event, then it will automatically be "
                       "deleted after that time if, even if no action has taken by the user. You can "
                       "decide whether to expire open, acknowledged or both types of events. The lifetime "
                       "always starts when the event is entering the open state."),
              elements = [
                  Age(),
                  ListChoice(
                    choices = [
                      ( "open", _("Expire events that are in the state <i>open</i>") ),
                      ( "ack", _("Expire events that are in the state <i>acknowledged</i>") ),
                    ],
                    default_value = [ "open" ],
                  )
              ],
          ),
        ),
        ( "match",
          RegExpUnicode(
            title = _("Text to match"),
            help = _("The rules does only apply when the given regular expression matches "
                     "the message text (infix search)."),
            size = 64,
          ) 
        ),
        ( "match_host",
          RegExpUnicode(
            title = _("Match host"),
            help = _("The rules does only apply when the given regular expression matches "
                     "the host name the message originates from. Note: in some cases the "
                     "event might use the IP address instead of the host name."),
          ) 
        ),
        ( "match_application",
          RegExpUnicode(
              title = _("Match syslog application (tag)"),
              help = _("Regular expression for matching the syslog tag (case insenstive)"),
          )
        ),
        ( "match_priority",
          Tuple(
              title = _("Match syslog priority"),
              help = _("Define a range of syslog priorities this rule matches"),
              orientation = "horizontal",
              show_titles = False,
              elements = [
                 DropdownChoice(label = _("from:"), choices = mkeventd.syslog_priorities, default_value = 4),
                 DropdownChoice(label = _(" to:"),   choices = mkeventd.syslog_priorities, default_value = 0),
              ],
          ),
        ),
        ( "match_facility",
          DropdownChoice(
              title = _("Match syslog facility"),
              help = _("Make the rule match only if the message has a certain syslog facility. "
                       "Messages not having a facility are classified as <tt>user</tt>."),
              choices = mkeventd.syslog_facilities,
          )
        ),
        ( "match_sl",
          Tuple(
            title = _("Match service level"),
            help = _("This setting is only useful for events that result from monitoring notifications "  
                     "sent by Check_MK. Those can set a service level already in the event. In such a "
                     "case you can make this rule match only certain service levels. Events that do not "),
            orientation = "horizontal",
            show_titles = False,
            elements = [ 
              DropdownChoice(label = _("from:"),  choices = mkeventd.service_levels, prefix_values = True),
              DropdownChoice(label = _(" to:"),  choices = mkeventd.service_levels, prefix_values = True),
            ],
          ),
        ),
        ( "match_ok",
          RegExpUnicode(
            title = _("Text to cancel event"),
            help = _("If a matching message appears with this text, then an event created "
                     "by this rule will automatically be cancelled (if host, application and match groups match). "),
            size = 64,
          ) 
        ),
        ( "cancel_priority",
          Tuple(
              title = _("Syslog priority to cancel event"),
              help = _("If the priority of the event lies withing this range and either no text to cancel "
                       "is specified or that text also matched, then events created with this rule will "
                       "automatically be cancelled (if host, application and match groups match)."),
              orientation = "horizontal",
              show_titles = False,
              elements = [
                 DropdownChoice(label = _("from:"), choices = mkeventd.syslog_priorities, default_value = 7),
                 DropdownChoice(label = _(" to:"),   choices = mkeventd.syslog_priorities, default_value = 5),
              ],
          ),
        ),
        ( "set_text",
          TextUnicode(
              title = _("Rewrite message text"),
              help = _("Replace the message text with this text. If you have bracketed "
                       "groups in the text to match, then you can use the placeholders "
                       "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                       "etc matching group.") + 
                     _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
                       "This allows you to add new information in front or at the end."), 
              size = 64,
              allow_empty = False,
          )
        ),
        ( "set_host",
          TextUnicode(
              title = _("Rewrite hostname"),
              help = _("Replace the host name with this text. If you have bracketed "
                       "groups in the text to match, then you can use the placeholders "
                       "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                       "etc matching group.") + 
                     _("The placeholder <tt>\\0</tt> will be replaced by the original host name. "
                       "This allows you to add new information in front or at the end."),
              allow_empty = False,
          )
        ),
        ( "set_application",
          TextUnicode(
              title = _("Rewrite application"),
              help = _("Replace the application (syslog tag) with this text. If you have bracketed "
                       "groups in the text to match, then you can use the placeholders "
                       "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                       "etc matching group.") + 
                     _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
                       "This allows you to add new information in front or at the end."),
              allow_empty = False,
          )
        ),
        ( "set_comment",
          TextUnicode(
              title = _("Add comment"),
              help = _("Attach a comment to the event. If you have bracketed "
                       "groups in the text to match, then you can use the placeholders "
                       "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                       "etc matching group.") + 
                     _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
                       "This allows you to add new information in front or at the end."),
              size = 64,
              allow_empty = False,
          )
        ),
        ( "set_contact",
          TextUnicode(
              title = _("Add contact information"),
              help = _("Attach information about a contact person. If you have bracketed "
                       "groups in the text to match, then you can use the placeholders "
                       "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                       "etc matching group.") + 
                     _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
                       "This allows you to add new information in front or at the end."),
              size = 64,
              allow_empty = False,
          )
        ),
    ],
    optional_keys = [ "delay", "livetime", "count", "expect", "match_priority", "match_priority", 
                      "match_facility", "match_sl", "match_host", "match_application", 
                      "set_text", "set_host", "set_application", "set_comment",
                      "set_contact", "cancel_priority", "match_ok" ],
    headers = [
        ( _("General Properties"), [ "id", "description", "disabled" ] ),
        ( _("Matching Criteria"), [ "match", "match_host", "match_application", "match_priority", "match_facility", 
                                    "match_sl", "match_ok", "cancel_priority" ]),
        ( _("Outcome &amp; Action"), [ "state", "sl", "actions", "drop" ]),
        ( _("Counting &amp; Timing"), [ "count", "expect", "delay", "livetime", ]),
        ( _("Rewriting"), [ "set_text", "set_host", "set_application", "set_comment", "set_contact" ]),
    ],
    render = "form",
    form_narrow = True,
)

# VS for simulating an even
vs_mkeventd_event = Dictionary(
    title = _("Event Simulator"),
    help = _("You can simulate an event here and check out, which rules are matching."),
    render = "form",
    form_narrow = True,
    optional_keys = False,
    elements = [
        ( "text",
          TextUnicode(
            title = _("Message Text"),
            size = 80,
            allow_empty = False,
            default_value = _("Still nothing happened.")),
        ),
        ( "application",
          TextUnicode(
            title = _("Application Name"),
            help = _("The syslog tag"),
            size = 40,
            allow_empty = True)
        ),
        ( "host",
          TextUnicode(
            title = _("Host Name"),
            help = _("The host name of the event"),
            size = 40,
            allow_empty = True)
        ),
        ( "priority",
          DropdownChoice(
            title = _("Syslog Priority"),
            choices = mkeventd.syslog_priorities, 
            default_value = 5,
          )
        ),
        ( "facility",
          DropdownChoice(
              title = _("Syslog Facility"),
              choices = mkeventd.syslog_facilities,
              default_value = 1,
          )
        ),
    ])
        

#.
#   .--Persistence---------------------------------------------------------.
#   |           ____               _     _                                 |
#   |          |  _ \ ___ _ __ ___(_)___| |_ ___ _ __   ___ ___            |
#   |          | |_) / _ \ '__/ __| / __| __/ _ \ '_ \ / __/ _ \           |
#   |          |  __/  __/ |  \__ \ \__ \ ||  __/ | | | (_|  __/           |
#   |          |_|   \___|_|  |___/_|___/\__\___|_| |_|\___\___|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def load_mkeventd_rules():
    filename = config_dir + "rules.mk"
    if not os.path.exists(filename):
        return []
    try:
        vars = { "rules" : [] }
        execfile(filename, vars, vars)
        # If we are running on OMD then we know the path to
        # the state retention file of mkeventd and can read
        # the rule statistics directly from that file.
        if defaults.omd_root and os.path.exists(status_file):
            mkeventd_status = eval(file(status_file).read())
            rule_stats = mkeventd_status["rule_stats"]
            for rule in vars["rules"]:
                rule["hits"] = rule_stats.get(rule["id"], 0)

        # Convert some data fields into a new format
        for rule in vars["rules"]:
            if "livetime" in rule:
                livetime = rule["livetime"]
                if type(livetime) != tuple:
                    rule["livetime"] = ( livetime, ["open"] )

        return vars["rules"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        return []

def save_mkeventd_rules(rules):
    make_nagios_directory(defaults.default_config_dir + "/mkeventd.d")
    make_nagios_directory(config_dir)
    out = create_user_file(config_dir + "rules.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    try:
        if config.mkeventd_pprint_rules:
            out.write("rules += \\\n%s\n" % pprint.pformat(rules))
            return
    except:
        pass

    out.write("rules += \\\n%r\n" % rules)


#.
#   .--WATO Modes----------------------------------------------------------.
#   |      __        ___  _____ ___    __  __           _                  |
#   |      \ \      / / \|_   _/ _ \  |  \/  | ___   __| | ___  ___        |
#   |       \ \ /\ / / _ \ | || | | | | |\/| |/ _ \ / _` |/ _ \/ __|       |
#   |        \ V  V / ___ \| || |_| | | |  | | (_) | (_| |  __/\__ \       |
#   |         \_/\_/_/   \_\_| \___/  |_|  |_|\___/ \__,_|\___||___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The actual configuration modes for all rules, one rule and the       |
#   | activation of the changes.                                           |
#   '----------------------------------------------------------------------'

def mode_mkeventd_rules(phase):
    if phase == "title":
        return _("Rules for event corelation")

    elif phase == "buttons":
        home_button()
        mkeventd_changes_button()
        if config.may("mkeventd.edit"):
            html.context_button(_("New Rule"), make_link([("mode", "mkeventd_edit_rule")]), "new")
            html.context_button(_("Reset Counters"), 
              make_action_link([("mode", "mkeventd_rules"), ("_reset_counters", "1")]), "resetcounters")
        html.context_button(_("Server Status"), make_link([("mode", "mkeventd_status")]), "status")
        return

    rules = load_mkeventd_rules()

    if phase == "action":
        # Validation of input for rule simulation (no further action here)
        if html.var("simulate") or html.var("_generate"):
            event = vs_mkeventd_event.from_html_vars("event")
            vs_mkeventd_event.validate_value(event, "event")

        if html.has_var("_generate") and html.check_transaction():
            if not event.get("application"):
                raise MKUserError("event_p_application", _("Please specify an application name"))
            if not event.get("host"):
                raise MKUserError("event_p_host", _("Please specify a host name"))
            rfc = mkeventd.send_event(event)
            return None, "Test event generated and sent to Event Console.<br><pre>%s</pre>" % rfc


        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = rules[nr]
            c = wato_confirm(_("Confirm rule deletion"),
                             _("Do you really want to delete the rule <b>%s</b> <i>%s</i>?" % 
                               (rule["id"], rule.get("description",""))))
            if c:
                log_mkeventd("delete-rule", _("Deleted rule %s") % rules[nr]["id"])
                del rules[nr]
                save_mkeventd_rules(rules)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_reset_counters"):
            c = wato_confirm(_("Confirm counter reset"),
                             _("Do you really want to reset all <i>Hits</i> counters to zero?"))
            if c:
                mkeventd.query("COMMAND RESETCOUNTERS")
                log_mkeventd("counter-reset", _("Resetted all rule hit counters to zero"))
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_copy_rules"):
            c = wato_confirm(_("Confirm copying rules"),
                             _("Do you really want to copy all event rules from the master and "
                               "replace your local configuration with them?"))
            if c:
                copy_rules_from_master()
                log_mkeventd("copy-rules-from-master", _("Copied the event rules from the master "
                             "into the local configuration"))
                return None, _("Copied rules from master")
            elif c == False:
                return ""
            else:
                return

            
        if html.check_transaction():
            if html.has_var("_move"):
                from_pos = int(html.var("_move"))
                to_pos = int(html.var("_where"))
                rule = rules[from_pos]
                del rules[from_pos] # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_mkeventd_rules(rules)
                log_mkeventd("move-rule", _("Changed position of rule %s") % rule["id"])
        return

    rep_mode = mkeventd.replication_mode()
    if rep_mode in [ "sync", "takeover" ]:
        copy_url = make_action_link([("mode", "mkeventd_rules"), ("_copy_rules", "1")])
        html.show_warning(_("WARNING: This Event Console is currently running as a replication "
          "slave. The rules edited here will not be used. Instead a copy of the rules of the "
          "master are being used in the case of a takeover. The same holds for the event "
          "actions in the global settings.<br><br>If you want you can copy the ruleset of "
          "the master into your local slave configuration: ") + \
          '<a class=button href="%s">' % copy_url + 
          _("Copy Rules From Master") + '</a>')

    if len(rules) == 0:
        html.write(_("You have not created any rules yet."))
        return

    # Simulator
    event = config.load_user_file("simulated_event", {})
    html.begin_form("simulator")
    vs_mkeventd_event.render_input("event", event)
    forms.end()
    html.hidden_fields()
    html.button("simulate", _("Try out"))
    html.button("_generate", _("Generate Event!"))
    html.end_form()
    html.write("<br>")

    if html.var("simulate"):
        event = vs_mkeventd_event.from_html_vars("event")
        config.save_user_file("simulated_event", event)
    else:
        event = None

    html.write('<table class=data>')
    html.write("<tr>")
    html.write("<th>%s</th>" % _("Actions"))
    html.write("<th></th>")
    html.write("<th>%s</th>" % _("ID"))
    html.write("<th>%s</th>" % _("State"))
    html.write("<th>%s</th>" % _("Priority"))
    html.write("<th>%s</th>" % _("Facility"))
    html.write("<th>%s</th>" % _("Service Level"))
    if defaults.omd_root:
        html.write("<th>%s</th>" % _("Hits"))
    html.write("<th>%s</th>" % _("Description"))
    html.write("<th>%s</th>" % _("Text to match"))
    html.write("</tr>")

    odd = "even"
    have_match = False
    for nr, rule in enumerate(rules):
        odd = odd == "odd" and "even" or "odd"
        html.write('<tr class="data %s0">' % odd)
        delete_url = make_action_link([("mode", "mkeventd_rules"), ("_delete", nr)])
        top_url    = make_action_link([("mode", "mkeventd_rules"), ("_move", nr), ("_where", 0)])
        bottom_url = make_action_link([("mode", "mkeventd_rules"), ("_move", nr), ("_where", len(rules)-1)])
        up_url     = make_action_link([("mode", "mkeventd_rules"), ("_move", nr), ("_where", nr-1)])
        down_url   = make_action_link([("mode", "mkeventd_rules"), ("_move", nr), ("_where", nr+1)])
        edit_url   = make_link([("mode", "mkeventd_edit_rule"), ("edit", nr)])
        clone_url  = make_link([("mode", "mkeventd_edit_rule"), ("clone", nr)])
        html.write('<td class=buttons>')
        html.icon_button(edit_url, _("Edit this rule"), "edit")
        html.icon_button(clone_url, _("Create a copy of this rule"), "clone")
        html.icon_button(delete_url, _("Delete this rule"), "delete")
        if not rule is rules[0]:
            html.icon_button(top_url, _("Move this rule to the top"), "top")
            html.icon_button(up_url, _("Move this rule one position up"), "up")
        else:
            html.empty_icon_button()
            html.empty_icon_button()
 
        if not rule is rules[-1]:
            html.icon_button(down_url, _("Move this rule one position down"), "down")
            html.icon_button(bottom_url, _("Move this rule to the bottom"), "bottom")
        else:
            html.empty_icon_button()
            html.empty_icon_button()
 
        html.write('</td>')
        html.write('<td>')
        if rule.get("disabled"):
            html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
        elif event:
            result = mkeventd.event_rule_matches(rule, event)
            if type(result) != tuple:
                html.icon(_("Rule does not match: %s") % result, "rulenmatch")
            else:
                cancelling, groups = result
                if have_match:
                    msg = _("This rule matches, but is overruled by a previous match.")
                    icon = "rulepmatch"
                else:
                    if cancelling:
                        msg = _("This rule does a cancelling match.")
                    else:
                        msg = _("This rule matches.")
                    icon = "rulematch"
                    have_match = True
                if groups:
                    msg += _(" Match groups: %s") % ",".join(groups)
                html.icon(msg, icon)

        html.write('</td>')
        html.write('<td><a href="%s">%s</a></td>' % (edit_url, rule["id"]))
        if rule.get("drop"):
            html.write('<td class="state statep">%s</td>' % _("DROP"))
        else:
            html.write('<td class="state state%d">%s</td>' % (rule["state"],
              {0:_("OK"), 1:_("WARN"), 2:_("CRIT"), 3:_("UNKNOWN"), -1:_("(syslog)")}[rule["state"]]))

        # Syslog priority
        if "match_priority" in rule:
            prio_from, prio_to = rule["match_priority"]
            if prio_from == prio_to:
                prio_text = mkeventd.syslog_priorities[prio_from][1]
            else:
                prio_text = mkeventd.syslog_priorities[prio_from][1][:2] + ".." + \
                            mkeventd.syslog_priorities[prio_to][1][:2]
        else:
            prio_text = ""
        html.write("<td>%s</td>" % prio_text)

        # Syslog Facility
        if "match_facility" in rule:
            facnr = rule["match_facility"]
            html.write("<td>%s</td>" % mkeventd.syslog_facilities[facnr][1])
        else:
            html.write("<td></td>")

        html.write('<td>%s</td>' % dict(mkeventd.service_levels()).get(rule["sl"], rule["sl"]))
        if defaults.omd_root:
            hits = rule.get('hits')
            html.write('<td class=number>%s</td>' % (hits != None and hits or ''))
        html.write('<td>%s</td>' % rule.get("description"))
        html.write('<td>%s</td>' % rule.get("match"))
        html.write('</tr>\n')
    html.write('</table>')


def copy_rules_from_master():
    answer = mkeventd.query("REPLICATE 0")
    if "rules" not in answer:
        raise MKGeneralException(_("Cannot get rules from local event daemon."))
    rules = answer["rules"]
    save_mkeventd_rules(rules)


def mode_mkeventd_edit_rule(phase):
    rules = load_mkeventd_rules()
    # Links from status view refer to rule via the rule id
    if html.var("rule_id"):
        rule_id = html.var("rule_id")
        for nr, rule in enumerate(rules):
            if rule["id"] == rule_id:
                html.set_var("edit", str(nr))
                break

    edit_nr = int(html.var("edit", -1)) # missing -> new rule
    clone_nr = int(html.var("clone", -1)) # Only needed in 'new' mode
    new = edit_nr < 0

    if phase == "title":
        if new:
            return _("Create new rule")
        else:
            return _("Edit rule %s" % rules[edit_nr]["id"])

    elif phase == "buttons":
        home_button()
        mkeventd_rules_button()
        mkeventd_changes_button()
        if clone_nr >= 0:
            html.context_button(_("Clear Rule"), html.makeuri([("_clear", "1")]), "clear")
        return

    if new:
        if clone_nr >= 0 and not html.var("_clear"):
            rule = {}
            rule.update(rules[clone_nr])
        else:
            rule = {}
    else:
        rule = rules[edit_nr]

    if phase == "action":
        if not html.check_transaction():
            return "mkeventd_rules"

        if not new:
            old_id = rule["id"]
        rule = vs_mkeventd_rule.from_html_vars("rule")
        vs_mkeventd_rule.validate_value(rule, "rule")
        if not new and old_id != rule["id"]:
            raise MKUserError("rule_p_id", 
                 _("It is not allowed to change the ID of an existing rule."))
        elif new:
            for r in rules:
                if r["id"] == rule["id"]:
                    raise MKUserError("rule_p_id", _("A rule with this ID already exists."))

        try:
            num_groups = re.compile(rule["match"]).groups
        except:
            raise MKUserError("rule_p_match",
                _("Invalid regular expression"))
        if num_groups > 9:
            raise MKUserError("rule_p_match", 
                    _("You matching text has too many regular expresssion subgroups. "
                      "Only nine are allowed."))

        if "count" in rule and "expect" in rule:
            raise MKUserError("rule_p_expect_USE", _("You cannot use counting and expecting "
                     "at the same time in the same rule."))

        if "expect" in rule and "delay" in rule:
            raise MKUserError("rule_p_expect_USE", _("You cannot use expecting and delay "
                     "at the same time in the same rule, sorry."))

        # Make sure that number of group replacements do not exceed number
        # of groups in regex of match
        num_repl = 9
        while num_repl > num_groups:
            repl = "\\%d" % num_repl
            for name, value in rule.items():
                if name.startswith("set_") and type(value) in [ str, unicode ]:
                    if repl in value:
                        raise MKUserError("rule_p_" + name,
                            _("You are using the replacment reference <tt>\%d</tt>, "
                              "but your match text has only %d subgroups." % (
                                num_repl, num_groups)))
            num_repl -= 1


        if new and clone_nr >= 0:
            rules[clone_nr:clone_nr] = [ rule ]
        elif new:
            rules = [ rule ] + rules
        else:
            rules[edit_nr] = rule

        save_mkeventd_rules(rules)
        if new:
            log_mkeventd("new-rule", _("Created new event corelation rule with id %s" % rule["id"]))
        else:
            log_mkeventd("edit-rule", _("Modified event corelation rule %s" % rule["id"]))
            # Reset hit counters of this rule
            mkeventd.query("COMMAND RESETCOUNTERS;" + rule["id"])
        return "mkeventd_rules"


    html.begin_form("rule")
    vs_mkeventd_rule.render_input("rule", rule)
    vs_mkeventd_rule.set_focus("rule")
    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def mkeventd_reload():
    mkeventd.query("COMMAND RELOAD")
    try:
        os.remove(log_dir + "mkeventd.log")
    except OSError:
        pass # ignore not existing logfile
    log_audit(None, "mkeventd-activate", _("Activated changes of event console configuration"))

# This hook is executed when one applies the pending configuration changes
# related to the mkeventd via WATO on the local system. The hook is called
# without parameters.
def call_hook_mkeventd_activate_changes():
    if hooks.registered('mkeventd-activate-changes'):
        hooks.call("mkeventd-activate-changes")

def mode_mkeventd_changes(phase):
    if phase == "title":
        return _("Event Console - Pending Changes")

    elif phase == "buttons":
        home_button()
        mkeventd_rules_button()
        if config.may("mkeventd.activate") and parse_audit_log("mkeventd") and mkeventd.daemon_running():
            html.context_button(_("Activate Changes!"),
                    html.makeactionuri([("_activate", "now")]), "apply", hot=True)

    elif phase == "action":
        if html.check_transaction():
            mkeventd_reload()
            call_hook_mkeventd_activate_changes()
            return "mkeventd_rules", _("Changes successfully activated.")

    else:
        if not mkeventd.daemon_running():
            warning = _("The Event Console Daemon is currently not running. ")
            if defaults.omd_root:
                warning += _("Please make sure that you have activated it with <tt>omd config set MKEVENTD on</tt> "
                             "before starting this site.")
            html.show_warning(warning)
        entries = parse_audit_log("mkeventd")
        if entries:
            render_audit_log(entries, "pending", hilite_others=True)
        else:
            html.write("<div class=info>" + _("There are no pending changes.") + "</div>")

def log_mkeventd(what, message):
    log_entry(None, what, message, "audit.log")    # central WATO audit log
    log_entry(None, what, message, "mkeventd.log")  # pending changes for mkeventd

def mkeventd_changes_button():
    pending = parse_audit_log("mkeventd")
    if len(pending) > 0:
        buttontext = "<b>%d " % len(pending) + _("Changes")  + "</b>"
        hot = True
        icon = "mkeventd"
    else:
        buttontext = _("No Changes")
        hot = False
        icon = "mkeventd"
    html.context_button(buttontext, make_link([("mode", "mkeventd_changes")]), icon, hot)

def mkeventd_rules_button():
    html.context_button(_("All Rules"), make_link([("mode", "mkeventd_rules")]), "back")

def mode_mkeventd_status(phase):
    if phase == "title":
        return _("Event Console - Server Status")

    elif phase == "buttons":
        home_button()
        mkeventd_rules_button()
        return
    
    elif phase == "action":
        if config.may("mkeventd.switchmode"):
            if html.has_var("_switch_sync"):
                new_mode = "sync"
            else:
                new_mode = "takeover"
            c = wato_confirm(_("Confirm switching replication mode"),
                    _("Do you really want to switch the event daemon to %s mode?" % 
                        new_mode))
            if c:
                mkeventd.query("COMMAND SWITCHMODE;%s" % new_mode)
                log_audit(None, "mkeventd-switchmode", _("Switched replication slave mode to %s" % new_mode))
                return None, _("Switched to %s mode") % new_mode
            elif c == False:
                return ""
            else:
                return

        return
                
    if not mkeventd.daemon_running():
        warning = _("The Event Console Daemon is currently not running. ")
        if defaults.omd_root:
            warning += _("Please make sure that you have activated it with <tt>omd config set MKEVENTD on</tt> "
                         "before starting this site.")
        html.show_warning(warning)
        return

    response = mkeventd.query("GET status")
    status = dict(zip(response[0], response[1]))
    repl_mode = status["status_replication_slavemode"]
    html.write("<h3>%s</h3>" % _("Current Server Status"))
    html.write("<ul>")
    html.write("<li>%s</li>" % _("Event Daemon is running."))
    html.write("<li>%s: <b>%s</b></li>" % (_("Current replication mode"), 
        { "sync" : _("synchronize"),
          "takeover" : _("Takeover!"),
        }.get(repl_mode, _("master / standalone"))))
    if repl_mode in [ "sync", "takeover" ]:
        html.write(("<li>" + _("Status of last synchronization: <b>%s</b>") + "</li>") % (
                status["status_replication_success"] and _("Success") or _("Failed!")))
        last_sync = status["status_replication_last_sync"]
        if last_sync:
            html.write("<li>" + _("Last successful sync %d seconds ago.") % (time.time() - last_sync) + "</li>")
        else:
            html.write(_("<li>No successful synchronization so far.</li>"))

    html.write("</ul>")
    
    if config.may("mkeventd.switchmode"):
        html.begin_form("switch")
        if repl_mode == "sync":
            html.button("_switch_takeover", _("Switch to Takeover mode!"))
        elif repl_mode == "takeover":
            html.button("_switch_sync", _("Switch back to sync mode!"))
        html.hidden_fields()
        html.end_form()
    


if mkeventd_enabled:
    modes["mkeventd_rules"]     = (["mkeventd.edit"], mode_mkeventd_rules)
    modes["mkeventd_edit_rule"] = (["mkeventd.edit"], mode_mkeventd_edit_rule)
    modes["mkeventd_changes"]   = (["mkeventd.edit"], mode_mkeventd_changes)
    modes["mkeventd_status"]    = ([], mode_mkeventd_status)
    


#.
#   .--Permissions---------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declaration of Event Console specific permissions for Multisite      |
#   '----------------------------------------------------------------------'

if mkeventd_enabled:
    config.declare_permission_section("mkeventd", _("Event Console"))

    config.declare_permission("mkeventd.edit",
       _("Configuration of event rules"),
       _("This permission allows the creation, modification and "
         "deletion of event corelation rules."),
         ["admin"])

    config.declare_permission("mkeventd.activate",
       _("Activate changes for event console"),
       _("Activation of changes for the event console (rule modification, "
         "global settings) is done separately from the monitoring configuration "
         "and needs this permission."),
         ["admin"])

    config.declare_permission("mkeventd.switchmode",
       _("Switch slave replication mode"),
       _("This permission is only useful if the Event Console is setup as a replication "
         "slave. It allows a manual switch between sync and takeover mode."),
         ["admin"])

    modules.append(
      ( "mkeventd_rules",  _("Event Console"), "mkeventd", "mkeventd.edit",
      _("Manage event classification and corelation rules for the "
        "event console")))


#.
#   .--Settings & Rules----------------------------------------------------.
#   | ____       _   _   _                       ____        _             |
#   |/ ___|  ___| |_| |_(_)_ __   __ _ ___   _  |  _ \ _   _| | ___  ___   |
#   |\___ \ / _ \ __| __| | '_ \ / _` / __|_| |_| |_) | | | | |/ _ \/ __|  |
#   | ___) |  __/ |_| |_| | | | | (_| \__ \_   _|  _ <| |_| | |  __/\__ \  |
#   ||____/ \___|\__|\__|_|_| |_|\__, |___/ |_| |_| \_\\__,_|_|\___||___/  |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Declarations for global settings of EC parameters and of a rule for  |
#   | active checks that query the EC status of a host.                    |
#   '----------------------------------------------------------------------'


if mkeventd_enabled:
    register_configvar_domain("mkeventd", config_dir, lambda msg: log_mkeventd('config-change', msg))
    group = _("Event Console")

    register_configvar(group,
        "remote_status",
        Optional(
            Tuple(
                elements = [
                  Integer(
                      title = _("Port number:"), 
                      help = _("If you are running the mkeventd as a non-root (such as in an OMD site) "
                               "please choose port number greater than 1024."),
                      minvalue = 1,
                      maxvalue = 65535,
                      default_value = 6558,
                  ),
                  Checkbox(
                      title = _("Security"),
                      label = _("allow execution of commands and actions via TCP"), 
                      help = _("Without this option the access is limited to querying the current "
                               "and historic event status."),
                      default_value = False,
                      true_label = _("allow commands"),
                      false_label = _("no commands"),
                  ),
                  Optional(
                      ListOfStrings(
                          help = _("The access to the event status via TCP will only be allowed from "
                                   "this source IP addresses"),

                          valuespec = IPv4Address(),
                          orientation = "horizontal",
                          allow_empty = False,
                      ),
                      label = _("Restrict access to the following source IP addresses"),
                      none_label = _("access unrestricted"),
                  )
                ],
            ),
            title = _("Access to event status via TCP"),
            help = _("In Multisite setups if you want <a href=\"%s\">event status checks</a> for hosts that "
                     "live on a remote site you need to activate remote access to the event status socket "
                     "via TCP. This allows to query the current event status via TCP. If you do not restrict "
                     "this to queries also event actions are possible from remote. This feature is not used "
                     "by the event status checks nor by Multisite so we propose not allowing commands via TCP."),
            none_label = _("no access via TCP"),
        ),
        domain = "mkeventd")

    register_configvar(group,
        "mkeventd_connect_timeout",
        Integer(
            title = _("Connect timeout to status socket"),
            help = _("When the Multisite GUI connects the socket of the event daemon "
                     "in order to retrieve information about current and historic events "
                     "then this timeout will be applied."),
            minvalue = 1,
            maxvalue = 120,
            default_value = 10,
            unit = "sec",
        ),
        domain = "multisite"
    )

    register_configvar(group,
        "replication",
        Optional(
            Dictionary(
                optional_keys = [ "takeover", "fallback", "disabled", "logging" ],
                elements = [
                    ( "master", 
                      Tuple(
                          title = _("Master Event Console"),
                          help = _("Specify the host name or IP address of the master Event Console that "
                                   "you want to replicate from. The port number must be the same as set "
                                   "in the master in <i>Access to event status via TCP</i>."),
                          elements = [
                              TextAscii(
                                  title = _("Hostname/IP address of Master Event Console:"),
                                  allow_empty = False,
                              ),
                              Integer(
                                  title = _("TCP Port number of status socket:"), 
                                  minvalue = 1,
                                  maxvalue = 65535,
                                  default_value = 6558,
                              ),
                          ],
                        )
                    ),
                    ( "interval",
                      Integer(
                          title = _("Replication interval"),
                          help = _("The replication will be triggered each this number of seconds"),
                          label = _("Do a replication every"),
                          unit = _("sec"),
                          minvalue = 1,
                          default_value = 10,
                      ),
                    ),
                    ( "connect_timeout",
                      Integer(
                          title = _("Connection timeout"),
                          help = _("TCP connection timeout for connecting to the master"),
                          label = _("Try bringing up TCP connection for"),
                          unit = _("sec"),
                          minvalue = 1,
                          default_value = 10,
                      ),
                    ),
                    ( "takeover", 
                      Integer(
                          title = _("Automatic takeover"),
                          help = _("If you enable this option then the slave will automatically "
                                   "takeover and enable event processing if the master is for "
                                   "the configured number of seconds unreachable."),
                          label = _("Takeover after a master downtime of"),
                          unit = _("sec"),
                          minvalue = 1,
                          default_value = 30,
                      ),
                    ),
                    ( "fallback",
                      Integer(
                          title = _("Automatic fallback"),
                          help = _("If you enable this option then the slave will automatically "
                                   "fallback from takeover mode to slavemode if the master is "
                                   "rechable again within the selected number of seconds since "
                                   "the previous unreachability (not since the takeover)"),
                          label = _("Fallback if master comes back within"),
                          unit = _("sec"),
                          minvalue = 1,
                          default_value = 60,
                      ),
                    ),
                    ( "disabled",
                      FixedValue(
                          True,
                          totext = _("Replication is disabled"),
                          title = _("Currently disable replication"),
                          help = _("This allows you to disable the replication without loosing "
                                   "your settings. If you check this box, then no replication "
                                   "will be done and the Event Console will act as its own master."),
                      ),
                    ),
                    ( "logging",
                      FixedValue(
                          True,
                          title = _("Log replication events"),
                          totext = _("logging is enabled"),
                          help = _("Enabling this option will create detailed log entries for all "
                                   "replication activities of the slave. If disabled only problems "
                                   "will be logged."),
                      ),
                    ),
                ]
            ),
            title = _("Enable replication from a master"),
        ),
        domain = "mkeventd"
    )


    
    register_configvar(group,
        "retention_interval",
        Age(title = _("State Retention Interval"),
            help = _("In this interval the event daemon will save its state "
                     "to disk, so that you won't loose your current event "
                     "state in case of a crash."),
            default_value = 60,
        ),
        domain = "mkeventd")
                
    register_configvar(group,
        "housekeeping_interval",
        Age(title = _("Housekeeping Interval"),
            help = _("From time to time the eventd checks for messages that are expected to "
                     "be seen on a regular base, for events that time out and yet for "
                     "count periods that elapse. Here you can specify the regular interval "
                     "for that job."),
            default_value = 60,
        ),
        domain = "mkeventd")

    register_configvar(group,
        "statistics_interval",
        Age(title = _("Statistics Interval"),
            help = _("The event daemon keeps statistics about the rate of messages, events "
                     "rule hits, and other stuff. These values are updated in the interval "
                     "configured here and are available in the sidebar snapin <i>Event Console "
                     "Performance</i>"),
            default_value = 5,
        ),
        domain = "mkeventd")

    register_configvar(group,
        "debug_rules",
        Checkbox(title = _("Debug rule execution"),
                 label = _("enable extensive rule logging"),
                 help = _("This option turns on logging the execution of rules. For each message received "
                          "the execution details of each rule are logged. This creates an immense "
                          "volume of logging and should never be used in productive operation."),
                default_value = False),
        domain = "mkeventd")

    register_configvar(group,
        "rule_optimizer",
        Checkbox(title = _("Optimize rule execution"),
                 label = _("enable optimized rule execution"),
                 help = _("This option turns on a faster algorithm for matching events to rules. "),
                default_value = True),
        domain = "mkeventd")

    register_configvar(group,
        "log_rulehits",
        Checkbox(title = _("Log rule hits"),
                 label = _("Log hits for rules in log of mkeventd"),
                 help = _("If you enable this option then every time an event matches a rule "
                          "(by normal hit, cancelling, counting or dropping) a log entry will be written "
                          "into the log file of the mkeventd. Please be aware that this might lead to "
                          "a large number of log entries. "),
                default_value = False),
        domain = "mkeventd")


    register_configvar(group,
        "debug_mkeventd_queries",
        Checkbox(title = _("Debug queries to mkeventd"),
                 label = _("enable debugging of queries"),
                 help = _("With this option turned on all queries made to the event daemon "
                          "will be displayed."),
                default_value = False),
        domain = "multisite")
    
    register_configvar(group,
        "mkeventd_pprint_rules",
        Checkbox(title = _("Pritty-Print rules in configuration file"),
                 label = _("enable pritty-printing of rules"),
                 help = _("When the WATO module of the Event Console saves rules to the file "
                          "<tt>mkeventd.d/wato/rules.mk</tt> it usually prints the Python "
                          "representation of the rules-list into one single line by using the "
                          "native Python code generator. Enabling this option switches to <tt>pprint</tt>, "
                          "which nicely indents everything. While this is a bit slower for large "
                          "rulesets it makes debugging and manual editing simpler."),
                default_value = False),
        domain = "multisite")
    

    register_configvar(group,
        "actions",
        vs_mkeventd_actions,
        domain = "mkeventd",
        allow_reset = False)

    register_configvar(group,
        "history_rotation",
        DropdownChoice(
            title = _("Event history logfile rotation"),
            help = _("Specify at which time period a new file for the event history will be created."),
            choices = [
                ( "daily", _("daily")),
                ( "weekly", _("weekly"))
            ],
            default_value = "daily",
            ),
        domain = "mkeventd")

    register_configvar(group,
        "history_lifetime",
        Integer(
            title = _("Event history lifetime"),
            help = _("After this number of days old logfile of event history "
                     "will be deleted."),
            default_value = 365,
            unit = _("days"),
            minvalue = 1,
        ),
        domain = "mkeventd")

    register_configvar(group,
        "socket_queue_len",
        Integer(
            title = _("Max. number of pending connections to the status socket"),
            help = _("When the Multisite GUI or the active check check_mkevents connects "
                     "to the socket of the event daemon in order to retrieve information "
                     "about current and historic events then its connection request might "
                     "be queued before being processed. This setting defines the number of unaccepted "
                     "connections to be queued before refusing new connections."),
            minvalue = 1,
            default_value = 10,
            label = "max.",
            unit = "pending connections",
        ),
        domain = "mkeventd"
    )

    register_configvar(group,
        "eventsocket_queue_len",
        Integer(
            title = _("Max. number of pending connections to the event socket"),
            help = _("The event socket is an alternative way for sending events "
                     "to the Event Console. It is used by the Check_MK logwatch check "
                     "when forwarding log messages to the Event Console. "
                     "This setting defines the number of unaccepted "
                     "connections to be queued before refusing new connections."),
            minvalue = 1,
            default_value = 10,
            label = "max.",
            unit = "pending connections",
        ),
        domain = "mkeventd"
    )

# Settings that should also be avaiable on distributed Sites that
# do not run an own eventd but want to query one or send notifications
# to one.
group = _("Notification") 
register_configvar(group,
    "mkeventd_notify_contactgroup",
    GroupSelection(
        "contact",
        title = _("Send notifications to Event Console"),
        no_selection = _("(don't send notifications to Event Console)"),
        label = _("send notifications of contactgroup:"),
        help = _("If you select a contact group here, then all notifications of "
                 "hosts and services in that contact group will be sent to the "
                 "event console. <b>Note</b>: you still need to create a rule "
                 "matching those messages in order to have events created."),
        default_value = '',

    ),
    domain = "multisite",
    need_restart = True)

register_configvar(group,
    "mkeventd_notify_facility",
    DropdownChoice(
        title = _("Syslog facility for Event Console notifications"),
        help = _("When sending notifications from the monitoring system to the event console "
                 "the following syslog facility will be set for these messages. Choosing "
                 "a unique facility makes creation of rules easier."),
        choices = mkeventd.syslog_facilities,
        default_value = 16, # local0
    ),
    domain = "multisite",
    need_restart = True)

register_configvar(group,
    "mkeventd_notify_remotehost",
    Optional(
        TextAscii(
            title = _("Host running Event Console")
        ),
        title = _("Forward notifications to remote host"),
        help = _("This will send the notification to a Check_MK Event Console on a remote host "
                 "by using syslog. <b>Note</b>: this setting will only be applied if no Event "
                 "Console is running locally in this site! That way you can use the same global "
                 "settings on your central and decentralized system and makes distributed WATO " 
                 "easier. Please also make sure that <b>Send notifications to Event Console</b> "
                 "is enabled."),
        label = _("Send to remote Event Console via syslog"),
        none_label = _("Do not send to remote host"),
    ),
    domain = "multisite",
    need_restart = True)

register_configvar(group,
    "mkeventd_service_levels",
    ListOf(
        Tuple(
            elements = [
                Integer(
                    title = _("internal ID"),
                    minvalue = 0,
                    maxvalue = 100,
                ),
                TextUnicode(
                    title = _("Name / Description"),
                    allow_empty = False,
                ),
            ],
            orientation = "horizontal",
        ),
        title = _("Service Levels for Event Console"),
        help = _("Here you can configure the list of possible service levels for an "
                 "event. Each event rule selects a service level. Internally the level is "
                 "represented as an integer number. Note: a higher number represents "
                 "a higher service level. This is important when filtering views "
                 "after the service level.<p>You can also attach service levels to hosts "
                 "and services in the monitoring. These levels will then be sent to the "
                 "Event Console when you forward notifications to it and will override the "
                 "setting of the matching rule."),
        allow_empty = False,
        default_value = [ (0, _("(no service level)")) ],
    ),
    domain = "multisite",
    allow_reset = False,
)


register_rulegroup("eventconsole",
    _("Event Console"),
    _("Settings and Checks dealing with the Check_MK Event Console"))
group = "eventconsole"


register_rule(
    group, 
    "active_checks:mkevents",
    Dictionary(
        title = _("Check event state in Event Console"),
        help = _("This check is part of the Check_MK Event Console and will check "
         "if there are any open events for a certain host (and maybe a certain "
         "application on that host. The state of the check will reflect the status "
         "of the worst open event for that host."),
        elements = [
            ( "hostspec",
              OptionalDropdownChoice(
                title = _("Host specification"),
                help = _("When quering the event status you can either use the monitoring "
                   "host name, the IP address or a custom host name for referring to a "
                   "host. This is needed in cases where the event source (syslog, snmptrapd) "
                   "do not send a host name that matches the monitoring host name."),
                choices = [
                    ( '$HOSTNAME$', _("Monitoring Host name") ),
                    ( '$HOSTADDRESS$', _("Host IP Address" ) ) ],
                otherlabel = _("Specify explicitly"),
                explicit = TextAscii(allow_empty = False),
                default_value = '$HOSTNAME$',
              )
            ),
            ( "application",
              RegExp(
                title = _("Application (regular expression)"),
                help = _("If you enter an application name here then only "
                   "events for that application name are counted. You enter "
                   "a regular expression here that must match a <b>part</b> "
                   "of the application name. Use anchors <tt>^</tt> and <tt>$</tt> "
                   "if you need a complete match."),
                allow_empty = False,
              )
            ),
            ( "ignore_acknowledged",
              FixedValue(
                  True,
                  title = _("Ignore Acknowledged Events"),
                  help = _("If you check this box then only open events are honored when "
                           "determining the event state. Acknowledged events are displayed "
                           "(i.e. their count) but not taken into account."),
                  totext = _("acknowledged events will not be honored"),
                 ) 
            ),
            ( "remote",
              Alternative(
                  title = _("Access to the Event Console"),
                  elements = [
                      Tuple(
                          elements = [
                              TextAscii(
                                  title = _("Hostname/IP address of Event Console:"),
                                  allow_empty = False,
                              ),
                              Integer(
                                  title = _("TCP Port number:"), 
                                  minvalue = 1,
                                  maxvalue = 65535,
                                  default_value = 6558,
                              ),
                          ],
                          title = _("Access via TCP"),
                          help = _("In a distributed setup where the Event Console is not running in the same "
                                   "site as the host is monitored you need to access the remote Event Console "
                                   "via TCP. Please make sure that this is activated in the global settings of "
                                   "the event console. The default port number is 6558."),
                      ), 
                      TextAscii(
                          title = _("Access via UNIX socket"),
                          allow_empty = False,
                          size = 64,
                      ),

                 ],
                 default_value = defaults.omd_root 
                      and defaults.omd_root + "/tmp/run/mkeventd/status" 
                      or defaults.livestatus_unix_socket.split("/",1)[0] + "/mkeventd/status"
            )
          ),
        ],
        optional_keys = [ "application", "remote", "ignore_acknowledged" ],
    ),
    match = 'all',
)

sl_help = _("This rule set is useful if you send your monitoring notifications "
            "into the Event Console. A service level set by this rule will be "
            "used as the service level of the resulting event in the Event Console.")

register_rule(
    group,
    "extra_host_conf:_ec_sl",
    DropdownChoice(
       title = _("Service Level of hosts"),
       help = sl_help,
       choices = mkeventd.service_levels,
    ),
    match = 'first',
)
    
register_rule(
    group,
    "extra_service_conf:_ec_sl",
    DropdownChoice(
       title = _("Service Level of services"),
       help = sl_help + _(" Note: if no service level is configured for a service "
        "then that of the host will be used instead (if configured)."),
       choices = mkeventd.service_levels,
    ),
    itemtype = 'service',
    match = 'first',
)

contact_help = _("This rule set is useful if you send your monitoring notifications "
                 "into the Event Console. The contact information that is set by this rule "
                 "will be put into the resulting event in the Event Console.")
contact_regex = r"^[^;'$|]*$"
contact_regex_error = _("The contact information must not contain one of the characters <tt>;</tt> <tt>'</tt> <tt>|</tt> or <tt>$</tt>")

register_rule(
    group,
    "extra_host_conf:_ec_contact",
    TextUnicode(
        title = _("Host contact information"),
        help = contact_help,
        size = 80,
        regex = contact_regex,
        regex_error = contact_regex_error,
    ),
    match = 'first',
)

register_rule(
    group,
    "extra_service_conf:_ec_contact",
    TextUnicode(
        title = _("Service contact information"),
        help = contact_help + _(" Note: if no contact information is configured for a service "
                       "then that of the host will be used instead (if configured)."),
        size = 80,
        regex = contact_regex,
        regex_error = contact_regex_error,
    ),
    itemtype = 'service',
    match = 'first',
)
#.
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Stuff for sending monitoring notifications into the event console.   |
#   '----------------------------------------------------------------------'
def mkeventd_update_notifiation_configuration(hosts):
    try:
        contactgroup = config.mkeventd_notify_contactgroup
    except:
        contactgroup = None

    try:
        facility = config.mkeventd_notify_facility
    except:
        facility = 16

    try:
        remote_console = config.mkeventd_notify_remotehost
    except:
        remote_console = None
    if not remote_console:
        remote_console = ""

    path = defaults.nagios_conf_dir + "/mkeventd_notifications.cfg"
    if not contactgroup and os.path.exists(path):
        os.remove(path)
    elif contactgroup:
        file(path, "w").write("""# Created by Check_MK Event Console
# This configuration will send notifications about hosts and
# services in the contact group '%(group)s' to the Event Console.

define contact {
    contact_name                   mkeventd
    alias                          "Notifications for Check_MK Event Console"
    contactgroups                  %(group)s
    host_notification_commands     mkeventd-notify-host
    service_notification_commands  mkeventd-notify-service
    host_notification_options      d,u,r
    service_notification_options   c,w,u,r
    host_notification_period       24X7
    service_notification_period    24X7
    email                          none
}

define command {
    command_name                   mkeventd-notify-host
    command_line                   mkevent -n %(facility)s '%(remote)s' $HOSTSTATEID$ '$HOSTNAME$' '' '$HOSTOUTPUT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$' 
}

define command {
    command_name                   mkeventd-notify-service
    command_line                   mkevent -n %(facility)s '%(remote)s' $SERVICESTATEID$ '$HOSTNAME$' '$SERVICEDESC$' '$SERVICEOUTPUT$' '$_SERVICEEC_SL$' '$_SERVICEEC_CONTACT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$' 
}
""" % { "group" : contactgroup, "facility" : facility, "remote" : remote_console })

api.register_hook("pre-activate-changes", mkeventd_update_notifiation_configuration)

# Only register the reload hook when mkeventd is enabled
if mkeventd_enabled:
    api.register_hook("activate-changes", lambda hosts: mkeventd_reload())

