#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# external imports
import re
from bs4 import BeautifulSoup as bs

# internal imports
from htmllib import html
import __builtin__
from htmllib import HTMLGenerator, html
from tools import compare_html, gentest, compare_and_empty, bcolors
from classes import DeprecatedRenderer, TableTester


def save_user_mock(name, data, user, unlock=False):
    pass


def read_out_simple_table(text):
    # Get the contents of the table as a list of lists
    data = []
    for row in bs(text, 'html5lib').findAll('tr'):
        columns = row.findAll('th')
        if not columns:
            columns = row.findAll('td')
        row_data = []
        for cell in columns:
            cell = re.sub(r'\s', '', re.sub(r'<[^<]*>', '', cell.text))
            row_data.append(cell)
        data.append(row_data)
    return data


def read_out_csv(text, separator):
    # Get the contents of the table as a list of lists
    data = []
    for row in text.split('\n'):
        columns = row.split(separator)
        data.append([re.sub(r'\s', '', re.sub(r'<[^<]*>', '', cell)) for cell in columns])
    data = [row for row in data if not all(cell == '' for cell in row)]
    return data




def test_basic():

    from table import Table

    html = TableTester()
    __builtin__.html = html

    id = 0
    title = " TEST "

    table = Table(id, title, searchable=False, sortable=False)
    table.row()
    table.cell("A", "1")
    table.cell("B", "2")
    table.row()
    table.cell("A", "1")
    table.cell("C", "4")
    table.end()

    assert read_out_simple_table(html.written_text) == [[u'A', u'B'], [u'1', u'2'], [u'1', u'4']]


def test_plug():

    from table import Table

    html = TableTester()
    __builtin__.html = html

    id = 0
    title = " TEST "

    table = Table(id, title, searchable=False, sortable=False)
    table.row()
    table.cell("A", "1")
    html.write("a")
    table.cell("B", "2")
    html.write("b")
    table.row()
    table.cell("A", "1")
    html.write("a")
    table.cell("C", "4")
    html.write("c")
    table.end()

    assert read_out_simple_table(html.written_text) == [[u'A', u'B'], [u'1a', u'2b'], [u'1a', u'4c']]


def test_context():
    import table

    html = TableTester()
    __builtin__.html = html

    table_id = 0
    rows    = [ (i, i**3) for i in range(10) ]
    header  = ["Number", "Cubical"]

    with table.open(table_id=table_id, searchable=False, sortable=False):
        for row in rows:
            table.row()
            for i in range(len(header)):
                table.cell(_(header[i]), row[i])

    text = html.written_text
    data = read_out_simple_table(text)
    assert data.pop(0) == header
    data = [ tuple(map(int, row)) for row in data if row and row[0]]
    assert data == rows


def test_nesting():

    from table import Table

    html = TableTester()
    __builtin__.html = html

    id = 0
    title = " TEST "

    table = Table(id, title, searchable=False, sortable=False)
    table.row()
    table.cell("A", "1")
    table.cell("B", "")

    t2 = Table(id+1, title+"2", searchable=False, sortable=False)
    t2.row()
    t2.cell("_", "+")
    t2.cell("|", "-")
    t2.end()

    table.end()
    text = html.written_text
    assert compare_html(text, '''<h3>  TEST </h3>
                            <table class="data oddeven">
                            <tr>  <th>   A  </th>  <th>   B  </th> </tr>
                            <tr class="data odd0">  <td>   1  </td>  <td>
                                <h3> TEST 2</h3>
                                <table class="data oddeven">
                                <tr><th>_</th><th>|</th></tr>
                                <tr class="data odd0"><td>+</td><td>-</td></tr>
                                </table>  </td>
                            </tr>
                            </table>'''), text


def test_nesting_context():

    import table

    html = TableTester()
    __builtin__.html = html

    id = 0
    title = " TEST "

    with table.open(table_id=id, title=title, searchable=False, sortable=False):
        table.row()
        table.cell("A", "1")
        table.cell("B", "")
        with table.open(id+1, title+"2", searchable=False, sortable=False):
            table.row()
            table.cell("_", "+")
            table.cell("|", "-")

    text = html.written_text
    assert compare_html(text, '''<h3>  TEST </h3>
                            <table class="data oddeven">
                            <tr>  <th>   A  </th>  <th>   B  </th> </tr>
                            <tr class="data odd0">  <td>   1  </td>  <td>
                                <h3> TEST 2</h3>
                                <table class="data oddeven">
                                <tr><th>_</th><th>|</th></tr>
                                <tr class="data odd0"><td>+</td><td>-</td></tr>
                                </table>  </td>
                            </tr>
                            </table>'''), text


def test_groupheader():
    print bcolors.WARNING + "TODO"


def test_table_wrapper(monkeypatch, tmpdir):
    import config
    monkeypatch.setattr(config, "save_user_file", save_user_mock)

    rows = [ (i, i**3) for i in range(10) ]
    header = ["Number", "Cubical"]
    for sortable in [True, False]:
        for searchable in [True, False]:
            for limit in [None, 2]:
                for output_format in ["html", "csv"]:
                    passed, emsg = table_test_cubical(sortable, searchable, limit, output_format, tmpdir)
                    assert passed, emsg


def table_test_cubical(sortable, searchable, limit, output_format, tmpdir):
    import table

    html = TableTester()
    __builtin__.html = html

    # Test data
    rows = [ (i, i**3) for i in range(10) ]
    header = ["Number", "Cubical"]

    # Table options
    table_id = 0
    title = " TEST "
    separator = ';'
    html.add_var('_%s_sort'   % table_id, "1,0")
    html.add_var('_%s_actions' % table_id, '1')

    # Table construction
    table.begin(table_id      = table_id,
                title         = title,
                sortable      = sortable,
                searchable    = searchable,
                limit         = limit,
                output_format = output_format)
    for row in rows:
        table.row()
        for i in range(len(header)):
            table.cell(_(header[i]), row[i])
    table.end()

    # Get generated html
    text = html.written_text

    # Data assertions
    if not output_format in ['html', 'csv']:
        return False, 'Fetch is not yet implemented'
    if output_format == 'html':
        data = read_out_simple_table(text)
        if not data.pop(0) == header:
            return False, 'Wrong header'
    elif output_format == 'csv':
        data = read_out_csv(text, separator)
        limit = len(data)
        if not data.pop(0) == header:
            return False, 'Wrong header'
    else:
        return False, 'Not yet implemented'

    # Reconstruct table data
    data = [ tuple(map(int, row)) for row in data if row and row[0]]
    if limit is None:
        limit = len(rows)

    # Assert data correctness
    if not len(data) <= limit:
        return False, 'Wrong number of rows: Got %s, should be <= %s' %(len(data), limit)
    if not data == rows[:limit]:
        return False, "Incorrect data: %s\n\nVS\n%s" % (data, rows[:limit])
    return True, ''


