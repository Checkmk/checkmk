import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_host_comment(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus):

    live: MockLiveStatusConnection = mock_livestatus
    newhost = "example.com"

    live.expect_query(
        f"COMMAND [...] ADD_HOST_COMMENT;{newhost};1;test123-...;This is a test comment for host {newhost}",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/comment/collections/host",
            params=json.dumps(
                {
                    "host_name": f"{newhost}",
                    "comment": f"This is a test comment for host {newhost}",
                    "persistent": True,
                }
            ),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_service_comment(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus):

    newhost = "example.com"
    servicename = "service1"

    live: MockLiveStatusConnection = mock_livestatus
    live.expect_query(
        f"COMMAND [...] ADD_SVC_COMMENT;{newhost};{servicename};1;test123-...;This is a test comment for host {newhost}",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/comment/collections/service",
            params=json.dumps(
                {
                    "host_name": f"{newhost}",
                    "service_description": "service1",
                    "comment": f"This is a test comment for host {newhost}",
                    "persistent": True,
                }
            ),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            status=204,
        )
