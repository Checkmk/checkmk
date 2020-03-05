import cmk.gui.plugins.views.inventory as inventory

RAW_ROWS = [('this_site', 'this_hostname')]
RAW_ROWS2 = [('this_site', 'this_hostname', 'foobar')]

INV_ROWS = [
    {
        'invtesttable_sid': 'A',
        'invtesttable_value1': 1,
        'invtesttable_value2': 4
    },
    {
        'invtesttable_sid': 'B',
        'invtesttable_value1': 2,
        'invtesttable_value2': 5
    },
    {
        'invtesttable_sid': 'C',
        'invtesttable_value1': 3,
        'invtesttable_value2': 6
    },
]

INV_HIST_ROWS = [
    {
        "invhist_time": 123,
        "invhist_new": 1,
        "invhist_changed": 2,
        "invhist_removed": 3,
        "invhist_delta": None,
    },
    {
        "invhist_time": 456,
        "invhist_new": 4,
        "invhist_changed": 5,
        "invhist_removed": 6,
        "invhist_delta": None,
    },
    {
        "invhist_time": 789,
        "invhist_new": 7,
        "invhist_changed": 8,
        "invhist_removed": 9,
        "invhist_delta": None,
    },
]


def test_query_row_table_inventory(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, [], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row


def test_query_row_table_inventory_unknown_columns(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, ['foo'], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row
        assert 'foo' not in row


def test_query_row_table_inventory_add_columns(monkeypatch):
    row_table = inventory.RowTableInventory("invtesttable", ".foo.bar:")
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_ROWS)
    rows = row_table.query(None, ['host_foo'], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row
        assert 'host_foo' in row


def test_query_row_table_inventory_history(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, [], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row


def test_query_row_table_inventory_history_unknown_columns(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, ['foo'], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row
        assert 'foo' not in row


def test_query_row_table_inventory_history_add_columns(monkeypatch):
    row_table = inventory.RowTableInventoryHistory()
    monkeypatch.setattr(row_table, "_get_inv_data", lambda only_sites, query: RAW_ROWS2)
    monkeypatch.setattr(row_table, "_get_rows", lambda hostrow: INV_HIST_ROWS)
    rows = row_table.query(None, ['host_foo'], None, None, None, [])
    for row in rows:
        assert 'site' in row
        assert 'host_name' in row
        assert 'host_foo' in row
