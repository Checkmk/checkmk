# Import modules that contain the page functions

import main
import page_logwatch
import views
import sidebar
import permissions

# map URLs to page rendering functions

pagehandlers.update({
   "index"                 : main.page_index,
   "main"                  : main.page_main,
   "switch_site"           : main.ajax_switch_site,
   "edit_views"            : views.page_edit_views,
   "edit_view"             : views.page_edit_view,
   "export_views"          : views.ajax_export,
   "view"                  : views.page_view,
   "logwatch"              : page_logwatch.page,
   "side"                  : sidebar.page_side,
   "sidebar_add_snapin"    : sidebar.page_add_snapin,
   "sidebar_snapin"        : sidebar.ajax_snapin,
   "sidebar_openclose"     : sidebar.ajax_openclose,
   "sidebar_move_snapin"   : sidebar.move_snapin,
   "switch_master_state"   : sidebar.ajax_switch_masterstate,
   "add_bookmark"          : sidebar.ajax_add_bookmark,
   "del_bookmark"          : sidebar.ajax_del_bookmark,
   "edit_bookmark"         : sidebar.page_edit_bookmark,
   "view_permissions"      : permissions.page_view_permissions,
   "edit_permissions"      : permissions.page_edit_permissions,
})

