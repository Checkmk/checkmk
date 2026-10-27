======================
Testing Vue components
======================

This page shows how to apply the :doc:`dev-testing` to
``packages/cmk-frontend-vue``. Read them first; this page only adds what is
specific to Vue.

Setup
=====

Tests live in the package's ``tests/`` directory and run on vitest with
``@testing-library/vue``. Run ``bazel run :vitest -- <args>`` from the
package, or ``bazel test :unit-test`` for the whole suite.

The public interface of a component
===================================

The same rule applies as everywhere else: test through the public interface
and assert on behavior. For a UI component, the public interface is the props
you pass in and the DOM it renders, as seen through the accessibility layer.

For building blocks (``src/components/``, the UX-approved reusable
components) this style is enforced, and every behavior a building block
implements needs a test.

Do
==

* Find elements through the accessibility layer:
  ``screen.getByRole('<role>', { name: '<accessible name>' })``.
* Drive them with ``@testing-library/user-event``.
* Simulate API backends with MockServiceWorker (grep ``from 'msw'`` for
  examples).

Do not
======

* Use ``@vue/test-utils``.
* Assert that events were emitted, mocks were called, CSS classes exist, or
  input fields hold certain values.
* Reach into a child component's internals, in tests or in production code:
  no ``document.querySelector()`` and no ``v-deep`` to change what a child
  renders. A child exposes its variants through props.

Beyond unit tests
=================

* Visual regressions belong in screenshot tests, which do not exist yet.
* To see a change in the browser, use the demo app, cmk-dev-deploy or the
  hot-reload dev server; the package README describes each workflow.
* If a good test in this style seems impossible, ask Team Bug; do not test
  implementation details instead.
