import pytest

pytestmark = pytest.mark.checks

info_1 = [[u'[[[site:heute:test]]]'], [u'{'], [u'"bytes_per_second":', u'1578215.4167199447,'],
          [u'"finished":', u'1511788263.410466,'], [u'"next_schedule":', u'1511874660.0,'],
          [
              u'"output":', u'"2017-11-27', u'14:11:02', u'---', u'Starting', u'backup',
              u'(Check_MK-klappfel-heute-test', u'to', u'testtgt)', u'---\\n2017-11-27',
              u'14:11:03', u'Verifying', u'backup', u'consistency\\n2017-11-27', u'14:11:03',
              u'---', u'Backup', u'completed', u'(Duration:', u'0:00:01,', u'Size:', u'1.80',
              u'MB,', u'IO:', u'1.51', u'MB/s)', u'---\\n",'
          ], [u'"pid":', u'20963,'], [u'"size":', u'1883330,'],
          [u'"started":', u'1511788262.20002,'], [u'"state":', u'"finished",'],
          [u'"success":', u'true'], [u'}']]

info_2 = [[u'[[[site:heute:test]]]'], [u'{'], [u'"bytes_per_second":', u'1578215.4167199447,'],
          [u'"finished":', u'1511788263.410466,'], [u'"next_schedule":', u'1511874660.0,'],
          [
              u'"output":', u'"2017-11-27', u'14:11:02', u'---', u'Starting', u'backup',
              u'(Check_MK-klappfel-heute-test', u'to', u'testtgt)', u'---\\n2017-11-27',
              u'14:11:03', u'Verifying', u'backup', u'consistency\\n2017-11-27', u'14:11:03',
              u'---', u'Backup', u'completed', u'(Duration:', u'0:00:01,', u'Size:', u'1.80',
              u'MB,', u'IO:', u'1.51', u'MB/s)', u'---\\n",'
          ], [u'"pid":', u'20963,'], [u'"size":', u'1883330,'],
          [u'"started":', u'1511788262.20002,'], [u'"state":', u'"finished",'],
          [u'"success":', u'true'], [u'}'], [u'[[[site:heute:test2]]]'], [u'{'],
          [u'"bytes_per_second":', u'0,'], [u'"finished":', u'1511788748.77112,'],
          [u'"next_schedule":', u'null,'],
          [
              u'"output":', u'"2017-11-27', u'14:19:07', u'---', u'Starting', u'backup',
              u'(Check_MK-klappfel-heute-test2', u'to', u'testtgt2)', u'---\\n2017-11-27',
              u'14:19:08', u'Verifying', u'backup', u'consistency\\n2017-11-27', u'14:19:08',
              u'---', u'Backup', u'completed', u'(Duration:', u'0:00:00,', u'Size:', u'87.07',
              u'MB,', u'IO:', u'0.00', u'B/s)', u'---\\n",'
          ], [u'"pid":', u'24201,'], [u'"size":', u'91299840,'],
          [u'"started":', u'1511788747.898509,'], [u'"state":', u'"finished",'],
          [u'"success":', u'true'], [u'}']]

info_3 = [[u'[[[system:test1]]]'], [u'{'], [u'"bytes_per_second":', u'0,'],
          [u'"finished":', u'1474547810.309871,'], [u'"next_schedule":', u'null,'],
          [
              u'"output":', u'"2016-09-22', u'14:36:50', u'---', u'Starting', u'backup',
              u'(Check_MK_Appliance-luss028-test1', u'to', u'test1)', u'---\\nFailed', u'to',
              u'create', u'the', u'backup', u'directory:', u'[Errno', u'13]', u'Permission',
              u'denied:',
              u'\'/mnt/auto/DIDK7838/Anwendungen/Check_MK_Appliance-luss028-test1-incomplete\'\\n",'
          ], [u'"pid":', u'29567,'], [u'"started":', u'1474547810.30425,'],
          [u'"state":', u'"finished",'], [u'"success":', u'false'], [u'}']]


# This only tests whether the parse function crashes or not
@pytest.mark.parametrize("info", [
    [],
    info_1,
    info_2,
    info_3,
])
def test_mkbackup_parse(check_manager, info):
    check = check_manager.get_check("mkbackup")
    check.run_parse(info)
