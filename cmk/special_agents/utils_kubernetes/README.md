Checkmk Kubernetes
==================

# Kubernetes 101

## What is Kubernetes

* Kubernetes is a container orchestration system (Kubernetes is the conductor of containers)
  * automates the deployment, scaling, and management of **containerized applicaions**
* Kubernetes offers a portable interface
  * therefore provides a consistent deployment experience across different environments, making it easy to move applications
* Kubernetes is based on a declarative configuration
  * Kubernetes uses declarative configuration files (YAML or JSON) to define the desired state, making it easy to manage & version control

## Why do you need Kubernetes

Here is a list of possible use cases which Kubernetes can handle:

* **Deploying applications**: Kubernetes can be used to deploy containerized applications on a cluster of servers
* **Scaling applications**: Kubernetes can be configured to automatically scale the number of containers running an application up or down
* **Self-healing**: Kubernetes can detect when a container or node fails and automatically reallocate or restart the container
* **Rolling updates**: Kubernetes can update an application without downtime by gradually replacing old containers with new ones
* **Blue-green deployments**: Kubernetes can deploy a new version of an application alongside the existing version, and switch traffic over to the new version once it's ready
* **Microservices architecture**: Kubernetes is suited for deploying & managing microservices-based applications

The main take-away should be that Kubernetes automates those processes and therefore makes some tasks of a possible system-admin redundant

### From the developer perspective

* **Provision with minimal effort** The simple goal of Kubernetes is to enable developers to deploy their applications to a cluster with minimal effort
* Minimal effort means that the developer should not need to worry about (only a few examples):
  * the details of the cluster
  * on which node the application is supposed to run
  * what happens if the application crashes
  * what happens if the node where the application runs crashes
* The minimal effort does not come for free. Kubernetes is a complex system and requires a lot of knowledge to use it properly. This is why Kubernetes is often referred to as a "black box" by developers.
  * The setup (usually done by DevOps) has a high initial effort
    * e.g. there are different ways to achieve load balancing but it involves extra awareness such as networking

## Real examples of how Kubernetes is used
* OpenAI scaling to 7500 nodes: https://openai.com/research/scaling-kubernetes-to-7500-nodes

## Why is Kubernetes considered so complex (in simple terms)

* **Terminology**: Kubernetes has a lot of specific terminology such as pods, nodes, services and controllers that are used to describe specific entities
* **Complexity**: Kubernetes has a lot of moving parts, including multiple components and tools that must be setup/configured correctly for it to work properly
* **Abstraction**: Kubernetes offers a high level of abstraction (a key identity) that makes it difficult to oversee the big picture
* **Distributed systems**: Kubernetes is, in its essence, a distributed system which requires at least some knowledge of distributed computing concepts
* **Configuration**: Kubernetes is highly configurable and also requires a lot of configuration
  * having the option to choose amongst multiple container runtimes is one example
* **Debugging**: Debugging issues in Kubernetes is not always straightforward
* **Loose coupling**: Despite having high integrity amongst the components, those are actually loosely coupled and can easily break things

----

## Definitions

This is only a minimal list of the most important entities in Kubernetes. For technical details refer to the docstring definitions in `utils_kubernetes/api.py` which provide further insights to the specific definitions.

* **container**: unit of software that packages code & its dependencies (definition from Docker)
* **pod**: the smallest entity from the Kubernetes perspective
  * the pod wraps around a container (or sometimes around a group of containers)
  * all containers in the pod share the same network namespace
  * define Kubernetes specific properties (e.g. labels)
  * simplifies application deployment: offers a simple & consistent way to deploy and manage applications in Kubernetes
    * it encapsulates the application logic and dependencies within a pod
    * specification of resource limits

### Kubernetes main components

#### Kubernetes components

* **kubelet**: primary node agent that runs on each worker node and is responsible for managing the state of the node and its containers (the kubelet communicates back to the control plane)
* **container runtime**: responsible for running containers (e.g. Docker, containerd, CRI-O)
* **node**: a worker machine in the cluster that runs containers.
  * each node has container runtime installed
  * is managed by the control plane components of the Kubernetes through the kubelet
  * can be a physical machine or virtual machine
  * each node can run multiple pods
  * theoretically it is possible to run Kubernetes using only one single node (but this misses the essence of Kubernetes)
  * nodes can be added or removed from the cluster
  * two types of nodes: worker & master node
* **worker node**: node that runs the applications deployed to the cluster
* **master node**: also known as a control plane node, node that manages the state of the cluster and makes gloabal decisions about the cluster
  * runs the control plane components of Kubernetes

#### Kubernetes Control Plane (the brain)

The control plane in Kubernetes is the set of components that manage state of the cluster, schedule work and provide an interface to interact with the system

* **API Server**: the central component, responsible for serving the Kubernetes API & managing the state of the cluster
  * using `kubectl` CLI communicates with the API server
  * this represents the current state of the cluster from the Kubernetes perspective -> one of Checkmk's datasources
* **Controller Manager**: component that manages controllers, which are responsible for ensuring the desired state of objects in the cluster
* **etcd**: distributed key-value store used to sotre the configuration data & state of the cluster
* **Kube-scheduler**: component that assigns newly created pods to nodes based on different factors

### Kubernetes objects

An **Kubernetes object** is a persistent entity in the Kubernetes system, representing the desired state of a cluster

* **Deployment**: k8s object that manages a set of identical, stateless pods, ensuring that the desired number of replicas are running at all times
* **ReplicaSet**: k8s object that ensures a specified number of replicas of a pod are running
* **DaemonSet**: k8s object that ensures that all nodes in a cluster run a copy of a pod
* **StatefulSet**: k8s object that manages a set of replicated pods, typically used for stateful applications such as databases
* **Job**: k8s object that creates one or more pods to perform a specific task, typically used for batch processing or data analysis
* **CronJob**: k8s object that creates jobs on a regular schedule
* **Persistent Volume Claim**: k8s object that provides a way to request and use persistent storage resources, decoupling storage requirements from the pod lifecycle

### Kubernetes general

* **Namespace**: some Kubernetes entities are defined namespace specific while others are defined cluster-wide
  * Kubernetes has a default namespace named "default"

