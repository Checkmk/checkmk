from hypothesis import assume, given, settings, strategies as st, Verbosity

from cmk.special_agents.agent_kube import Pod, pod_api_based_checkmk_sections
from cmk.special_agents.utils_kubernetes.schemata import api


@given(internal_pod=st.builds(api.Pod))
@settings(max_examples=5, verbosity=Verbosity.verbose)
def test_pod_api_sections_output(internal_pod):
    """Test that all api sections can be attempted to be generated from a pod"""
    pod = Pod(
        uid="",
        metadata=internal_pod.metadata,
        spec=internal_pod.spec,
        status=internal_pod.status,
        resources=internal_pod.resources,
        containers=internal_pod.containers,
    )
    assert len(list(pod_api_based_checkmk_sections(pod))) > 0
