========
SAML 2.0
========

.. note:: This page describes the SAML 2.0 authentication method available in the commercial editions of Checkmk 2.2.0 and above.

Introduction
############

SAML (Security Assertion Markup Language) is an open standard for exchanging authentication and authorization data between an **Identity Provider (IdP)** and a **Service Provider (SP)**.
The SP is the system that holds the protected resources and needs to know if users authenticated to access them.
In our case, the SP is the Checkmk site.
The IdP is responsible for authenticating users and providing the SP with the necessary information about the user.
The IdP is some third-party service, such as Google Workspace or Azure AD.

Checkmk Implementation
######################

The following diagram shows the basic flow of a SAML authentication process in Checkmk:

.. uml:: sec-auth-saml-flow.puml

Initiation
**********

The process is initiated by the browser (in this context often called User Agent) when the user clicks the "Login with SAML" button.
The ``RelayState`` that is part of this request is carried along throughout the whole process and contains the information about the requested resource and the ID of the SAML connection as configured in Checkmk.

Checkmk as the SP responds with a form that is automatically submitted to the IdP via ``<body onload="document.forms[0].submit()">``.
The form contains the appropriate IdP endpoint to connect to (such as "``https://login.microsoftonline.com/<tenant-id>/saml2``") and the ``SAMLRequest`` parameter.

Note that Checkmk's **Content Security Policy** would normally not allow the automatic submission of forms to external sites.
For this reason, Checkmk adds the IdP endpoint as an allowed form action in its response.

SAMLRequest
***********

The ``SAMLRequest`` is signed by Checkmk using either the builtin certificate or a custom certificate and includes the following information (among others):

.. csv-table:: Table 1: SAMLRequest Parameters
   :header: Parameter, Description
   :widths: 20, 80

   "ID", "A unique identifier for the request. Checkmk stores this ID (in redis) to later validate the InResponseTo parameter in the SAMLResponse."
   "IssueInstant", "The time when the request was issued."
   "Destination", "The IdP endpoint to send the request to."
   "AssertionConsumer- ServiceURL", "The Checkmk endpoint to post the SAMLResponse to."
   "Issuer", "The Checkmk endpoint where the IdP can find the metadata."
   "Signature", "The signature of the request, including the algorithm, signature value, and the certificate."

This ``SAMLRequest`` data is embedded in xml in the ``AuthnRequest`` element and base64-encoded.

After the UA automatically submits the form to the IdP, the IdP authenticates the user and generates a ``SAMLResponse``.
If the user has authenticated to the IdP before, the IdP might not ask for credentials again and directly generate the ``SAMLResponse``.

SAMLResponse
************

After receiving the ``SAMLResponse`` from the IdP, the UA sends it back to the SP (Checkmk).
This is also typically done by automatically submitting the form to the "AssertionConsumerServiceURL" (ACS) endpoint of the SP.

The ``SAMLResponse`` contains the following information (among others):

.. csv-table:: Table 2: SAMLResponse Parameters
   :header: Parameter, Description
   :widths: 20, 80

   "ID", "A unique identifier for the response."
   "InResponseTo", "The ID of the request that this response is in response to."
   "IssueInstant", "The time when the response was issued."
   "Destination", "The Checkmk endpoint to post the response to."
   "Issuer", "The IdP endpoint where the SP can find the metadata."
   "Status", "The status of the response, indicating success or failure."
   "Assertion", "The actual assertion containing the user attributes, a signature, and the certificate."

The ``SAMLResponse`` data is embedded in xml in the ``Response`` element and base64-encoded.

Session Creation
****************

Checkmk validates the ``SAMLResponse``.
The IdP can either sign the whole response, or only the assertion.
Checkmk accepts both variants.

Checkmk can also be configured to require the IdP to encrypt the response.

In addition, Checkmk verifies the ID in the ``InResponseTo`` parameter to ensure that the response is indeed a response to a request that was initiated by Checkmk.

If the validation is successful, Checkmk creates a session for the user and redirects the UA to the ``RelayState`` URL.

Useful Links
############

- `SAML 2.0 Specification <http://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-tech-overview-2.0.html>`_
- `Wikipedia on SAML 2.0 (extensive!) <https://en.wikipedia.org/wiki/SAML_2.0>`_
- `SAML Tracer Firefox Plugin <https://github.com/SimpleSAMLphp/SAML-tracer/>`_
- `Local Testing tools (e.g. a simple IdP) <https://simplesamlphp.org/docs/stable/index.html>`_
- `That IdP in Docker <https://github.com/kristophjunge/docker-test-saml-idp>`_
