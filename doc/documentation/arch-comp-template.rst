====================
<TEMPLATE COMPONENT>
====================

The following sections are an excerpt of `arc42's <https://docs.arc42.org/section-1/>`_ template.

Try to fill all sections with the corresponding information of your component.

**Important: Double check your exposed interfaces with the top-level
architecture:** :ref:`topo & interfaces`

Introduction and goals
======================
* underlying business goals, essential features and functional requirements
  for the system
* quality goals for the architecture,
* relevant stakeholders and their expectations

Requirements overview
---------------------
Short description of the functional requirements, driving forces, extract
(or abstract) of requirements. Link to (hopefully existing) requirements
documents (with version number and information where to find it).


Architecture
============

White-box overall system
------------------------
Add here an UML diagram, which shows the internals of your component,
including external and internal interfaces.

Interfaces
----------
Describe the exposed interfaces of your components. How is your component
communicating with the rest of the system.


Runtime view (optional)
=======================
* important use cases or features: how do building blocks execute them?
* interactions at critical external interfaces: how do building blocks cooperate
  with users and neighboring systems?
* operation and administration: launch, start-up, stop
* error and exception scenarios

Deployment view (optional)
==========================
The deployment view describes:

* the technical infrastructure used to execute your system, with infrastructure
  elements like computers, processors as well as other infrastructure elements
  and
* the mapping of (software) building blocks to that infrastructure elements.

Risks and technical debts (optional)
====================================
A list of identified technical risks or technical debts, ordered by priority
