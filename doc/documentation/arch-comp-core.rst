==================
Nagios & Microcore
==================

Components and interfaces
=========================

.. uml::

   package "On disk" as disk {
     database Config
     database State
   }

   disk   <-- [Core] : use
   [Core] -- Livestatus
   [Core] -- Log
   [Core] -  [Check engine]
