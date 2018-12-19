import pytest
from pathlib2 import Path

import cmk.gui.modules as modules
import cmk.gui.config as config
import cmk.gui.permissions as permissions
from cmk.gui.permissions import (
    permission_section_registry,)


@pytest.fixture(autouse=True)
def load_plugins(register_builtin_html, monkeypatch, tmpdir):
    config_dir = Path("%s" % tmpdir).joinpath("var/check_mk/web")
    config_dir.mkdir(parents=True)  # pylint: disable=no-member
    monkeypatch.setattr(config, "config_dir", "%s" % config_dir)
    modules.load_all_plugins()


def test_registered_permission_sections():
    expected_sections = [
        ('graph_collection', (50, u'Graph Collections', True)),
        ('graph_tuning', (50, u'Graph tunings', True)),
        ('sla_configuration', (50, u'Service Level Agreements', True)),
        ('custom_graph', (50, u'Custom Graphs', True)),
        ('bookmark_list', (50, u'Bookmark lists', True)),
        ('custom_snapin', (50, u'Custom snapins', True)),
        ('sidesnap', (50, u'Sidebar snapins', True)),
        ('notification_plugin', (50, u'Notification plugins', True)),
        ('wato', (50, u"WATO - Check_MK's Web Administration Tool", False)),
        ('background_jobs', (50, u'Background jobs', False)),
        ('bi', (50, u'BI - Check_MK Business Intelligence', False)),
        ('general', (10, u'General Permissions', False)),
        ('mkeventd', (50, u'Event Console', False)),
        ('action', (50, u'Commands on host and services', True)),
        ('dashboard', (50, u'Dashboards', True)),
        ('report', (50, u'Reports', True)),
        ('nagvis', (50, u'NagVis', False)),
        ('view', (50, u'Views', True)),
    ]

    section_names = permission_section_registry.keys()
    assert sorted([s[0] for s in expected_sections]) == sorted(section_names)

    for name, (sort_index, title, do_sort) in expected_sections:
        section = permission_section_registry[name]()
        assert section.title == title
        assert section.sort_index == sort_index
        assert section.do_sort == do_sort


def test_registered_permissions():
    expected_permissions = [
        ('view.invchassis_of_host', {
            'description': u'invchassis_of_host - A view for the Chassis of one host',
            'name': 'view.invchassis_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Chassis (invchassis_of_host)'
        }),
        ('view.perf_matrix_search', {
            'description': u'perf_matrix_search - A Matrix of performance data values, grouped by hosts and services',
            'name': 'view.perf_matrix_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Search performance data (perf_matrix_search)'
        }),
        ('wato.service_discovery_to_ignored', {
            'description': u'Service discovery: Disabled services',
            'name': 'wato.service_discovery_to_ignored',
            'defaults': ['admin', 'user'],
            'title': u'Service discovery: Disabled services'
        }),
        ('wato.mkps', {
            'description': u'This permission gives read access to the Check_MK MKP manager. It allows to view and download installed packages. MKPs contain extensions to Check_MK such as new check plugins or GUI extensions.',
            'name': 'wato.mkps',
            'defaults': ['admin'],
            'title': u'Visit Extension Package Manager'
        }),
        ('view.alertstats', {
            'description': u'alertstats - Shows number of alerts grouped for each service.',
            'name': 'view.alertstats',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Alert Statistics (alertstats)'
        }),
        ('general.csv_export', {
            'description': u'Export data of views using the CSV export',
            'name': 'general.csv_export',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Use CSV export'
        }),
        ('view.hostproblems', {
            'description': u'hostproblems - A complete list of all host problems with a search form for selecting handled and unhandled',
            'name': 'view.hostproblems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host problems (hostproblems)'
        }),
        ('view.invcontainer_search', {
            'description': u'invcontainer_search - A view for searching in the inventory data for HW containers',
            'name': 'view.invcontainer_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search HW containers (invcontainer_search)'
        }),
        ('general.see_user_views', {
            'description': u'Is needed for seeing views that other users have created.',
            'name': 'general.see_user_views',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user views'
        }),
        ('view.failed_notifications', {
            'description': u'failed_notifications - Failed notification events of hosts and services.',
            'name': 'view.failed_notifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Failed notifications (failed_notifications)'
        }),
        ('general.force_views', {
            'description': u'Make own published views override builtin views for all users.',
            'name': 'general.force_views',
            'defaults': ['admin'],
            'title': u'Modify builtin views'
        }),
        ('general.edit_foreign_reports', {
            'description': u'Allows to edit reports created by other users.',
            'name': 'general.edit_foreign_reports',
            'defaults': ['admin'],
            'title': u'Edit foreign reports'
        }),
        ('view.invorarecoveryarea_of_host', {
            'description': u'invorarecoveryarea_of_host - A view for the Oracle recovery areas of one host',
            'name': 'view.invorarecoveryarea_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Oracle recovery areas (invorarecoveryarea_of_host)'
        }),
        ('view.host_unknown', {
            'description': u'host_unknown - All services of a given host that are in state UNKNOWN',
            'name': 'view.host_unknown',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - UNKNOWN Services of host (host_unknown)'
        }),
        ('sidesnap.nagvis_maps', {
            'description': u'List of available NagVis maps. This only works with NagVis 1.5 and above. ',
            'name': 'sidesnap.nagvis_maps',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'NagVis Maps'
        }),
        ('view.allhosts', {
            'description': u'allhosts - Overall state of all hosts, with counts of services in the various states.',
            'name': 'view.allhosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - All hosts (allhosts)'
        }),
        ('sidesnap.hostgroups', {
            'description': u'Directs links to all host groups',
            'name': 'sidesnap.hostgroups',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Host Groups'
        }),
        ('general.publish_reports', {
            'description': u'Make reports visible and usable for other users.',
            'name': 'general.publish_reports',
            'defaults': ['admin', 'user'],
            'title': u'Publish reports'
        }),
        ('mkeventd.config', {
            'description': u'This permission allows to configure the global settings of the event console.',
            'name': 'mkeventd.config',
            'defaults': ['admin'],
            'title': u'Configuration of Event Console '
        }),
        ('sidesnap.biaggr_groups_tree', {
            'description': u'A direct link to all groups of BI aggregations organized as tree',
            'name': 'sidesnap.biaggr_groups_tree',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'BI Aggregation Groups Tree'
        }),
        ('view.comments_of_host', {
            'description': u'comments_of_host - Linkable view showing all comments of a specific host',
            'name': 'view.comments_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Comments of host (comments_of_host)'
        }),
        ('wato.backups', {
            'description': u'Access to the module <i>Site backup</i>. Please note: a user with write access to this module can make arbitrary changes to the configuration by restoring uploaded snapshots.',
            'name': 'wato.backups',
            'defaults': ['admin'],
            'title': u'Backup & Restore'
        }),
        ('general.edit_foreign_custom_snapin', {
            'description': u'Allows to edit Custom snapins created by other users.',
            'name': 'general.edit_foreign_custom_snapin',
            'defaults': ['admin'],
            'title': u'Edit foreign Custom snapins'
        }),
        ('view.svcproblems_dash', {
            'description': 'svcproblems_dash - All non-downtime, non-acknownledged services, used for the dashbaord',
            'name': 'view.svcproblems_dash',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service problems (svcproblems_dash)'
        }),
        ('view.invsensor_of_host', {
            'description': u'invsensor_of_host - A view for the Sensors of one host',
            'name': 'view.invsensor_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Sensors (invsensor_of_host)'
        }),
        ('wato.users', {
            'description': u'This permission is needed for the modules <b>Users</b>, <b>Roles</b> and <b>Contact Groups</b>',
            'name': 'wato.users',
            'defaults': ['admin'],
            'title': u'User management'
        }),
        ('view.invdockerimages_search', {
            'description': u'invdockerimages_search - A view for searching in the inventory data for Docker images',
            'name': 'view.invdockerimages_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Docker images (invdockerimages_search)'
        }),
        ('view.invstack_of_host', {
            'description': u'invstack_of_host - A view for the Stacks of one host',
            'name': 'view.invstack_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Stacks (invstack_of_host)'
        }),
        ('general.notify', {
            'description': u'This permissions allows users to send notifications to the users of the monitoring system using the web interface.',
            'name': 'general.notify',
            'defaults': ['admin'],
            'title': u'Notify Users'
        }),
        ('wato.snapshots', {
            'description': u'Access to the module <i>Snaphsots</i>. Please note: a user with write access to this module can make arbitrary changes to the configuration by restoring uploaded snapshots.',
            'name': 'wato.snapshots',
            'defaults': ['admin'],
            'title': u'Manage snapshots'
        }),
        ('view.inv_hosts_cpu', {
            'description': u'inv_hosts_cpu - A list of all hosts with some CPU related inventory data',
            'name': 'view.inv_hosts_cpu',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - CPU Related Inventory of all Hosts (inv_hosts_cpu)'
        }),
        ('general.edit_foreign_graph_tuning', {
            'description': u'Allows to edit Graph tunings created by other users.',
            'name': 'general.edit_foreign_graph_tuning',
            'defaults': ['admin'],
            'title': u'Edit foreign Graph tunings'
        }),
        (u'notification_plugin.mail', {
            'description': u'',
            'name': u'notification_plugin.mail',
            'defaults': ['admin', 'user'],
            'title': u'HTML Email'
        }),
        ('general.see_user_custom_graph', {
            'description': u'Is needed for seeing Custom Graphs that other users have created.',
            'name': 'general.see_user_custom_graph',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Custom Graphs'
        }),
        (u'notification_plugin.asciimail', {
            'description': u'',
            'name': u'notification_plugin.asciimail',
            'defaults': ['admin', 'user'],
            'title': u'ASCII Email'
        }),
        ('sidesnap.speedometer', {
            'description': u'A gadget that shows your current service check rate in relation to the scheduled check rate. If the Speed-O-Meter shows a speed of 100 percent, all service checks are being executed in exactly the rate that is desired.',
            'name': 'sidesnap.speedometer',
            'defaults': ['admin'],
            'title': u'Service Speed-O-Meter'
        }),
        ('view.mobile_hostproblems_unack', {
            'description': 'mobile_hostproblems_unack - This view is used by the mobile GUI',
            'name': 'view.mobile_hostproblems_unack',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Hosts - Problems (unhandled) (mobile_hostproblems_unack)'
        }),
        ('dashboard.simple_problems', {
            'description': u'A compact dashboard which lists your unhandled host and service problems.',
            'name': 'dashboard.simple_problems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Host & Services Problems'
        }),
        ('view.downtimes', {
            'description': u'downtimes - All host- and service-downtimes',
            'name': 'view.downtimes',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Downtimes (downtimes)'
        }),
        ('report.service_availability', {
            'description': u'A report showing the availability of the services of an\narbitrary view.',
            'name': 'report.service_availability',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Service Availability'
        }),
        ('general.see_all', {
            'description': u"See all objects regardless of contacts and contact groups. If combined with 'perform commands' then commands may be done on all objects.",
            'name': 'general.see_all',
            'defaults': ['admin', 'guest'],
            'title': u'See all host and services'
        }),
        ('view.mobile_hostsvcevents', {
            'description': 'mobile_hostsvcevents - This view is used by the mobile GUI',
            'name': 'view.mobile_hostsvcevents',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Events of host & services (mobile_hostsvcevents)'
        }),
        ('view.host', {
            'description': u'host - All services of a given host. The host and site must be set via HTML variables.',
            'name': 'view.host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services of Host (host)'
        }),
        ('view.hostproblems_dash', {
            'description': 'hostproblems_dash - A complete list of all host problems, optimized for usage in the dashboard',
            'name': 'view.hostproblems_dash',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host problems (hostproblems_dash)'
        }),
        ('view.service_graphs', {
            'description': u'service_graphs - Shows all graphs including timerange selections of a collection of services.',
            'name': 'view.service_graphs',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service Graphs (service_graphs)'
        }),
        ('view.ec_event', {
            'description': u'ec_event - Details about one event',
            'name': 'view.ec_event',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Event Details (ec_event)'
        }),
        ('wato.download_all_agents', {
            'description': u'Register all hosts with the agent bakery and download all monitoring agents that have been created with the agent bakery, even if you are not a contact for the host in question. Please note that these agents might contain confidential information such as passwords.',
            'name': 'wato.download_all_agents',
            'defaults': ['admin'],
            'title': u'Register all hosts & download all monitoring agents'
        }),
        ('wato.groups', {
            'description': u'Access to the modules for managing host and service groups.',
            'name': 'wato.groups',
            'defaults': ['admin'],
            'title': u'Host & Service Groups'
        }),
        ('view.stale_hosts', {
            'description': u'stale_hosts - Hosts that have not been checked for too long.',
            'name': 'view.stale_hosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Stale hosts (stale_hosts)'
        }),
        ('bi.see_all', {
            'description': u'With this permission set, the BI aggregation rules are applied to all hosts and services - not only those the user is a contact for. If you remove this permissions then the user will see incomplete aggregation trees with status based only on those items.',
            'name': 'bi.see_all',
            'defaults': ['admin', 'guest'],
            'title': u'See all hosts and services'
        }),
        ('general.see_user_dashboards', {
            'description': u'Is needed for seeing dashboards that other users have created.',
            'name': 'general.see_user_dashboards',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user dashboards'
        }),
        ('view.searchhost', {
            'description': u'searchhost - A form for searching hosts using flexible filters',
            'name': 'view.searchhost',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host search (searchhost)'
        }),
        ('view.comments', {
            'description': u'comments - All host- and service comments',
            'name': 'view.comments',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Comments (comments)'
        }),
        ('action.clearmodattr', {
            'description': u'Reset all manually modified attributes of a host or service (like disabled notifications)',
            'name': 'action.clearmodattr',
            'defaults': ['admin'],
            'title': u'Reset modified attributes'
        }),
        ('wato.custom_attributes', {
            'description': u'Manage custom host- and user attributes',
            'name': 'wato.custom_attributes',
            'defaults': ['admin'],
            'title': u'Manage custom attributes'
        }),
        ('general.see_user_stored_report', {
            'description': u'Is needed for seeing Stored reports that other users have created.',
            'name': 'general.see_user_stored_report',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Stored reports'
        }),
        ('sidesnap.hostmatrix', {
            'description': u'A matrix showing a colored square for each host',
            'name': 'sidesnap.hostmatrix',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Host Matrix'
        }),
        ('general.publish_reports_to_foreign_groups', {
            'description': u'Make reports visible and usable for users of contact groups the publishing user is not a member of.',
            'name': 'general.publish_reports_to_foreign_groups',
            'defaults': ['admin'],
            'title': u'Publish reports to foreign contact groups'
        }),
        ('wato.edit_hosts', {
            'description': u'Modify the properties of existing hosts. Please note: for the management of services (inventory) there is a separate permission (see below)',
            'name': 'wato.edit_hosts',
            'defaults': ['admin', 'user'],
            'title': u'Modify existing hosts'
        }),
        ('sidesnap.tag_tree', {
            'description': u'This snapin shows tree views of your hosts based on their tag classifications. You can configure which tags to use in your global settings of Multisite.',
            'name': 'sidesnap.tag_tree',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Virtual Host Tree'
        }),
        ('view.hostgroup', {
            'description': u'hostgroup - Lists members of a host group with the number of services in the different states.',
            'name': 'view.hostgroup',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host Group (hostgroup)'
        }),
        ('view.uncheckedsvc', {
            'description': u'uncheckedsvc - Services that have not been checked for too long according to their configured check intervals.',
            'name': 'view.uncheckedsvc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Stale services (uncheckedsvc)'
        }),
        ('view.recentsvc', {
            'description': u'recentsvc - Service whose state changed in the last 60 minutes',
            'name': 'view.recentsvc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Recently changed services (recentsvc)'
        }),
        ('action.star', {
            'description': u'This permission allows a user to make certain host and services his personal favorites. Favorites can be used for a having a fast access to items that are needed on a regular base.',
            'name': 'action.star',
            'defaults': ['user', 'admin'],
            'title': u'Use favorites'
        }),
        ('view.host_crit', {
            'description': u'host_crit - All services of a given host that are in state CRIT',
            'name': 'view.host_crit',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - CRIT Services of host (host_crit)'
        }),
        ('wato.move_hosts', {
            'description': u'Move existing hosts to other folders. Please also add the permission <i>Modify existing hosts</i>.',
            'name': 'wato.move_hosts',
            'defaults': ['admin', 'user'],
            'title': u'Move existing hosts'
        }),
        ('general.edit_foreign_sla_configuration', {
            'description': u'Allows to edit Service Level Agreements created by other users.',
            'name': 'general.edit_foreign_sla_configuration',
            'defaults': ['admin'],
            'title': u'Edit foreign Service Level Agreements'
        }),
        ('general.see_failed_notifications_24h', {
            'description': u'If Check_MK is unable to notify users about problems, the site will warn about this situation very visibly inside the UI (both in the Tactical Overview and the Dashboard). This affects only users with this permission. Users with this permission will only see failed notifications that occured within the last 24 hours.',
            'name': 'general.see_failed_notifications_24h',
            'defaults': ['user'],
            'title': u'See failed Notifications (last 24 hours)'
        }),
        ('sidesnap.hosts', {
            'description': u'A summary state of each host with a link to the view showing its services',
            'name': 'sidesnap.hosts',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'All Hosts'
        }),
        ('general.edit_foreign_dashboards', {
            'description': u'Allows to edit dashboards created by other users.',
            'name': 'general.edit_foreign_dashboards',
            'defaults': ['admin'],
            'title': u'Edit foreign dashboards'
        }),
        ('view.aggr_single', {
            'description': u'aggr_single - Shows a single aggregation.',
            'name': 'view.aggr_single',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Single Aggregation (aggr_single)'
        }),
        ('view.downtimes_of_service', {
            'description': u'downtimes_of_service - Lists all downtimes for services.',
            'name': 'view.downtimes_of_service',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Downtimes of service (downtimes_of_service)'
        }),
        (u'notification_plugin.mkeventd', {
            'description': u'',
            'name': u'notification_plugin.mkeventd',
            'defaults': ['admin', 'user'],
            'title': u'Forward Notification to Event Console'
        }),
        ('general.delete_foreign_stored_report', {
            'description': u'Allows to delete Stored reports created by other users.',
            'name': 'general.delete_foreign_stored_report',
            'defaults': ['admin'],
            'title': u'Delete foreign Stored reports'
        }),
        ('action.reschedule', {
            'description': u'Reschedule host and service checks',
            'name': 'action.reschedule',
            'defaults': ['user', 'admin'],
            'title': u'Reschedule checks'
        }),
        ('general.edit_custom_snapin', {
            'description': u'Allows to create own Custom snapins, customize builtin Custom snapins and use them.',
            'name': 'general.edit_custom_snapin',
            'defaults': ['admin', 'user'],
            'title': u'Customize Custom snapins and use them'
        }),
        ('view.notifications', {
            'description': u'notifications - All notification events of hosts or services.',
            'name': 'view.notifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Host- and Service notifications (notifications)'
        }),
        ('view.invswpac_search', {
            'description': u'invswpac_search - A view for searching in the inventory data for Software packages',
            'name': 'view.invswpac_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Software packages (invswpac_search)'
        }),
        ('sidesnap.reports', {
            'description': u'Direct access to global reports, selection for the default reporting time range, link to report editor.',
            'name': 'sidesnap.reports',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Reporting'
        }),
        ('general.delete_foreign_dashboards', {
            'description': u'Allows to delete dashboards created by other users.',
            'name': 'general.delete_foreign_dashboards',
            'defaults': ['admin'],
            'title': u'Delete foreign dashboards'
        }),
        ('view.mobile_svcnotifications', {
            'description': 'mobile_svcnotifications - This view is used by the mobile GUI',
            'name': 'view.mobile_svcnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Service Notifications (mobile_svcnotifications)'
        }),
        ('view.hoststatus', {
            'description': u'hoststatus - Shows details of a host.',
            'name': 'view.hoststatus',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Status of Host (hoststatus)'
        }),
        ('general.publish_custom_graph', {
            'description': u'Make Custom Graphs visible and usable for other users.',
            'name': 'general.publish_custom_graph',
            'defaults': ['admin', 'user'],
            'title': u'Publish Custom Graphs'
        }),
        ('view.aggr_all', {
            'description': u'aggr_all - Displays all BI aggregations.',
            'name': 'view.aggr_all',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - All Aggregations (aggr_all)'
        }),
        ('view.svcbyhgroups', {
            'description': u'svcbyhgroups - Service grouped by host groups. Services not member of a host group are not displayed. Services being in more groups, are displayed once for each group',
            'name': 'view.svcbyhgroups',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Serv. by host groups (svcbyhgroups)'
        }),
        ('view.aggr_problems', {
            'description': u'aggr_problems - All aggregations that have a non-OK state (honoring state assumptions)',
            'name': 'view.aggr_problems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Problem Aggregations (aggr_problems)'
        }),
        ('wato.use', {
            'description': u"This permissions allows users to use WATO - Check_MK's Web Administration Tool. Without this permission all references to WATO (buttons, links, snapins) will be invisible.",
            'name': 'wato.use',
            'defaults': ['admin', 'user'],
            'title': u'Use WATO'
        }),
        ('general.schedule_reports_all', {
            'description': u'Allows a user to modify scheduled reports of other users and also to specify arbitrary Email addresses as report destination.',
            'name': 'general.schedule_reports_all',
            'defaults': ['admin'],
            'title': u'Manage All Scheduled Reports'
        }),
        ('mkeventd.seeunrelated', {
            'description': u'If that user does not have the permission <i>See all events</i> then this permission controls wether he/she can see events that are not related to a host in the monitoring and that do not have been assigned specific contact groups to via the event rule.',
            'name': 'mkeventd.seeunrelated',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'See events not related to a known host'
        }),
        ('wato.agent_deployment', {
            'description': u'This permissions allows full control of the automatic agent updates.',
            'name': 'wato.agent_deployment',
            'defaults': ['admin'],
            'title': u'Configuration of agent updates'
        }),
        (u'notification_plugin.slack', {
            'description': u'',
            'name': u'notification_plugin.slack',
            'defaults': ['admin', 'user'],
            'title': u'Slack'
        }),
        ('general.edit_graph_collection', {
            'description': u'Allows to create own Graph Collections, customize builtin Graph Collections and use them.',
            'name': 'general.edit_graph_collection',
            'defaults': ['admin', 'user'],
            'title': u'Customize Graph Collections and use them'
        }),
        ('nagvis.Map_view', {
            'description': u'Grants read access to all maps the user is a contact for.',
            'name': 'nagvis.Map_view',
            'defaults': ['user'],
            'title': u'View permitted maps'
        }),
        ('view.servicedescpnp', {
            'description': u'servicedescpnp - Graphs for all Services with a certain description',
            'name': 'view.servicedescpnp',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Graphs of services with description: (servicedescpnp)'
        }),
        ('view.invdockercontainers_search', {
            'description': u'invdockercontainers_search - A view for searching in the inventory data for Docker containers',
            'name': 'view.invdockercontainers_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Docker containers (invdockercontainers_search)'
        }),
        ('sidesnap.admin', {
            'description': u'Direct access to WATO - the web administration GUI of Check_MK',
            'name': 'sidesnap.admin',
            'defaults': ['admin', 'user'],
            'title': u'WATO &middot; Configuration'
        }),
        ('general.see_user_reports', {
            'description': u'Is needed for seeing reports that other users have created.',
            'name': 'general.see_user_reports',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user reports'
        }),
        ('wato.api_allowed', {
            'description': u'This permissions specifies if the role is able to use Web-API functions. It is only available for automation users.',
            'name': 'wato.api_allowed',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Access to Web-API'
        }),
        ('general.configure_sidebar', {
            'description': u'This allows the user to add, move and remove sidebar snapins.',
            'name': 'general.configure_sidebar',
            'defaults': ['admin', 'user'],
            'title': u'Configure sidebar'
        }),
        ('view.invchassis_search', {
            'description': u'invchassis_search - A view for searching in the inventory data for Chassis',
            'name': 'view.invchassis_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Chassis (invchassis_search)'
        }),
        ('wato.analyze_config', {
            'description': u'WATO has a module that gives you hints on how to tune your Check_MK installation.',
            'name': 'wato.analyze_config',
            'defaults': ['admin'],
            'title': u'Access the best analyze configuration functionality provided by WATO'
        }),
        ('wato.notifications', {
            'description': u'This permission is needed for the new rule based notification configuration via the WATO module <i>Notifications</i>.',
            'name': 'wato.notifications',
            'defaults': ['admin'],
            'title': u'Notification configuration'
        }),
        ('view.invoradataguardstats_of_host', {
            'description': u'invoradataguardstats_of_host - A view for the Oracle dataguard statistics of one host',
            'name': 'view.invoradataguardstats_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Oracle dataguard statistics (invoradataguardstats_of_host)'
        }),
        ('wato.service_discovery_to_removed', {
            'description': u'Service discovery: Remove services',
            'name': 'wato.service_discovery_to_removed',
            'defaults': ['admin', 'user'],
            'title': u'Service discovery: Remove services'
        }),
        ('view.problemsofhost', {
            'description': u'problemsofhost - All problem services of a given host. The host and site must be set via HTTP variables.',
            'name': 'view.problemsofhost',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Problems of host (problemsofhost)'
        }),
        ('action.fakechecks', {
            'description': u'Manually submit check results for host and service checks',
            'name': 'action.fakechecks',
            'defaults': ['admin'],
            'title': u'Fake check results'
        }),
        (u'notification_plugin.pushover', {
            'description': u'',
            'name': u'notification_plugin.pushover',
            'defaults': ['admin', 'user'],
            'title': u'Push Notifications (using Pushover)'
        }),
        ('mkeventd.archive_events_of_hosts', {
            'description': u'Archive all open events of all hosts shown in host views',
            'name': 'mkeventd.archive_events_of_hosts',
            'defaults': ['user', 'admin'],
            'title': u'Archive events of hosts'
        }),
        ('wato.bi_admin', {
            'description': u'Edit all rules and aggregations for Business Intelligence, create, modify and delete rule packs.',
            'name': 'wato.bi_admin',
            'defaults': ['admin'],
            'title': u'Business Intelligence Administration'
        }),
        ('view.invoradataguardstats_search', {
            'description': u'invoradataguardstats_search - A view for searching in the inventory data for Oracle dataguard statistics',
            'name': 'view.invoradataguardstats_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Oracle dataguard statistics (invoradataguardstats_search)'
        }),
        ('view.ec_historyentry', {
            'description': u'ec_historyentry - Details about a historical event history entry',
            'name': 'view.ec_historyentry',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Event History Entry (ec_historyentry)'
        }),
        ('view.service', {
            'description': u'service - Status of a single service, to be used for linking',
            'name': 'view.service',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service (service)'
        }),
        ('mkeventd.seeall', {
            'description': u'If a user lacks this permission then he/she can see only those events that originate from a host that he/she is a contact for.',
            'name': 'mkeventd.seeall',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'See all events'
        }),
        ('general.change_password', {
            'description': u'Permits the user to change the password.',
            'name': 'general.change_password',
            'defaults': ['admin', 'user'],
            'title': u'Edit the user password'
        }),
        ('general.publish_custom_snapin', {
            'description': u'Make Custom snapins visible and usable for other users.',
            'name': 'general.publish_custom_snapin',
            'defaults': ['admin', 'user'],
            'title': u'Publish Custom snapins'
        }),
        ('wato.sites', {
            'description': u'Access to the module for managing connections to remote monitoring sites.',
            'name': 'wato.sites',
            'defaults': ['admin'],
            'title': u'Site management'
        }),
        ('general.edit_graph_tuning', {
            'description': u'Allows to create own Graph tunings, customize builtin Graph tunings and use them.',
            'name': 'general.edit_graph_tuning',
            'defaults': ['admin', 'user'],
            'title': u'Customize Graph tunings and use them'
        }),
        ('view.mobile_events', {
            'description': 'mobile_events - This view is used by the mobile GUI',
            'name': 'view.mobile_events',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Events (mobile_events)'
        }),
        ('wato.activateforeign', {
            'description': u'When several users work in parallel with WATO then several pending changes of different users might pile up before changes are activate. Only with this permission a user will be allowed to activate the current configuration if this situation appears.',
            'name': 'wato.activateforeign',
            'defaults': ['admin'],
            'title': u'Activate Foreign Changes'
        }),
        ('report.host', {
            'description': u'This report shows various information about one single host. It is not visible in the sidebar, because it needs a host to be called. Call it via a button at a view that is displaying one host.',
            'name': 'report.host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Report of Host'
        }),
        ('general.painter_options', {
            'description': u'Some of the display columns offer options for customizing their output. For example time stamp columns can be displayed absolute, relative or in a mixed style. This permission allows the user to modify display options',
            'name': 'general.painter_options',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Change column display options'
        }),
        ('view.mobile_notifications', {
            'description': 'mobile_notifications - This view is used by the mobile GUI',
            'name': 'view.mobile_notifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Notifications (mobile_notifications)'
        }),
        ('sidesnap.sitestatus', {
            'description': u'Connection state of each site and button for enabling and disabling the site connection',
            'name': 'sidesnap.sitestatus',
            'defaults': ['user', 'admin'],
            'title': u'Site Status'
        }),
        ('view.inv_hosts_ports', {
            'description': u'inv_hosts_ports - A list of all hosts with statistics about total, used and free networking interfaces',
            'name': 'view.inv_hosts_ports',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Switch port statistics (inv_hosts_ports)'
        }),
        ('wato.automation', {
            'description': u'This permission is needed for a remote administration of the site as a distributed WATO slave.',
            'name': 'wato.automation',
            'defaults': ['admin'],
            'title': u'Site remote automation'
        }),
        ('view.invother_of_host', {
            'description': u'invother_of_host - A view for the Other entities of one host',
            'name': 'view.invother_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Other entities (invother_of_host)'
        }),
        ('general.edit_foreign_views', {
            'description': u'Allows to edit views created by other users.',
            'name': 'general.edit_foreign_views',
            'defaults': ['admin'],
            'title': u'Edit foreign views'
        }),
        ('view.invswpac_of_host', {
            'description': u'invswpac_of_host - A view for the Software packages of one host',
            'name': 'view.invswpac_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Software packages (invswpac_of_host)'
        }),
        ('general.edit_views', {
            'description': u'Allows to create own views, customize builtin views and use them.',
            'name': 'general.edit_views',
            'defaults': ['admin', 'user'],
            'title': u'Customize views and use them'
        }),
        ('view.invoratablespace_search', {
            'description': u'invoratablespace_search - A view for searching in the inventory data for Oracle tablespaces',
            'name': 'view.invoratablespace_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Oracle tablespaces (invoratablespace_search)'
        }),
        ('general.see_sidebar', {
            'description': u'Without this permission the Check_MK sidebar will be invisible',
            'name': 'general.see_sidebar',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Use Check_MK sidebar'
        }),
        ('sidesnap.servicegroups', {
            'description': u'Direct links to all service groups',
            'name': 'sidesnap.servicegroups',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Service Groups'
        }),
        ('report.instant', {
            'description': '',
            'name': 'report.instant',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Template for PDF exporting'
        }),
        ('general.edit_foreign_custom_graph', {
            'description': u'Allows to edit Custom Graphs created by other users.',
            'name': 'general.edit_foreign_custom_graph',
            'defaults': ['admin'],
            'title': u'Edit foreign Custom Graphs'
        }),
        ('general.edit_foreign_bookmark_list', {
            'description': u'Allows to edit Bookmark lists created by other users.',
            'name': 'general.edit_foreign_bookmark_list',
            'defaults': ['admin'],
            'title': u'Edit foreign Bookmark lists'
        }),
        ('wato.service_discovery_to_undecided', {
            'description': u'Service discovery: Move to undecided services',
            'name': 'wato.service_discovery_to_undecided',
            'defaults': ['admin', 'user'],
            'title': u'Service discovery: Move to undecided services'
        }),
        ('wato.agents', {
            'description': u'Manage customized packaged monitoring agents for Linux, Windows and other operating systems',
            'name': 'wato.agents',
            'defaults': ['admin'],
            'title': u'Manage Monitoring Agents'
        }),
        ('view.servicedesc', {
            'description': u'servicedesc - All Services with a certain description',
            'name': 'view.servicedesc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - All Services with this description: (servicedesc)'
        }),
        ('mkeventd.update_comment', {
            'description': u'Needed for changing a comment when updating an event',
            'name': 'mkeventd.update_comment',
            'defaults': ['user', 'admin'],
            'title': u'Update an event: change comment'
        }),
        ('general.edit_user_attributes', {
            'description': u'This allows a user to edit his personal user attributes. You also need the permission <i>Edit the user profile</i> in order to do this.',
            'name': 'general.edit_user_attributes',
            'defaults': ['admin', 'user'],
            'title': u'Edit personal user attributes'
        }),
        ('view.logfile', {
            'description': u'logfile - Displays entries from the logfile of the monitoring core.',
            'name': 'view.logfile',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Search Global Logfile (logfile)'
        }),
        ('action.enablechecks', {
            'description': u'Enable and disable active or passive checks on hosts and services',
            'name': 'action.enablechecks',
            'defaults': ['admin'],
            'title': u'Enable/disable checks'
        }),
        ('view.invfan_search', {
            'description': u'invfan_search - A view for searching in the inventory data for Fans',
            'name': 'view.invfan_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Fans (invfan_search)'
        }),
        ('view.invorasga_of_host', {
            'description': u'invorasga_of_host - A view for the Oracle performance of one host',
            'name': 'view.invorasga_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Oracle performance (invorasga_of_host)'
        }),
        ('mkeventd.see_in_tactical_overview', {
            'description': u'Whether or not the user is permitted to see the number of open events in the tactical overview snapin.',
            'name': 'mkeventd.see_in_tactical_overview',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'See events in tactical overview snapin'
        }),
        ('general.publish_sla_configuration', {
            'description': u'Make Service Level Agreements visible and usable for other users.',
            'name': 'general.publish_sla_configuration',
            'defaults': ['admin', 'user'],
            'title': u'Publish Service Level Agreements'
        }),
        ('mkeventd.edit', {
            'description': u'This permission allows the creation, modification and deletion of event correlation rules.',
            'name': 'mkeventd.edit',
            'defaults': ['admin'],
            'title': u'Configuration of event rules'
        }),
        ('view.svcgroups_grid', {
            'description': u'svcgroups_grid - A short overview over all service groups, without explicity listing of the actual hosts and services',
            'name': 'view.svcgroups_grid',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Servicegroups - Service Groups (Grid) (svcgroups_grid)'
        }),
        ('view.ec_events', {
            'description': u'ec_events - Table of all currently open events (handled and unhandled)',
            'name': 'view.ec_events',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Events (ec_events)'
        }),
        ('sidesnap.wiki', {
            'description': u'Shows the Wiki Navigation of the OMD Site',
            'name': 'sidesnap.wiki',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Wiki'
        }),
        ('view.invdockercontainers_of_host', {
            'description': u'invdockercontainers_of_host - A view for the Docker containers of one host',
            'name': 'view.invdockercontainers_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Docker containers (invdockercontainers_of_host)'
        }),
        ('mkeventd.update', {
            'description': u'Needed for acknowledging and changing the comment and contact of an event',
            'name': 'mkeventd.update',
            'defaults': ['user', 'admin'],
            'title': u'Update an event'
        }),
        ('view.ec_history_of_event', {
            'description': u'ec_history_of_event - History entries of one specific event',
            'name': 'view.ec_history_of_event',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - History of Event (ec_history_of_event)'
        }),
        ('view.aggr_hostproblems', {
            'description': u'aggr_hostproblems - All single-host aggregations that are in non-OK state (honoring state assumptions)',
            'name': 'view.aggr_hostproblems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Single-Host Problems (aggr_hostproblems)'
        }),
        ('general.delete_foreign_custom_snapin', {
            'description': u'Allows to delete Custom snapins created by other users.',
            'name': 'general.delete_foreign_custom_snapin',
            'defaults': ['admin'],
            'title': u'Delete foreign Custom snapins'
        }),
        ('view.sitesvcs', {
            'description': u'sitesvcs - All services of a given site.',
            'name': 'view.sitesvcs',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services of Site (sitesvcs)'
        }),
        ('general.force_reports', {
            'description': u'Make own published reports override builtin reports for all users.',
            'name': 'general.force_reports',
            'defaults': ['admin'],
            'title': u'Modify builtin reports'
        }),
        ('view.hostgroups', {
            'description': u'hostgroups - A short overview over all host groups, without an explicity listing of the actual hosts',
            'name': 'view.hostgroups',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hostgroups - Host Groups (Summary) (hostgroups)'
        }),
        ('wato.icons', {
            'description': u'Upload or delete custom icons',
            'name': 'wato.icons',
            'defaults': ['admin'],
            'title': u'Manage Custom Icons'
        }),
        ('general.delete_foreign_graph_tuning', {
            'description': u'Allows to delete Graph tunings created by other users.',
            'name': 'general.delete_foreign_graph_tuning',
            'defaults': ['admin'],
            'title': u'Delete foreign Graph tunings'
        }),
        (u'notification_plugin.victorops', {
            'description': u'',
            'name': u'notification_plugin.victorops',
            'defaults': ['admin', 'user'],
            'title': u'VictorOPS'
        }),
        ('wato.timeperiods', {
            'description': u'Access to the module <i>Timeperiods</i>',
            'name': 'wato.timeperiods',
            'defaults': ['admin'],
            'title': u'Timeperiods'
        }),
        ('wato.edit_folders', {
            'description': u'Modify the properties of existing folders.',
            'name': 'wato.edit_folders',
            'defaults': ['admin', 'user'],
            'title': u'Modify existing folders'
        }),
        ('view.nagstamon_hosts', {
            'description': u'nagstamon_hosts - The view is intended for NagStaMon as web service.',
            'name': 'view.nagstamon_hosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host problems for NagStaMon (nagstamon_hosts)'
        }),
        ('action.acknowledge', {
            'description': u'Acknowledge host and service problems and remove acknowledgements',
            'name': 'action.acknowledge',
            'defaults': ['user', 'admin'],
            'title': u'Acknowledge'
        }),
        ('view.hostsvcnotifications', {
            'description': u'hostsvcnotifications - All notification events concerning the state of a certain host (including services)',
            'name': 'view.hostsvcnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Notifications of host & services (hostsvcnotifications)'
        }),
        ('view.invorainstance_of_host', {
            'description': u'invorainstance_of_host - A view for the Oracle instances of one host',
            'name': 'view.invorainstance_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Oracle instances (invorainstance_of_host)'
        }),
        ('action.downtimes', {
            'description': u'Schedule and remove downtimes on hosts and services',
            'name': 'action.downtimes',
            'defaults': ['user', 'admin'],
            'title': u'Set/Remove downtimes'
        }),
        ('background_jobs.see_foreign_jobs', {
            'description': u'Allows you to see jobs of other users.',
            'name': 'background_jobs.see_foreign_jobs',
            'defaults': ['admin'],
            'title': u'See foreign background jobs'
        }),
        ('view.invfan_of_host', {
            'description': u'invfan_of_host - A view for the Fans of one host',
            'name': 'view.invfan_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Fans (invfan_of_host)'
        }),
        ('wato.rename_hosts', {
            'description': u'Rename existing hosts. Please also add the permission <i>Modify existing hosts</i>.',
            'name': 'wato.rename_hosts',
            'defaults': ['admin'],
            'title': u'Rename existing hosts'
        }),
        ('general.ignore_soft_limit', {
            'description': u'Allows to ignore the soft query limit imposed upon the number of datasets returned by a query',
            'name': 'general.ignore_soft_limit',
            'defaults': ['admin', 'user'],
            'title': u'Ignore soft query limit'
        }),
        ('view.invstack_search', {
            'description': u'invstack_search - A view for searching in the inventory data for Stacks',
            'name': 'view.invstack_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Stacks (invstack_search)'
        }),
        ('view.mobile_service', {
            'description': 'mobile_service - This view is used by the mobile GUI',
            'name': 'view.mobile_service',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Services - Service (mobile_service)'
        }),
        ('nagvis.Map_edit_*', {
            'description': u'Grants modify access to all maps.',
            'name': 'nagvis.Map_edit_*',
            'defaults': [],
            'title': u'Edit all maps'
        }),
        ('general.delete_stored_report', {
            'description': u'Allows to delete own Stored reports.',
            'name': 'general.delete_stored_report',
            'defaults': ['admin', 'user'],
            'title': u'Delete Stored reports'
        }),
        ('view.mobile_searchsvc', {
            'description': 'mobile_searchsvc - This view is used by the mobile GUI',
            'name': 'view.mobile_searchsvc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Services - Search (mobile_searchsvc)'
        }),
        ('view.searchsvc', {
            'description': u'searchsvc - Almost all available filters, used for searching services and maybe doing actions',
            'name': 'view.searchsvc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service search (searchsvc)'
        }),
        ('report.bi_availability', {
            'description': u'',
            'name': 'report.bi_availability',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI Availability'
        }),
        ('sidesnap.dashboards', {
            'description': u'Links to all dashboards',
            'name': 'sidesnap.dashboards',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Dashboards'
        }),
        ('view.starred_hosts', {
            'description': u'starred_hosts - Overall state of your favorite hosts',
            'name': 'view.starred_hosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Favorite hosts (starred_hosts)'
        }),
        ('general.edit_profile', {
            'description': u'Permits the user to change the user profile settings.',
            'name': 'general.edit_profile',
            'defaults': ['admin', 'user'],
            'title': u'Edit the user profile'
        }),
        ('general.delete_foreign_reports', {
            'description': u'Allows to delete reports created by other users.',
            'name': 'general.delete_foreign_reports',
            'defaults': ['admin'],
            'title': u'Delete foreign reports'
        }),
        ('view.ec_events_of_monhost', {
            'description': u'ec_events_of_monhost - Currently open events of a host that is monitored',
            'name': 'view.ec_events_of_monhost',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Events of Monitored Host (ec_events_of_monhost)'
        }),
        ('view.alerthandlers', {
            'description': u'alerthandlers - All alert handler executions.',
            'name': 'view.alerthandlers',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Alert handler executions (alerthandlers)'
        }),
        ('general.see_stales_in_tactical_overview', {
            'description': u'Show the column for stale host and service checks in the tactical overview snapin.',
            'name': 'general.see_stales_in_tactical_overview',
            'defaults': ['guest', 'user', 'admin'],
            'title': u'See stale objects in tactical overview snapin'
        }),
        ('report.instant_availability', {
            'description': '',
            'name': 'report.instant_availability',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Template for PDF exporting of availability views'
        }),
        ('view.events_dash', {
            'description': 'events_dash - Events of the last 4 hours.',
            'name': 'view.events_dash',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Events of the last 4 hours (for the dashboard) (events_dash)'
        }),
        ('wato.sign_agents', {
            'description': u'Sign baked agent packages for Linux, Windows and other operating systems',
            'name': 'wato.sign_agents',
            'defaults': ['admin'],
            'title': u'Sign agents'
        }),
        ('view.events', {
            'description': u'events - All historic events of hosts or services (alerts, downtimes, etc.)',
            'name': 'view.events',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Host- and Service events (events)'
        }),
        ('background_jobs.stop_foreign_jobs', {
            'description': u'Allows you to stop jobs of other users. Note: some jobs cannot be stopped.',
            'name': 'background_jobs.stop_foreign_jobs',
            'defaults': ['admin'],
            'title': u'Stop foreign background jobs'
        }),
        ('general.force_dashboards', {
            'description': u'Make own published dashboards override builtin dashboards for all users.',
            'name': 'general.force_dashboards',
            'defaults': ['admin'],
            'title': u'Modify builtin dashboards'
        }),
        ('view.hostnotifications', {
            'description': u'hostnotifications - Notification events of hosts.',
            'name': 'view.hostnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Notifications of host (hostnotifications)'
        }),
        ('wato.all_folders', {
            'description': u'Without this permission, operations on folders can only be done by users that are members of one of the folders contact groups. This permission grants full access to all folders and hosts.',
            'name': 'wato.all_folders',
            'defaults': ['admin'],
            'title': u'Write access to all hosts and folders'
        }),
        ('wato.hosttags', {
            'description': u'Create, remove and edit host tags. Removing host tags also might remove rules, so this permission should not be available to normal users. ',
            'name': 'wato.hosttags',
            'defaults': ['admin'],
            'title': u'Manage host tags'
        }),
        ('view.mobile_hostsvcnotifications', {
            'description': 'mobile_hostsvcnotifications - This view is used by the mobile GUI',
            'name': 'view.mobile_hostsvcnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Notifications of host & services (mobile_hostsvcnotifications)'
        }),
        ('wato.manage_mkps', {
            'description': u'Allows to upload, install, deinstall, create and modify extension packages (MKPs). Note: MKPs contain executable code.',
            'name': 'wato.manage_mkps',
            'defaults': ['admin'],
            'title': u'Manage Extension Packages (MKPs)'
        }),
        ('nagvis.Rotation_view_*', {
            'description': u'Grants read access to all rotations.',
            'name': 'nagvis.Rotation_view_*',
            'defaults': ['guest'],
            'title': u'Use all map rotations'
        }),
        ('general.publish_graph_collection', {
            'description': u'Make Graph Collections visible and usable for other users.',
            'name': 'general.publish_graph_collection',
            'defaults': ['admin', 'user'],
            'title': u'Publish Graph Collections'
        }),
        ('general.publish_dashboards_to_foreign_groups', {
            'description': u'Make dashboards visible and usable for users of contact groups the publishing user is not a member of.',
            'name': 'general.publish_dashboards_to_foreign_groups',
            'defaults': ['admin'],
            'title': u'Publish dashboards to foreign contact groups'
        }),
        ('mkeventd.switchmode', {
            'description': u'This permission is only useful if the Event Console is setup as a replication slave. It allows a manual switch between sync and takeover mode.',
            'name': 'mkeventd.switchmode',
            'defaults': ['admin'],
            'title': u'Switch slave replication mode'
        }),
        ('general.see_user_graph_collection', {
            'description': u'Is needed for seeing Graph Collections that other users have created.',
            'name': 'general.see_user_graph_collection',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Graph Collections'
        }),
        ('view.allservices', {
            'description': u'allservices - All services grouped by hosts.',
            'name': 'view.allservices',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - All services (allservices)'
        }),
        ('wato.global', {
            'description': u'Access to the module <i>Global settings</i>',
            'name': 'wato.global',
            'defaults': ['admin'],
            'title': u'Global settings'
        }),
        ('wato.see_all_folders', {
            'description': u'Users without this permissions can only see folders with a contact group they are in.',
            'name': 'wato.see_all_folders',
            'defaults': ['admin'],
            'title': u'Read access to all hosts and folders'
        }),
        ('view.invbackplane_search', {
            'description': u'invbackplane_search - A view for searching in the inventory data for Backplanes',
            'name': 'view.invbackplane_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Backplanes (invbackplane_search)'
        }),
        ('view.ec_event_mobile', {
            'description': u'ec_event_mobile - Details about one event\n',
            'name': 'view.ec_event_mobile',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Event Console - Event Details (ec_event_mobile)'
        }),
        ('sidesnap.cmc_stats', {
            'description': u'Live monitor of the performance statistics of the Check_MK Micro Core. Note: this snapin only works if <b>all</b> of your sites are running the Check_MK Cores',
            'name': 'sidesnap.cmc_stats',
            'defaults': ['admin'],
            'title': u'Micro Core Statistics'
        }),
        ('general.edit_foreign_graph_collection', {
            'description': u'Allows to edit Graph Collections created by other users.',
            'name': 'general.edit_foreign_graph_collection',
            'defaults': ['admin'],
            'title': u'Edit foreign Graph Collections'
        }),
        ('view.searchpnp', {
            'description': u'searchpnp - Search for services and display their graphs',
            'name': 'view.searchpnp',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Search Time Graphs (searchpnp)'
        }),
        ('view.host_ok', {
            'description': u'host_ok - All services of a given host that are in state OK',
            'name': 'view.host_ok',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - OK Services of host (host_ok)'
        }),
        ('background_jobs.delete_foreign_jobs', {
            'description': u'Allows you to delete jobs of other users. Note: some jobs cannot be deleted',
            'name': 'background_jobs.delete_foreign_jobs',
            'defaults': ['admin'],
            'title': u'Delete foreign background jobs'
        }),
        ('general.force_custom_snapin', {
            'description': u'Make own published Custom snapins override builtin Custom snapins for all users.',
            'name': 'general.force_custom_snapin',
            'defaults': ['admin'],
            'title': u'Modify builtin Custom snapins'
        }),
        ('view.invother_search', {
            'description': u'invother_search - A view for searching in the inventory data for Other entities',
            'name': 'view.invother_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Other entities (invother_search)'
        }),
        ('wato.agent_deploy_custom_files', {
            'description': u'Edit the ruleset "Deploy custom files with agent".',
            'name': 'wato.agent_deploy_custom_files',
            'defaults': ['admin'],
            'title': u'Configure custom agent file deployments'
        }),
        ('view.hosttiles', {
            'description': u'hosttiles - Displays hosts in a tiled layout, where each host is a single tile.',
            'name': 'view.hosttiles',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - All hosts (tiled) (hosttiles)'
        }),
        ('nagvis.Map_delete', {
            'description': u'Permits to delete all maps the user is contact for.',
            'name': 'nagvis.Map_delete',
            'defaults': ['user'],
            'title': u'Delete permitted maps'
        }),
        ('view.invmodule_search', {
            'description': u'invmodule_search - A view for searching in the inventory data for Modules',
            'name': 'view.invmodule_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Modules (invmodule_search)'
        }),
        ('general.force_graph_collection', {
            'description': u'Make own published Graph Collections override builtin Graph Collections for all users.',
            'name': 'general.force_graph_collection',
            'defaults': ['admin'],
            'title': u'Modify builtin Graph Collections'
        }),
        ('general.view_option_columns', {
            'description': u'Interactively change the number of columns being displayed by a view (does not edit or customize the view)',
            'name': 'general.view_option_columns',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Change view display columns'
        }),
        ('view.host_warn', {
            'description': u'host_warn - All services of a given host that are in state WARN',
            'name': 'view.host_warn',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - WARN Services of host (host_warn)'
        }),
        ('view.invunknown_search', {
            'description': u'invunknown_search - A view for searching in the inventory data for Unknown entities',
            'name': 'view.invunknown_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Unknown entities (invunknown_search)'
        }),
        ('view.svc_dt_hist', {
            'description': u'svc_dt_hist - All historic scheduled downtimes of a certain service',
            'name': 'view.svc_dt_hist',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Historic downtimes of service (svc_dt_hist)'
        }),
        ('general.ignore_hard_limit', {
            'description': u'Allows to ignore the hard query limit imposed upon the number of datasets returned by a query',
            'name': 'general.ignore_hard_limit',
            'defaults': ['admin'],
            'title': u'Ignore hard query limit'
        }),
        ('action.notifications', {
            'description': u'Enable and disable notifications on hosts and services',
            'name': 'action.notifications',
            'defaults': ['admin'],
            'title': u'Enable/disable notifications'
        }),
        ('sidesnap.views', {
            'description': u'Links to global views and dashboards',
            'name': 'sidesnap.views',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Views'
        }),
        ('general.edit_dashboards', {
            'description': u'Allows to create own dashboards, customize builtin dashboards and use them.',
            'name': 'general.edit_dashboards',
            'defaults': ['admin', 'user'],
            'title': u'Customize dashboards and use them'
        }),
        ('general.reporting', {
            'description': u'Allows the user to use the reporting, i.e. generate reports. For creating own report templates or customizing existing ones a dedicated permission is required.',
            'name': 'general.reporting',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Use Reporting'
        }),
        ('wato.download_agent_output', {
            'description': u'Allows to download the current agent output or SNMP walks of the monitored hosts.',
            'name': 'wato.download_agent_output',
            'defaults': ['admin'],
            'title': u'Download Agent Output / SNMP Walks'
        }),
        ('general.see_failed_notifications', {
            'description': u'If Check_MK is unable to notify users about problems, the site will warn about this situation very visibly inside the UI (both in the Tactical Overview and the Dashboard). This affects only users with this permission. Users with this permission will see failed notifications between now and the configured <a href="wato.py?mode=edit_configvar&varname=failed_notification_horizon">Failed notification horizon</a>.',
            'name': 'general.see_failed_notifications',
            'defaults': ['admin'],
            'title': u'See failed Notifications (all)'
        }),
        ('wato.service_discovery_to_monitored', {
            'description': u'Service discovery: Move to monitored services',
            'name': 'wato.service_discovery_to_monitored',
            'defaults': ['admin', 'user'],
            'title': u'Service discovery: Move to monitored services'
        }),
        ('view.downtimes_of_host', {
            'description': u'downtimes_of_host - Lists all host downtimes.',
            'name': 'view.downtimes_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Downtimes of host (downtimes_of_host)'
        }),
        ('general.see_user_graph_tuning', {
            'description': u'Is needed for seeing Graph tunings that other users have created.',
            'name': 'general.see_user_graph_tuning',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Graph tunings'
        }),
        ('view.invsensor_search', {
            'description': u'invsensor_search - A view for searching in the inventory data for Sensors',
            'name': 'view.invsensor_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Sensors (invsensor_search)'
        }),
        ('view.aggr_host', {
            'description': u'aggr_host - All aggregations the given host is part of',
            'name': 'view.aggr_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Aggregations Affected by Host (aggr_host)'
        }),
        ('view.mobile_host', {
            'description': 'mobile_host - This view is used by the mobile GUI',
            'name': 'view.mobile_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Services - Services of host (mobile_host)'
        }),
        ('view.svcproblems', {
            'description': u'svcproblems - All problems of services not currently in a downtime.',
            'name': 'view.svcproblems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service problems (svcproblems)'
        }),
        ('view.invinterface_of_host', {
            'description': u'invinterface_of_host - A view for the Network interfaces of one host',
            'name': 'view.invinterface_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Network interfaces (invinterface_of_host)'
        }),
        ('general.edit_sla_configuration', {
            'description': u'Allows to create own Service Level Agreements, customize builtin Service Level Agreements and use them.',
            'name': 'general.edit_sla_configuration',
            'defaults': ['admin', 'user'],
            'title': u'Customize Service Level Agreements and use them'
        }),
        ('view.contactnotifications', {
            'description': u'contactnotifications - All notification events sent to',
            'name': 'view.contactnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Notifications of contact (contactnotifications)'
        }),
        ('view.aggr_hostgroup_boxed', {
            'description': u'aggr_hostgroup_boxed - Hostgroup with boxed BIs for each host\n',
            'name': 'view.aggr_hostgroup_boxed',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Hostgroup with BI state (aggr_hostgroup_boxed)'
        }),
        ('wato.activate', {
            'description': u'This permission is needed for activating the current configuration (and thus rewriting the monitoring configuration and restart the monitoring daemon.)',
            'name': 'wato.activate',
            'defaults': ['admin', 'user'],
            'title': u'Activate Configuration'
        }),
        ('view.aggr_service', {
            'description': u'aggr_service - All aggregations affected by a certain service',
            'name': 'view.aggr_service',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Aggregations Affected by Service (aggr_service)'
        }),
        ('wato.manage_hosts', {
            'description': u'Add hosts to the monitoring and remove hosts from the monitoring. Please also add the permission <i>Modify existing hosts</i>.',
            'name': 'wato.manage_hosts',
            'defaults': ['admin', 'user'],
            'title': u'Add & remove hosts'
        }),
        ('general.edit_notifications', {
            'description': u'This allows a user to edit his personal notification settings. You also need the permission <i>Edit the user profile</i> in order to do this.',
            'name': 'general.edit_notifications',
            'defaults': ['admin', 'user'],
            'title': u'Edit personal notification settings'
        }),
        ('report.instant_graph_collection', {
            'description': '',
            'name': 'report.instant_graph_collection',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Template for PDF exporting of graph collections'
        }),
        ('sidesnap.mkeventd_performance', {
            'description': u'Monitor the performance of the Event Console',
            'name': 'sidesnap.mkeventd_performance',
            'defaults': ['admin'],
            'title': u'Event Console Performance'
        }),
        ('view.svcgroups', {
            'description': u'svcgroups - A short overview over all service groups, without explicity listing of the actual hosts and services',
            'name': 'view.svcgroups',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Servicegroups - Service Groups (Summary) (svcgroups)'
        }),
        ('sidesnap.nagios_legacy', {
            'description': u'The legacy Nagios GUI has been removed.',
            'name': 'sidesnap.nagios_legacy',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Old Nagios GUI'
        }),
        ('view.aggr_singlehost', {
            'description': u'aggr_singlehost - A single host related aggregation',
            'name': 'view.aggr_singlehost',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Single-Host Aggregations of Host (aggr_singlehost)'
        }),
        ('view.host_pending', {
            'description': u'host_pending - All services of a given host that are PENDING',
            'name': 'view.host_pending',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - PENDING Services of host (host_pending)'
        }),
        ('view.aggr_hostnameaggrs', {
            'description': u'aggr_hostnameaggrs - Host related aggregations',
            'name': 'view.aggr_hostnameaggrs',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Hostname Aggregations (aggr_hostnameaggrs)'
        }),
        ('wato.bi_rules', {
            'description': u'User the WATO BI module, create, modify and delete BI rules and aggregations in packs that you are a contact of',
            'name': 'wato.bi_rules',
            'defaults': ['admin', 'user'],
            'title': u'Business Intelligence Rules and Aggregations'
        }),
        ('general.acknowledge_werks', {
            'description': u'In the change log of the Check_MK software version the administrator can manage change log entries (Werks) that requrire user interaction. These <i>incompatible Werks</i> can be acknowledged only if the user has this permission.',
            'name': 'general.acknowledge_werks',
            'defaults': ['admin'],
            'title': u'Acknowledge Incompatible Werks'
        }),
        ('view.aggr_all_api', {
            'description': u'aggr_all_api - List of all aggregations, containing the name of aggregations and state information',
            'name': 'view.aggr_all_api',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - List of all Aggregations for simple API calls (aggr_all_api)'
        }),
        ('general.disable_notifications', {
            'description': u'This permissions provides a checkbox and timerange in the personal settings of the user that allows him to completely disable all of his notifications. Use with caution.',
            'name': 'general.disable_notifications',
            'defaults': ['admin'],
            'title': u'Disable all personal notifications'
        }),
        ('sidesnap.master_control', {
            'description': u'Buttons for switching globally states such as enabling checks and notifications',
            'name': 'sidesnap.master_control',
            'defaults': ['admin'],
            'title': u'Master Control'
        }),
        ('wato.download_agents', {
            'description': u'Download the default Check_MK monitoring agents for Linux, Windows and other operating systems.',
            'name': 'wato.download_agents',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Monitoring Agents'
        }),
        ('nagvis.*_*_*', {
            'description': u'This permission grants full access to NagVis.',
            'name': 'nagvis.*_*_*',
            'defaults': ['admin'],
            'title': u'Full access'
        }),
        ('general.publish_dashboards', {
            'description': u'Make dashboards visible and usable for other users.',
            'name': 'general.publish_dashboards',
            'defaults': ['admin', 'user'],
            'title': u'Publish dashboards'
        }),
        (u'notification_plugin.spectrum', {
            'description': u'',
            'name': u'notification_plugin.spectrum',
            'defaults': ['admin', 'user'],
            'title': u'Spectrum Server'
        }),
        ('view.mobile_contactnotifications', {
            'description': 'mobile_contactnotifications - This view is used by the mobile GUI',
            'name': 'view.mobile_contactnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Notifications of contact (mobile_contactnotifications)'
        }),
        ('view.sitehosts', {
            'description': u'sitehosts - Link view showing all hosts of one site',
            'name': 'view.sitehosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - All hosts of site (sitehosts)'
        }),
        ('view.invorasga_search', {
            'description': u'invorasga_search - A view for searching in the inventory data for Oracle performance',
            'name': 'view.invorasga_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Oracle performance (invorasga_search)'
        }),
        ('sidesnap.problem_hosts', {
            'description': u'A summary state of all hosts that have a problem, with links to problems of those hosts',
            'name': 'sidesnap.problem_hosts',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Problem Hosts'
        }),
        ('general.edit_bookmark_list', {
            'description': u'Allows to create own Bookmark lists, customize builtin Bookmark lists and use them.',
            'name': 'general.edit_bookmark_list',
            'defaults': ['admin', 'user'],
            'title': u'Customize Bookmark lists and use them'
        }),
        ('general.see_user_bookmark_list', {
            'description': u'Is needed for seeing Bookmark lists that other users have created.',
            'name': 'general.see_user_bookmark_list',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Bookmark lists'
        }),
        ('view.svcbygroups', {
            'description': u'svcbygroups - Service grouped by service groups. Services not member of a group are not displayed. Services being in more groups, are displayed once for each group',
            'name': 'view.svcbygroups',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services by group (svcbygroups)'
        }),
        ('view.pending_discovery', {
            'description': u'pending_discovery - Differences to currently monitored services on a host.',
            'name': 'view.pending_discovery',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Pending service discovery (pending_discovery)'
        }),
        ('general.edit_custom_graph', {
            'description': u'Allows to create own Custom Graphs, customize builtin Custom Graphs and use them.',
            'name': 'general.edit_custom_graph',
            'defaults': ['admin', 'user'],
            'title': u'Customize Custom Graphs and use them'
        }),
        ('view.mobile_svcevents', {
            'description': 'mobile_svcevents - This view is used by the mobile GUI',
            'name': 'view.mobile_svcevents',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Log - Events of service (mobile_svcevents)'
        }),
        ('mkeventd.actions', {
            'description': u'This permission is needed for performing the configured actions (execution of scripts and sending emails).',
            'name': 'mkeventd.actions',
            'defaults': ['user', 'admin'],
            'title': u'Perform custom action'
        }),
        ('view.hosts', {
            'description': u'hosts - All services of hosts which match a name',
            'name': 'view.hosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services of Hosts (hosts)'
        }),
        ('view.svcnotifications', {
            'description': u'svcnotifications - All notification events concerning the state of a certain service.',
            'name': 'view.svcnotifications',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Service Notifications (svcnotifications)'
        }),
        ('view.invorainstance_search', {
            'description': u'invorainstance_search - A view for searching in the inventory data for Oracle instances',
            'name': 'view.invorainstance_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Oracle instances (invorainstance_search)'
        }),
        ('view.hostgroupgrid', {
            'description': u'hostgroupgrid - Hosts grouped by hostgroups, with a brief list of all services',
            'name': 'view.hostgroupgrid',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host Groups (Grid) (hostgroupgrid)'
        }),
        ('general.act', {
            'description': u'Allows users to perform Nagios commands. If no further permissions are granted, actions can only be done on objects one is a contact for',
            'name': 'general.act',
            'defaults': ['admin', 'user'],
            'title': u'Perform commands'
        }),
        ('wato.hosts', {
            'description': u'Access to the management of hosts and folders. This module has some additional permissions (see below).',
            'name': 'wato.hosts',
            'defaults': ['admin', 'user'],
            'title': u'Host management'
        }),
        ('view.api_downtimes', {
            'description': u'api_downtimes - All host- and service-downtimes (including ids)',
            'name': 'view.api_downtimes',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Downtimes (api_downtimes)'
        }),
        ('report.instant_view', {
            'description': '',
            'name': 'report.instant_view',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Template for PDF exporting of views'
        }),
        ('wato.random_hosts', {
            'description': u'The creation of random hosts is a facility for test and development and disabled by default. It allows you to create a number of random hosts and thus simulate larger environments.',
            'name': 'wato.random_hosts',
            'defaults': [],
            'title': u'Create random hosts'
        }),
        ('sidesnap.bookmarks', {
            'description': u'A simple and yet practical snapin allowing to create bookmarks to views and other content in the main frame',
            'name': 'sidesnap.bookmarks',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Bookmarks'
        }),
        ('view.aggr_single_api', {
            'description': u'aggr_single_api - Single Aggregation for simple API calls. Contains the state and state output.',
            'name': 'view.aggr_single_api',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Single Aggregation for simple API calls (aggr_single_api)'
        }),
        ('wato.update_dns_cache', {
            'description': u'Updating the DNS cache is neccessary in order to reflect IP address changes in hosts that are configured without an explicit address.',
            'name': 'wato.update_dns_cache',
            'defaults': ['admin', 'user'],
            'title': u'Update DNS Cache'
        }),
        ('view.aggr_summary', {
            'description': u'aggr_summary - Simple summary page of all BI aggregates that is used as a web services.',
            'name': 'view.aggr_summary',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - BI Aggregations Summary State (aggr_summary)'
        }),
        ('background_jobs.stop_jobs', {
            'description': u'Configures the permission to stop background jobs. Note: some jobs cannot be stopped.',
            'name': 'background_jobs.stop_jobs',
            'defaults': ['user', 'admin'],
            'title': u'Stop background jobs'
        }),
        (u'notification_plugin..f12', {
            'description': u'',
            'name': u'notification_plugin..f12',
            'defaults': ['admin', 'user'],
            'title': u'.f12'
        }),
        ('view.hostsvcevents', {
            'description': u'hostsvcevents - All historic events concerning the state of a certain host (including services)',
            'name': 'view.hostsvcevents',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Events of host & services (hostsvcevents)'
        }),
        ('mkeventd.update_contact', {
            'description': u'Needed for changing a contact when updating an event',
            'name': 'mkeventd.update_contact',
            'defaults': ['user', 'admin'],
            'title': u'Update an event: change contact'
        }),
        ('view.hostevents', {
            'description': u'hostevents - All historic events concerning the state of a certain host (without services)',
            'name': 'view.hostevents',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Events of host (hostevents)'
        }),
        ('view.invpsu_search', {
            'description': u'invpsu_search - A view for searching in the inventory data for Power supplies',
            'name': 'view.invpsu_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Power supplies (invpsu_search)'
        }),
        ('view.invorarecoveryarea_search', {
            'description': u'invorarecoveryarea_search - A view for searching in the inventory data for Oracle recovery areas',
            'name': 'view.invorarecoveryarea_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Oracle recovery areas (invorarecoveryarea_search)'
        }),
        ('background_jobs.manage_jobs', {
            'description': u'Allows you to see the job overview page.',
            'name': 'background_jobs.manage_jobs',
            'defaults': ['admin'],
            'title': u'Manage background jobs'
        }),
        ('report.default', {
            'description': '',
            'name': 'report.default',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Default template for all reports'
        }),
        ('background_jobs.delete_jobs', {
            'description': u'Configures the permission to delete background jobs. Note: some jobs cannot be deleted.',
            'name': 'background_jobs.delete_jobs',
            'defaults': ['user', 'admin'],
            'title': u'Delete background jobs'
        }),
        ('general.publish_views', {
            'description': u'Make views visible and usable for other users.',
            'name': 'general.publish_views',
            'defaults': ['admin', 'user'],
            'title': u'Publish views'
        }),
        ('sidesnap.search', {
            'description': u'Interactive search field for direct access to hosts, services, host- and servicegroups.<br>You can use the following filters:<br> <i>h:</i> Host, <i>s:</i> Service<br> <i>hg:</i> Hostgroup, <i>sg:</i> Servicegroup<br><i>ad:</i> Address, <i>al:</i> Alias, <i>tg:</i> Hosttag',
            'name': 'sidesnap.search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Quicksearch'
        }),
        ('view.host_graphs', {
            'description': u'host_graphs - Shows host graphs including timerange selections of a collection of hosts.',
            'name': 'view.host_graphs',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host Graphs (host_graphs)'
        }),
        ('sidesnap.performance', {
            'description': u'Live monitor of the overall performance of all monitoring servers',
            'name': 'sidesnap.performance',
            'defaults': ['admin'],
            'title': u'Server Performance'
        }),
        ('general.delete_foreign_sla_configuration', {
            'description': u'Allows to delete Service Level Agreements created by other users.',
            'name': 'general.delete_foreign_sla_configuration',
            'defaults': ['admin'],
            'title': u'Delete foreign Service Level Agreements'
        }),
        ('wato.manage_folders', {
            'description': u'Add new folders and delete existing folders. If a folder to be deleted contains hosts then the permission to delete hosts is also required.',
            'name': 'wato.manage_folders',
            'defaults': ['admin', 'user'],
            'title': u'Add & remove folders'
        }),
        ('wato.add_or_modify_executables', {
            'description': u'There are different places in Check_MK where an admin can use the GUI to add executable code to Check_MK. For example when configuring datasource programs, the user inserts a command line for gathering monitoring data. This command line is then executed during monitoring by Check_MK. Another example is the upload of extension packages (MKPs). All these functions have in common that the user provides data that is executed by Check_MK. If you want to ensure that your WATO users cannot "inject" arbitrary executables into your Check_MK installation, you only need to remove this permission for them. This permission is needed in addition to the other component related permissions. For example you need the <tt>wato.rulesets</tt> permission together with this permission to be able to configure rulesets where bare command lines are configured.',
            'name': 'wato.add_or_modify_executables',
            'defaults': ['admin'],
            'title': u'Can add or modify executables'
        }),
        ('general.publish_views_to_foreign_groups', {
            'description': u'Make views visible and usable for users of contact groups the publishing user is not a member of.',
            'name': 'general.publish_views_to_foreign_groups',
            'defaults': ['admin'],
            'title': u'Publish views to foreign contact groups'
        }),
        ('general.delete_foreign_custom_graph', {
            'description': u'Allows to delete Custom Graphs created by other users.',
            'name': 'general.delete_foreign_custom_graph',
            'defaults': ['admin'],
            'title': u'Delete foreign Custom Graphs'
        }),
        ('view.starred_services', {
            'description': u'starred_services - All of your favorites services by hosts.',
            'name': 'view.starred_services',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Favorite services (starred_services)'
        }),
        ('sidesnap.tactical_overview', {
            'description': u'The total number of hosts and service with and without problems',
            'name': 'sidesnap.tactical_overview',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Tactical Overview'
        }),
        ('view.mobile_hoststatus', {
            'description': 'mobile_hoststatus - This view is used by the mobile GUI',
            'name': 'view.mobile_hoststatus',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Hosts - Host status (mobile_hoststatus)'
        }),
        ('mkeventd.delete', {
            'description': u'Finally archive an event without any further action',
            'name': 'mkeventd.delete',
            'defaults': ['user', 'admin'],
            'title': u'Archive an event'
        }),
        ('view.aggr_singlehosts', {
            'description': u'aggr_singlehosts - Lists all aggregations which only rely on information of one host.',
            'name': 'view.aggr_singlehosts',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Single-Host Aggregations (aggr_singlehosts)'
        }),
        ('sidesnap.wato_foldertree', {
            'description': u'This snapin shows the folders defined in WATO. It can be used to open views filtered by the WATO folder. It works standalone, without interaction with any other snapin.',
            'name': 'sidesnap.wato_foldertree',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Tree of folders'
        }),
        ('view.nagstamon_svc', {
            'description': u'nagstamon_svc - This view is intended for usage as web service for NagStaMon.',
            'name': 'view.nagstamon_svc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service problems for NagStaMon (nagstamon_svc)'
        }),
        ('mkeventd.changestate', {
            'description': u'This permission allows to change the state classification of an event (e.g. from CRIT to WARN).',
            'name': 'mkeventd.changestate',
            'defaults': ['user', 'admin'],
            'title': u'Change event state'
        }),
        ('wato.passwords', {
            'description': u'This permission is needed for the module <i>Passwords</i>.',
            'name': 'wato.passwords',
            'defaults': ['admin', 'user'],
            'title': u'Password management'
        }),
        ('view.mobile_svcproblems_unack', {
            'description': 'mobile_svcproblems_unack - This view is used by the mobile GUI',
            'name': 'view.mobile_svcproblems_unack',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Services - Problems (unhandled) (mobile_svcproblems_unack)'
        }),
        ('mkeventd.activate', {
            'description': u'Activation of changes for the event console (rule modification, global settings) is done separately from the monitoring configuration and needs this permission.',
            'name': 'mkeventd.activate',
            'defaults': ['admin'],
            'title': u'Activate changes for event console'
        }),
        ('view.hostsbygroup', {
            'description': u'hostsbygroup - A complete listing of all host groups and each of their hosts',
            'name': 'view.hostsbygroup',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Host Groups (hostsbygroup)'
        }),
        ('general.see_availability', {
            'description': u'See the availability views of hosts and services',
            'name': 'general.see_availability',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See the availability'
        }),
        ('view.ec_history_of_host', {
            'description': u'ec_history_of_host - History entries of one specific host',
            'name': 'view.ec_history_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Event History of Host (ec_history_of_host)'
        }),
        ('wato.diag_host', {
            'description': u'Check whether or not the host is reachable, test the different methods a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out the correct monitoring configuration for that host.',
            'name': 'wato.diag_host',
            'defaults': ['admin', 'user'],
            'title': u'Host Diagnostic'
        }),
        ('view.unmonitored_services', {
            'description': u'unmonitored_services - Services not being monitored due to configuration.',
            'name': 'view.unmonitored_services',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Unmonitored services (unmonitored_services)'
        }),
        ('sidesnap.wato_folders', {
            'description': u'This snapin shows the folders defined in WATO. It can be used to open views filtered by the WATO folder. This snapin interacts with the "Views" snapin, when both are enabled.',
            'name': 'sidesnap.wato_folders',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Folders'
        }),
        ('sidesnap.custom_links', {
            'description': u'This snapin contains custom links which can be configured via the configuration variable <tt>custom_links</tt> in <tt>multisite.mk</tt>',
            'name': 'sidesnap.custom_links',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Custom Links'
        }),
        ('action.remove_all_downtimes', {
            'description': u'Allow the user to use the action "Remove all" downtimes',
            'name': 'action.remove_all_downtimes',
            'defaults': ['user', 'admin'],
            'title': u'Remove all downtimes'
        }),
        ('wato.alert_handlers', {
            'description': u'This permission is needed for creating alert handlers, which automatically execute custom scripts upon monitoring alerts.',
            'name': 'wato.alert_handlers',
            'defaults': ['admin'],
            'title': u'Alert handler configuration'
        }),
        ('view.invdockerimages_of_host', {
            'description': u'invdockerimages_of_host - A view for the Docker images of one host',
            'name': 'view.invdockerimages_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Docker images (invdockerimages_of_host)'
        }),
        ('wato.clone_hosts', {
            'description': u'Clone existing hosts to create new ones from the existing one.Please also add the permission <i>Add & remove hosts</i>.',
            'name': 'wato.clone_hosts',
            'defaults': ['admin', 'user'],
            'title': u'Clone hosts'
        }),
        (u'notification_plugin.sms', {
            'description': u'',
            'name': u'notification_plugin.sms',
            'defaults': ['admin', 'user'],
            'title': u'SMS (using smstools)'
        }),
        ('general.edit_reports', {
            'description': u'Allows to create own reports, customize builtin reports and use them.',
            'name': 'general.edit_reports',
            'defaults': ['admin', 'user'],
            'title': u'Customize reports and use them'
        }),
        ('view.aggr_group', {
            'description': u'aggr_group - Displays all aggregations of a certain group.',
            'name': 'view.aggr_group',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'BI - Aggregation group (aggr_group)'
        }),
        ('view.mobile_searchhost', {
            'description': 'mobile_searchhost - This view is used by the mobile GUI',
            'name': 'view.mobile_searchhost',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Hosts - Search (mobile_searchhost)'
        }),
        ('general.force_custom_graph', {
            'description': u'Make own published Custom Graphs override builtin Custom Graphs for all users.',
            'name': 'general.force_custom_graph',
            'defaults': ['admin'],
            'title': u'Modify builtin Custom Graphs'
        }),
        ('general.view_option_refresh', {
            'description': u'Interactively change the automatic browser reload of a view being displayed (does not edit or customize the view)',
            'name': 'general.view_option_refresh',
            'defaults': ['admin', 'user'],
            'title': u'Change view display refresh'
        }),
        (u'notification_plugin.pagerduty', {
            'description': u'',
            'name': u'notification_plugin.pagerduty',
            'defaults': ['admin', 'user'],
            'title': u'PagerDuty'
        }),
        ('nagvis.Map_edit', {
            'description': u'Grants modify access to all maps the user is contact for.',
            'name': 'nagvis.Map_edit',
            'defaults': ['user'],
            'title': u'Edit permitted maps'
        }),
        ('view.mobile_hostproblems', {
            'description': 'mobile_hostproblems - This view is used by the mobile GUI',
            'name': 'view.mobile_hostproblems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Hosts - Problems (all) (mobile_hostproblems)'
        }),
        ('general.see_crash_reports', {
            'description': u'In case an exception happens while Check_MK is running it may produce crash reports that you can use to track down the issues in the code or send it as report to the Check_MK team to fix this issue Only users with this permission are able to see the reports in the GUI.',
            'name': 'general.see_crash_reports',
            'defaults': ['admin'],
            'title': u'See crash reports'
        }),
        ('general.delete_foreign_bookmark_list', {
            'description': u'Allows to delete Bookmark lists created by other users.',
            'name': 'general.delete_foreign_bookmark_list',
            'defaults': ['admin'],
            'title': u'Delete foreign Bookmark lists'
        }),
        ('view.host_dt_hist', {
            'description': u'host_dt_hist - All historic scheduled downtimes of a certain host',
            'name': 'view.host_dt_hist',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Historic downtimes of host (host_dt_hist)'
        }),
        ('view.invpsu_of_host', {
            'description': u'invpsu_of_host - A view for the Power supplies of one host',
            'name': 'view.invpsu_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Power supplies (invpsu_of_host)'
        }),
        ('nagvis.Map_view_*', {
            'description': u'Grants read access to all maps.',
            'name': 'nagvis.Map_view_*',
            'defaults': ['guest'],
            'title': u'View all maps'
        }),
        ('general.force_graph_tuning', {
            'description': u'Make own published Graph tunings override builtin Graph tunings for all users.',
            'name': 'general.force_graph_tuning',
            'defaults': ['admin'],
            'title': u'Modify builtin Graph tunings'
        }),
        ('view.host_export', {
            'description': u'host_export - All services of a given host. The host and site must be set via HTTP variables.',
            'name': 'view.host_export',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services of Host (host_export)'
        }),
        ('dashboard.main', {
            'description': u'This dashboard gives you a general overview on the state of your monitored devices.',
            'name': 'dashboard.main',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Main Overview'
        }),
        ('wato.clear_auditlog', {
            'description': u'Clear the entries of the audit log. To be able to clear the audit log a user needs the generic WATO permission "Make changes, perform actions", the "View audit log" and this permission.',
            'name': 'wato.clear_auditlog',
            'defaults': ['admin'],
            'title': u'Clear audit Log'
        }),
        ('wato.services', {
            'description': u'Do inventory and service configuration on existing hosts.',
            'name': 'wato.services',
            'defaults': ['admin', 'user'],
            'title': u'Manage services'
        }),
        ('wato.edit_all_passwords', {
            'description': u'Without this permission, users can only edit passwords which are shared with a contact group they are member of. This permission grants full access to all passwords.',
            'name': 'wato.edit_all_passwords',
            'defaults': ['admin'],
            'title': u'Write access to all passwords'
        }),
        ('wato.set_read_only', {
            'description': u'Prevent other users from making modifications to WATO.',
            'name': 'wato.set_read_only',
            'defaults': ['admin'],
            'title': u'Set WATO to read only mode for other users'
        }),
        ('general.schedule_reports', {
            'description': u'Allows a user to create or modify entries in the report scheduler.',
            'name': 'general.schedule_reports',
            'defaults': ['user', 'admin'],
            'title': u'Manage Own Scheduled Reports'
        }),
        ('dashboard.topology', {
            'description': u'This dashboard uses the parent relationships of your hosts to display a hierarchical map.',
            'name': 'dashboard.topology',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Network Topology'
        }),
        ('view.servicegroup', {
            'description': u'servicegroup - Services of a service group',
            'name': 'view.servicegroup',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service Group (servicegroup)'
        }),
        ('sidesnap.time', {
            'description': u'A large clock showing the current time of the web server',
            'name': 'sidesnap.time',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Server Time'
        }),
        ('view.invoratablespace_of_host', {
            'description': u'invoratablespace_of_host - A view for the Oracle tablespaces of one host',
            'name': 'view.invoratablespace_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Oracle tablespaces (invoratablespace_of_host)'
        }),
        ('wato.edit', {
            'description': u'This permission is needed in order to make any changes or perform any actions at all. Without this permission, the user is only able to view data, and that only in modules he has explicit permissions for.',
            'name': 'wato.edit',
            'defaults': ['admin', 'user'],
            'title': u'Make changes, perform actions'
        }),
        ('action.addcomment', {
            'description': u'Add comments to hosts or services, and remove comments',
            'name': 'action.addcomment',
            'defaults': ['user', 'admin'],
            'title': u'Add comments'
        }),
        ('view.comments_of_service', {
            'description': u'comments_of_service - Linkable view showing all comments of a specific service',
            'name': 'view.comments_of_service',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Comments of service (comments_of_service)'
        }),
        ('general.publish_stored_report', {
            'description': u'Make Stored reports visible and usable for other users.',
            'name': 'general.publish_stored_report',
            'defaults': ['admin', 'user'],
            'title': u'Publish Stored reports'
        }),
        ('view.hostpnp', {
            'description': u'hostpnp - All graphs for a certain host.',
            'name': 'view.hostpnp',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service graphs of host (hostpnp)'
        }),
        ('view.inv_host', {
            'description': u'inv_host - The complete hardware- and software inventory of a host',
            'name': 'view.inv_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Inventory of host (inv_host)'
        }),
        ('general.publish_graph_tuning', {
            'description': u'Make Graph tunings visible and usable for other users.',
            'name': 'general.publish_graph_tuning',
            'defaults': ['admin', 'user'],
            'title': u'Publish Graph tunings'
        }),
        ('view.invmodule_of_host', {
            'description': u'invmodule_of_host - A view for the Modules of one host',
            'name': 'view.invmodule_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Modules (invmodule_of_host)'
        }),
        ('view.pendingsvc', {
            'description': u'pendingsvc - Lists all services in state PENDING.',
            'name': 'view.pendingsvc',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Pending Services (pendingsvc)'
        }),
        ('view.invcontainer_of_host', {
            'description': u'invcontainer_of_host - A view for the HW containers of one host',
            'name': 'view.invcontainer_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - HW containers (invcontainer_of_host)'
        }),
        ('general.delete_foreign_views', {
            'description': u'Allows to delete views created by other users.',
            'name': 'general.delete_foreign_views',
            'defaults': ['admin'],
            'title': u'Delete foreign views'
        }),
        ('view.ec_events_mobile', {
            'description': u'ec_events_mobile - Table of all currently open events (handled and unhandled)\n',
            'name': 'view.ec_events_mobile',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Event Console - Events (ec_events_mobile)'
        }),
        ('general.publish_bookmark_list', {
            'description': u'Make Bookmark lists visible and usable for other users.',
            'name': 'general.publish_bookmark_list',
            'defaults': ['admin', 'user'],
            'title': u'Publish Bookmark lists'
        }),
        ('general.use', {
            'description': u'Users without this permission are not let in at all',
            'name': 'general.use',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Use Multisite at all'
        }),
        ('view.mobile_svcproblems', {
            'description': 'mobile_svcproblems - This view is used by the mobile GUI',
            'name': 'view.mobile_svcproblems',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Mobile - Services - Problems (all) (mobile_svcproblems)'
        }),
        ('view.svcevents', {
            'description': u'svcevents - All historic events concerning the state of a certain service',
            'name': 'view.svcevents',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - Events of service (svcevents)'
        }),
        ('view.service_check_durations', {
            'description': u'service_check_durations - All services ordered by their service check durations, grouped by their sites.\n',
            'name': 'view.service_check_durations',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Service check durations (service_check_durations)'
        }),
        ('sidesnap.biaggr_groups', {
            'description': u'A direct link to all groups of BI aggregations',
            'name': 'sidesnap.biaggr_groups',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'BI Aggregation Groups'
        }),
        ('view.allhosts_mini', {
            'description': u'allhosts_mini - Showing all hosts in a compact layout.',
            'name': 'view.allhosts_mini',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - All hosts (Mini) (allhosts_mini)'
        }),
        ('view.invinterface_search', {
            'description': u'invinterface_search - A view for searching in the inventory data for Network interfaces',
            'name': 'view.invinterface_search',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Search Network interfaces (invinterface_search)'
        }),
        ('wato.rulesets', {
            'description': u'Access to the module for managing Check_MK rules. Please note that a user can only manage rules in folders he has permissions to. ',
            'name': 'wato.rulesets',
            'defaults': ['admin', 'user'],
            'title': u'Rulesets'
        }),
        ('general.instant_reports', {
            'description': u"Allows the user the do instant reporting. At the top of each view a button will be visible for exporting the current view's data as a PDF file.",
            'name': 'general.instant_reports',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Instant Reports - PDF Export'
        }),
        ('wato.parentscan', {
            'description': u'This permission is neccessary for performing automatic scans for network parents of hosts (making use of traceroute). Please note, that for actually modifying the parents via the scan and for the creation of gateway hosts proper permissions for host and folders are also neccessary.',
            'name': 'wato.parentscan',
            'defaults': ['admin', 'user'],
            'title': u'Perform network parent scan'
        }),
        ('view.ec_events_of_host', {
            'description': u'ec_events_of_host - Currently open events of one specific host',
            'name': 'view.ec_events_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Events of Host (ec_events_of_host)'
        }),
        ('view.ec_history_recent', {
            'description': u'ec_history_recent - Information about events and actions on events during the recent 24 hours.',
            'name': 'view.ec_history_recent',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Event Console - Recent Event History (ec_history_recent)'
        }),
        ('view.invunknown_of_host', {
            'description': u'invunknown_of_host - A view for the Unknown entities of one host',
            'name': 'view.invunknown_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Unknown entities (invunknown_of_host)'
        }),
        ('wato.seeall', {
            'description': u'When this permission is set then the user sees also such modules he has no explicit access to (see below).',
            'name': 'wato.seeall',
            'defaults': ['admin'],
            'title': u'Read access to all modules'
        }),
        ('wato.pattern_editor', {
            'description': u'Access to the module for analyzing and validating logfile patterns.',
            'name': 'wato.pattern_editor',
            'defaults': ['admin', 'user'],
            'title': u'Logfile Pattern Analyzer'
        }),
        ('general.delete_foreign_graph_collection', {
            'description': u'Allows to delete Graph Collections created by other users.',
            'name': 'general.delete_foreign_graph_collection',
            'defaults': ['admin'],
            'title': u'Delete foreign Graph Collections'
        }),
        ('nagvis.Map_delete_*', {
            'description': u'Permits to delete all maps.',
            'name': 'nagvis.Map_delete_*',
            'defaults': [],
            'title': u'Delete all maps'
        }),
        ('action.customnotification', {
            'description': u'Manually let the core send a notification to a host or service in order to test if notifications are setup correctly',
            'name': 'action.customnotification',
            'defaults': ['user', 'admin'],
            'title': u'Send custom notification'
        }),
        ('view.allhosts_deploy', {
            'description': u'allhosts_deploy - Current agent update status of all registered hosts.',
            'name': 'view.allhosts_deploy',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Hosts - Agent update status (allhosts_deploy)'
        }),
        ('general.force_sla_configuration', {
            'description': u'Make own published Service Level Agreements override builtin Service Level Agreements for all users.',
            'name': 'general.force_sla_configuration',
            'defaults': ['admin'],
            'title': u'Modify builtin Service Level Agreements'
        }),
        ('view.perf_matrix', {
            'description': u'perf_matrix - A Matrix of Performance data values from all hosts in a certain host group',
            'name': 'view.perf_matrix',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Matrix of Performance Data (perf_matrix)'
        }),
        ('wato.auditlog', {
            'description': u'Access to the historic audit log. The currently pending changes can be seen by all users with access to WATO.',
            'name': 'wato.auditlog',
            'defaults': ['admin'],
            'title': u'Audit Log'
        }),
        ('view.hostgroupservices', {
            'description': u'hostgroupservices - All services of a certain hostgroup',
            'name': 'view.hostgroupservices',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Services - Services of Hostgroup (hostgroupservices)'
        }),
        ('general.see_user_sla_configuration', {
            'description': u'Is needed for seeing Service Level Agreements that other users have created.',
            'name': 'general.see_user_sla_configuration',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Service Level Agreements'
        }),
        ('wato.dcd_connections', {
            'description': u'Manage the Dynamic configuration connections',
            'name': 'wato.dcd_connections',
            'defaults': ['admin'],
            'title': u'Manage Dynamic configuration'
        }),
        ('view.downtime_history', {
            'description': u'downtime_history - All historic scheduled downtimes of hosts and services',
            'name': 'view.downtime_history',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'Log - History of scheduled downtimes (downtime_history)'
        }),
        ('view.inv_host_history', {
            'description': u'inv_host_history - The history for changes in hardware- and software inventory of a host',
            'name': 'view.inv_host_history',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Inventory history of host (inv_host_history)'
        }),
        ('sidesnap.admin_mini', {
            'description': u'Access to WATO modules with only icons (saves space)',
            'name': 'sidesnap.admin_mini',
            'defaults': ['admin', 'user'],
            'title': u'WATO &middot; Quickaccess'
        }),
        ('view.invbackplane_of_host', {
            'description': u'invbackplane_of_host - A view for the Backplanes of one host',
            'name': 'view.invbackplane_of_host',
            'defaults': ['user', 'admin', 'guest'],
            'title': u'HW/SW inventory - Backplanes (invbackplane_of_host)'
        }),
        ('wato.bake_agents', {
            'description': u'Bake new agent packages for Linux, Windows and other operating systems',
            'name': 'wato.bake_agents',
            'defaults': ['admin'],
            'title': u'Bake agents'
        }),
        ('sidesnap.about', {
            'description': u'Links to webpage, documentation and download of Check_MK',
            'name': 'sidesnap.about',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'About Check_MK'
        }),
        ('general.logout', {
            'description': u'Permits the user to logout.',
            'name': 'general.logout',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'Logout'
        }),
        ('general.force_bookmark_list', {
            'description': u'Make own published Bookmark lists override builtin Bookmark lists for all users.',
            'name': 'general.force_bookmark_list',
            'defaults': ['admin'],
            'title': u'Modify builtin Bookmark lists'
        }),
        ('general.see_user_custom_snapin', {
            'description': u'Is needed for seeing Custom snapins that other users have created.',
            'name': 'general.see_user_custom_snapin',
            'defaults': ['admin', 'user', 'guest'],
            'title': u'See user Custom snapins'
        }),
    ]

    permission_names = permissions.permission_registry.keys()
    assert sorted([s[0] for s in expected_permissions]) == sorted(permission_names)

    for perm_name, expected_perm in expected_permissions:
        section_name = perm_name.split(".", 1)[0]
        permission = permissions.permission_registry[perm_name]()
        assert permission.section == permission_section_registry[section_name]
        assert permission.name == expected_perm["name"]
        assert permission.title == expected_perm["title"]
        assert permission.description == expected_perm["description"]
        assert permission.defaults == expected_perm["defaults"]


def test_declare_permission_section(monkeypatch):
    monkeypatch.setattr(permissions, "permission_section_registry",
                        permissions.PermissionSectionRegistry())
    assert "bla" not in permissions.permission_section_registry
    config.declare_permission_section("bla", u"bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    section = permissions.permission_section_registry["bla"]()
    assert section.title == u"bla perm"
    assert section.sort_index == 50
    assert section.do_sort == False


def test_declare_permission(monkeypatch):
    monkeypatch.setattr(permissions, "permission_section_registry",
                        permissions.PermissionSectionRegistry())
    assert "bla" not in permissions.permission_section_registry
    config.declare_permission_section("bla", u"bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    monkeypatch.setattr(permissions, "permission_registry", permissions.PermissionRegistry())
    assert "bla.blub" not in permissions.permission_registry
    config.declare_permission("bla.blub", u"bla perm", u"descrrrrr", ["admin"])
    assert "bla.blub" in permissions.permission_registry

    permission = permissions.permission_registry["bla.blub"]()
    assert permission.section == permissions.permission_section_registry["bla"]
    assert permission.name == "bla.blub"
    assert permission.title == u"bla perm"
    assert permission.description == "descrrrrr"
    assert permission.defaults == ["admin"]


@pytest.mark.parametrize("do_sort,result", [
    (True, ['sec1.1', 'sec1.A', 'sec1.a', 'sec1.b', 'sec1.g', 'sec1.Z', 'sec1.z']),
    (False, ['sec1.Z', 'sec1.z', 'sec1.A', 'sec1.b', 'sec1.a', 'sec1.1', 'sec1.g']),
])
def test_permission_sorting(do_sort, result):
    sections = permissions.PermissionSectionRegistry()
    perms = permissions.PermissionRegistry()

    @sections.register
    class Sec1(permissions.PermissionSection):
        @property
        def name(self):
            return "sec1"

        @property
        def title(self):
            return "SEC1"

        @property
        def do_sort(self):
            return do_sort

    section_name = "sec1"
    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        cls = type(
            "TestPermission%s%s" % (section_name.title(), permission_name.title()),
            (permissions.Permission,), {
                "section": Sec1,
                "permission_name": permission_name,
                "title": permission_name.title(),
                "description": "bla",
                "defaults": ["admin"],
            })
        perms.register_plugin(cls)

    sorted_perms = [p.name for p in perms.get_sorted_permissions(Sec1())]
    assert sorted_perms == result
