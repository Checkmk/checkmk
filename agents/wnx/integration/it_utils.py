import pytest


# we are checking that input is OK(long enough for example)
def check_actual_input(name, lines, alone, data):
    if data is None:
        pytest.skip('"%s" Data is absent' % name)
        return False

    if not alone:
        lines += 2

    if len(data) < lines:
        pytest.skip('"%s" Data is TOO short:\n %s' % (name, '\n'.join(data)))
        return False

    return True
