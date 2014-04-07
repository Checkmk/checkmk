#!/usr/bin/python
# place this file to ~/local/share/check_mk/web/plugins/wato to get two new fields in the wato host properties.
# this fields can be used to add Latiude and Longitude information. Usefull for the Nagvis Geomap

declare_host_attribute(
   NagiosTextAttribute(
    "lat",
    "_LAT",
    "Latitude",
    "Latitude",
   ),
   show_in_table = False,
   show_in_folder = False,
)

declare_host_attribute(
   NagiosTextAttribute(
    "long",
    "_LONG",
    "Longitude",
    "Longitude",
   ),
   show_in_table = False,
   show_in_folder = False,
)
