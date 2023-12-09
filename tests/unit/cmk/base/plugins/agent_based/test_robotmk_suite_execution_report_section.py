#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.base.plugins.agent_based.robotmk_suite_execution_report_section import (
    _tests_by_items,
    parse,
)

from cmk.plugins.lib.robotmk_rebot_xml import (
    Keyword,
    KeywordStatus,
    Outcome,
    RFTest,
    StatusV6,
    Suite,
)
from cmk.plugins.lib.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptsConfig,
    Section,
    SuiteRebotReport,
    SuiteReport,
    TestReport,
)

_STRING_TABLE = [
    [
        '{"suite_id":"calc","attempts":["AllTestsPassed"],"rebot":{"Ok":{"xml":"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\r\\n<robot generator=\\"Rebot 5.0.1 (Python 3.9.13 on win32)\\" generated=\\"20231127 07:14:43.631\\" rpa=\\"true\\" schemaversion=\\"3\\">\\r\\n<suite id=\\"s1\\" name=\\"Tasks\\" source=\\"C:\\\\robotmk\\\\v2\\\\data\\\\windows-example-calculator\\\\tasks.robot\\">\\r\\n<test id=\\"s1-t1\\" name=\\"Count My Veggies\\" line=\\"16\\">\\r\\n<kw name=\\"Check Veggies Excel And Start Calculator\\">\\r\\n<kw name=\\"Does File Exist\\" library=\\"RPA.FileSystem\\">\\r\\n<var>${exists}</var>\\r\\n<arg>${INPUT_EXCEL}</arg>\\r\\n<doc>Returns True if the given file exists, False if not.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:06.665\\" level=\\"INFO\\">${exists} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:06.659\\" endtime=\\"20231127 07:14:06.665\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $exists\\">\\r\\n<kw name=\\"Fail\\" library=\\"BuiltIn\\">\\r\\n<arg>Missing input: ${INPUT_EXCEL}</arg>\\r\\n<doc>Fails the test with the given message and optionally alters its tags.</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:06.668\\" endtime=\\"20231127 07:14:06.668\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:06.668\\" endtime=\\"20231127 07:14:06.668\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:06.665\\" endtime=\\"20231127 07:14:06.668\\"/>\\r\\n</if>\\r\\n<kw name=\\"Windows Search\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Use Windows search window to launch application.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:06.670\\" level=\\"INFO\\">Sending keys \'{Win}\' to element &lt;module \'uiautomation\' from \'C:\\\\\\\\ProgramData\\\\\\\\robocorp\\\\\\\\ht\\\\\\\\ccadad1_716b162_7a4bb785\\\\\\\\lib\\\\\\\\site-packages\\\\\\\\uiautomation\\\\\\\\__init__.py\'&gt;</msg>\\r\\n<msg timestamp=\\"20231127 07:14:07.212\\" level=\\"INFO\\">Sending keys \'Calculator\' to element &lt;module \'uiautomation\' from \'C:\\\\\\\\ProgramData\\\\\\\\robocorp\\\\\\\\ht\\\\\\\\ccadad1_716b162_7a4bb785\\\\\\\\lib\\\\\\\\site-packages\\\\\\\\uiautomation\\\\\\\\__init__.py\'&gt;</msg>\\r\\n<msg timestamp=\\"20231127 07:14:07.972\\" level=\\"INFO\\">Sending keys \'{Enter}\' to element &lt;module \'uiautomation\' from \'C:\\\\\\\\ProgramData\\\\\\\\robocorp\\\\\\\\ht\\\\\\\\ccadad1_716b162_7a4bb785\\\\\\\\lib\\\\\\\\site-packages\\\\\\\\uiautomation\\\\\\\\__init__.py\'&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:06.668\\" endtime=\\"20231127 07:14:11.517\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:06.659\\" endtime=\\"20231127 07:14:11.517\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Read Veggies Excel\\">\\r\\n<var>${inputs}</var>\\r\\n<doc>Reads the Excel sheet for veggies</doc>\\r\\n<kw name=\\"Open Workbook\\" library=\\"RPA.Excel.Files\\">\\r\\n<arg>${INPUT_EXCEL}</arg>\\r\\n<doc>Open an existing Excel workbook.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">Opened workbook: &lt;RPA.Excel.Files.XlsxWorkbook object at 0x00000177681A4970&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.518\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Read Worksheet As Table\\" library=\\"RPA.Excel.Files\\">\\r\\n<var>${inputs}</var>\\r\\n<arg>Sheet1</arg>\\r\\n<arg>${TRUE}</arg>\\r\\n<arg>${TRUE}</arg>\\r\\n<doc>Read the contents of a worksheet into a Table container. Allows\\r\\nsorting/filtering/manipulating using the ``RPA.Tables`` library.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">Created table: Table(columns=[\'Carrots\', \'Turnips\', \'Totals\'], rows=5)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">${inputs} = Table(columns=[\'Carrots\', \'Turnips\', \'Totals\'], rows=5)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Close Workbook\\" library=\\"RPA.Excel.Files\\">\\r\\n<doc>Close the active workbook.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">Closing workbook: &lt;RPA.Excel.Files.XlsxWorkbook object at 0x00000177681A4970&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${inputs}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">${inputs} = Table(columns=[\'Carrots\', \'Turnips\', \'Totals\'], rows=5)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.518\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Count Veggie Totals\\">\\r\\n<var>${outputs}</var>\\r\\n<arg>${inputs}</arg>\\r\\n<doc>Counts the total amounts with Calculator Application</doc>\\r\\n<kw name=\\"Create List\\" library=\\"BuiltIn\\">\\r\\n<var>${totals}</var>\\r\\n<doc>Returns a list containing given items.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:11.532\\" level=\\"INFO\\">${totals} = []</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:11.532\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${row}</var>\\r\\n<value>@{table}</value>\\r\\n<iter>\\r\\n<var name=\\"${row}\\">{\'Carrots\': 15, \'Turnips\': 6, \'Totals\': None}</var>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Carrots]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:11.799\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:11.799\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x000001776853C9D0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:11.801\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:11.930\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CE80&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:12.440\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:12.443\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:12.445\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CE80&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:12.445\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:12.497\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177683191F0&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:12.441\\" endtime=\\"20231127 07:14:13.076\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.077\\" endtime=\\"20231127 07:14:13.077\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:12.441\\" endtime=\\"20231127 07:14:13.077\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:13.077\\" endtime=\\"20231127 07:14:13.077\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:13.077\\" endtime=\\"20231127 07:14:13.078\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:12.441\\" endtime=\\"20231127 07:14:13.078\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:13.078\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:12.441\\" endtime=\\"20231127 07:14:13.078\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:13.079\\" endtime=\\"20231127 07:14:13.079\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:13.079\\" endtime=\\"20231127 07:14:13.079\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.079\\" endtime=\\"20231127 07:14:13.079\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:13.080\\" level=\\"INFO\\">${digits} = 15</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.079\\" endtime=\\"20231127 07:14:13.080\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:13.081\\" level=\\"INFO\\">${digit_list} = [\'1\', \'5\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.080\\" endtime=\\"20231127 07:14:13.081\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">1</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:13.084\\" level=\\"INFO\\">Getting element with locator: name:One</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.085\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CE80&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.085\\" level=\\"INFO\\">Locator \'name:One\' produced matcher: MatchObject(locators=[(\'Name\', \'One\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.164\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768319190&gt;, locator=\'name:One\', name=\'One\', automation_id=\'num1Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=791, bottom=890, width=216, height=99, xcenter=200, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.081\\" endtime=\\"20231127 07:14:13.734\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.081\\" endtime=\\"20231127 07:14:13.734\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">5</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:13.740\\" level=\\"INFO\\">Getting element with locator: name:Five</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.741\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CE80&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.741\\" level=\\"INFO\\">Locator \'name:Five\' produced matcher: MatchObject(locators=[(\'Name\', \'Five\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:13.814\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768319A00&gt;, locator=\'name:Five\', name=\'Five\', automation_id=\'num5Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=690, bottom=789, width=216, height=99, xcenter=418, ycenter=739)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.734\\" endtime=\\"20231127 07:14:14.376\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.734\\" endtime=\\"20231127 07:14:14.377\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:13.081\\" endtime=\\"20231127 07:14:14.377\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:14.377\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Plus</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:14.381\\" level=\\"INFO\\">Getting element with locator: name:Plus</msg>\\r\\n<msg timestamp=\\"20231127 07:14:14.382\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CE80&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:14.382\\" level=\\"INFO\\">Locator \'name:Plus\' produced matcher: MatchObject(locators=[(\'Name\', \'Plus\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:14.457\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768319D60&gt;, locator=\'name:Plus\', name=\'Plus\', automation_id=\'plusButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=791, bottom=890, width=216, height=99, xcenter=855, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:14.377\\" endtime=\\"20231127 07:14:15.024\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Turnips]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:15.024\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.024\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768355C70&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.024\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.143\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.024\\" endtime=\\"20231127 07:14:15.660\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:15.660\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.660\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.660\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:15.692\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377460&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.660\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.660\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.660\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.660\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">${digits} = 6</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">${digit_list} = [\'6\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.273\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">6</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">Getting element with locator: name:Six</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.273\\" level=\\"INFO\\">Locator \'name:Six\' produced matcher: MatchObject(locators=[(\'Name\', \'Six\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.338\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x000001776853CDC0&gt;, locator=\'name:Six\', name=\'Six\', automation_id=\'num6Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=690, bottom=789, width=216, height=99, xcenter=637, ycenter=739)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.909\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.910\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.273\\" endtime=\\"20231127 07:14:16.910\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:15.024\\" endtime=\\"20231127 07:14:16.910\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Equals</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:16.915\\" level=\\"INFO\\">Getting element with locator: name:Equals</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.915\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.915\\" level=\\"INFO\\">Locator \'name:Equals\' produced matcher: MatchObject(locators=[(\'Name\', \'Equals\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:16.972\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x000001776853C850&gt;, locator=\'name:Equals\', name=\'Equals\', automation_id=\'equalButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=893, bottom=992, width=216, height=99, xcenter=855, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:16.911\\" endtime=\\"20231127 07:14:17.538\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Get Result From Calc\\">\\r\\n<var>${total}</var>\\r\\n<doc>Reads Calculator\'s calculation result</doc>\\r\\n<kw name=\\"Get Attribute\\" library=\\"RPA.Windows\\">\\r\\n<var>${result}</var>\\r\\n<arg>Calculator - IdCalculatorResults</arg>\\r\\n<arg>Name</arg>\\r\\n<doc>Get attribute value of the element defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:17.538\\" level=\\"INFO\\">Getting element with locator: id:\\"CalculatorResults\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.538\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.538\\" level=\\"INFO\\">Locator \'id:\\"CalculatorResults\\"\' produced matcher: MatchObject(locators=[(\'AutomationId\', \'CalculatorResults\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.563\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.TextControl object at 0x0000017768355250&gt;, locator=\'id:\\"CalculatorResults\\"\', name=\'Display is 21\', automation_id=\'CalculatorResults\', control_type=\'TextControl\', class_name=\'\', left=88, right=968, top=177, bottom=320, width=880, height=143, xcenter=528, ycenter=248)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.564\\" level=\\"INFO\\">${result} = Display is 21</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.538\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Remove String\\" library=\\"String\\">\\r\\n<var>${total}</var>\\r\\n<arg>${result}</arg>\\r\\n<arg>Display is${SPACE}</arg>\\r\\n<doc>Removes all ``removables`` from the given ``string``.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:17.564\\" level=\\"INFO\\">${total} = 21</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Convert To Integer\\" library=\\"BuiltIn\\">\\r\\n<var>${total}</var>\\r\\n<arg>${total}</arg>\\r\\n<doc>Converts the given item to an integer number.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:17.564\\" level=\\"INFO\\">${total} = 21</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${total}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:17.564\\" level=\\"INFO\\">${total} = 21</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.538\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Append To List\\" library=\\"Collections\\">\\r\\n<arg>${totals}</arg>\\r\\n<arg>${total}</arg>\\r\\n<doc>Adds ``values`` to the end of ``list``.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:17.564\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${row}\\">{\'Carrots\': 99, \'Turnips\': 12, \'Totals\': None}</var>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Carrots]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:17.571\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.571\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768115280&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.571\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:17.685\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776809FAF0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:18.190\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:18.195\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.196\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776809FAF0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.196\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.221\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768355B20&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.191\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.191\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.191\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.190\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">${digits} = 99</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">${digit_list} = [\'9\', \'9\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:18.802\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">9</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">Getting element with locator: name:Nine</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776809FAF0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.802\\" level=\\"INFO\\">Locator \'name:Nine\' produced matcher: MatchObject(locators=[(\'Name\', \'Nine\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:18.895\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768115610&gt;, locator=\'name:Nine\', name=\'Nine\', automation_id=\'num9Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=588, bottom=687, width=216, height=99, xcenter=637, ycenter=637)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:19.453\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:19.453\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">9</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:19.456\\" level=\\"INFO\\">Getting element with locator: name:Nine</msg>\\r\\n<msg timestamp=\\"20231127 07:14:19.456\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776809FAF0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:19.456\\" level=\\"INFO\\">Locator \'name:Nine\' produced matcher: MatchObject(locators=[(\'Name\', \'Nine\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:19.535\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177683773A0&gt;, locator=\'name:Nine\', name=\'Nine\', automation_id=\'num9Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=588, bottom=687, width=216, height=99, xcenter=637, ycenter=637)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:19.453\\" endtime=\\"20231127 07:14:20.110\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:19.453\\" endtime=\\"20231127 07:14:20.110\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:18.802\\" endtime=\\"20231127 07:14:20.110\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:20.110\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Plus</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:20.111\\" level=\\"INFO\\">Getting element with locator: name:Plus</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.114\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776809FAF0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.114\\" level=\\"INFO\\">Locator \'name:Plus\' produced matcher: MatchObject(locators=[(\'Name\', \'Plus\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.158\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377250&gt;, locator=\'name:Plus\', name=\'Plus\', automation_id=\'plusButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=791, bottom=890, width=216, height=99, xcenter=855, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:20.110\\" endtime=\\"20231127 07:14:20.727\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Turnips]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:20.727\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.727\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x000001776853C940&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.727\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:20.842\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:20.727\\" endtime=\\"20231127 07:14:21.345\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:21.345\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:21.345\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:21.345\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:21.387\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768319A60&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.345\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.345\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.345\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.345\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">${digits} = 12</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">${digit_list} = [\'1\', \'2\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:21.949\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">1</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">Getting element with locator: name:One</msg>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:21.949\\" level=\\"INFO\\">Locator \'name:One\' produced matcher: MatchObject(locators=[(\'Name\', \'One\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:22.028\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768348880&gt;, locator=\'name:One\', name=\'One\', automation_id=\'num1Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=791, bottom=890, width=216, height=99, xcenter=200, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:22.593\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:22.593\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">2</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:22.593\\" level=\\"INFO\\">Getting element with locator: name:Two</msg>\\r\\n<msg timestamp=\\"20231127 07:14:22.593\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:22.593\\" level=\\"INFO\\">Locator \'name:Two\' produced matcher: MatchObject(locators=[(\'Name\', \'Two\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:22.643\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768348A60&gt;, locator=\'name:Two\', name=\'Two\', automation_id=\'num2Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=791, bottom=890, width=216, height=99, xcenter=418, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:22.593\\" endtime=\\"20231127 07:14:23.208\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:22.593\\" endtime=\\"20231127 07:14:23.208\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:21.949\\" endtime=\\"20231127 07:14:23.208\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:20.727\\" endtime=\\"20231127 07:14:23.208\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Equals</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:23.208\\" level=\\"INFO\\">Getting element with locator: name:Equals</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.208\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.208\\" level=\\"INFO\\">Locator \'name:Equals\' produced matcher: MatchObject(locators=[(\'Name\', \'Equals\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.256\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177683197C0&gt;, locator=\'name:Equals\', name=\'Equals\', automation_id=\'equalButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=893, bottom=992, width=216, height=99, xcenter=855, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.208\\" endtime=\\"20231127 07:14:23.812\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Get Result From Calc\\">\\r\\n<var>${total}</var>\\r\\n<doc>Reads Calculator\'s calculation result</doc>\\r\\n<kw name=\\"Get Attribute\\" library=\\"RPA.Windows\\">\\r\\n<var>${result}</var>\\r\\n<arg>Calculator - IdCalculatorResults</arg>\\r\\n<arg>Name</arg>\\r\\n<doc>Get attribute value of the element defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:23.812\\" level=\\"INFO\\">Getting element with locator: id:\\"CalculatorResults\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.812\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853C340&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.812\\" level=\\"INFO\\">Locator \'id:\\"CalculatorResults\\"\' produced matcher: MatchObject(locators=[(\'AutomationId\', \'CalculatorResults\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.831\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.TextControl object at 0x000001776853CC10&gt;, locator=\'id:\\"CalculatorResults\\"\', name=\'Display is 111\', automation_id=\'CalculatorResults\', control_type=\'TextControl\', class_name=\'\', left=88, right=968, top=177, bottom=320, width=880, height=143, xcenter=528, ycenter=248)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.831\\" level=\\"INFO\\">${result} = Display is 111</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.812\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Remove String\\" library=\\"String\\">\\r\\n<var>${total}</var>\\r\\n<arg>${result}</arg>\\r\\n<arg>Display is${SPACE}</arg>\\r\\n<doc>Removes all ``removables`` from the given ``string``.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:23.831\\" level=\\"INFO\\">${total} = 111</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Convert To Integer\\" library=\\"BuiltIn\\">\\r\\n<var>${total}</var>\\r\\n<arg>${total}</arg>\\r\\n<doc>Converts the given item to an integer number.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:23.831\\" level=\\"INFO\\">${total} = 111</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${total}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:23.831\\" level=\\"INFO\\">${total} = 111</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.812\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Append To List\\" library=\\"Collections\\">\\r\\n<arg>${totals}</arg>\\r\\n<arg>${total}</arg>\\r\\n<doc>Adds ``values`` to the end of ``list``.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:17.564\\" endtime=\\"20231127 07:14:23.831\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${row}\\">{\'Carrots\': 3, \'Turnips\': 9, \'Totals\': None}</var>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Carrots]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:23.844\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.844\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768355C10&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.844\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:23.958\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768355490&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:24.464\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:24.464\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:24.464\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768355490&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:24.464\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:24.497\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768115EE0&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:24.464\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.069\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:24.464\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:25.069\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:25.069\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:24.464\\" endtime=\\"20231127 07:14:25.069\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:24.464\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">${digits} = 3</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">${digit_list} = [\'3\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.071\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">3</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">Getting element with locator: name:Three</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768355490&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.071\\" level=\\"INFO\\">Locator \'name:Three\' produced matcher: MatchObject(locators=[(\'Name\', \'Three\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.143\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x000001776809FAC0&gt;, locator=\'name:Three\', name=\'Three\', automation_id=\'num3Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=791, bottom=890, width=216, height=99, xcenter=637, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.712\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.712\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.071\\" endtime=\\"20231127 07:14:25.712\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:25.712\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Plus</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:25.712\\" level=\\"INFO\\">Getting element with locator: name:Plus</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.712\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768355490&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.712\\" level=\\"INFO\\">Locator \'name:Plus\' produced matcher: MatchObject(locators=[(\'Name\', \'Plus\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:25.768\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x000001776809FF10&gt;, locator=\'name:Plus\', name=\'Plus\', automation_id=\'plusButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=791, bottom=890, width=216, height=99, xcenter=855, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:25.712\\" endtime=\\"20231127 07:14:26.327\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Turnips]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:26.331\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.331\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768348EB0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.331\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.439\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768348160&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.327\\" endtime=\\"20231127 07:14:26.946\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:26.950\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.951\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768348160&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.951\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:26.978\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768385E50&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.947\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.947\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.947\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:27.544\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.946\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:27.544\\" level=\\"INFO\\">${digits} = 9</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:27.544\\" level=\\"INFO\\">${digit_list} = [\'9\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:27.544\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">9</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:27.549\\" level=\\"INFO\\">Getting element with locator: name:Nine</msg>\\r\\n<msg timestamp=\\"20231127 07:14:27.549\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768348160&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:27.549\\" level=\\"INFO\\">Locator \'name:Nine\' produced matcher: MatchObject(locators=[(\'Name\', \'Nine\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:27.612\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768115EE0&gt;, locator=\'name:Nine\', name=\'Nine\', automation_id=\'num9Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=588, bottom=687, width=216, height=99, xcenter=637, ycenter=637)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:28.190\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:28.190\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:27.544\\" endtime=\\"20231127 07:14:28.190\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:26.327\\" endtime=\\"20231127 07:14:28.192\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Equals</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:28.195\\" level=\\"INFO\\">Getting element with locator: name:Equals</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.196\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768348160&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.196\\" level=\\"INFO\\">Locator \'name:Equals\' produced matcher: MatchObject(locators=[(\'Name\', \'Equals\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.255\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377580&gt;, locator=\'name:Equals\', name=\'Equals\', automation_id=\'equalButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=893, bottom=992, width=216, height=99, xcenter=855, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.192\\" endtime=\\"20231127 07:14:28.823\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Get Result From Calc\\">\\r\\n<var>${total}</var>\\r\\n<doc>Reads Calculator\'s calculation result</doc>\\r\\n<kw name=\\"Get Attribute\\" library=\\"RPA.Windows\\">\\r\\n<var>${result}</var>\\r\\n<arg>Calculator - IdCalculatorResults</arg>\\r\\n<arg>Name</arg>\\r\\n<doc>Get attribute value of the element defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:28.829\\" level=\\"INFO\\">Getting element with locator: id:\\"CalculatorResults\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.829\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768348160&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.829\\" level=\\"INFO\\">Locator \'id:\\"CalculatorResults\\"\' produced matcher: MatchObject(locators=[(\'AutomationId\', \'CalculatorResults\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.847\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.TextControl object at 0x0000017768355850&gt;, locator=\'id:\\"CalculatorResults\\"\', name=\'Display is 12\', automation_id=\'CalculatorResults\', control_type=\'TextControl\', class_name=\'\', left=88, right=968, top=177, bottom=320, width=880, height=143, xcenter=528, ycenter=248)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.847\\" level=\\"INFO\\">${result} = Display is 12</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.824\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Remove String\\" library=\\"String\\">\\r\\n<var>${total}</var>\\r\\n<arg>${result}</arg>\\r\\n<arg>Display is${SPACE}</arg>\\r\\n<doc>Removes all ``removables`` from the given ``string``.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:28.847\\" level=\\"INFO\\">${total} = 12</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Convert To Integer\\" library=\\"BuiltIn\\">\\r\\n<var>${total}</var>\\r\\n<arg>${total}</arg>\\r\\n<doc>Converts the given item to an integer number.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:28.847\\" level=\\"INFO\\">${total} = 12</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${total}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:28.847\\" level=\\"INFO\\">${total} = 12</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.824\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Append To List\\" library=\\"Collections\\">\\r\\n<arg>${totals}</arg>\\r\\n<arg>${total}</arg>\\r\\n<doc>Adds ``values`` to the end of ``list``.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:23.831\\" endtime=\\"20231127 07:14:28.847\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${row}\\">{\'Carrots\': 10, \'Turnips\': 3, \'Totals\': None}</var>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Carrots]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:28.856\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.856\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768319BE0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.856\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:28.968\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CA30&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:29.472\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:29.477\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:29.477\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CA30&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:29.477\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:29.505\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177684F0520&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:29.474\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:29.474\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:29.474\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:30.076\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:29.472\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:30.076\\" level=\\"INFO\\">${digits} = 10</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:30.076\\" level=\\"INFO\\">${digit_list} = [\'1\', \'0\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.076\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">1</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:30.081\\" level=\\"INFO\\">Getting element with locator: name:One</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.081\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CA30&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.081\\" level=\\"INFO\\">Locator \'name:One\' produced matcher: MatchObject(locators=[(\'Name\', \'One\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.126\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768043220&gt;, locator=\'name:One\', name=\'One\', automation_id=\'num1Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=791, bottom=890, width=216, height=99, xcenter=200, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.690\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:30.690\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">0</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:30.690\\" level=\\"INFO\\">Getting element with locator: name:Zero</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.690\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CA30&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.690\\" level=\\"INFO\\">Locator \'name:Zero\' produced matcher: MatchObject(locators=[(\'Name\', \'Zero\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:30.754\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768130A00&gt;, locator=\'name:Zero\', name=\'Zero\', automation_id=\'num0Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=893, bottom=992, width=216, height=99, xcenter=418, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.690\\" endtime=\\"20231127 07:14:31.327\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.690\\" endtime=\\"20231127 07:14:31.327\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:30.076\\" endtime=\\"20231127 07:14:31.327\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:31.327\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Plus</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:31.330\\" level=\\"INFO\\">Getting element with locator: name:Plus</msg>\\r\\n<msg timestamp=\\"20231127 07:14:31.330\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x000001776853CA30&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:31.330\\" level=\\"INFO\\">Locator \'name:Plus\' produced matcher: MatchObject(locators=[(\'Name\', \'Plus\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:31.377\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768130A00&gt;, locator=\'name:Plus\', name=\'Plus\', automation_id=\'plusButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=791, bottom=890, width=216, height=99, xcenter=855, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:31.327\\" endtime=\\"20231127 07:14:31.955\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Turnips]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:31.955\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:31.955\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x00000177682F4AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:31.955\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:32.067\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768006880&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:31.955\\" endtime=\\"20231127 07:14:32.574\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:32.574\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:32.574\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768006880&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:32.574\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:32.606\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377220&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:32.574\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:32.574\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:32.574\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:32.574\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">${digits} = 3</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">${digit_list} = [\'3\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.177\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">3</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">Getting element with locator: name:Three</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768006880&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.177\\" level=\\"INFO\\">Locator \'name:Three\' produced matcher: MatchObject(locators=[(\'Name\', \'Three\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.244\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768319CD0&gt;, locator=\'name:Three\', name=\'Three\', automation_id=\'num3Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=791, bottom=890, width=216, height=99, xcenter=637, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.796\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.796\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.177\\" endtime=\\"20231127 07:14:33.796\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:31.955\\" endtime=\\"20231127 07:14:33.796\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Equals</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:33.799\\" level=\\"INFO\\">Getting element with locator: name:Equals</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.799\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768006880&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.799\\" level=\\"INFO\\">Locator \'name:Equals\' produced matcher: MatchObject(locators=[(\'Name\', \'Equals\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:33.844\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377430&gt;, locator=\'name:Equals\', name=\'Equals\', automation_id=\'equalButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=893, bottom=992, width=216, height=99, xcenter=855, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:33.796\\" endtime=\\"20231127 07:14:34.412\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Get Result From Calc\\">\\r\\n<var>${total}</var>\\r\\n<doc>Reads Calculator\'s calculation result</doc>\\r\\n<kw name=\\"Get Attribute\\" library=\\"RPA.Windows\\">\\r\\n<var>${result}</var>\\r\\n<arg>Calculator - IdCalculatorResults</arg>\\r\\n<arg>Name</arg>\\r\\n<doc>Get attribute value of the element defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:34.412\\" level=\\"INFO\\">Getting element with locator: id:\\"CalculatorResults\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.412\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768006880&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.412\\" level=\\"INFO\\">Locator \'id:\\"CalculatorResults\\"\' produced matcher: MatchObject(locators=[(\'AutomationId\', \'CalculatorResults\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.TextControl object at 0x0000017768355250&gt;, locator=\'id:\\"CalculatorResults\\"\', name=\'Display is 13\', automation_id=\'CalculatorResults\', control_type=\'TextControl\', class_name=\'\', left=88, right=968, top=177, bottom=320, width=880, height=143, xcenter=528, ycenter=248)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">${result} = Display is 13</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.412\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Remove String\\" library=\\"String\\">\\r\\n<var>${total}</var>\\r\\n<arg>${result}</arg>\\r\\n<arg>Display is${SPACE}</arg>\\r\\n<doc>Removes all ``removables`` from the given ``string``.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">${total} = 13</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Convert To Integer\\" library=\\"BuiltIn\\">\\r\\n<var>${total}</var>\\r\\n<arg>${total}</arg>\\r\\n<doc>Converts the given item to an integer number.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">${total} = 13</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${total}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">${total} = 13</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.412\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Append To List\\" library=\\"Collections\\">\\r\\n<arg>${totals}</arg>\\r\\n<arg>${total}</arg>\\r\\n<doc>Adds ``values`` to the end of ``list``.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:28.847\\" endtime=\\"20231127 07:14:34.428\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${row}\\">{\'Carrots\': 14, \'Turnips\': 91, \'Totals\': None}</var>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Carrots]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x0000017768348970&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.428\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:34.557\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:35.078\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:35.081\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.081\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.081\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.112\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177683856D0&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.078\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.078\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.078\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.078\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">${digits} = 14</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">${digit_list} = [\'1\', \'4\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:35.679\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">1</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">Getting element with locator: name:One</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.679\\" level=\\"INFO\\">Locator \'name:One\' produced matcher: MatchObject(locators=[(\'Name\', \'One\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:35.737\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x000001776853C9A0&gt;, locator=\'name:One\', name=\'One\', automation_id=\'num1Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=791, bottom=890, width=216, height=99, xcenter=200, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:36.300\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:36.301\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">4</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:36.302\\" level=\\"INFO\\">Getting element with locator: name:Four</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.306\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.306\\" level=\\"INFO\\">Locator \'name:Four\' produced matcher: MatchObject(locators=[(\'Name\', \'Four\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.365\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768377070&gt;, locator=\'name:Four\', name=\'Four\', automation_id=\'num4Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=690, bottom=789, width=216, height=99, xcenter=200, ycenter=739)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:36.301\\" endtime=\\"20231127 07:14:36.936\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:36.301\\" endtime=\\"20231127 07:14:36.936\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:35.679\\" endtime=\\"20231127 07:14:36.936\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:36.937\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Plus</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:36.940\\" level=\\"INFO\\">Getting element with locator: name:Plus</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.941\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768319AC0&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.941\\" level=\\"INFO\\">Locator \'name:Plus\' produced matcher: MatchObject(locators=[(\'Name\', \'Plus\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:36.989\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768130C70&gt;, locator=\'name:Plus\', name=\'Plus\', automation_id=\'plusButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=791, bottom=890, width=216, height=99, xcenter=855, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:36.937\\" endtime=\\"20231127 07:14:37.562\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Number To Calc\\">\\r\\n<arg>${row}[Turnips]</arg>\\r\\n<doc>Splits the input number into digits and clicks Calculator buttons</doc>\\r\\n<kw name=\\"Control Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Controls the window defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:37.562\\" level=\\"INFO\\">Getting element with locator: Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:37.562\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x000001776853C520&gt;, locator=\'Calculator and type:WindowControl\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:37.562\\" level=\\"INFO\\">Locator \'Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:37.674\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:37.562\\" endtime=\\"20231127 07:14:38.177\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click If Available\\">\\r\\n<var>${cleared}</var>\\r\\n<arg>Calculator - CE</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>${locator}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:38.177\\" level=\\"INFO\\">Getting element with locator: name:\\"Clear entry\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.177\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.177\\" level=\\"INFO\\">Locator \'name:\\"Clear entry\\"\' produced matcher: MatchObject(locators=[(\'Name\', \'Clear entry\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.209\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177680431F0&gt;, locator=\'name:\\"Clear entry\\"\', name=\'Clear entry\', automation_id=\'clearEntryButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=310, right=526, top=385, bottom=484, width=216, height=99, xcenter=418, ycenter=434)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.177\\" endtime=\\"20231127 07:14:38.775\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${TRUE}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.775\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</return>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.177\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<return>\\r\\n<value>${FALSE}</value>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</return>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.177\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</try>\\r\\n<msg timestamp=\\"20231127 07:14:38.776\\" level=\\"INFO\\">${cleared} = True</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.177\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"not $cleared\\">\\r\\n<kw name=\\"Click If Available\\">\\r\\n<arg>Calculator - C</arg>\\r\\n<doc>Clicks Windows locator if available</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</if>\\r\\n<kw name=\\"Convert To String\\" library=\\"BuiltIn\\">\\r\\n<var>${digits}</var>\\r\\n<arg>${number}</arg>\\r\\n<doc>Converts the given item to a Unicode string.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:38.776\\" level=\\"INFO\\">${digits} = 91</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.776\\" endtime=\\"20231127 07:14:38.776\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Split String To Characters\\" library=\\"String\\">\\r\\n<var>${digit_list}</var>\\r\\n<arg>${digits}</arg>\\r\\n<doc>Splits the given ``string`` to characters.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:38.778\\" level=\\"INFO\\">${digit_list} = [\'9\', \'1\']</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.778\\" endtime=\\"20231127 07:14:38.778\\"/>\\r\\n</kw>\\r\\n<for flavor=\\"IN\\">\\r\\n<var>${digit}</var>\\r\\n<value>@{digit_list}</value>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">9</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:38.781\\" level=\\"INFO\\">Getting element with locator: name:Nine</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.782\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.782\\" level=\\"INFO\\">Locator \'name:Nine\' produced matcher: MatchObject(locators=[(\'Name\', \'Nine\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:38.839\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x0000017768043670&gt;, locator=\'name:Nine\', name=\'Nine\', automation_id=\'num9Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=529, right=745, top=588, bottom=687, width=216, height=99, xcenter=637, ycenter=637)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.778\\" endtime=\\"20231127 07:14:39.439\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.778\\" endtime=\\"20231127 07:14:39.439\\"/>\\r\\n</iter>\\r\\n<iter>\\r\\n<var name=\\"${digit}\\">1</var>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - ${digit}</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:39.439\\" level=\\"INFO\\">Getting element with locator: name:One</msg>\\r\\n<msg timestamp=\\"20231127 07:14:39.439\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:39.439\\" level=\\"INFO\\">Locator \'name:One\' produced matcher: MatchObject(locators=[(\'Name\', \'One\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:39.503\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177682F4AC0&gt;, locator=\'name:One\', name=\'One\', automation_id=\'num1Button\', control_type=\'ButtonControl\', class_name=\'Button\', left=92, right=308, top=791, bottom=890, width=216, height=99, xcenter=200, ycenter=840)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:39.439\\" endtime=\\"20231127 07:14:40.066\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:39.439\\" endtime=\\"20231127 07:14:40.066\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:38.778\\" endtime=\\"20231127 07:14:40.066\\"/>\\r\\n</for>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:37.562\\" endtime=\\"20231127 07:14:40.066\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Click\\" library=\\"RPA.Windows\\">\\r\\n<arg>Calculator - Equals</arg>\\r\\n<tag>action</tag>\\r\\n<tag>mouse</tag>\\r\\n<doc>Mouse click on element matching given locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:40.066\\" level=\\"INFO\\">Getting element with locator: name:Equals</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.066\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.066\\" level=\\"INFO\\">Locator \'name:Equals\' produced matcher: MatchObject(locators=[(\'Name\', \'Equals\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.131\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.ButtonControl object at 0x00000177683856D0&gt;, locator=\'name:Equals\', name=\'Equals\', automation_id=\'equalButton\', control_type=\'ButtonControl\', class_name=\'Button\', left=747, right=963, top=893, bottom=992, width=216, height=99, xcenter=855, ycenter=942)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.066\\" endtime=\\"20231127 07:14:40.703\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Get Result From Calc\\">\\r\\n<var>${total}</var>\\r\\n<doc>Reads Calculator\'s calculation result</doc>\\r\\n<kw name=\\"Get Attribute\\" library=\\"RPA.Windows\\">\\r\\n<var>${result}</var>\\r\\n<arg>Calculator - IdCalculatorResults</arg>\\r\\n<arg>Name</arg>\\r\\n<doc>Get attribute value of the element defined by the locator.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:40.703\\" level=\\"INFO\\">Getting element with locator: id:\\"CalculatorResults\\"</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.703\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x00000177684F0F40&gt;, locator=\'Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.703\\" level=\\"INFO\\">Locator \'id:\\"CalculatorResults\\"\' produced matcher: MatchObject(locators=[(\'AutomationId\', \'CalculatorResults\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.TextControl object at 0x000001776853CB50&gt;, locator=\'id:\\"CalculatorResults\\"\', name=\'Display is 105\', automation_id=\'CalculatorResults\', control_type=\'TextControl\', class_name=\'\', left=88, right=968, top=177, bottom=320, width=880, height=143, xcenter=528, ycenter=248)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">${result} = Display is 105</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.703\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Remove String\\" library=\\"String\\">\\r\\n<var>${total}</var>\\r\\n<arg>${result}</arg>\\r\\n<arg>Display is${SPACE}</arg>\\r\\n<doc>Removes all ``removables`` from the given ``string``.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">${total} = 105</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Convert To Integer\\" library=\\"BuiltIn\\">\\r\\n<var>${total}</var>\\r\\n<arg>${total}</arg>\\r\\n<doc>Converts the given item to an integer number.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">${total} = 105</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>${total}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">${total} = 105</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.703\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Append To List\\" library=\\"Collections\\">\\r\\n<arg>${totals}</arg>\\r\\n<arg>${total}</arg>\\r\\n<doc>Adds ``values`` to the end of ``list``.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:34.428\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</iter>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</for>\\r\\n<kw name=\\"Set Table Column\\" library=\\"RPA.Tables\\">\\r\\n<arg>${table}</arg>\\r\\n<arg>Totals</arg>\\r\\n<arg>${totals}</arg>\\r\\n<doc>Assign values to a column in the table.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<return>\\r\\n<value>@{table}</value>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</return>\\r\\n<msg timestamp=\\"20231127 07:14:40.719\\" level=\\"INFO\\">${outputs} = [{\'Carrots\': 15, \'Turnips\': 6, \'Totals\': 21}, {\'Carrots\': 99, \'Turnips\': 12, \'Totals\': 111}, {\'Carrots\': 3, \'Turnips\': 9, \'Totals\': 12}, {\'Carrots\': 10, \'Turnips\': 3, \'Totals\': 13}, {\'Carrots\': 14, \'T...</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:11.532\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Save Veggie Results Excel\\">\\r\\n<arg>${outputs}</arg>\\r\\n<doc>Writes the Excel sheet for total amounts of veggies</doc>\\r\\n<kw name=\\"Create Workbook\\" library=\\"RPA.Excel.Files\\">\\r\\n<arg>C:\\\\\\\\robotmk\\\\\\\\v2\\\\\\\\data\\\\\\\\windows-example-calculator${/}calculation_results.xlsx</arg>\\r\\n<arg>xlsx</arg>\\r\\n<doc>Create and open a new Excel workbook.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.719\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Create Worksheet\\" library=\\"RPA.Excel.Files\\">\\r\\n<arg>Vegetables</arg>\\r\\n<arg>${outputs}</arg>\\r\\n<arg>${TRUE}</arg>\\r\\n<arg>${TRUE}</arg>\\r\\n<doc>Create a new worksheet in the current workbook.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.735\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Save Workbook\\" library=\\"RPA.Excel.Files\\">\\r\\n<arg>${OUTPUT_EXCEL}</arg>\\r\\n<doc>Save the active workbook.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.735\\" endtime=\\"20231127 07:14:40.735\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.719\\" endtime=\\"20231127 07:14:40.735\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Close Window\\" library=\\"RPA.Windows\\">\\r\\n<arg>name:Calculator</arg>\\r\\n<tag>window</tag>\\r\\n<doc>Closes identified windows or logs the problems.</doc>\\r\\n<msg timestamp=\\"20231127 07:14:40.751\\" level=\\"INFO\\">Getting element with locator: name:Calculator and type:WindowControl</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.751\\" level=\\"INFO\\">Resulted root element: WindowsElement(item=&lt;uiautomation.uiautomation.PaneControl object at 0x00000177684F0F10&gt;, locator=\'name:Calculator\', name=\'Desktop 1\', automation_id=\'\', control_type=\'PaneControl\', class_name=\'#32769\', left=0, right=1920, top=0, bottom=1200, width=1920, height=1200, xcenter=960, ycenter=600)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.751\\" level=\\"INFO\\">Locator \'name:Calculator and type:WindowControl\' produced matcher: MatchObject(locators=[(\'Name\', \'Calculator\', 0), (\'ControlType\', \'WindowControl\', 0)], _classes=set(), max_level=0)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.864\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768195910&gt;, locator=\'name:Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.893\\" level=\\"INFO\\">Getting element with locator: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768195910&gt;, locator=\'name:Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:40.896\\" level=\\"INFO\\">Returning element: WindowsElement(item=&lt;uiautomation.uiautomation.WindowControl object at 0x0000017768195910&gt;, locator=\'name:Calculator and type:WindowControl\', name=\'Calculator\', automation_id=\'\', control_type=\'WindowControl\', class_name=\'ApplicationFrameWindow\', left=80, right=1296, top=64, bottom=1005, width=1216, height=941, xcenter=688, ycenter=534)</msg>\\r\\n<msg timestamp=\\"20231127 07:14:41.411\\" level=\\"INFO\\">Closing window with name: Calculator (PID: 2704)</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:40.735\\" endtime=\\"20231127 07:14:41.411\\"/>\\r\\n</kw>\\r\\n<doc>A sample robot that reads two columns of input and outputs calculations</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:06.658\\" endtime=\\"20231127 07:14:41.432\\"/>\\r\\n</test>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:14:04.925\\" endtime=\\"20231127 07:14:41.433\\"/>\\r\\n</suite>\\r\\n<statistics>\\r\\n<total>\\r\\n<stat pass=\\"1\\" fail=\\"0\\" skip=\\"0\\">All Tasks</stat>\\r\\n</total>\\r\\n<tag>\\r\\n</tag>\\r\\n<suite>\\r\\n<stat pass=\\"1\\" fail=\\"0\\" skip=\\"0\\" id=\\"s1\\" name=\\"Tasks\\">Tasks</stat>\\r\\n</suite>\\r\\n</statistics>\\r\\n<errors>\\r\\n</errors>\\r\\n</robot>\\r\\n","html_base64":"aXJyZWxldmFudA==","timestamp":1701098081}},"config":{"interval":120,"timeout":90,"n_attempts_max":1}}'
    ],
    [
        '{"suite_id":"math","attempts":["AllTestsPassed"],"rebot":{"Ok":{"xml":"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\r\\n<robot generator=\\"Rebot 6.1.1 (Python 3.11.4 on win32)\\" generated=\\"20231127 07:15:45.884\\" rpa=\\"false\\" schemaversion=\\"4\\">\\r\\n<suite id=\\"s1\\" name=\\"Tasks\\" source=\\"C:\\\\robotmk\\\\v2\\\\data\\\\retry_suite\\\\tasks.robot\\">\\r\\n<kw name=\\"Setup\\" library=\\"math\\" type=\\"SETUP\\">\\r\\n<msg timestamp=\\"20231127 07:15:45.515\\" level=\\"INFO\\">Setting up...</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.515\\"/>\\r\\n</kw>\\r\\n<test id=\\"s1-t1\\" name=\\"Addition 1\\" line=\\"17\\">\\r\\n<kw name=\\"Add\\" library=\\"math\\">\\r\\n<var>${result}</var>\\r\\n<arg>${20}</arg>\\r\\n<arg>${15}</arg>\\r\\n<msg timestamp=\\"20231127 07:15:45.515\\" level=\\"INFO\\">${result} = 35</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.515\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Should Be Equal As Integers\\" library=\\"BuiltIn\\">\\r\\n<arg>${result}</arg>\\r\\n<arg>${35}</arg>\\r\\n<doc>Fails if objects are unequal after converting them to integers.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.515\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.515\\"/>\\r\\n</test>\\r\\n<test id=\\"s1-t2\\" name=\\"Addition 2\\" line=\\"21\\">\\r\\n<kw name=\\"Add\\" library=\\"math\\">\\r\\n<var>${result}</var>\\r\\n<arg>${1}</arg>\\r\\n<arg>${2}</arg>\\r\\n<msg timestamp=\\"20231127 07:15:45.518\\" level=\\"INFO\\">${result} = 3</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.518\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Should Be Equal As Integers\\" library=\\"BuiltIn\\">\\r\\n<arg>${result}</arg>\\r\\n<arg>${expected_result_2}</arg>\\r\\n<doc>Fails if objects are unequal after converting them to integers.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.518\\" endtime=\\"20231127 07:15:45.518\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.515\\" endtime=\\"20231127 07:15:45.518\\"/>\\r\\n</test>\\r\\n<kw name=\\"Teardown\\" library=\\"math\\" type=\\"TEARDOWN\\">\\r\\n<msg timestamp=\\"20231127 07:15:45.518\\" level=\\"INFO\\">Tearing down...</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.518\\" endtime=\\"20231127 07:15:45.518\\"/>\\r\\n</kw>\\r\\n<doc>Test file for configuring RobotFramework</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:15:45.468\\" endtime=\\"20231127 07:15:45.518\\"/>\\r\\n</suite>\\r\\n<statistics>\\r\\n<total>\\r\\n<stat pass=\\"2\\" fail=\\"0\\" skip=\\"0\\">All Tests</stat>\\r\\n</total>\\r\\n<tag>\\r\\n</tag>\\r\\n<suite>\\r\\n<stat pass=\\"2\\" fail=\\"0\\" skip=\\"0\\" id=\\"s1\\" name=\\"Tasks\\">Tasks</stat>\\r\\n</suite>\\r\\n</statistics>\\r\\n<errors>\\r\\n</errors>\\r\\n</robot>\\r\\n","html_base64":"aXJyZWxldmFudA==","timestamp":1701098145}},"config":{"interval":15,"timeout":5,"n_attempts_max":1}}',
    ],
    [
        '{"suite_id":"google_imagesearch","attempts":["AllTestsPassed"],"rebot":{"Ok":{"xml":"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\r\\n<robot generator=\\"Rebot 5.0.1 (Python 3.9.13 on win32)\\" generated=\\"20231127 07:10:46.520\\" rpa=\\"true\\" schemaversion=\\"3\\">\\r\\n<suite id=\\"s1\\" name=\\"Tasks\\" source=\\"C:\\\\robotmk\\\\v2\\\\data\\\\google-imagesearch\\\\tasks.robot\\">\\r\\n<test id=\\"s1-t1\\" name=\\"Execute Google image search and store the first result image\\" line=\\"48\\">\\r\\n<try>\\r\\n<branch type=\\"TRY\\">\\r\\n<kw name=\\"Open Google search page\\">\\r\\n<kw name=\\"Get Environment Variable\\" library=\\"OperatingSystem\\">\\r\\n<var>${use_chrome}</var>\\r\\n<arg>USE_CHROME</arg>\\r\\n<arg>${EMPTY}</arg>\\r\\n<doc>Returns the value of an environment variable with the given name.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:04.396\\" level=\\"INFO\\">${use_chrome} = </msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.395\\" endtime=\\"20231127 07:10:04.396\\"/>\\r\\n</kw>\\r\\n<if>\\r\\n<branch type=\\"IF\\" condition=\\"&quot;${use_chrome}&quot; != &quot;&quot;\\">\\r\\n<kw name=\\"Open Available Browser\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>${GOOGLE_URL}</arg>\\r\\n<arg>browser_selection=Chrome</arg>\\r\\n<arg>download=${True}</arg>\\r\\n<doc>Attempts to open a browser on the user\'s device from a set of\\r\\nsupported browsers. Automatically downloads a corresponding webdriver\\r\\nif none is already installed.</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:10:04.397\\" endtime=\\"20231127 07:10:04.397\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:10:04.397\\" endtime=\\"20231127 07:10:04.397\\"/>\\r\\n</branch>\\r\\n<branch type=\\"ELSE\\">\\r\\n<kw name=\\"Open Available Browser\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>${GOOGLE_URL}</arg>\\r\\n<doc>Attempts to open a browser on the user\'s device from a set of\\r\\nsupported browsers. Automatically downloads a corresponding webdriver\\r\\nif none is already installed.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:06.244\\" level=\\"INFO\\">====== WebDriver manager ======</msg>\\r\\n<msg timestamp=\\"20231127 07:10:11.942\\" level=\\"INFO\\">Downloaded webdriver to: C:\\\\Windows\\\\System32\\\\config\\\\systemprofile\\\\AppData\\\\Local\\\\robocorp\\\\webdrivers\\\\.wdm\\\\drivers\\\\chromedriver\\\\win64\\\\119.0.6045.105\\\\chromedriver-win32/chromedriver.exe</msg>\\r\\n<msg timestamp=\\"20231127 07:10:11.942\\" level=\\"INFO\\">Creating an instance of the Chrome WebDriver.</msg>\\r\\n<msg timestamp=\\"20231127 07:10:13.244\\" level=\\"INFO\\">Created Chrome browser with arguments: --disable-dev-shm-usage --disable-web-security --allow-running-insecure-content --no-sandbox</msg>\\r\\n<msg timestamp=\\"20231127 07:10:13.244\\" level=\\"INFO\\" html=\\"true\\">&lt;p&gt;Attempted combinations:&lt;/p&gt;&lt;div class=\\"doc\\"&gt;&lt;table&gt;&lt;tr&gt;&lt;th&gt;Browser&lt;/th&gt;&lt;th&gt;Download&lt;/th&gt;&lt;th&gt;Error&lt;/th&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td&gt;Chrome&lt;/td&gt;&lt;td&gt;False&lt;/td&gt;&lt;td&gt;expected str, bytes or os.PathLike object, not NoneType&lt;/td&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td&gt;Chrome&lt;/td&gt;&lt;td&gt;True&lt;/td&gt;&lt;td&gt;&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;&lt;/div&gt;</msg>\\r\\n<msg timestamp=\\"20231127 07:10:13.244\\" level=\\"INFO\\">Opening url \'https://google.com/?hl=en\'</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.397\\" endtime=\\"20231127 07:10:13.905\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.397\\" endtime=\\"20231127 07:10:13.905\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.396\\" endtime=\\"20231127 07:10:13.905\\"/>\\r\\n</if>\\r\\n<kw name=\\"Run Keyword And Ignore Error\\" library=\\"BuiltIn\\">\\r\\n<arg>Close Google Sign in</arg>\\r\\n<doc>Runs the given keyword with the given arguments and ignores possible error.</doc>\\r\\n<kw name=\\"Close Google Sign in\\">\\r\\n<kw name=\\"Click Element If Visible\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>No thanks</arg>\\r\\n<doc>Click element if it is visible</doc>\\r\\n<msg timestamp=\\"20231127 07:10:13.922\\" level=\\"INFO\\" html=\\"true\\">Ran with keyword &lt;b&gt;Element Should Be Visible&lt;/b&gt; which returned error: &lt;i&gt;Element with locator \'No thanks\' not found.&lt;/i&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.906\\" endtime=\\"20231127 07:10:13.924\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.906\\" endtime=\\"20231127 07:10:13.924\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.906\\" endtime=\\"20231127 07:10:13.924\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Run Keyword And Ignore Error\\" library=\\"BuiltIn\\">\\r\\n<arg>Reject Google Cookies</arg>\\r\\n<doc>Runs the given keyword with the given arguments and ignores possible error.</doc>\\r\\n<kw name=\\"Reject Google Cookies\\">\\r\\n<kw name=\\"Click Element If Visible\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>xpath://button/div[contains(text(), \'Reject all\')]</arg>\\r\\n<doc>Click element if it is visible</doc>\\r\\n<msg timestamp=\\"20231127 07:10:13.962\\" level=\\"INFO\\">Element \'xpath://button/div[contains(text(), \'Reject all\')]\' is displayed.</msg>\\r\\n<msg timestamp=\\"20231127 07:10:13.962\\" level=\\"INFO\\">Clicking element \'xpath://button/div[contains(text(), \'Reject all\')]\'.</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.924\\" endtime=\\"20231127 07:10:14.029\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.924\\" endtime=\\"20231127 07:10:14.030\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:13.924\\" endtime=\\"20231127 07:10:14.030\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Run Keyword And Ignore Error\\" library=\\"BuiltIn\\">\\r\\n<arg>Accept Google Consent</arg>\\r\\n<doc>Runs the given keyword with the given arguments and ignores possible error.</doc>\\r\\n<kw name=\\"Accept Google Consent\\">\\r\\n<kw name=\\"Click Element If Visible\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>xpath://button/div[contains(text(), \'I agree\')]</arg>\\r\\n<doc>Click element if it is visible</doc>\\r\\n<msg timestamp=\\"20231127 07:10:14.046\\" level=\\"INFO\\" html=\\"true\\">Ran with keyword &lt;b&gt;Element Should Be Visible&lt;/b&gt; which returned error: &lt;i&gt;Element with locator \'xpath://button/div[contains(text(), \'I agree\')]\' not found.&lt;/i&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.031\\" endtime=\\"20231127 07:10:14.046\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.031\\" endtime=\\"20231127 07:10:14.047\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.030\\" endtime=\\"20231127 07:10:14.047\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.395\\" endtime=\\"20231127 07:10:14.047\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Search for\\">\\r\\n<arg>${SEARCH_TERM}</arg>\\r\\n<kw name=\\"Wait Until Page Contains Element\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>name:q</arg>\\r\\n<doc>Waits until the element ``locator`` appears on the current page.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.048\\" endtime=\\"20231127 07:10:14.064\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Input Text\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>name:q</arg>\\r\\n<arg>${text}</arg>\\r\\n<doc>Types the given ``text`` into the text field identified by ``locator``.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:14.065\\" level=\\"INFO\\">Typing text \'cute monkey picture\' into text field \'name:q\'.</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.065\\" endtime=\\"20231127 07:10:14.227\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Press Keys\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>name:q</arg>\\r\\n<arg>ENTER</arg>\\r\\n<doc>Simulates the user pressing key(s) to an element or on the active browser.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:14.227\\" level=\\"INFO\\">Sending key(s) (\'ENTER\',) to name:q element.</msg>\\r\\n<msg timestamp=\\"20231127 07:10:14.537\\" level=\\"INFO\\">Pressing special key ENTER to element.</msg>\\r\\n<msg timestamp=\\"20231127 07:10:14.538\\" level=\\"INFO\\">Releasing special key ENTER.</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.227\\" endtime=\\"20231127 07:10:16.393\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Wait Until Page Contains Element\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>search</arg>\\r\\n<doc>Waits until the element ``locator`` appears on the current page.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:16.393\\" endtime=\\"20231127 07:10:16.412\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:14.047\\" endtime=\\"20231127 07:10:16.412\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Capture Image Result\\">\\r\\n<kw name=\\"Click Link\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>Images</arg>\\r\\n<doc>Clicks a link identified by ``locator``.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:16.412\\" level=\\"INFO\\">Clicking link \'Images\'.</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:16.412\\" endtime=\\"20231127 07:10:17.975\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Wait Until Page Contains Element\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>css:div[data-ri=\\"0\\"]</arg>\\r\\n<arg>2</arg>\\r\\n<doc>Waits until the element ``locator`` appears on the current page.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:17.975\\" endtime=\\"20231127 07:10:17.994\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Capture Element Screenshot\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>css:div[data-ri=\\"0\\"]</arg>\\r\\n<doc>Captures a screenshot from the element identified by ``locator`` and embeds it into log file.</doc>\\r\\n<msg timestamp=\\"20231127 07:10:18.094\\" level=\\"INFO\\" html=\\"true\\">&lt;/td&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td colspan=\\"3\\"&gt;&lt;img alt=\\"screenshot\\" class=\\"robot-seleniumlibrary-screenshot\\" src=\\"data:image/png;base64,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\\" width=\\"400px\\"&gt;</msg>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:17.994\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:16.412\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.393\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</branch>\\r\\n<branch type=\\"EXCEPT\\">\\r\\n<kw name=\\"Capture Page Screenshot\\" library=\\"RPA.Browser.Selenium\\">\\r\\n<arg>%{ROBOT_ARTIFACTS}${/}error.png</arg>\\r\\n<doc>Takes a screenshot of the current page and embeds it into a log file.</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:10:18.095\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</kw>\\r\\n<kw name=\\"Fail\\" library=\\"BuiltIn\\">\\r\\n<arg>Checkout the screenshot: error.png</arg>\\r\\n<doc>Fails the test with the given message and optionally alters its tags.</doc>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:10:18.095\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</kw>\\r\\n<status status=\\"NOT RUN\\" starttime=\\"20231127 07:10:18.095\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</branch>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.393\\" endtime=\\"20231127 07:10:18.095\\"/>\\r\\n</try>\\r\\n<kw name=\\"Close Browser\\" library=\\"RPA.Browser.Selenium\\" type=\\"TEARDOWN\\">\\r\\n<doc>Closes the current browser.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:18.095\\" endtime=\\"20231127 07:10:20.164\\"/>\\r\\n</kw>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:04.392\\" endtime=\\"20231127 07:10:20.164\\"/>\\r\\n</test>\\r\\n<doc>Executes Google image search and stores the first result image.</doc>\\r\\n<status status=\\"PASS\\" starttime=\\"20231127 07:10:02.977\\" endtime=\\"20231127 07:10:20.166\\"/>\\r\\n</suite>\\r\\n<statistics>\\r\\n<total>\\r\\n<stat pass=\\"1\\" fail=\\"0\\" skip=\\"0\\">All Tasks</stat>\\r\\n</total>\\r\\n<tag>\\r\\n</tag>\\r\\n<suite>\\r\\n<stat pass=\\"1\\" fail=\\"0\\" skip=\\"0\\" id=\\"s1\\" name=\\"Tasks\\">Tasks</stat>\\r\\n</suite>\\r\\n</statistics>\\r\\n<errors>\\r\\n</errors>\\r\\n</robot>\\r\\n","html_base64":"aXJyZWxldmFudA==","timestamp":1701097844}},"config":{"interval":120,"timeout":90,"n_attempts_max":1}}'
    ],
    [
        '{"suite_id":"skipped_tests","attempts":["TestFailures"],"rebot":{"Ok":{"xml":"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\r\\n<robot generator=\\"Rebot 5.0.1 (Python 3.9.12 on win32)\\" generated=\\"20231130 06:40:56.603\\" rpa=\\"false\\" schemaversion=\\"3\\">\\r\\n<suite id=\\"s1\\" name=\\"Tasks\\" source=\\"C:\\\\robotmk\\\\v2\\\\data\\\\minimal_suite_skipped_tests\\\\tasks.robot\\">\\r\\n<test id=\\"s1-t1\\" name=\\"Main Test One\\" line=\\"2\\">\\r\\n<kw name=\\"Fail\\" library=\\"BuiltIn\\">\\r\\n<arg>msg=\\"Raised an error in Test 1\\"</arg>\\r\\n<doc>Fails the test with the given message and optionally alters its tags.</doc>\\r\\n<msg timestamp=\\"20231130 06:40:53.349\\" level=\\"FAIL\\">\\"Raised an error in Test 1\\"</msg>\\r\\n<status status=\\"FAIL\\" starttime=\\"20231130 06:40:53.348\\" endtime=\\"20231130 06:40:53.349\\"/>\\r\\n</kw>\\r\\n<status status=\\"FAIL\\" starttime=\\"20231130 06:40:53.347\\" endtime=\\"20231130 06:40:53.349\\">\\"Raised an error in Test 1\\"</status>\\r\\n</test>\\r\\n<test id=\\"s1-t2\\" name=\\"Main Test Two\\" line=\\"5\\">\\r\\n<tag>robot:exit</tag>\\r\\n<status status=\\"FAIL\\" starttime=\\"20231130 06:40:53.351\\" endtime=\\"20231130 06:40:53.351\\">Failure occurred and exit-on-failure mode is in use.</status>\\r\\n</test>\\r\\n<test id=\\"s1-t3\\" name=\\"Main Test Three\\" line=\\"8\\">\\r\\n<tag>some_other_tag</tag>\\r\\n<status status=\\"FAIL\\" starttime=\\"20231130 06:40:53.351\\" endtime=\\"20231130 06:40:53.351\\">Failure occurred and exit-on-failure mode is in use.</status>\\r\\n</test>\\r\\n<status status=\\"FAIL\\" starttime=\\"20231130 06:40:53.283\\" endtime=\\"20231130 06:40:53.353\\"/>\\r\\n</suite>\\r\\n<statistics>\\r\\n<total>\\r\\n<stat pass=\\"0\\" fail=\\"3\\" skip=\\"0\\">All Tests</stat>\\r\\n</total>\\r\\n<tag>\\r\\n</tag>\\r\\n<suite>\\r\\n<stat pass=\\"0\\" fail=\\"3\\" skip=\\"0\\" id=\\"s1\\" name=\\"Tasks\\">Tasks</stat>\\r\\n</suite>\\r\\n</statistics>\\r\\n<errors>\\r\\n</errors>\\r\\n</robot>\\r\\n","html_base64":"aXJyZWxldmFudA==","timestamp":1701355253}},"config":{"interval":10,"timeout":5,"n_attempts_max":1}}'
    ],
]


def test_parse() -> None:
    assert parse(_STRING_TABLE) == Section(
        suites={
            "calc": SuiteReport(
                attempts=[AttemptOutcome.AllTestsPassed],
                config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
                rebot=SuiteRebotReport(
                    top_level_suite=Suite.model_construct(
                        name="Tasks",
                        suite=[],
                        test=[
                            RFTest.model_construct(
                                id="s1-t1",
                                name="Count My Veggies",
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 658000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 41, 432000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[
                                    Keyword(
                                        name="Check Veggies Excel And Start Calculator",
                                        id="s1-t1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Does File Exist",
                                        id="s1-t1-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Fail",
                                        id="s1-t1-k1-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 668000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 668000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Windows Search",
                                        id="s1-t1-k1-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Read Veggies Excel",
                                        id="s1-t1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Open Workbook",
                                        id="s1-t1-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Read Worksheet As Table",
                                        id="s1-t1-k2-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Close Workbook",
                                        id="s1-t1-k2-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Count Veggie Totals",
                                        id="s1-t1-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Create List",
                                        id="s1-t1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k1-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k1-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k1-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 13, 79000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 13, 79000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k1-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k1-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k1-k1-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 13, 81000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 13, 734000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k1-k1-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 13, 734000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 14, 376000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k1-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k1-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k1-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k1-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k1-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k1-k3-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 16, 909000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Result From Calc",
                                        id="s1-t1-k3-k2-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Attribute",
                                        id="s1-t1-k3-k2-k1-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Remove String",
                                        id="s1-t1-k3-k2-k1-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To Integer",
                                        id="s1-t1-k3-k2-k1-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Append To List",
                                        id="s1-t1-k3-k2-k1-k6",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k2-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k2-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k2-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k2-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k2-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k1-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 19, 453000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k1-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 19, 453000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 20, 110000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k2-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k2-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k2-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k2-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k2-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k2-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k3-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 22, 593000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k3-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 22, 593000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 23, 208000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k2-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Result From Calc",
                                        id="s1-t1-k3-k2-k2-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Attribute",
                                        id="s1-t1-k3-k2-k2-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Remove String",
                                        id="s1-t1-k3-k2-k2-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To Integer",
                                        id="s1-t1-k3-k2-k2-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Append To List",
                                        id="s1-t1-k3-k2-k2-k6",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k3-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k3-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k3-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k3-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k3-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k3-k1-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 25, 712000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k3-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k3-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k3-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k3-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k3-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k3-k3-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 28, 190000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Result From Calc",
                                        id="s1-t1-k3-k2-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Attribute",
                                        id="s1-t1-k3-k2-k3-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Remove String",
                                        id="s1-t1-k3-k2-k3-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To Integer",
                                        id="s1-t1-k3-k2-k3-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Append To List",
                                        id="s1-t1-k3-k2-k3-k6",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k4-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k4-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k4-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k4-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k4-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k4-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k4-k1-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 30, 690000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k4-k1-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 30, 690000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 31, 327000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k4-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k4-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k4-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k4-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k4-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k4-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k4-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k4-k3-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 33, 796000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k4-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Result From Calc",
                                        id="s1-t1-k3-k2-k4-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Attribute",
                                        id="s1-t1-k3-k2-k4-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Remove String",
                                        id="s1-t1-k3-k2-k4-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To Integer",
                                        id="s1-t1-k3-k2-k4-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Append To List",
                                        id="s1-t1-k3-k2-k4-k6",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k5-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k5-k1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k5-k1-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k5-k1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k5-k1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k1-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 36, 300000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k1-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 36, 301000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 36, 936000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Input Number To Calc",
                                        id="s1-t1-k3-k2-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Control Window",
                                        id="s1-t1-k3-k2-k5-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k5-k3-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click If Available",
                                        id="s1-t1-k3-k2-k5-k3-k3-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.NOT_RUN,
                                                starttime=datetime(2023, 11, 27, 7, 14, 38, 776000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 38, 776000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To String",
                                        id="s1-t1-k3-k2-k5-k3-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Split String To Characters",
                                        id="s1-t1-k3-k2-k5-k3-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k3-k6-k1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 38, 778000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 39, 439000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k3-k6-k2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 39, 439000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 66000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Click",
                                        id="s1-t1-k3-k2-k5-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Result From Calc",
                                        id="s1-t1-k3-k2-k5-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Get Attribute",
                                        id="s1-t1-k3-k2-k5-k5-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Remove String",
                                        id="s1-t1-k3-k2-k5-k5-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Convert To Integer",
                                        id="s1-t1-k3-k2-k5-k5-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Append To List",
                                        id="s1-t1-k3-k2-k5-k6",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Set Table Column",
                                        id="s1-t1-k3-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Save Veggie Results Excel",
                                        id="s1-t1-k4",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Create Workbook",
                                        id="s1-t1-k4-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Create Worksheet",
                                        id="s1-t1-k4-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Save Workbook",
                                        id="s1-t1-k4-k3",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Close Window",
                                        id="s1-t1-k5",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                                endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                        status=StatusV6.model_construct(
                            status=Outcome.PASS,
                            starttime=datetime(2023, 11, 27, 7, 14, 4, 925000),
                            endtime=datetime(2023, 11, 27, 7, 14, 41, 433000),
                            elapsed=None,
                        ),
                    ),
                    timestamp=1701098081,
                ),
            ),
            "math": SuiteReport(
                attempts=[AttemptOutcome.AllTestsPassed],
                config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
                rebot=SuiteRebotReport(
                    top_level_suite=Suite.model_construct(
                        name="Tasks",
                        suite=[],
                        test=[
                            RFTest.model_construct(
                                id="s1-t1",
                                name="Addition 1",
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[
                                    Keyword(
                                        name="Add",
                                        id="s1-t1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Should Be Equal As Integers",
                                        id="s1-t1-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                ],
                            ),
                            RFTest.model_construct(
                                id="s1-t2",
                                name="Addition 2",
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[
                                    Keyword(
                                        name="Add",
                                        id="s1-t2-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                    Keyword(
                                        name="Should Be Equal As Integers",
                                        id="s1-t2-k2",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                                endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                                                elapsed=None,
                                            )
                                        ),
                                    ),
                                ],
                            ),
                        ],
                        status=StatusV6.model_construct(
                            status=Outcome.PASS,
                            starttime=datetime(2023, 11, 27, 7, 15, 45, 468000),
                            endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                            elapsed=None,
                        ),
                    ),
                    timestamp=1701098145,
                ),
            ),
            "google_imagesearch": SuiteReport(
                attempts=[AttemptOutcome.AllTestsPassed],
                config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
                rebot=SuiteRebotReport(
                    top_level_suite=Suite.model_construct(
                        name="Tasks",
                        suite=[],
                        test=[
                            RFTest.model_construct(
                                id="s1-t1",
                                name="Execute Google image search and store the first result image",
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 10, 4, 392000),
                                    endtime=datetime(2023, 11, 27, 7, 10, 20, 164000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[
                                    Keyword(
                                        name="Close Browser",
                                        id="s1-t1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.PASS,
                                                starttime=datetime(2023, 11, 27, 7, 10, 4, 395000),
                                                endtime=datetime(2023, 11, 27, 7, 10, 4, 396000),
                                                elapsed=None,
                                            )
                                        ),
                                    )
                                ],
                            )
                        ],
                        status=StatusV6.model_construct(
                            status=Outcome.PASS,
                            starttime=datetime(2023, 11, 27, 7, 10, 2, 977000),
                            endtime=datetime(2023, 11, 27, 7, 10, 20, 166000),
                            elapsed=None,
                        ),
                    ),
                    timestamp=1701097844,
                ),
            ),
            "skipped_tests": SuiteReport(
                attempts=[AttemptOutcome.TestFailures],
                config=AttemptsConfig(interval=10, timeout=5, n_attempts_max=1),
                rebot=SuiteRebotReport(
                    top_level_suite=Suite.model_construct(
                        name="Tasks",
                        suite=[],
                        test=[
                            RFTest.model_construct(
                                id="s1-t1",
                                name="Main Test One",
                                status=StatusV6.model_construct(
                                    status=Outcome.FAIL,
                                    starttime=datetime(2023, 11, 30, 6, 40, 53, 347000),
                                    endtime=datetime(2023, 11, 30, 6, 40, 53, 349000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[
                                    Keyword(
                                        name="Fail",
                                        id="s1-t1-k1",
                                        status=KeywordStatus.model_construct(
                                            status=StatusV6.model_construct(
                                                status=Outcome.FAIL,
                                                starttime=datetime(2023, 11, 30, 6, 40, 53, 348000),
                                                endtime=datetime(2023, 11, 30, 6, 40, 53, 349000),
                                                elapsed=None,
                                            )
                                        ),
                                    )
                                ],
                            ),
                            RFTest.model_construct(
                                id="s1-t2",
                                name="Main Test Two",
                                status=StatusV6.model_construct(
                                    status=Outcome.FAIL,
                                    starttime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                                    endtime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                                    elapsed=None,
                                ),
                                robot_exit=True,
                                keywords=[],
                            ),
                            RFTest.model_construct(
                                id="s1-t3",
                                name="Main Test Three",
                                status=StatusV6.model_construct(
                                    status=Outcome.FAIL,
                                    starttime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                                    endtime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                                    elapsed=None,
                                ),
                                robot_exit=False,
                                keywords=[],
                            ),
                        ],
                        status=StatusV6.model_construct(
                            status=Outcome.FAIL,
                            starttime=datetime(2023, 11, 30, 6, 40, 53, 283000),
                            endtime=datetime(2023, 11, 30, 6, 40, 53, 353000),
                            elapsed=None,
                        ),
                    ),
                    timestamp=1701355253,
                ),
            ),
        },
        tests={
            "calc-Tasks-Count My Veggies": TestReport(
                test=RFTest.model_construct(
                    id="s1-t1",
                    name="Count My Veggies",
                    status=StatusV6.model_construct(
                        status=Outcome.PASS,
                        starttime=datetime(2023, 11, 27, 7, 14, 6, 658000),
                        endtime=datetime(2023, 11, 27, 7, 14, 41, 432000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[
                        Keyword(
                            name="Check Veggies Excel And Start Calculator",
                            id="s1-t1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Does File Exist",
                            id="s1-t1-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Fail",
                            id="s1-t1-k1-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 668000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 668000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Windows Search",
                            id="s1-t1-k1-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Read Veggies Excel",
                            id="s1-t1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Open Workbook",
                            id="s1-t1-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Read Worksheet As Table",
                            id="s1-t1-k2-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Close Workbook",
                            id="s1-t1-k2-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 518000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Count Veggie Totals",
                            id="s1-t1-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Create List",
                            id="s1-t1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k1-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k1-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k1-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 13, 79000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 13, 79000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k1-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k1-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k1-k1-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 13, 81000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 13, 734000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k1-k1-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 13, 734000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 14, 376000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k1-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k1-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k1-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k1-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k1-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 15, 24000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 15, 660000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k1-k3-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 16, 273000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 16, 909000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Result From Calc",
                            id="s1-t1-k3-k2-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Attribute",
                            id="s1-t1-k3-k2-k1-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Remove String",
                            id="s1-t1-k3-k2-k1-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To Integer",
                            id="s1-t1-k3-k2-k1-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 538000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Append To List",
                            id="s1-t1-k3-k2-k1-k6",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 12, 440000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k2-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k2-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k2-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k2-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k2-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k1-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 18, 802000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 19, 453000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k1-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 19, 453000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 20, 110000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k2-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k2-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k2-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k2-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k2-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k2-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 20, 727000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 21, 345000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k3-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 21, 949000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 22, 593000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k3-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 22, 593000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 23, 208000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k2-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Result From Calc",
                            id="s1-t1-k3-k2-k2-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Attribute",
                            id="s1-t1-k3-k2-k2-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Remove String",
                            id="s1-t1-k3-k2-k2-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To Integer",
                            id="s1-t1-k3-k2-k2-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 812000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Append To List",
                            id="s1-t1-k3-k2-k2-k6",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 17, 564000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 18, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k3-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k3-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k3-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k3-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k3-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k3-k1-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 25, 71000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 25, 712000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k3-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k3-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k3-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k3-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k3-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 26, 327000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 26, 946000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k3-k3-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 27, 544000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 28, 190000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Result From Calc",
                            id="s1-t1-k3-k2-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Attribute",
                            id="s1-t1-k3-k2-k3-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Remove String",
                            id="s1-t1-k3-k2-k3-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To Integer",
                            id="s1-t1-k3-k2-k3-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 824000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Append To List",
                            id="s1-t1-k3-k2-k3-k6",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 23, 831000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 24, 464000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k4-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k4-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k4-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k4-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k4-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k4-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k4-k1-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 30, 76000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 30, 690000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k4-k1-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 30, 690000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 31, 327000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k4-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k4-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k4-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k4-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k4-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k4-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k4-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 31, 955000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 32, 574000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k4-k3-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 33, 177000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 33, 796000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k4-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Result From Calc",
                            id="s1-t1-k3-k2-k4-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Attribute",
                            id="s1-t1-k3-k2-k4-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Remove String",
                            id="s1-t1-k3-k2-k4-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To Integer",
                            id="s1-t1-k3-k2-k4-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 412000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Append To List",
                            id="s1-t1-k3-k2-k4-k6",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 28, 847000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 29, 472000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k5-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k5-k1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k5-k1-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k5-k1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k5-k1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k1-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 35, 679000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 36, 300000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k1-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 36, 301000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 36, 936000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Input Number To Calc",
                            id="s1-t1-k3-k2-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Control Window",
                            id="s1-t1-k3-k2-k5-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k5-k3-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click If Available",
                            id="s1-t1-k3-k2-k5-k3-k3-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.NOT_RUN,
                                    starttime=datetime(2023, 11, 27, 7, 14, 38, 776000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 38, 776000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To String",
                            id="s1-t1-k3-k2-k5-k3-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Split String To Characters",
                            id="s1-t1-k3-k2-k5-k3-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 37, 562000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 38, 177000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k3-k6-k1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 38, 778000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 39, 439000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k3-k6-k2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 39, 439000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 66000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Click",
                            id="s1-t1-k3-k2-k5-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Result From Calc",
                            id="s1-t1-k3-k2-k5-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Get Attribute",
                            id="s1-t1-k3-k2-k5-k5-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Remove String",
                            id="s1-t1-k3-k2-k5-k5-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Convert To Integer",
                            id="s1-t1-k3-k2-k5-k5-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 703000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Append To List",
                            id="s1-t1-k3-k2-k5-k6",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 34, 428000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 35, 78000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Set Table Column",
                            id="s1-t1-k3-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 11, 532000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Save Veggie Results Excel",
                            id="s1-t1-k4",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Create Workbook",
                            id="s1-t1-k4-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Create Worksheet",
                            id="s1-t1-k4-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Save Workbook",
                            id="s1-t1-k4-k3",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 40, 719000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Close Window",
                            id="s1-t1-k5",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 14, 6, 659000),
                                    endtime=datetime(2023, 11, 27, 7, 14, 6, 665000),
                                    elapsed=None,
                                )
                            ),
                        ),
                    ],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
                rebot_timestamp=1701098081,
            ),
            "math-Tasks-Addition 1": TestReport(
                test=RFTest.model_construct(
                    id="s1-t1",
                    name="Addition 1",
                    status=StatusV6.model_construct(
                        status=Outcome.PASS,
                        starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                        endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[
                        Keyword(
                            name="Add",
                            id="s1-t1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Should Be Equal As Integers",
                            id="s1-t1-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    elapsed=None,
                                )
                            ),
                        ),
                    ],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
                rebot_timestamp=1701098145,
            ),
            "math-Tasks-Addition 2": TestReport(
                test=RFTest.model_construct(
                    id="s1-t2",
                    name="Addition 2",
                    status=StatusV6.model_construct(
                        status=Outcome.PASS,
                        starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                        endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[
                        Keyword(
                            name="Add",
                            id="s1-t2-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                                    elapsed=None,
                                )
                            ),
                        ),
                        Keyword(
                            name="Should Be Equal As Integers",
                            id="s1-t2-k2",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                                    elapsed=None,
                                )
                            ),
                        ),
                    ],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
                rebot_timestamp=1701098145,
            ),
            "google_imagesearch-Tasks-Execute Google image search and store the first result image": TestReport(
                test=RFTest.model_construct(
                    id="s1-t1",
                    name="Execute Google image search and store the first result image",
                    status=StatusV6.model_construct(
                        status=Outcome.PASS,
                        starttime=datetime(2023, 11, 27, 7, 10, 4, 392000),
                        endtime=datetime(2023, 11, 27, 7, 10, 20, 164000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[
                        Keyword(
                            name="Close Browser",
                            id="s1-t1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 27, 7, 10, 4, 395000),
                                    endtime=datetime(2023, 11, 27, 7, 10, 4, 396000),
                                    elapsed=None,
                                )
                            ),
                        )
                    ],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
                rebot_timestamp=1701097844,
            ),
            "skipped_tests-Tasks-Main Test One": TestReport(
                test=RFTest.model_construct(
                    id="s1-t1",
                    name="Main Test One",
                    status=StatusV6.model_construct(
                        status=Outcome.FAIL,
                        starttime=datetime(2023, 11, 30, 6, 40, 53, 347000),
                        endtime=datetime(2023, 11, 30, 6, 40, 53, 349000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[
                        Keyword(
                            name="Fail",
                            id="s1-t1-k1",
                            status=KeywordStatus.model_construct(
                                status=StatusV6.model_construct(
                                    status=Outcome.FAIL,
                                    starttime=datetime(2023, 11, 30, 6, 40, 53, 348000),
                                    endtime=datetime(2023, 11, 30, 6, 40, 53, 349000),
                                    elapsed=None,
                                )
                            ),
                        )
                    ],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=10, timeout=5, n_attempts_max=1),
                rebot_timestamp=1701355253,
            ),
            "skipped_tests-Tasks-Main Test Two": TestReport(
                test=RFTest.model_construct(
                    id="s1-t2",
                    name="Main Test Two",
                    status=StatusV6.model_construct(
                        status=Outcome.FAIL,
                        starttime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                        endtime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                        elapsed=None,
                    ),
                    robot_exit=True,
                    keywords=[],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=10, timeout=5, n_attempts_max=1),
                rebot_timestamp=1701355253,
            ),
            "skipped_tests-Tasks-Main Test Three": TestReport(
                test=RFTest.model_construct(
                    id="s1-t3",
                    name="Main Test Three",
                    status=StatusV6.model_construct(
                        status=Outcome.FAIL,
                        starttime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                        endtime=datetime(2023, 11, 30, 6, 40, 53, 351000),
                        elapsed=None,
                    ),
                    robot_exit=False,
                    keywords=[],
                ),
                html=b"irrelevant",
                attempts_config=AttemptsConfig(interval=10, timeout=5, n_attempts_max=1),
                rebot_timestamp=1701355253,
            ),
        },
    )


class _StatusV6Factory(ModelFactory[StatusV6]):
    __model__ = StatusV6


class _SuiteFactory(ModelFactory[Suite]):
    __model__ = Suite

    status = _StatusV6Factory.build(
        factory_use_construct=True,
        status=Outcome.PASS,
        starttime=datetime(2023, 11, 14, 13, 27, 40),
        endtime=datetime(2023, 11, 14, 13, 45, 56),
    )


class _TestFactory(ModelFactory[RFTest]):
    __model__ = RFTest

    status = _StatusV6Factory.build(
        factory_use_construct=True,
        status=Outcome.PASS,
        starttime=datetime(2023, 11, 14, 13, 29, 33),
        endtime=datetime(2023, 11, 14, 13, 31, 34),
    )
    keywords: Sequence[Keyword] = []


def test_extract_tests_empty() -> None:
    assert not _tests_by_items(
        _SuiteFactory.build(factory_use_construct=True, name="EmptySuite", test=[], suite=[])
    )


def test_extract_single_test() -> None:
    single_test_suite = _SuiteFactory.build(
        factory_use_construct=True,
        name="SingleTestSuite",
        test=[
            _TestFactory.build(
                factory_use_construct=True, id="s1-t1", name="Test1", robot_exit=False
            )
        ],
        suite=[],
    )
    assert _tests_by_items(single_test_suite) == {
        "SingleTestSuite-Test1": _TestFactory.build(
            factory_use_construct=True, id="s1-t1", name="Test1", robot_exit=False
        )
    }


def test_extract_multiple_tests() -> None:
    multiple_tests_suite = _SuiteFactory.build(
        factory_use_construct=True,
        name="MultipleTestsSuite",
        test=[
            _TestFactory.build(
                factory_use_construct=True, id="s1-t1", name="Test1", robot_exit=False
            ),
            _TestFactory.build(
                factory_use_construct=True, id="s1-t2", name="Test2", robot_exit=False
            ),
        ],
        suite=[],
    )
    assert _tests_by_items(multiple_tests_suite) == {
        "MultipleTestsSuite-Test1": _TestFactory.build(
            factory_use_construct=True, id="s1-t1", name="Test1", robot_exit=False
        ),
        "MultipleTestsSuite-Test2": _TestFactory.build(
            factory_use_construct=True, id="s1-t2", name="Test2", robot_exit=False
        ),
    }


def test_extract_tests_from_nested_suites() -> None:
    nested_suites = _SuiteFactory.build(
        factory_use_construct=True,
        name="TopSuite",
        test=[
            _TestFactory.build(
                factory_use_construct=True, id="s1-t1", name="Test4", robot_exit=False
            )
        ],
        suite=[
            _SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite1",
                test=[
                    _TestFactory.build(
                        factory_use_construct=True, id="s1-s1-t1", name="Test1", robot_exit=False
                    ),
                ],
                suite=[
                    _SuiteFactory.build(
                        factory_use_construct=True,
                        name="SubSubSuite",
                        test=[
                            _TestFactory.build(
                                factory_use_construct=True,
                                id="s1-s1-s1-t1",
                                name="Test2",
                                robot_exit=True,
                            )
                        ],
                        suite=[],
                    )
                ],
            ),
            _SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite2",
                test=[
                    _TestFactory.build(
                        factory_use_construct=True, id="s1-s2-t1", name="Test3", robot_exit=False
                    )
                ],
                suite=[],
            ),
        ],
    )
    assert _tests_by_items(nested_suites) == {
        "TopSuite-Test4": _TestFactory.build(
            factory_use_construct=True, id="s1-t1", name="Test4", robot_exit=False
        ),
        "TopSuite-SubSuite1-Test1": _TestFactory.build(
            factory_use_construct=True, id="s1-s1-t1", name="Test1", robot_exit=False
        ),
        "TopSuite-SubSuite1-SubSubSuite-Test2": _TestFactory.build(
            factory_use_construct=True, id="s1-s1-s1-t1", name="Test2", robot_exit=True
        ),
        "TopSuite-SubSuite2-Test3": _TestFactory.build(
            factory_use_construct=True, id="s1-s2-t1", name="Test3", robot_exit=False
        ),
    }
