This directory is a place for storing "almost-raw" fixtures, containing data
"almost-directly" from Kubernetes.

The fixtures are split into subdirectories by Kubernetes version.

The script `format.py` takes the raw output from `kubectl get ... -o json` and
changes it into a Python script (which must then be formatted with `ruff` to be
CI-compliant).

Usage example:

```
kubectl get deploy myrelease-checkmk-cluster-collector -o json \
    | ./format.py \
    > 1_33/simple_deployment_with_terminating_replicas_fg.py
```
