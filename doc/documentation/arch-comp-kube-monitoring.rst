==================================
Kubernetes Monitoring (agent_kube)
==================================

Introduction and goals
======================

The goal of this component is to realize monitoring of Kubernetes environments
with Checkmk. This is realized through a special agent which relies on the
Kubernetes API and either Checkmk's self-deployed Kubernetes collectors as data
sources or similar sources provided by the Kubernetes hosting environment.

Setup
=====

The Kubernetes monitoring solution consists of the Checkmk special agent which
is executed in the context of the Checkmk site and optionally of the Checkmk
Kubernetes collectors which are deployed to the Kubernetes environment.

The collectors are responsible for collecting memory and CPU usage data of
running applications. Some Kubernetes environments such as OpenShift are too
restrictive for the collectors to run successfully. In such cases, an
environment-specific alternative is developed (for example, using OpenShift
Prometheus).

The Kubernetes special agent is responsible for querying the data from the
Kubernetes API as well as aggregating the usage data collected by the
collectors. The Kubernetes API is the "brain" of Kubernetes and is by default
available with each running Kubernetes setup.

.. uml:: arch-comp-kube-monitoring-setup.puml


Setup configurability
---------------------
There are some key characteristics which should be kept in mind:

* There can be **up to two** active data sources for a monitoring setup:

  * For Kubernetes API data: The Kubernetes API server (**mandatory** - the
    monitoring solution will not work without it)
  * For usage metrics (optional and one of):

    * The Checkmk collectors: cluster collector & node collectors (for Vanilla,
      GKE, EKS, other supported versions)
    * OpenShift Prometheus (for OpenShift)

Both Prometheus and the Checkmk collectors are optional data sources, so the
monitoring will still continue to work even if the data is opted out of or
cannot be queried. The information displayed by the checks is adaptive to which
data sources are configured.

The Kubernetes API server, however, is central to Kubernetes and therefore also
to the Checkmk monitoring solution. It reports the current state of the cluster
and its objects (how those objects were configured, which objects are running,
which objects are scheduled, which objects are terminated, etc.).


The collectors
--------------

The collectors retrieve the usage metrics from the running containers.


Node Collector
^^^^^^^^^^^^^^

The Node Collector is a set of pods which are deployed through `DaemonSets`_
(which allow for ensuring that an instance of the pod runs on each node of the
cluster).

.. _DaemonSets: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/

It collects two things:

* Container usage metrics

  * Uses `cAdvisor`_ to determine usage data of all containers running on each node
    of the cluster. (`DaemonSet <container-ds_>`_)

    .. _cAdvisor: https://github.com/google/cadvisor
    .. _container-ds: https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/node-collector-container-metrics-ds.yaml

  * Node-specific metrics - uses the normal check_mk_agent on each node of the
    cluster. (`DaemonSet <machine-ds_>`_)

    .. _machine-ds: https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/node-collector-machine-sections-ds.yaml

The Node Collector sends the data to the Cluster Collector at fixed time
intervals.


Cluster Collector (`Deployment`_)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _Deployment: https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/cluster-collector-deploy.yaml

The Cluster Collector is the pod responsible for holding the latest data
provided by each Node Collector. There should be one instance running in the
cluster, as is ensured by the Deployment.  The Kubernetes special agent queries
the latest usage data from the Cluster Collector. As new data comes in from the
Node Collectors, existing data is overwritten. Outdated data is also removed at
fixed intervals (e.g. due to a node being removed).


Architecture
============

Collecting Data
---------------

Kubernetes API
^^^^^^^^^^^^^^

The Kubernetes API  is the only source of truth for obtaining the current state
of the objects (which are running, pending, etc.).

Querying the Kubernetes API is done via object references. For example, a
Deployment can manage multiple Pods, and querying the state of the deployment
might return a reference to each of the managed pods, which then must be
separately queried in the API. Not all references are direct (e.g.
``StatefulSet`` might reference a ``ReplicaSet`` which might reference one or
more ``Pod``.

The API response depends on the Kubernetes version. Fields can be added,
deprecated, or removed, depending on the version.


Checkmk Collectors
^^^^^^^^^^^^^^^^^^

The Checkmk Collectors are only as-up-to-date as the last time the Node
Collectors updated them. If a Node Collector fails and stops sending metrics,
then the data will grow stale.

As a verification mechanism, the Kubernetes API can be used to identify if the
queried metrics are still relevant. A simple timestamp can also be used to
determine how old the most recent stored data is.


Processing Data with the Special Agent
--------------------------------------

* Objects are queried from the Kubernetes API from the Python module
  ``api_server.py``. All necessary objects (i.e., monitored objects) are queried
  here, never later.

* The queried objects are transformed to Pydantic data models that we defined
  (``schemata/api.py``). Since Kubernetes API responses can vary across
  versions, these Pydantic models give us a consistent way to reason about the
  data across all versions. The transformation functions are found in
  ``transform*.py``. We do not use the output directly from the Kubernetes API
  call, but in most cases, the models will look similar to the API response.

* The collector usage metrics are queried and mapped to the already-parsed
  objects from the Kubernetes API (remember: only the Kubernetes API tells the
  truth).

  * Usage metrics of terminated objects (according to the API) are discarded

  * Rate values are calculated for CPU (metrics are saved in JSON for the
    current iteration, ``{cluster_name}_containers_counters.json``)

  * Usage metrics have their own AgentSections


Data flow of agent_kube
-----------------------

The module ``kubernetes.client`` (from the upstream Kubernetes Python package)
is the lowest level in our Kubernetes plugin. The client is used to communicate
with the Kubernetes API. It returns Python objects that directly correspond to
the Kubernetes API (the module itself is generated upstream (by the Kubernetes
project maintainers) using Kubernetes' OpenAPI specification). If the Kubernetes
API changes and the Python library gets updated, there is a good chance that it
becomes incompatible with previous versions of the API. To adapt to this in
Checkmk, we make use of Pydantic models (in ``schemata/api.py``) which remain
consistent between versions. This enables us to confine the changes required
across Kubernetes versions to merely the transformation from the raw objects to
our Pydantic models; the rest of the code can usually remain untouched.

The wrapper around the Kubernetes library is ``from_kubernetes()`` in
``api_server.py``. The function used to transform the raw Kubernetes objects
into the Pydantic models live in ``transform.py``.

The gathered data is sent to Checkmk via the normal agent section
mechanism. Pydantic is used for serializing and de-serializing the data before
and after transport, respectively. The file ``schemata/section.py`` contains the
schemata for this serialization. The file ``kube_resources.py`` contains the
logic for de-serialization. A unit test ensures that the two remain in sync.

.. uml:: arch-comp-kube-monitoring-agent-flow.puml


Technical debts
===============

* Kubernetes Python client (used exclusively in api_server.py)

  * Python library that facilitates calls to the Kubernetes API
  * Limitations:

    * Often lags behind the officially supported Kubernetes versions
    * Not a direct translation from the Go specification (some definitions can
      be misleading)


See also
========

* `Checkmk user docs for Kubernetes <https://docs.checkmk.com/latest/en/monitoring_kubernetes.html>`_
* `Checkmk user docs for OpenShift <https://docs.checkmk.com/latest/en/monitoring_openshift.html>`_
* `checkmk_kube_agent repository <https://github.com/Checkmk/checkmk_kube_agent>`_
* `Checkmk demo using Kubernetes <https://www.youtube.com/watch?v=H9AlO98afUE&t=1s>`_
