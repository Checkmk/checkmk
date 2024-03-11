==============
Painter API v1
==============

Introduction and goals
======================

The `Painter` classes are responsible for rendering one specific cell in a
livestatus backed table view. They accept the data from a lower-level
data-structure and will emit

* HTML
* JSON
* text (for CSV exports)
* (planned) Vue specific JSON export

For this purpose, formatting and configuration are split in the new
architecture. The `Painter` class holds for example a `Formatters` instance,
which can emit to any format. It also holds other methods for data-
manipulation.

The implementation of the base classes currently resides in:

* `cmk.gui.painter.v1.painter_lib`

Architecture
============

Class diagram
-------------

.. uml:: arch-comp-painters-v1.puml
