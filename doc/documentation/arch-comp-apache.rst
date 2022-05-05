======
Apache
======

Introduction and goals
======================

The Apache web server is responsible for providing HTTP access to Checkmk sites.
:doc:`arch-comp-omd` manages a setup of multiple Apache instances to give every
Checkmk site on a Linux system the opportunity to serve user interfaces and APIs
via HTTP via the default HTTP or HTTPS ports.

Architecture
============

Components and interfaces
-------------------------

.. uml:: arch-comp-apache.puml

Across the different Apache instances we have defined these responsibilities:

* System Apache: Listens on default HTTP ports (HTTP and/or HTTPS) and forwards
  requests to Site Apache in a reverse proxy setup.
* System Apache: Terminates HTTPS in case TLS secured transport is required.
  It's the responsibility of customer administrators to set up and maintain the
  TLS configuration of the System Apache according to their requirements.
* Site Apache: Serves all the HTTP components of a site. All components that
  either a UI or a REST API are delivered via the Site Apache.
* Site Apache: Listens locally on a TCP port for the reverse proxy requests from
  the System Apache. No direct connect from non-localhost is possible to the
  Site Apache.
* Site Apache: Authentication is managed in the context of the Site Apache. It
  is either done on an Apache level for basic authentication, Kerberos or SAML
  or on application level when using the default Checkmk UI authentication.

System Apache: Reverse proxy setup
----------------------------------

OMD follows the approach of extending the Linux system with as small changes to
the global configurations as possible. Following this approach, to register the
site specific reverse proxy configuration with the System Apache, OMD registers
with the System Apache using a single file
`/etc/apache2/conf-{available,enabled}/zzz_omd.conf`. The file includes the site
specific reverse proxy settings as displayed below.

.. uml:: arch-comp-apache-reverse-proxy.puml

Site Apache: Offering web server for components to register at
--------------------------------------------------------------

The main configuration file of the Site Apache is `$OMD_ROOT/etc/apache/apache.conf`.
Components of Checkmk sites can register their own Apache configurations by
adding their configuration in `$OMD_ROOT/etc/apache/conf.d`.

The most important ones are :doc:`arch-comp-nagvis` and the user interface
together with the REST API of Checkmk.

.. uml::

    @startuml
    
    component apache {
        component "[[../arch-comp-apache.html#mod-wsgi mod_wsgi]]" as mod_wsgi {
            component GUI
            component "REST API" as rest_api
        }
        component "[[../arch-comp-apache.html#mod-fcgid mod_fcgid]]" as mod_fcgid {
            component "[[../arch-comp-nagvis.html NagVis]]" as nagvis
        }
    }
    
    @enduml

.. _mod-fcgid:

Site Apache: `mod_fcgid` - Allowing use of PHP
----------------------------------------------

The Apache module `mod_fcgid <https://httpd.apache.org/mod_fcgid/>`_ enables the
Apache web server to run PHP code. It is
configured with the Site Apache using the file
`$OMD_ROOT/etc/apache/conf.d/02_fcgid.conf`. Within the Site Apache PHP is executed using
the wrapper script `$OMD_ROOT/etc/apache/php-wrapper`.

Checkmk is not shipping it's own PHP installation. Instead it uses the binaries
and libraries provided by the Operating System. As you can see in `php-wrapper`,
the `php-cgi` command is used to execute PHP. We also use the default system
wide PHP configuration file `php.ini` which is typically located below
`/etc/php/$VERSION/cgi/php.ini` or similar - depending on your Linux
distribution.

.. _mod-wsgi:

Site Apache: `mod_wsgi` - Python application server
---------------------------------------------------

The Apache module `mod_wsgi <https://modwsgi.readthedocs.io/>`_ enables the
Apache web server to run Python WSGI applications. It is configured with the
Site Apache using the file `$OMD_ROOT/etc/apache/conf.d/02_wsgi.conf`.

The Checkmk user interface is registered with `mod_wsgi` using the configuration
file `$OMD_ROOT/etc/apache/conf.d/check_mk.conf`.

Site Apache: Logs
-----------------

The logs of the Site Apache are written to `$OMD_ROOT/var/log/apache`.

See also
--------
- :doc:`arch-comp-omd`
- `User manual: Securing Checkmk with HTTPS <https://docs.checkmk.com/master/en/omd_https.html>`_
- `mod_wsgi <https://modwsgi.readthedocs.io/>`_
- `mod_fcgid <https://httpd.apache.org/mod_fcgid/>`_
