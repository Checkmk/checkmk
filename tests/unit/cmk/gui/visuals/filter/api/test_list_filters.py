from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection, mock_wato_folders: None
) -> None:
    # just to make sure all filters can be returned
    live: MockLiveStatusConnection = mock_livestatus

    live.expect_query("GET hostgroups\nColumns: name alias")
    # for some reason this query doesn't run on the "NO_SITE" site, unless hostgroups have data
    live.expect_query("GET servicegroups\nColumns: name alias", sites=["local", "remote"])

    with live:
        resp = clients.VisualFilterClient.get_all()

    assert resp.status_code == 200
    assert resp.json["id"] == "all"
