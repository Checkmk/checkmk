import pytest

from cmk.base.plugins.agent_based.mobileiron_versions import is_too_old


@pytest.mark.parametrize(
    "string, expected_results",
    [
        ("2021-01-01", True),
        ("210101", True),
        ("290101", False),
        ("290101", False),
    ],
)
def test_is_too_old(string, expected_results) -> None:
    assert is_too_old(string) == expected_results


def test_is_too_old_raises() -> None:
    with pytest.raises(ValueError):
        is_too_old("random-string")
