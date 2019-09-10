import time
import os
import pytest
import cmk.utils.paths
import cmk.utils.log
import cmk_base.piggyback as piggyback
import cmk_base.console
from cmk_base.config import piggyback_max_cachefile_age


@pytest.fixture(autouse=True)
def verbose_logging():
    old_root_log_level = cmk_base.console.logger.getEffectiveLevel()
    cmk_base.console.logger.setLevel(cmk.utils.log.VERBOSE)
    yield
    cmk_base.console.logger.setLevel(old_root_log_level)


@pytest.fixture(autouse=True)
def test_config():
    piggyback_dir = cmk.utils.paths.piggyback_dir
    host_dir = piggyback_dir / "test-host"
    host_dir.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

    for f in piggyback_dir.glob("*/*"):
        f.unlink()

    source_file = piggyback_dir / "test-host" / "source1"
    with source_file.open(mode="w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"<<<check_mk>>>\nlala\n")

    cmk.utils.paths.piggyback_source_dir.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    with source_status_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"")
    source_stat = source_status_file.stat()  # pylint: disable=no-member

    os.utime(str(source_file), (source_stat.st_atime, source_stat.st_mtime))


def test_get_piggyback_raw_data_no_data():
    assert piggyback.get_piggyback_raw_data("no-host", piggyback_max_cachefile_age) == []


def test_get_piggyback_raw_data():
    assert piggyback.get_piggyback_raw_data("test-host", piggyback_max_cachefile_age) == [
        ('source1', '<<<check_mk>>>\nlala\n')
    ]


def test_get_piggyback_raw_data_outdate_old_pigs():
    assert piggyback.get_piggyback_raw_data("test-host", piggyback_max_cachefile_age) == [
        ('source1', '<<<check_mk>>>\nlala\n')
    ]

    # Fake age the test-host piggyback file
    os.utime(str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
             (time.time() - 10, time.time() - 10))

    piggyback.store_piggyback_raw_data("source1", {"test-host2": [
        u"<<<check_mk>>>",
        u"lulu",
    ]})

    assert piggyback.get_piggyback_raw_data("test-host", piggyback_max_cachefile_age) == []


def test_get_piggyback_raw_data_source_not_sending_anymore():
    assert piggyback.get_piggyback_raw_data("test-host", piggyback_max_cachefile_age) == [
        ('source1', '<<<check_mk>>>\nlala\n')
    ]
    piggyback.store_piggyback_raw_data("source1", {})
    assert piggyback.get_piggyback_raw_data("test-host", piggyback_max_cachefile_age) == []


def test_has_piggyback_raw_data_no_data():
    assert piggyback.has_piggyback_raw_data("no-host", piggyback_max_cachefile_age) is False


def test_has_piggyback_raw_data():
    assert piggyback.has_piggyback_raw_data("test-host", piggyback_max_cachefile_age) is True


def test_remove_source_status_file_not_existing():
    assert piggyback.remove_source_status_file("nosource") is False


def test_remove_source_status_file():
    assert piggyback.remove_source_status_file("source1") is True


def test_store_piggyback_raw_data_new_host():
    piggyback.store_piggyback_raw_data("source2", {"pig": [
        u"<<<check_mk>>>",
        u"lulu",
    ]})

    assert piggyback.get_piggyback_raw_data("pig", piggyback_max_cachefile_age) == [
        ('source2', '<<<check_mk>>>\nlulu\n'),
    ]


def test_store_piggyback_raw_data_second_source():
    piggyback.store_piggyback_raw_data("source2", {"test-host": [
        u"<<<check_mk>>>",
        u"lulu",
    ]})

    assert sorted(piggyback.get_piggyback_raw_data("test-host",
                                                   piggyback_max_cachefile_age)) == sorted([
                                                       ('source1', '<<<check_mk>>>\nlala\n'),
                                                       ('source2', '<<<check_mk>>>\nlulu\n'),
                                                   ],)


def test_get_source_and_piggyback_hosts():
    cmk.utils.paths.piggyback_source_dir.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

    piggyback.store_piggyback_raw_data("source1", {
        "test-host2": [
            u"<<<check_mk>>>",
            u"source1",
        ],
        "test-host": [
            u"<<<check_mk>>>",
            u"source1",
        ]
    })

    # Fake age the test-host piggyback file
    os.utime(str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
             (time.time() - 10, time.time() - 10))

    piggyback.store_piggyback_raw_data("source1", {"test-host2": [
        u"<<<check_mk>>>",
        u"source1",
    ]})

    piggyback.store_piggyback_raw_data("source2", {
        "test-host2": [
            u"<<<check_mk>>>",
            u"source2",
        ],
        "test-host": [
            u"<<<check_mk>>>",
            u"source2",
        ]
    })

    assert sorted(list(
        piggyback.get_source_and_piggyback_hosts(piggyback_max_cachefile_age))) == sorted([
            ('source1', 'test-host2'),
            ('source2', 'test-host'),
            ('source2', 'test-host2'),
        ])
