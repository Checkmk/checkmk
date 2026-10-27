===================
Testing with pytest
===================

This page shows how to apply the :doc:`dev-testing` to Python tests. Read
them first; this page only adds what is specific to pytest.

Pytest setup
============

Pytest setup follows the same scoping as the tests. There is no root conftest
under ``tests/``.

* When several suites need the same setup (site under test, session timeout,
  sharding, diagnostics, ...), write a plugin module in
  ``tests/testlib/pytest_helpers/``, or in
  ``tests/testlib/system/pytest_helpers/`` if it needs the site under test.
* Each suite's conftest registers the plugins it needs from its
  ``pytest_addoption``. ``tests/system/conftest.py`` does this for all system
  suites, ``non-free/tests/system/conftest.py`` for those below ``non-free/``.
* Setup that only one suite needs stays in that suite's conftest.

**Only tests assert.** Helpers in ``tests/testlib`` and
``non-free/tests/testlib`` raise instead: ``AssertionError`` with a message
when they check something for the test, ``RuntimeError`` when their own setup
fails. Pytest does not rewrite asserts in these libraries, so a bare
``assert`` there fails without saying why.

Test through the public surface
===============================

Do not call ``_private`` functions from a test. Their behavior is reachable
through the public entry point, and testing there also checks what the user
actually sees:

.. code-block:: python

   # bad - parse_apt() strips the Ubuntu Pro advertisement before it calls
   # _data_is_valid(), so this result never reaches the user
   def test_data_is_valid_with_ubuntu_pro_advertisement() -> None:
       assert _data_is_valid(UBUNTU_PRO_ADVERTISEMENT) is False


   # good - asserts on the section the check function receives
   def test_ubuntu_pro_advertisement_is_ignored() -> None:
       assert parse_apt(UBUNTU_PRO_ADVERTISEMENT) == Section(
           updates=["base-files"], removals=[], sec_updates=[]
       )

Dependencies
============

**Inject over patch.** ``unittest.mock.patch`` and ``mocker.patch`` are
acceptable only for boundaries you do not own and cannot inject, such as
``sys.stdin``, ``requests.post`` or OS calls. Even then, assert on the outcome
rather than on the mock:

.. code-block:: python

   # acceptable - requests.post is a third-party boundary
   with patch("requests.post") as mock_post:
       mock_post.side_effect = responses
       transmit_data(tmp_path, logger=mock.Mock())

**Pick the double:**

======  =============================================  ======================================
Double  Implementation                                 Use when
======  =============================================  ======================================
Stub    ``Mock(spec=X)`` with ``.return_value`` set    Collaborator is expensive to build
Fake    Hand-written class with in-memory state        Collaborator has state across calls
Mock    ``Mock()`` + ``assert_called_*``               Last resort: the call is the behavior
======  =============================================  ======================================

* **Always pass** ``spec=``. Access to an attribute the real class lacks then
  raises ``AttributeError`` at once. You do not need a Protocol to stub a
  concrete class.
* **Avoid** ``assert_called_*``. Static analysis cannot see these calls, and
  they break on renames although behavior is unchanged. To check *what* was
  sent, inject a fake that appends each call to a list.

A stub for a collaborator that needs site state the test does not care about:

.. code-block:: python

   def test_relay_choices_always_include_no_relay() -> None:
       manager = Mock(spec=RelayConfigManager)
       manager.all.return_value = {}

       choices = relay_choices(manager)

       assert choices == [("", "No relay")]

A mock where the call itself is the contract: ``hooks.call("bla")`` must fire
every handler registered under ``"bla"`` and no others.

.. code-block:: python

   def test_call_fires_only_matching_hooks(mocker: MockerFixture) -> None:
       bla, blub = mocker.Mock(), mocker.Mock()
       hooks.register("bla", bla)
       hooks.register("blub", blub)

       hooks.call("bla")

       bla.assert_called_once()
       blub.assert_not_called()

Shape of a test
===============

* Name the test after the outcome: ``test_dangerous_markup_is_escaped``, not
  ``test_escape_to_html_permissive``.
* Separate Arrange, Act and Assert with blank lines. Do not add ``# Arrange``
  comments.
* Do not bundle operations. "get returns None before any run" and "get returns
  the stored value after a store" are two tests:

.. code-block:: python

   def test_get_next_run_ts_returns_none_before_any_run() -> None:
       assert get_next_run_ts(next_run_file_path(var_dir)) is None


   def test_get_next_run_ts_returns_stored_timestamp() -> None:
       ts_file_path = next_run_file_path(var_dir)
       now = datetime.now().replace(microsecond=0)
       store_next_run_ts(ts_file_path, int(now.timestamp()))

       assert get_next_run_ts(ts_file_path) == now

* Exception, state machines: keep sequential act/assert cycles in one test
  when each assert depends on the previous transition and splitting would
  duplicate setup or hide that dependency. Separate the cycles with blank
  lines:

.. code-block:: python

   def test_should_run_product_usage_on_schedule() -> None:
       now = datetime.now()
       ts_file_path = next_run_file_path(var_dir)

       assert should_run_collection_on_schedule(var_dir, now) is False

       store_next_run_ts(ts_file_path, 1)

       assert should_run_collection_on_schedule(var_dir, now) is True

* Several ``pytest.raises`` blocks in one test hide each other's failures.
  Parametrize them instead:

.. code-block:: python

   @pytest.mark.parametrize(
       "version_string",
       [
           pytest.param("2.2.0rc1", id="rc without patch level"),
           pytest.param("2.2.0p5-rc", id="patch with bare rc suffix"),
           pytest.param("2023.12.24-rc1", id="daily with rc suffix"),
       ],
   )
   def test_invalid_version_string_raises(version_string: str) -> None:
       with pytest.raises(ValueError):
           Version.from_str(version_string)

Parametrize
===========

* Name every case with ``pytest.param(..., id="descriptive name")``.
* To keep a table layout that helps scanning, wrap the decorator in
  ``# fmt: off`` / ``# fmt: on``.
* An ``if`` on a parametrized argument bundles two behaviors. Split the test:

.. code-block:: python

   # bad - "out is None" selects between two behaviors
   def test_escape_text(inp: str, out: str | None) -> None:
       if out is None:
           assert escaping.escape_permissive(inp) == inp
       else:
           assert escaping.escape_permissive(inp) == out


   # good - one test per behavior
   def test_allowed_tags_pass_through_unchanged(tag: str) -> None:
       assert escaping.escape_permissive(tag) == tag


   def test_dangerous_markup_is_escaped(inp: str, expected: str) -> None:
       assert escaping.escape_permissive(inp) == expected

* When a ``pytest.param`` row needs several lines, write separate named tests.

Editions
========

Do not use ``skip_if_edition`` / ``skip_if_not_edition`` on package or
integration tests. If the edition is an input to the logic, pass the edition
enum as a plain test parameter.

Flaky tests
===========

To reproduce a flake, run the test alone and repeatedly with
``--count 10 --log-cli-level INFO``. Quarantine a confirmed flake with
``@pytest.mark.skip(reason="CMK-<ID>")``.
