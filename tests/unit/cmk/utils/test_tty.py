# -*- coding: utf-8 -*-

import cmk.utils.tty as tty


def test_print_table(capsys):
    tty.reinit()
    tty.print_table(
        ['foo', 'bar'],  #
        ['', ''],
        [['Guildo', 'Horn'], ['Dieter Thomas', 'Kuhn']])
    captured = capsys.readouterr()
    assert captured.out == ('foo           bar \n'
                            '------------- ----\n'
                            'Guildo        Horn\n'
                            'Dieter Thomas Kuhn\n')
    assert captured.err == ''


def test_print_colored_table(capsys):
    tty.reinit()
    tty.print_table(
        ['foo', 'bar'],  #
        ['XX', 'YY'],
        [['Angus', 'Young'], ['Estas', 'Tonne']])
    captured = capsys.readouterr()
    assert captured.out == ('XXfoo  YY bar  \n'
                            'XX-----YY -----\n'
                            'XXAngusYY Young\n'
                            'XXEstasYY Tonne\n')
    assert captured.err == ''


def test_print_indented_colored_table(capsys):
    tty.reinit()
    tty.print_table(
        ['foo', 'bar'],  #
        ['XX', 'YY'],
        [['Dieter', 'Bohlen'], ['Thomas', 'Anders']],
        indent='====')
    captured = capsys.readouterr()
    assert captured.out == ('====XXfoo   YY bar   \n'
                            '====XX------YY ------\n'
                            '====XXDieterYY Bohlen\n'
                            '====XXThomasYY Anders\n')
    assert captured.err == ''
