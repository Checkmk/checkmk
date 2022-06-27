=================================
Livestatus client - livestatus.py
=================================

Introduction and goals
======================

Livestatus is providing data held by the the in-memory database of our
monitoring core for external programs.

The distributed architecture of Checkmk is powered by the livestatus protocol
making it one of the most important parts of Checkmk.

The most used client library implementation is our python implementation
`livestatus.py`. Many of our internal components use this library to communicate
with the monitoring core.

Implementation
--------------

The implementation is located in the Checkmk git at
`livestatus/api/python/livestatus.py`.

The client is built as standalone module and must not rely on other Python code
of Checkmk.

See also
--------
- :doc:`arch-comp-core`
- :doc:`arch-comp-livestatus`
- `User manual: Livestatus <https://docs.checkmk.com/master/en/livestatus.html>`_
