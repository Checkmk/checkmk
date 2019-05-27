import os
import pytest

pytestmark = pytest.mark.checks

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/mysql.include'))


@pytest.mark.parametrize('info,expected_items', [
    ([
        ['this is not a header line -> default item: mysql'],
        ['[[some/other/socket/name]]'],
        ['some', 'info'],
        ['[[item/w/o/info]]'],
    ], ('mysql', 'some/other/socket/name')),
])
def test_mysql_parse_per_item(info, expected_items):
    @mysql_parse_per_item
    def dummy_parse(info):
        return 'Whoop'

    parsed = dummy_parse(info)

    assert parsed == {key: 'Whoop' for key in expected_items}
