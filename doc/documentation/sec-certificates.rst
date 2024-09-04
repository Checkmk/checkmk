====================
Certificates
====================

Architecture
============

.. uml::

    sprite $certificate [29x25/16] {
        fffffffffffffffffffffffffffff
        f000000000000000000000000000f
        fffffffffffffffffffffffffffff
        f000000000000000000000000000f
        f000000000000000000000000000f
        f0000000000000f0000000000000f
        f000000000000fff000000000000f
        f000000000000f0f000000000000f
        f00000000000f000f00000000000f
        f0000000fffff000fffff0000000f
        f000000ff00000000000f0000000f
        f00000000f000000000f00000000f
        f000000000f0000000f000000000f
        f0000000000f00000f0000000000f
        f0000000000f00000f0000000000f
        f000000000f00fff00f000000000f
        f000000000f0ff0ff0f000000000f
        f000000000ff00000ff000000000f
        f000000000000000000000000000f
        f000000000000000000000000000f
        f000000000000000000000000000f
        f000ffff000ffffffffffffff000f
        f000000000000000000000000000f
        ffffffffffffffffffffff000000f
    }

    !procedure $site($label, $name)
        node "$name" as $label {
            ' certs
            rectangle "[[../sec-certificates.html#https-certificate HTTPS Certificate]]" <<$certificate>> as $label##_https_cert
            rectangle "[[../sec-certificates.html#agentca Site '$site-name' agent signing CA]]" <<$certificate>> as $label##_agent_ca
            rectangle "[[../sec-certificates.html#site-site-name-local-ca Site '$site-name' local CA]]" <<$certificate>> as $label##_site_ca
            rectangle "[[../sec-certificates.html#sitecertificate $site-name]]" <<$certificate>> as $label##_site_cert

            rectangle "[[../sec-certificates.html#customer-name-broker-signing-ca Message broker '$customer-name' CA]]" <<$certificate>> as $label##_broker_ca
            rectangle "[[../sec-certificates.html#site-name-broker-certificate Message broker $site-name cert]]" <<$certificate>> as $label##_broker_cert

        ' ca - certs relationships
        $label##_site_ca -d-> $label##_site_cert: signs
        $label##_site_ca -d-> $label##_broker_ca: signs
        $label##_broker_ca -d-> $label##_broker_cert: signs

        ' components
        component wato as $label##_wato
        component "REST API" as $label##_restapi
        component mknotifyd as $label##_mknotifyd
        component livestatus as $label##_livestatus
        component agent_receiver as $label##_agent_receiver
        component fetcher as $label##_fetcher

        ' interfaces
        interface https as $label##_gui_https_i
        interface tls as $label##_mknotifyd_i
        interface tls as $label##_livestatus_i
        interface https as $label##_agent_receiver_i

        ' components to interfaces
        $label##_wato -u- $label##_gui_https_i
        $label##_restapi -u- $label##_gui_https_i
        $label##_mknotifyd -u- $label##_mknotifyd_i
        $label##_livestatus -u- $label##_livestatus_i
        $label##_agent_receiver -u- $label##_agent_receiver_i

        ' interfaces to certs
        $label##_gui_https_i -[dotted]u- $label##_https_cert
        $label##_mknotifyd_i -[dotted]u- $label##_site_cert
        $label##_livestatus_i -[dotted]u- $label##_site_cert
        $label##_agent_receiver_i -[dotted]u- $label##_site_cert
        }
        node "Entity monitored by $name" {
            rectangle "[[../sec-certificates.html#agent-uuid $agent-uuid]]" <<$certificate>> as $label##_agent_cert
            $label##_agent_ca -> $label##_agent_cert: signs

            component cmk_agent_ctl as $label##_agent_ctl
            interface tls as $label##_agent_ctl_i
            $label##_agent_ctl -u- $label##_agent_ctl_i
            $label##_agent_ctl ..> $label##_agent_receiver_i
        $label##_fetcher ..> $label##_agent_ctl_i

        $label##_agent_ctl_i -[dotted]u- $label##_agent_cert
        }
    !endprocedure

    $site("foo", "Central Site")
    $site("bar", "Remote Site")

    bar_mknotifyd ..> foo_mknotifyd_i
    foo_wato ..> bar_livestatus_i
    foo_wato ..> bar_gui_https_i



Certificates
------------

HTTPS Certificate
^^^^^^^^^^^^^^^^^
* User-Provided
* Not accessible by site
* Does the remote have requirements?

.. _AgentCA:

Site '$site-name' agent signing CA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Created by omd
* `etc/ssl/agents/ca.pem`
* must be a CA
* signs the agent certs

Site '$site-name' local CA
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Created by omd
* `etc/ssl/ca.pem`
* must be a CA
* signs the site certificates

.. _SiteCertificate:

$site-name
^^^^^^^^^^

* Created by omd
* `etc/ssl/sites/$sitename.pem`
* Used by `omd/packages/stunnel/skel/etc/stunnel/server.conf`

$agent-UUID
^^^^^^^^^^^

* Created by REST API
* stored in the connection configuration of the agent
* Validated by the agent-receiver and the fetcher to authenticate an agent

'$customer-name' broker signing CA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Created by omd
* CME: `etc/rabbitmq/ssl/multisite/$customer-name/ca.pem`
* other editions: `etc/rabbitmq/ssl/multisite/ca.pem`
* must be a CA
* signs the local and remote site certs
* Central site sends CA and certs to remote sites, only stores locally the public key of the remote site

$site-name broker certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Created by omd
* CME: `etc/rabbitmq/ssl/multisite/$customer-name/$site-name_cert.pem`
* other editions: `etc/rabbitmq/ssl/multisite/$site-name_cert.pem`
* Used by RabbitMQ broker to authenticate the connections

Interface agent controller - agent-receiver/fetcher
---------------------------------------------------

Pull-mode:
^^^^^^^^^^
* Fetcher provides certificate (:ref:`sitecertificate`)
* agent controller has cert signed by :ref:`agentca`.

Push-mode:
^^^^^^^^^^

* agent-receiver has cert :ref:`sitecertificate`
* agent controller provides cert signed by :ref:`agentca`.

Risks and technical debts
=========================

* Problem/Obstacle: The site is not aware of its address or FQDN.
* In 2.1 and 2.2 the agent controller used its own certificate with the same common name/signer as the :ref:`sitecertificate`.
  That was changed with Werk #15688.
