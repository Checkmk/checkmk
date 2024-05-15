==================================
Kubernetes Monitoring (agent_kube)
==================================

1 Introduction and goals
========================

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
restrictive for the collectors to run successfully. In such case, an
environment specific alternative is developed (e.g. OpenShift Prometheus).

The Kubernetes special agent is responsible for querying the data from the
Kubernetes API as well as aggregating the usage data collected by the
collectors. The Kubernetes API is the "brain" of Kubernetes and is per default
available with each running Kubernetes setup.

.. uml:: arch-comp-kube-monitoring-setup.puml


Setup configurability
---------------------
There are some key characteristics which should be kept in mind:

* There can be up to two active data sources for a monitoring setup:
    * For Kubernetes API data: The Kubernetes API server (mandatory)
    * For usage metrics (optional & one of):
        * The Checkmk collectors: cluster collector & node collectors (Vanilla, GKE, EKS, other supported versions)
        * OpenShift Prometheus (for OpenShift)
* The Kubernetes API is the mandatory data source; the monitoring solution will not work without it

Prometheus as additional data source while all others can optionally opt to the
Checkmk collectors:
* both are optional data sources so the monitoring will still continue to work even if the data is opted out or cannot be queried
* the information displayed by the checks is adaptive to what data sources are configured

The Kubernetes API server is central to Kubernetes and therefore also to the
Checkmk monitoring solution. It reports the current state of the cluster
and its objects: how those objects were configured, which objects are running,
which objects are scheduled, which objects are terminated, etc.


The collectors
--------------

The collectors retrieve the usage metrics from the running containers

* Node Collector
    * set of pods which are deployed through DaemonSets (a DaemonSet ensures that a copy of the pod runs on each node of the cluster):
        * container usage metrics: relies on the cAdvisor to determine the container usage data of all container running on a node (`container metrics daemonset template <https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/node-collector-container-metrics-ds.yaml>`_)
        * node specific: machine-sections contains an adjusted Checkmk agent to send node specific Checkmk sections (`machine-sections daemonset template <https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/node-collector-machine-sections-ds.yaml>`_)
    * sends the data to the Cluster Collector at fixed time intervals
* Cluster Collector (`cluster collector deployment template <https://github.com/Checkmk/checkmk_kube_agent/blob/main/deploy/charts/checkmk/templates/cluster-collector-deploy.yaml>`_)
    * pod responsible for holding the latest data provided by each Node Collector deployed through a deployment (deployment aims to have a specified number of copies of the pod running in the cluster; in our case 1 copy should be running)
    * the Kubernetes special agent queries the latest usage data
    * new usage data from Node Collectors overwrites existing data
    * outdated data is removed at fixed intervals (e.g. due to a node being removed)



Architecture
============

Key information which influenced design decisions
-------------------------------------------------
Kubernetes API:
* is the only truth of the current state of the objects (which ones are running, pending, etc.)

Querying the Kubernetes API:

* object references (e.g. a deployment manages multiple pods)
    * an API deployment response contains references to the managed pods but details of each pods must be queried separately
    * not all references are direct (e.g. StatefulSet -> manages ReplicaSet -> manages pods)
* response depends on the Kubernetes version
    * fields can be added, deprecated, removed depending on the Kubernetes version

Collectors:

* usage metrics are only up to date depending on when the node collectors last updated them
    * if a node collector fails and stops sending usage metrics then those won't get updated
* verification mechanism:
    * refer to the Kubernetes API to identify if the queried metrics are still relevant
    * refer to a timestamp how old those metrics are


Special Agent General Flow
--------------------------

The following descriptions are listed in chronological order of the special agent
itself.

Querying the objects from the Kubernetes API happens in module
`utils_kubernetes/api_server.py`. All the necessary objects (the monitored ones)
are queried exclusively here and not at a later point.

The queried objects are 'transformed' to our own defined pydantic models defined
under `utils_kubernetes/schemata/api.py`. The direct output from the
Kubernetes API call is not directly used due to following reasons.

The 'transformation' functions which translate the Kubernetes API object response to
the associating self-defined pydantic model are present in `utils_kubernetes/transform*.py`.
In most cases, the models will look very similar to the Kubernetes API response.

The rest of the special agent exclusively works with the 'transformed' API
pydantic models which allows the agent to be version agnostic.

The collector usage metrics are queried and mapped to the already parsed objects from
the Kubernetes API (remember: only the Kubernetes API tells the truth):
* usage metrics of terminated objects (according to the API) are discarded
* rate values are calculated for CPU (metrics are saved in json for the current iteration `{cluster_name}_containers_counters.json`)
* usage metrics have their own agent_sections

.. uml:: arch-comp-kube-monitoring-agent-flow.puml

Technical debts
---------------

* Kubernetes Python client:
    * Python library which is meant to facilitate calls to the Kubernetes API
    * used exclusively in `utils_kubernetes/api_server.py`
    * Limitations:
        * the client more often than not lacks behind the officially supported Kubernetes versions
        * the client is not a direct translation from the Go specification (some definitions can be rather misleading)


See also
--------

* `User Manual <https://docs.checkmk.com/latest/en/monitoring_kubernetes.html>`_
* `Kubernetes Crash Course <https://github.com/Checkmk/checkmk/blob/master/cmk.plugins.kube/README.md>`_
* `checkmk_kube_agent repository <https://github.com/Checkmk/checkmk_kube_agent>`_
* `Checkmk Demo <https://www.youtube.com/watch?v=H9AlO98afUE&t=1s>`_
