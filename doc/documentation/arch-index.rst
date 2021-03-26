=============================
CheckMK software architecture
=============================


Top-level Architecture
======================

.. _topo & interfaces:

Topology and interfaces
-----------------------

.. uml::

   !include <awslib/AWSCommon>
   !include <awslib/General/Users>

   Users(end_user, "End User", "checkmk User")
   Users(third_party, "3rd Party", "external systems")

   package "OMD: CheckMK run-time environment" as omd {
      [CheckMK Server] as cmk
      cmk -u- Livestatus
      Livestatus -u- [UI]
      cmk -u- REST
      cmk -u- WebAPI
   }

   cloud {
      [Agent-based host] as agent_host
      agent_host -u- TCP
      agent_host -u- Syslog

      [SNMP host] as snmp_host
      snmp_host -u- SNMP
      snmp_host -u- trap
   }

   ' third_party
   third_party -r- cmk : notifications

   ' end_user
   Livestatus -u- end_user
   REST -u- end_user
   WebAPI -u- end_user
   [UI] -u- end_user

   ' agent_host
   cmk -- TCP
   cmk -- Syslog

   ' snmp_host
   cmk -- SNMP
   cmk -- trap


.. toctree::
   :maxdepth: 1

   arch-comp-omd.rst
   arch-comp-hosts.rst

Components
==========

.. toctree::
   :maxdepth: 1

   arch-comp-checkengine.rst
   arch-comp-core.rst
   arch-comp-livestatus.rst
   arch-comp-template.rst
