#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

# WATO-Module for the rules and aggregations of Check_MK BI

# We need to replace the BI constants internally with something
# that we can replace back after writing the BI-Rules out
# with pprint.pformat
#   .--Base class----------------------------------------------------------.
#   |             ____                        _                            |
#   |            | __ )  __ _ ___  ___    ___| | __ _ ___ ___              |
#   |            |  _ \ / _` / __|/ _ \  / __| |/ _` / __/ __|             |
#   |            | |_) | (_| \__ \  __/ | (__| | (_| \__ \__ \             |
#   |            |____/ \__,_|___/\___|  \___|_|\__,_|___/___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'

class ModeBI(WatoMode):

    # .--------------------------------------------------------------------.
    # | Initialization and default modes                                   |
    # '--------------------------------------------------------------------'
    def __init__(self):
        WatoMode.__init__(self)
        self._bi_constants = {
            'ALL_HOSTS'          : 'ALL_HOSTS-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HOST_STATE'         : 'HOST_STATE-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HIDDEN'             : 'HIDDEN-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_HOST'       : 'FOREACH_HOST-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_CHILD'      : 'FOREACH_CHILD-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_CHILD_WITH' : 'FOREACH_CHILD_WITH-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_PARENT'     : 'FOREACH_PARENT-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_SERVICE'    : 'FOREACH_SERVICE-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'REMAINING'          : 'REMAINING-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'DISABLED'           : 'DISABLED-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HARD_STATES'        : 'HARD_STATES-f41e728b-0bce-40dc-82ea-51091d034fc3',
        }
        self.load_config()
        self.create_valuespecs()


    def title(self):
        return _("Business Intelligence")


    def buttons(self):
        home_button()


    # .--------------------------------------------------------------------.
    # | Loading and saving                                                 |
    # '--------------------------------------------------------------------'
    def load_config(self):
        filename = multisite_dir + "bi.mk"
        try:
            vars = { "aggregation_rules" : {},
                     "aggregations"      : [],
                     "host_aggregations" : [],
                   }
            vars.update(self._bi_constants)
            if os.path.exists(filename):
                execfile(filename, vars, vars)
            else:
                exec(bi_example, vars, vars)

            # Convert rules from old-style tuples to new-style dicts
            self._aggregation_rules = {}
            for ruleid, rule in vars["aggregation_rules"].items():
                self._aggregation_rules[ruleid] = self.convert_rule_from_bi(rule, ruleid)

            self._aggregations = []
            for aggregation in vars["aggregations"]:
                self._aggregations.append(self.convert_aggregation_from_bi(aggregation, single_host = False))
            for aggregation in vars["host_aggregations"]:
                self._aggregations.append(self.convert_aggregation_from_bi(aggregation, single_host = True))

        except Exception, e:
            if config.debug:
                raise

            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                              (filename, e)))


    def save_config(self):
        def replace_constants(s):
            for name, uuid in self._bi_constants.items():
                while True:
                    n = s.replace("'%s'" % uuid, name)
                    if n != s:
                        s = n
                    else:
                        break
            return s[0] + '\n ' + s[1:-1] + '\n' + s[-1]

        make_nagios_directory(multisite_dir)
        out = create_user_file(multisite_dir + "bi.mk", "w")
        out.write(wato_fileheader())
        for ruleid, rule in self._aggregation_rules.items():
            rule = self.convert_rule_to_bi(rule)
            out.write('aggregation_rules["%s"] = %s\n\n' %
                    ( ruleid, replace_constants(pprint.pformat(rule, width=50))))
        out.write('\n')
        for aggregation in self._aggregations:
            if aggregation["single_host"]:
                out.write("host_aggregations.append(\n")
            else:
                out.write("aggregations.append(\n")
            out.write(replace_constants(pprint.pformat(self.convert_aggregation_to_bi(aggregation))))
            out.write(")\n")

        # Make sure that BI aggregates are replicated to all other sites that allow
        # direct user login
        update_login_sites_replication_status()


    def convert_aggregation_to_bi(self, aggr):
        if len(aggr["groups"]) == 1:
            conv = (aggr["groups"][0],)
        else:
            conv = (aggr["groups"],)
        node = self.convert_node_to_bi(aggr["node"])
        convaggr = conv + node
        if aggr["hard_states"]:
            convaggr = (self._bi_constants["HARD_STATES"],) + convaggr
        if aggr["disabled"]:
            convaggr = (self._bi_constants["DISABLED"],) + convaggr
        return convaggr


    def convert_node_to_bi(self, node):
        if node[0] == "call":
            return node[1]
        elif node[0] == "host":
            return (node[1][0], self._bi_constants['HOST_STATE'])
        elif node[0] == "remaining":
            return (node[1][0], self._bi_constants['REMAINING'])
        elif node[0] == "service":
            return node[1]
        elif node[0] == "foreach_host":
            what = node[1][0]

            tags = node[1][1]
            if node[1][2]:
                hostspec = node[1][2]
            else:
                hostspec = self._bi_constants['ALL_HOSTS']

            if type(what == tuple) and what[0] == 'child_with':
                child_conditions = what[1]
                what             = what[0]
                child_tags       = child_conditions[0]
                child_hostspec   = child_conditions[1] and child_conditions[1] or self._bi_constants['ALL_HOSTS']
                return (self._bi_constants["FOREACH_" + what.upper()], child_tags, child_hostspec, tags, hostspec) \
                       + self.convert_node_to_bi(node[1][3])
            else:
                return (self._bi_constants["FOREACH_" + what.upper()], tags, hostspec) + self.convert_node_to_bi(node[1][3])
        elif node[0] == "foreach_service":
            tags = node[1][0]
            if node[1][1]:
                spec = node[1][1]
            else:
                spec = self._bi_constants['ALL_HOSTS']
            service = node[1][2]
            return (self._bi_constants["FOREACH_SERVICE"], tags, spec, service) + self.convert_node_to_bi(node[1][3])


    def convert_aggregation_from_bi(self, aggr, single_host):
        if aggr[0] == self._bi_constants["DISABLED"]:
            disabled = True
            aggr = aggr[1:]
        else:
            disabled = False

        if aggr[0] == self._bi_constants["HARD_STATES"]:
            hard_states = True
            aggr = aggr[1:]
        else:
            hard_states = False

        if type(aggr[0]) != list:
            groups = [aggr[0]]
        else:
            groups = aggr[0]
        node = self.convert_node_from_bi(aggr[1:])
        return {
            "disabled"    : disabled,
            "hard_states" : hard_states,
            "groups"      : groups,
            "node"        : node,
            "single_host" : single_host,
        }

    # Make some conversions so that the format of the
    # valuespecs is matched
    def convert_rule_from_bi(self, rule, ruleid):
        if type(rule) == tuple:
            rule = {
                "title"       : rule[0],
                "params"      : rule[1],
                "aggregation" : rule[2],
                "nodes"       : rule[3],
            }
        crule = {}
        crule.update(rule)
        crule["nodes"] = map(self.convert_node_from_bi, rule["nodes"])
        parts = rule["aggregation"].split("!")
        crule["aggregation"] = (parts[0], tuple(map(tryint, parts[1:])))
        crule["id"] = ruleid
        return crule

    def convert_rule_to_bi(self, rule):
        brule = {}
        brule.update(rule)
        if "id" in brule:
            del brule["id"]
        brule["nodes"] = map(self.convert_node_to_bi, rule["nodes"])
        brule["aggregation"] = "!".join(
                    [ rule["aggregation"][0] ] + map(str, rule["aggregation"][1]))
        return brule


    # Convert node-Tuple into format used by CascadingDropdown
    def convert_node_from_bi(self, node):
        if len(node) == 2:
            if type(node[1]) == list:
                return ("call", node)
            elif node[1] == self._bi_constants['HOST_STATE']:
                return ("host", (node[0],))
            elif node[1] == self._bi_constants['REMAINING']:
                return ("remaining", (node[0],))
            else:
                return ("service", node)

        else: # FOREACH_...

            foreach_spec = node[0]
            if foreach_spec == self._bi_constants['FOREACH_CHILD_WITH']:
                # extract the conditions meant for matching the childs
                child_conditions = list(node[1:3])
                if child_conditions[1] == self._bi_constants['ALL_HOSTS']:
                    child_conditions[1] = None
                node = node[0:1] + node[3:]

            # Extract the list of tags
            if type(node[1]) == list:
                tags = node[1]
                node = node[0:1] + node[2:]
            else:
                tags = []

            hostspec = node[1]
            if hostspec == self._bi_constants['ALL_HOSTS']:
                hostspec = None

            if foreach_spec == self._bi_constants['FOREACH_SERVICE']:
                service = node[2]
                subnode = self.convert_node_from_bi(node[3:])
                return ("foreach_service", (tags, hostspec, service, subnode))
            else:

                subnode = self.convert_node_from_bi(node[2:])
                if foreach_spec == self._bi_constants['FOREACH_HOST']:
                    what = "host"
                elif foreach_spec == self._bi_constants['FOREACH_CHILD']:
                    what = "child"
                elif foreach_spec == self._bi_constants['FOREACH_CHILD_WITH']:
                    what = ("child_with", child_conditions)
                elif foreach_spec == self._bi_constants['FOREACH_PARENT']:
                    what = "parent"
                return ("foreach_host", (what, tags, hostspec, subnode))



    # .--------------------------------------------------------------------.
    # | Valuespecs                                                         |
    # '--------------------------------------------------------------------'

    def create_valuespecs(self):
        self._vs_call_rule = self.vs_call_rule()
        self._vs_host_re = self.vs_host_re()
        self._vs_node = self.vs_node()
        self._vs_aggregation = self.vs_aggregation()


    def rule_choices(self):
        return [
           (key, key + " - " + rule["title"])
           for (key, rule)
           in self._aggregation_rules.items() ]



    def validate_rule_call(self, value, varprefix):
        rule_id, arguments = value
        rule_params = self._aggregation_rules[rule_id]['params']

        if len(arguments) != len(rule_params):
            raise MKUserError(varprefix + "_1_0", _("The rule you selected needs %d argument(s) (%s), "
                                           "but you configured %d arguments.") %
                                    (len(rule_params), ', '.join(rule_params), len(arguments)))


    def vs_call_rule(self):
        return Tuple(
            elements = [
                DropdownChoice(
                    title = _("Rule:"),
                    choices = self.rule_choices(),
                    sorted = True,
                ),
                ListOfStrings(
                    orientation = "horizontal",
                    size = 12,
                    title = _("Arguments:"),
                ),
            ],
            validate = lambda v, vp: self.validate_rule_call(v, vp),
        )


    def vs_host_re(self):
        host_re_help = _("Either an exact host name or a regular expression exactly matching the host "
                         "name. Example: <tt>srv.*p</tt> will match <tt>srv4711p</tt> but not <tt>xsrv4711p2</tt>. ")
        return TextUnicode(
            title = _("Host:"),
            help = host_re_help,
            allow_empty = False,
        )


    def node_call_choices(self):
        # Configuration of explicit rule call
        return [ ( "call", _("Call a Rule"), self._vs_call_rule ), ]


    # Configuration of FOREACH_...-type nodes
    def foreach_choices(self, subnode_choices):
        return [
          ( "foreach_host", _("Create nodes based on a host search"),
             Tuple(
                 elements = [
                    CascadingDropdown(
                        title = _("Refer to:"),
                        choices = [
                            ( 'host',       _("The found hosts themselves") ),
                            ( 'child',      _("The found hosts' childs") ),
                            ( 'child_with', _("The found hosts' childs (with child filtering)"),
                                Tuple(elements = [
                                    HostTagCondition(
                                        title = _("Child Host Tags:")
                                    ),
                                    OptionalDropdownChoice(
                                        title = _("Child Host Name:"),
                                        choices = [
                                            ( None, _("All Hosts")),
                                        ],
                                        explicit = TextAscii(size = 60),
                                        otherlabel = _("Regex for host name"),
                                        default_value = None,
                                    ),
                                ]),
                            ),
                            ( 'parent',     _("The found hosts' parents") ),
                        ],
                        help = _('When selecting <i>The found hosts\' childs</i>, the conditions '
                          '(tags and host name) are used to match a host, but you will get one '
                          'node created for each child of the matched host. The '
                          'place holder <tt>$1$</tt> contains the name of the found child.<br><br>'
                          'When selecting <i>The found hosts\' parents</i>, the conditions '
                          '(tags and host name) are used to match a host, but you will get one '
                          'node created for each of the parent hosts of the matched host. '
                          'The place holder <tt>$1$</tt> contains the name of the child host '
                          'and <tt>$2$</tt> the name of the parent host.'),
                    ),
                    HostTagCondition(
                        title = _("Host Tags:")
                    ),
                    OptionalDropdownChoice(
                        title = _("Host Name:"),
                        choices = [
                            ( None, _("All Hosts")),
                        ],
                        explicit = TextAscii(size = 60),
                        otherlabel = _("Regex for host name"),
                        default_value = None,
                        help = _("If you choose \"Regex for host name\", you need to provide a regex "
                                 "which results in exactly one match group."),
                    ),
                    CascadingDropdown(
                        title = _("Nodes to create:"),
                        help = _("When calling a rule you can use the place holder <tt>$1$</tt> "
                                 "in the rule arguments. It will be replaced by the actual host "
                                 "names found by the search - one host name for each rule call."),
                        choices = subnode_choices,
                    ),
                 ]
            )
          ),
          ( "foreach_service", _("Create nodes based on a service search"),
             Tuple(
                 elements = [
                    HostTagCondition(
                        title = _("Host Tags:")
                    ),
                    OptionalDropdownChoice(
                        title = _("Host Name:"),
                        choices = [
                            ( None, _("All Hosts")),
                        ],
                        explicit = TextAscii(size = 60),
                        otherlabel = _("Regex for host name"),
                        default_value = None,
                    ),
                    TextAscii(
                        title = _("Service Regex:"),
                        help = _("Subexpressions enclosed in <tt>(</tt> and <tt>)</tt> will be available "
                                 "as arguments <tt>$2$</tt>, <tt>$3$</tt>, etc."),
                        size = 80,
                    ),
                    CascadingDropdown(
                        title = _("Nodes to create:"),
                        help = _("When calling a rule you can use the place holder <tt>$1$</tt> "
                                 "in the rule arguments. It will be replaced by the actual host "
                                 "names found by the search - one host name for each rule call. If you "
                                 "have regular expression subgroups in the service pattern, then "
                                 "the place holders <tt>$2$</tt> will represent the first group match, "
                                 "<tt>$3</tt> the second, and so on..."),
                        choices = subnode_choices,
                    ),
                 ]
            )
          )
        ]
    def vs_node(self):
        # Configuration of leaf nodes
        vs_node_simplechoices = [
            ( "host", _("State of a host"),
               Tuple(
                   help = _("Will create child nodes representing the state of hosts (usually the "
                            "host check is done via ping)."),
                   elements = [ self._vs_host_re, ]
               )
            ),
            ( "service", _("State of a service"),
              Tuple(
                  help = _("Will create child nodes representing the state of services."),
                  elements = [
                      self._vs_host_re,
                      TextUnicode(
                          title = _("Service:"),
                          help = _("A regular expression matching the <b>beginning</b> of a service description. You can "
                                   "use a trailing <tt>$</tt> in order to define an exact match. For each "
                                   "matching service on the specified hosts one child node will be created. "),
                      ),
                  ]
              ),
            ),
            ( "remaining", _("State of remaining services"),
              Tuple(
                  help = _("Create a child node for each service on the specified hosts that is not "
                           "contained in any other node of the aggregation."),
                  elements = [ self._vs_host_re ],
              )
            ),
        ]


        return CascadingDropdown(
           choices = vs_node_simplechoices + self.node_call_choices() \
                  + self.foreach_choices(vs_node_simplechoices + self.node_call_choices())
        )


    def aggregation_choices(self):
        choices = []
        for aid, ainfo in bi_aggregation_functions.items():
            choices.append((
                aid,
                ainfo["title"],
                ainfo["valuespec"],
            ))
        return choices


    def vs_aggregation(self):

        return Dictionary(
            title = _("Aggregation Properties"),
            optional_keys = False,
            render = "form",
            elements = [
            ( "groups",
              ListOfStrings(
                  title = _("Aggregation Groups"),
                  help = _("List of groups in which to show this aggregation. Usually "
                           "each aggregation is only in one group. Group names are arbitrary "
                           "texts. At least one group is mandatory."),
                  valuespec = TextUnicode(),
              ),
            ),
            ( "node",
              CascadingDropdown(
                  title = _("Rule to call"),
                  choices = self.node_call_choices() + self.foreach_choices(self.node_call_choices())
              )
            ),
            ( "disabled",
              Checkbox(
                  title = _("Disabled"),
                  label = _("Currently disable this aggregation"),
              )
            ),
            ( "hard_states",
              Checkbox(
                  title = _("Use Hard States"),
                  label = _("Base state computation on hard states"),
                  help = _("Hard states can only differ from soft states if at least one host or service "
                           "of the BI aggregate has more than 1 maximum check attempt. For example if you "
                           "set the maximum check attempts of a service to 3 and the service is CRIT "
                           "just since one check then it's soft state is CRIT, but its hard state is still OK."),
              )
            ),
            ( "single_host",
              Checkbox(
                  title = _("Optimization"),
                  label = _("The aggregation covers data from only one host and its parents."),
                  help = _("If you have a large number of aggregations that cover only one host and "
                           "maybe its parents (such as Check_MK cluster hosts), "
                           "then please enable this optimization. It reduces the time for the "
                           "computation. Do <b>not</b> enable this for aggregations that contain "
                           "data of more than one host!"),
              ),
            ),
          ]
        )



    # .--------------------------------------------------------------------.
    # | Methods for analysing the rules and aggregations                   |
    # '--------------------------------------------------------------------'

    def aggregation_title(self, aggregation):
        rule = self.aggregation_toplevel_rule(aggregation)
        return "%s (%s)" % (rule["title"], rule["id"])


    def aggregation_toplevel_rule(self, aggregation):
        rule_id, description = self.rule_called_by_node(aggregation["node"])
        return self._aggregation_rules[rule_id]


    # Returns the rule called by a node - if any
    # Result is a pair of the rule and a descriptive title
    def rule_called_by_node(self, node):
        if node[0] == "call":
            if node[1][1]:
                args = _("with arguments: %s") % ", ".join(node[1][1])
            else:
                args = _("without arguments")
            return node[1][0], _("Explicit call ") + args
        elif node[0] == "foreach_host":
            subnode = node[1][-1]
            if subnode[0] == 'call':
                if node[1][0] == 'host':
                    info = _("Called for all hosts...")
                elif node[1][0] == 'child':
                    info = _("Called for each child of...")
                else:
                    info = _("Called for each parent of...")
                return subnode[1][0], info
        elif node[0] == "foreach_service":
            subnode = node[1][-1]
            if subnode[0] == 'call':
                return subnode[1][0], _("Called for each service...")


    # Checks if the rule 'rule' uses either directly
    # or indirectly the rule with the id 'ruleid'. In
    # case of success, returns the nesting level
    def rule_uses_rule(self, rule, ruleid, level=0):
        for node in rule["nodes"]:
            r = self.rule_called_by_node(node)
            if r:
                ru_id, info = r
                if ru_id == ruleid: # Rule is directly being used
                    return level + 1
                # Check if lower rules use it
                else:
                    l = self.rule_uses_rule(self._aggregation_rules[ru_id], ruleid, level + 1)
                    if l:
                        return l
        return False


    def count_bi_rule_references(self, ruleid):
        aggr_refs = 0
        for aggregation in self._aggregations:
            called_rule_id, info = self.rule_called_by_node(aggregation["node"])
            if called_rule_id == ruleid:
                aggr_refs += 1

        level = 0
        rule_refs = 0
        for rid, rule in self._aggregation_rules.items():
            l = self.rule_uses_rule(rule, ruleid)
            level = max(l, level)
            if l == 1:
                rule_refs += 1

        return aggr_refs, rule_refs, level


    def aggregation_sub_rule_ids(self, rule):
        sub_rule_ids = []
        for node in rule["nodes"]:
            r = self.rule_called_by_node(node)
            if r:
                sub_rule_ids.append(r[0])
        return sub_rule_ids



    # .--------------------------------------------------------------------.
    # | Generic rendering                                                  |
    # '--------------------------------------------------------------------'

    def render_rule_tree(self, ruleid, tree_path):
        rule = self._aggregation_rules[ruleid]
        edit_url = html.makeuri([("mode", "bi_edit_rule"), ("id", ruleid)])
        title = "%s (%s)" % (rule["title"], ruleid)

        sub_rule_ids = self.aggregation_sub_rule_ids(rule)
        if not sub_rule_ids:
            html.write('<li><a href="%s">%s</a></li>' % (edit_url, title))
        else:
            html.begin_foldable_container("bi_rule_trees", tree_path, False, title,
                                          title_url=edit_url, tree_img="tree_black")
            for sub_rule_id in sub_rule_ids:
                self.render_rule_tree(sub_rule_id, tree_path + "/" + sub_rule_id)
            html.end_foldable_container()



#.
#   .--Aggregations--------------------------------------------------------.
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   '----------------------------------------------------------------------'

class ModeBIAggregations(ModeBI):
    def __init__(self):
        ModeBI.__init__(self)


    def title(self):
        return ModeBI.title(self) + " - " + _("Aggregations")


    def buttons(self):
        ModeBI.buttons(self)
        html.context_button(_("Rules"), html.makeuri([("mode", "bi_rules")]), "aggr")
        if self._aggregation_rules:
            html.context_button(_("New Aggregation"),
                  html.makeuri_contextless([("mode", "bi_edit_aggregation")]), "new")


    def action(self):
        nr = int(html.var("_del_aggr"))
        c = wato_confirm(_("Confirm aggregation deletion"),
            _("Do you really want to delete the aggregation number <b>%s</b>?") % (nr+1))
        if c:
            del self._aggregations[nr]
            log_pending(SYNC, None, "bi-delete-aggregation", _("Deleted BI aggregation number %d") % (nr+1))
            self.save_config()
        elif c == False: # not yet confirmed
            return ""


    def page(self):
        table.begin("bi_aggr", _("Aggregations"))
        for nr, aggregation in enumerate(self._aggregations):
            table.row()
            table.cell(_("Actions"), css="buttons")
            edit_url = html.makeuri([("mode", "bi_edit_aggregation"), ("id", nr)])
            html.icon_button(edit_url, _("Edit this aggregation"), "edit")
            delete_url = html.makeactionuri([("_del_aggr", nr)])
            html.icon_button(delete_url, _("Delete this aggregation"), "delete")
            table.cell(_("Nr."), nr + 1, css="number")
            table.cell("", css="buttons")
            if aggregation["disabled"]:
                html.icon(_("This aggregation is currently disabled."), "disabled")
            if aggregation["single_host"]:
                html.icon(_("This aggregation covers only data from a single host."), "host")
            table.cell(_("Groups"), ", ".join(aggregation["groups"]))
            ruleid, description = self.rule_called_by_node(aggregation["node"])
            edit_url = html.makeuri([("mode", "bi_edit_rule"), ("id", ruleid)])
            table.cell(_("Rule Tree"), css="bi_rule_tree")
            self.render_aggregation_rule_tree(aggregation)
            table.cell(_("Note"), description)
        table.end()


    def render_aggregation_rule_tree(self, aggregation):
        toplevel_rule = self.aggregation_toplevel_rule(aggregation)
        self.render_rule_tree(toplevel_rule["id"], toplevel_rule["id"])



#.
#   .--Rules---------------------------------------------------------------.
#   |                       ____        _                                  |
#   |                      |  _ \ _   _| | ___  ___                        |
#   |                      | |_) | | | | |/ _ \/ __|                       |
#   |                      |  _ <| |_| | |  __/\__ \                       |
#   |                      |_| \_\\__,_|_|\___||___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

class ModeBIRules(ModeBI):
    def __init__(self):
        ModeBI.__init__(self)
        self._view_type = html.var("view", "list")


    def title(self):
        return ModeBI.title(self) + " - " + _("Rules")


    def buttons(self):
        ModeBI.buttons(self)
        if self._view_type == "list":
            html.context_button(_("Aggregations"), html.makeuri_contextless([("mode", "bi_aggregations")]), "aggr")
            html.context_button(_("New Rule"), html.makeuri_contextless([("mode", "bi_edit_rule")]), "new")
            html.context_button(_("Unused Rules"), html.makeuri_contextless([("mode", "bi_rules"), ("view", "unused")]), "unusedbirules")

        else:
            html.context_button(_("Back"), html.makeuri([("view", "list")]), "back")


    def action(self):
        if html.var("_del_rule"):
            ruleid = html.var("_del_rule")
            c = wato_confirm(_("Confirm rule deletion"),
                _("Do you really want to delete the rule with "
                  "the id <b>%s</b>?") % ruleid)
            if c:
                del self._aggregation_rules[ruleid]
                log_pending(SYNC, None, "bi-delete-rule", _("Deleted BI rule with id %s") % ruleid)
                self.save_config()
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload

    def page(self):
        if not self._aggregations and not self._aggregation_rules:
            menu_items = [
                ("bi_edit_rule", _("Create aggregation rule"), "new", "bi_rules",
                  _("Rules are the nodes in BI aggregations. "
                    "Each aggregation has one rule as its root."))
            ]
            render_main_menu(menu_items)
            return

        if self._view_type == "list":
            self.render_rules(_("Rules"), only_unused = False)
        else:
            self.render_rules(_("Unused BI Rules"), only_unused = True)


    def render_rules(self, title, only_unused):
        aggregations_that_use_rule = self.find_aggregation_rule_usages()

        rules = self._aggregation_rules.items()
        # Sort rules according to nesting level, and then to id
        rules_refs = [ (ruleid, rule, self.count_bi_rule_references(ruleid))
                       for (ruleid, rule) in rules ]
        rules_refs.sort(cmp = lambda a,b: cmp(a[2][2], b[2][2]) or cmp(a[1]["title"], b[1]["title"]))

        table.begin("bi_rules", title)
        for ruleid, rule, (aggr_refs, rule_refs, level) in rules_refs:
            refs = aggr_refs + rule_refs
            if not only_unused or refs == 0:
                table.row()
                table.cell(_("Actions"), css="buttons")
                edit_url = html.makeuri_contextless([("mode", "bi_edit_rule"), ("id", ruleid)])
                html.icon_button(edit_url, _("Edit this rule"), "edit")
                if rule_refs == 0:
                    tree_url = html.makeuri([("mode", "bi_rule_tree"), ("id", ruleid)])
                    html.icon_button(tree_url, _("This is a top-level rule. Show rule tree"), "bitree")
                if refs == 0:
                    delete_url = html.makeactionuri([("mode", "bi_rules"), ("_del_rule", ruleid)])
                    html.icon_button(delete_url, _("Delete this rule"), "delete")
                table.cell(_("Level"), level or "", css="number")
                table.cell(_("ID"), '<a href="%s">%s</a>' % (edit_url, ruleid))
                table.cell(_("Parameters"), " ".join(rule["params"]))
                table.cell(_("Title"), rule["title"])
                table.cell(_("Aggregation"),  "/".join([rule["aggregation"][0]] + map(str, rule["aggregation"][1])))
                table.cell(_("Nodes"), len(rule["nodes"]), css="number")
                table.cell(_("Used by"))
                have_this = set([])
                for (aggr_id, aggregation) in aggregations_that_use_rule.get(ruleid, []):
                    if aggr_id not in have_this:
                        aggr_url = html.makeuri_contextless([("mode", "bi_edit_aggregation"), ("id", aggr_id)])
                        html.write('<a href="%s">%s</a><br>' % (aggr_url, html.attrencode(self.aggregation_title(aggregation))))
                        have_this.add(aggr_id)
                table.cell(_("Comment"), rule.get("comment", ""))
        table.end()


    def find_aggregation_rule_usages(self):
        aggregations_that_use_rule = {}
        for aggr_id, aggregation in enumerate(self._aggregations):
            ruleid, description = self.rule_called_by_node(aggregation["node"])
            aggregations_that_use_rule.setdefault(ruleid, []).append((aggr_id, aggregation))
            sub_rule_ids = self.aggregation_recursive_sub_rule_ids(ruleid)
            for sub_rule_id in sub_rule_ids:
                aggregations_that_use_rule.setdefault(sub_rule_id, []).append((aggr_id, aggregation))
        return aggregations_that_use_rule


    def aggregation_recursive_sub_rule_ids(self, ruleid):
        rule = self._aggregation_rules[ruleid]
        sub_rule_ids = self.aggregation_sub_rule_ids(rule)
        if not sub_rule_ids:
            return []
        result = sub_rule_ids[:]
        for sub_rule_id in sub_rule_ids:
            result += self.aggregation_recursive_sub_rule_ids(sub_rule_id)
        return result



#.
#   .--Rule Tree-----------------------------------------------------------.
#   |               ____        _        _____                             |
#   |              |  _ \ _   _| | ___  |_   _| __ ___  ___                |
#   |              | |_) | | | | |/ _ \   | || '__/ _ \/ _ \               |
#   |              |  _ <| |_| | |  __/   | || | |  __/  __/               |
#   |              |_| \_\\__,_|_|\___|   |_||_|  \___|\___|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

class ModeBIRuleTree(ModeBI):
    def __init__(self):
        ModeBI.__init__(self)
        self._ruleid = html.var("id")


    def title(self):
        return ModeBI.title(self) + " - " + _("Rule Tree of") + " " + self._ruleid


    def buttons(self):
        ModeBI.buttons(self)
        html.context_button(_("Back"), html.makeuri([("mode", "bi_rules")]), "back")


    def page(self):
        aggr_refs, rule_refs, level = self.count_bi_rule_references(self._ruleid)
        if rule_refs == 0:
            table.begin(sortable=False, searchable=False)
            table.row()
            table.cell(_("Rule Tree"), css="bi_rule_tree")
            self.render_rule_tree(self._ruleid, self._ruleid)
            table.end()




#.
#   .--Edit Aggregation----------------------------------------------------.
#   |                          _____    _ _ _                              |
#   |                         | ____|__| (_) |_                            |
#   |                         |  _| / _` | | __|                           |
#   |                         | |__| (_| | | |_                            |
#   |                         |_____\__,_|_|\__|                           |
#   |                                                                      |
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   '----------------------------------------------------------------------'

class ModeBIEditAggregation(ModeBI):
    def __init__(self):
        ModeBI.__init__(self)
        self._edited_nr = int(html.var("id", "-1")) # In case of Aggregations: index in list
        if self._edited_nr == -1:
            self._new = True
            self._edited_aggregation = { "groups" : [ _("Main") ] }
        else:
            self._new = False
            self._edited_aggregation = self._aggregations[self._edited_nr]



    def title(self):
        if self._new:
            return ModeBI.title(self) + " - " + _("Create New Aggregations")
        else:
            return ModeBI.title(self) + " - " + _("Edit Aggregations")


    def buttons(self):
        html.context_button(_("Abort"), html.makeuri([("mode", "bi_aggregations")]), "abort")



    def action(self):
        if html.check_transaction():
            new_aggr = self._vs_aggregation.from_html_vars('aggr')
            self._vs_aggregation.validate_value(new_aggr, 'aggr')
            if len(new_aggr["groups"]) == 0:
                raise MKUserError('rule_p_groups_0', _("Please define at least one aggregation group"))
            if self._new:
                self._aggregations.append(new_aggr)
                log_pending(SYNC, None, "bi-new-aggregation", _("Created new BI aggregation %d") % (len(self._aggregations)))
            else:
                self._aggregations[self._edited_nr] = new_aggr
                log_pending(SYNC, None, "bi-new-aggregation", _("Modified BI aggregation %d") % (self._edited_nr + 1))
            self.save_config()
        return "bi_aggregations"


    def page(self):
        html.begin_form("biaggr", method = "POST")
        self._vs_aggregation.render_input("aggr", self._edited_aggregation)
        forms.end()
        html.hidden_fields()
        html.button("_save", self._new and _("Create") or _("Save"), "submit")
        html.set_focus("rule_p_groups_0")
        html.end_form()


#.
#   .--Edit Rule-----------------------------------------------------------.
#   |                _____    _ _ _     ____        _                      |
#   |               | ____|__| (_) |_  |  _ \ _   _| | ___                 |
#   |               |  _| / _` | | __| | |_) | | | | |/ _ \                |
#   |               | |__| (_| | | |_  |  _ <| |_| | |  __/                |
#   |               |_____\__,_|_|\__| |_| \_\\__,_|_|\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

class ModeBIEditRule(ModeBI):
    def __init__(self):
        ModeBI.__init__(self)
        self._ruleid = html.var("id") # In case of Aggregations: index in list
        self._new = not self._ruleid


    def title(self):
        if self._new:
            return ModeBI.title(self) + " - " + _("Create New Rule")
        else:
            return ModeBI.title(self) + " - " + _("Edit Rule") + " " + html.attrencode(self._ruleid)


    def buttons(self):
        html.context_button(_("Abort"), html.makeuri([("mode", "bi_rules")]), "abort")



    def action(self):
        if html.check_transaction():
            vs_rule = self.valuespec()
            new_rule = vs_rule.from_html_vars('rule')
            vs_rule.validate_value(new_rule, 'rule')
            if self._new:
                self._ruleid = new_rule["id"]

            if self._new and self._ruleid in self._aggregation_rules:
                raise MKUserError('rule_p_id',
                    _("There is already a rule with the id <b>%s</b>" % self._ruleid))
            if not new_rule["nodes"]:
                raise MKUserError(None,
                    _("Please add at least one child node. Empty rules are useless."))

            if self._new:
                del new_rule["id"]
                self._aggregation_rules[self._ruleid] = new_rule
                log_pending(SYNC, None, "bi-new-rule", _("Create new BI rule %s") % self._ruleid)
            else:
                self._aggregation_rules[self._ruleid].update(new_rule)
                new_rule["id"] = self._ruleid
                if self.rule_uses_rule(new_rule, new_rule["id"]):
                    raise MKUserError(None, _("There is a cycle in your rules. This rule calls itself - "
                                              "either directly or indirectly."))
                log_pending(SYNC, None, "bi-edit-rule", _("Modified BI rule %s") % self._ruleid)

            self.save_config()
        return "bi_rules"

    def page(self):
        if self._new:
            value = {}
        else:
            value = self._aggregation_rules[self._ruleid]

        html.begin_form("birule", method="POST")
        self.valuespec().render_input("rule", value)
        forms.end()
        html.hidden_fields()
        html.button("_save", self._new and _("Create") or _("Save"), "submit")
        if self._new:
            html.set_focus("rule_p_id")
        else:
            html.set_focus("rule_p_title")
        html.end_form()


    def valuespec(self):
        elements = [
            ( "title",
               TextUnicode(
                   title = _("Rule Title"),
                   help = _("The title of the BI nodes which are created from this rule. This will be "
                            "displayed as the name of the node in the BI view. For "
                            "top level nodes this title must be unique. You can insert "
                            "rule parameters like <tt>$FOO$</tt> or <tt>$BAR$</tt> here."),
                   allow_empty = False,
                   size = 64,
               ),
            ),

            ( "comment",
               TextUnicode(
                   title = _("Comment"),
                   help = _("An arbitrary comment of this rule for you."),
                   size = 64,
               ),
            ),
            ( "params",
              ListOfStrings(
                  title = _("Parameters"),
                  help = _("Parameters are used in order to make rules more flexible. They must "
                           "be named like variables in programming languages. For example you can "
                           "make your rule have the two parameters <tt>HOST</tt> and <tt>INST</tt>. "
                           "When calling the rule - from an aggergation or a higher level rule - "
                           "you can then specify two arbitrary values for these parameters. In the "
                           "title of the rule as well as the host and service names, you can insert the "
                           "actual value of the parameters by <tt>$HOST$</tt> and <tt>$INST$</tt> "
                           "(enclosed in dollar signs)."),
                  orientation = "horizontal",
                  valuespec = TextAscii(
                    size = 12,
                    regex = '[A-Za-z_][A-Za-z0-9_]*',
                    regex_error = _("Parameters must contain only A-Z, a-z, 0-9 and _ "
                                    "and must not begin with a digit."),
                  )
              )
            ),
            ( "aggregation",
              CascadingDropdown(
                title = _("Aggregation Function"),
                help = _("The aggregation function decides how the status of a node "
                         "is constructed from the states of the child nodes."),
                orientation = "horizontal",
                choices = self.aggregation_choices(),
              )
            ),
            ( "nodes",
              ListOf(
                  self._vs_node,
                  add_label = _("Add child node generator"),
                  title = _("Nodes that are aggregated by this rule"),
              ),
            ),
        ]


        if self._new:
            elements = [
            ( "id",
              TextAscii(
                  title = _("Unique Rule ID"),
                  help = _("The ID of the rule must be a unique text. It will be used as an internal key "
                           "when rules refer to each other. The rule IDs will not be visible in the status "
                           "GUI. They are just used within the configuration."),
                  allow_empty = False,
                  size = 12,
              ),
            )] + elements

        return Dictionary(
            title = _("General Properties"),
            optional_keys = False,
            render = "form",
            elements = elements,
            headers = [
                ( _("General Properties"),     [ "id", "title", "comment", "params" ]),
                ( _("Aggregation Function"),   [ "aggregation" ], ),
                ( _("Child Node Generation"),  [ "nodes" ] ),
            ]
        )


#.
#   .--Aggregation functions-----------------------------------------------.
#   |             _                     __                                 |
#   |            / \   __ _  __ _ _ __ / _|_   _ _ __   ___ ___            |
#   |           / _ \ / _` |/ _` | '__| |_| | | | '_ \ / __/ __|           |
#   |          / ___ \ (_| | (_| | |  |  _| |_| | | | | (__\__ \           |
#   |         /_/   \_\__, |\__, |_|  |_|  \__,_|_| |_|\___|___/           |
#   |                 |___/ |___/                                          |
#   '----------------------------------------------------------------------'

bi_aggregation_functions = {}

bi_aggregation_functions["worst"] = {
    "title"     : _("Worst - take worst of all node states"),
    "valuespec" : Tuple(
        elements = [
            Integer(
                help = _("Normally this value is <tt>1</tt>, which means that the worst state "
                         "of all child nodes is being used as the total state. If you set it for example "
                         "to <tt>2</tt>, then the node with the worst state is not being regarded. "
                         "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                         "state would be WARN."),
                title = _("Take n'th worst state for n = "),
                default_value = 1,
                min_value = 1),
            MonitoringState(
                title = _("Restrict severity to at worst"),
                help = _("Here a maximum severity of the node state can be set. This severity is not "
                         "exceeded, even if some of the childs have more severe states."),
                default_value = 2,
            ),
        ]),
}

bi_aggregation_functions["best"] = {
    "title"     : _("Best - take best of all node states"),
    "valuespec" : Tuple(
        elements = [
            Integer(
                help = _("Normally this value is <tt>1</tt>, which means that the best state "
                         "of all child nodes is being used as the total state. If you set it for example "
                         "to <tt>2</tt>, then the node with the best state is not being regarded. "
                         "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                         "state would be WARN."),
                title = _("Take n'th best state for n = "),
                default_value = 1,
                min_value = 1),
            MonitoringState(
                title = _("Restrict severity to at worst"),
                help = _("Here a maximum severity of the node state can be set. This severity is not "
                         "exceeded, even if some of the childs have more severe states."),
                default_value = 2,
            ),
        ]),
}

def vs_count_ok_count(title, defval, defvalperc):
    return Alternative(
        title = title,
        style = "dropdown",
        match = lambda x: str(x).endswith("%") and 1 or 0,
        elements = [
            Integer(
                title = _("Explicit number"),
                label=_("Number of OK-nodes"),
                min_value = 0,
                default_value = defval
            ),
            Transform(
                Percentage(
                    label=_("Percent of OK-nodes"),
                    display_format = "%.0f",
                    default_value = defvalperc),
                title = _("Percentage"),
                forth = lambda x: float(x[:-1]),
                back = lambda x: "%d%%" % x,
            ),
        ]
    )

bi_aggregation_functions["count_ok"] = {
    "title"     : _("Count the number of nodes in state OK"),
    "valuespec" : Tuple(
        elements = [
            vs_count_ok_count(_("Required number of OK-nodes for a total state of OK:"), 2, 50),
            vs_count_ok_count(_("Required number of OK-nodes for a total state of WARN:"), 1, 25),
        ]),
}

#.
#   .--Example Configuration-----------------------------------------------.
#   |               _____                           _                      |
#   |              | ____|_  ____ _ _ __ ___  _ __ | | ___                 |
#   |              |  _| \ \/ / _` | '_ ` _ \| '_ \| |/ _ \                |
#   |              | |___ >  < (_| | | | | | | |_) | |  __/                |
#   |              |_____/_/\_\__,_|_| |_| |_| .__/|_|\___|                |
#   |                                        |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

bi_example = '''
aggregation_rules["host"] = (
  "Host $HOST$",
  [ "HOST" ],
  "worst",
  [
      ( "general",      [ "$HOST$" ] ),
      ( "performance",    [ "$HOST$" ] ),
      ( "filesystems",  [ "$HOST$" ] ),
      ( "networking",   [ "$HOST$" ] ),
      ( "applications", [ "$HOST$" ] ),
      ( "logfiles",     [ "$HOST$" ] ),
      ( "hardware",     [ "$HOST$" ] ),
      ( "other",        [ "$HOST$" ] ),
  ]
)

aggregation_rules["general"] = (
  "General State",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", HOST_STATE ),
      ( "$HOST$", "Uptime" ),
      ( "checkmk",  [ "$HOST$" ] ),
  ]
)

aggregation_rules["filesystems"] = (
  "Disk & Filesystems",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "Disk|MD" ),
      ( "multipathing", [ "$HOST$" ]),
      ( FOREACH_SERVICE, "$HOST$", "fs_(.*)", "filesystem", [ "$HOST$", "$1$" ] ),
      ( FOREACH_SERVICE, "$HOST$", "Filesystem(.*)", "filesystem", [ "$HOST$", "$1$" ] ),
  ]
)

aggregation_rules["filesystem"] = (
  "$FS$",
  [ "HOST", "FS" ],
  "worst",
  [
      ( "$HOST$", "fs_$FS$$" ),
      ( "$HOST$", "Filesystem$FS$$" ),
      ( "$HOST$", "Mount options of $FS$$" ),
  ]
)

aggregation_rules["multipathing"] = (
  "Multipathing",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "Multipath" ),
  ]
)

aggregation_rules["performance"] = (
  "Performance",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "CPU|Memory|Vmalloc|Kernel|Number of threads" ),
  ]
)

aggregation_rules["hardware"] = (
  "Hardware",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "IPMI|RAID" ),
  ]
)

aggregation_rules["networking"] = (
  "Networking",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "NFS|Interface|TCP" ),
  ]
)

aggregation_rules["checkmk"] = (
  "Check_MK",
  [ "HOST" ],
  "worst",
  [
       ( "$HOST$", "Check_MK|Uptime" ),
  ]
)

aggregation_rules["logfiles"] = (
  "Logfiles",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "LOG" ),
  ]
)
aggregation_rules["applications"] = (
  "Applications",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "ASM|ORACLE|proc" ),
  ]
)

aggregation_rules["other"] = (
  "Other",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", REMAINING ),
  ]
)

host_aggregations += [
  ( DISABLED, "Hosts", FOREACH_HOST, [ "tcp" ], ALL_HOSTS, "host", ["$1$"] ),
]
'''

#.
#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Integrate all that stuff into WATO                                  |
#   '----------------------------------------------------------------------'

config.declare_permission("wato.bi_rules",
    _("Business Intelligence Rules"),
    _("Edit the rules for the BI aggregations."),
     [ "admin" ])


modes.update({
    "bi_rules"           : (["bi_rules"], ModeBIRules),
    "bi_aggregations"    : (["bi_rules"], ModeBIAggregations),
    "bi_rule_tree"       : (["bi_rules"], ModeBIRuleTree),
    "bi_edit_rule"       : (["bi_rules"], ModeBIEditRule),
    "bi_edit_aggregation": (["bi_rules"], ModeBIEditAggregation),
})

