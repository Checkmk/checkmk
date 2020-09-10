from typing import List
from ..agent_based_api.v1 import state


class OraErrors:
    """
    >>> for line in ([""], ["", "FAILURE","ORA-", "foo"], ["", "FAILURE","ORA-"], ["", "FAILURE"],
    ... ["", "select"], ["", "ORA-bar"], ["ORA-bar", "some", "data"]):
    ...     [OraErrors(line).ignore,OraErrors(line).has_error,
    ...     OraErrors(line).error_text,OraErrors(line).error_severity]
    [False, False, '', <state.OK: 0>]
    [False, True, 'ORA- foo', <state.UNKNOWN: 3>]
    [False, True, 'ORA-', <state.UNKNOWN: 3>]
    [True, False, '', <state.OK: 0>]
    [True, False, '', <state.OK: 0>]
    [False, True, 'Found error in agent output "ORA-bar"', <state.UNKNOWN: 3>]
    [False, True, 'Found error in agent output "ORA-bar some data"', <state.UNKNOWN: 3>]
    """
    def __init__(self, line: List[str]):
        # Default values
        self.ignore = False
        self.has_error = False
        self.error_text = ""
        self.error_severity = state.OK

        # Update according to line content
        self.handle_errors(line)

    # This function must be executed for each agent line which has been
    # found for the current item. It must deal with the ORA-* error
    # messages. It has to skip over the lines which show the SQL statement
    # and the SQL error message which comes before the ORA-* message.
    def handle_errors(self, line):
        if len(line) == 1:
            return

        if line[0].startswith('ORA-'):
            self.has_error = True
            self.error_text = 'Found error in agent output "%s"' % ' '.join(line)
            self.error_severity = state.UNKNOWN
            return

        # Handle error output from new agent
        if line[1] == 'FAILURE':
            if len(line) >= 3 and line[2].startswith("ORA-"):
                self.has_error = True
                self.error_text = "%s" % ' '.join(line[2:])
                self.error_severity = state.UNKNOWN
                return
            self.ignore = True
            return  # ignore other FAILURE lines

        # Handle error output from old (pre 1.2.0p2) agent
        if line[1] in ['select', '*', 'ERROR']:
            self.ignore = True
            return
        if line[1].startswith('ORA-'):
            self.has_error = True
            self.error_text = 'Found error in agent output "%s"' % ' '.join(line[1:])
            self.error_severity = state.UNKNOWN
            return
