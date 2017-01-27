#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# external imports
import re
from bs4 import BeautifulSoup as bs

# internal imports
from htmllib import html
import __builtin__
from htmllib import HTMLGenerator, HTMLCheck_MK
from tools import compare_html , gentest, compare_and_empty
from classes import DeprecatedRenderer


import traceback
def save_user_mock(name, data, user, unlock=False):
    pass

class TableTest(html):

    written_text = ''
    tag_counter  = 0

    def __init__(self):
        super(TableTest, self).__init__()
        self.myfile = "testfile"

    def lowlevel_write(self, text):

        if re.match(r'.*\.close_\w+[(][)]', '\n'.join(traceback.format_stack()), re.DOTALL):
            self.tag_counter -= 1 if self.tag_counter > 0 else 0
            self.written_text += " " * 4 * self.tag_counter + text
        elif re.match(r'.*\.open_\w+[(]', '\n'.join(traceback.format_stack()), re.DOTALL):
            self.written_text += " " * 4 * self.tag_counter + text
            self.tag_counter += 1
        else:
            self.written_text += " " * 4 * self.tag_counter + text + ''


def test_table(monkeypatch, tmpdir):
    monkeypatch.setattr(config, "save_user_file", save_user_mock)
    table_test_cubical(False, False, None, 'html', tmpdir)


def test_limit(monkeypatch, tmpdir):
    import config
    monkeypatch.setattr(config, "save_user_file", save_user_mock)
    table_test_cubical(False, False, 2, 'html', tmpdir)


def test_sortable(monkeypatch, tmpdir):
    import config
    monkeypatch.setattr(config, "save_user_file", save_user_mock)
    table_test_cubical(True, False, None, 'html', tmpdir)


def test_searchable(monkeypatch, tmpdir):
    import config
    monkeypatch.setattr(config, "save_user_file", save_user_mock)
    table_test_cubical(False, True, None, 'html', tmpdir)


def test_csv(monkeypatch, tmpdir):
    import config
    monkeypatch.setattr(config, "save_user_file", save_user_mock)
    table_test_cubical(False, False, None, 'csv', tmpdir)


def read_out_table(text):
    # Get the contents of the table as a list of lists
    data = []
    for row in bs(text, 'html5lib').findAll('tr'):
        columns = row.findAll('th')
        if not columns:
            columns = row.findAll('td')
        data.append([re.sub(r'\s', '', re.sub(r'<[^<]*>', '', cell.text)) for cell in columns])
    return data


def read_out_csv(text, separator):
    # Get the contents of the table as a list of lists
    data = []
    for row in text.split('\n'):
        columns = row.split(separator)
        data.append([re.sub(r'\s', '', re.sub(r'<[^<]*>', '', cell)) for cell in columns])
    data = [row for row in data if not all(cell == '' for cell in row)]
    return data


def table_test_cubical(sortable, searchable, limit, output_format, tmpdir):
    import table

    html = TableTest()
    __builtin__.html = html

    table_id = 0
    title = " TEST "
    separator = ';'

    html.add_var('_%s_sort'   % table_id, "1,0")
    html.add_var('_%s_actions' % table_id, '1')

    rows = [ (i, i**3) for i in range(10) ]
    header = ["Number", "Cubical"]

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

    # TODO: Is this still needed?
    ## write to file: This is part of the test! Look at the generated HTML!
    #filename = "%s" % tmpdir.join("web/testtable_%s_%s_%s.html" % \
    #                            ("sortable" * sortable, "searchable" * searchable, limit))
    #try:
    #    with open(filename, "w") as html_file:
    #        pass
    #except:
    #    filename = os.path.basename(filename)

    #text = html.written_text
    #with open(filename, "w") as html_file:
    #    html_file.write(text)
    text = html.written_text

    # Data assertions
    assert output_format in ['html', 'csv'], 'Fetch is not yet implemented'
    if output_format == 'html':
        data = read_out_table(text)
        assert data.pop(0) == header
    elif output_format == 'csv':
        data = read_out_csv(text, separator)
        assert data.pop(0) == header, header
    else:
        assert False, 'Not yet implemented!'

    data = [ tuple(map(int, row)) for row in data if row and row[0]]
    if limit is None:
        limit = len(rows)

    assert len(data) == limit
    assert data == rows[:limit]
