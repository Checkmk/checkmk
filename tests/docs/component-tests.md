# Component tests in Checkmk

## Objective

As a developer or QA engineer, I want to understand what a component test is and
how it differs from unit and system tests, so that I can recognise which parts
of Checkmk can be tested at component level and suggest and write such tests.

This page covers:

- [What a component test is](#what-a-component-test-is) and
  [how it compares to unit and system tests](#how-the-three-levels-compare)
- [Why we need them](#motivation-shift-left)
- [How to find parts of Checkmk that can be tested this way](#identifying-the-component-to-test)
- [Names that are easy to misread](#misleading-naming)

## What a component test is

Component tests sit between unit and system tests. A component test runs **one
part of Checkmk, the component** — for example a daemon, an HTTP service, an
agent plugin binary, or a query layer over a database — the way production runs
it, while everything around it is under the test's control, either replaced by
a fake or started by the test itself. It must not require a Checkmk site.

**Compared to a unit test, more of the code really runs.** A unit test calls a
function directly and patches out whatever that function talks to, so nothing is
started and no connection is opened. It tells you a function returns the right
value, but nothing about the program once it is running and communicating. A
component test starts the component and drives it the way its clients do in
production — so it can cover shutdown on SIGTERM, a child process that crashes
or hangs, an mTLS handshake, a schema migration. It is **black-box**: the
component is only ever touched from the outside, through its public interfaces,
and never by reaching into it. That is also why the fakes are attached to a
protocol rather than to a function name, and why these tests survive refactoring
of the code they exercise.

**Compared to a system test, there is no site.** A system test installs a
Checkmk package and creates a Checkmk site; a component test never does.

## Motivation: shift left

The motivation is to catch errors **as early as possible**. A dependency that is
slow, broken or lying, a crashed child, an expiring certificate: until now these
were reachable only in system tests, which need a built package and a site.
That makes system tests expensive: only a selection of them runs before submit,
in the medium chain, and the full set runs after the change is already merged.
Component tests need no package and no site and are hermetic, so they run in the
Gerrit change-validation gate on every patchset — a failure lands on the
author's change instead of surfacing in time-intensive medium-chain or
heavy-chain runs, resulting in quicker feedback.

## How the three levels compare

### What is under test

- **Unit** — a function or class, inside the test process.
- **Component** — one part of Checkmk, driven through its external, public
  interface.
- **System** — a running Checkmk site.

### Where the fakes sit

- **Unit** — patched internals: `unittest.mock`, `fakeredis`, patched
  `cmk.utils.paths`.
- **Component** — a process or protocol boundary: Wiremock, fake child
  binaries. Or nothing, when the dependency can be used as in production
  (ClickHouse, Oracle).
- **System** — nothing is faked.

### Site

- **Unit** — none. (`tests/testlib/unit/fake_site.py` fabricates a site
  _layout_, not a site.)
- **Component** — none.
- **System** — a Checkmk site, installed from a built package.

### Where the tests live, and what runs them

- **Unit** — next to the code under test, usually
  `[non-free/]packages/<package>/tests/unit/`; code in `cmk/` that has not been
  split out into packages yet is tested in `tests/unit/`; run by Bazel.
- **Component** — next to the code under test, usually
  `[non-free/]packages/<package>/tests/component/`; run by Bazel.
- **System** — `tests/system/<suite>/`; run by pytest directly, targets defined
  in `tests/run_tests.sh` (e.g. `test-system-singlesite`,
  `test-system-multisite`).

### CI

- **Unit** — the "All unit tests" change-validation stage; gates every
  patchset.
- **Component** — also the "All unit tests" change-validation stage, so they
  gate every patchset as well. The exception is mk-oracle, which runs in a
  separate stage.
- **System** — needs a built package, so it runs outside change validation. A
  selection runs before submit in the medium chain; the full set runs after
  submit.

## Identifying the component to test

Before anything else, understand how the feature works: which parts of the
product take part in it, how information flows from one part to the next, and
over which connection each part communicates with the next.

The type of connection decides whether the dependency at its other end can be
faked, and with what. Some examples:

- **HTTP** — faked with a server that speaks the same protocol (Wiremock, or a
  small server started by the test).
- **A socket** — replaced by a mock socket that the test reads from and writes
  to.
- **A child process** — a fake binary is put where the production binary is
  looked up, so the test decides what it prints, how long it takes, and whether
  it crashes.
- **A database or another datastore** — usually not faked at all: the test
  starts an instance or connects to an existing one and lets the component talk
  to it.

The list is not closed — other connections over which the component exchanges
information with the outside can be faked the same way, files included. And
where there is a choice of connections, fake the ones around the behaviour you
want to test, not the ones inside it.

What you cannot fake this way is a plain function call inside one running
program: there is nothing in between that a fake could replace. That rules out
every part which runs _inside_ another program instead of being started on its
own — check execution in `cmk/base`, `cmk/gui` and the REST API are of this
kind, and for them the only options are unit tests, where the behaviour can be
judged from the code alone, and system tests for everything else. The line
runs through packages, not around them: one package can ship a daemon that
qualifies and a GUI part that does not, so judge each part on its own rather
than the whole package.

### Example: the relay

The relay lets a Checkmk site monitor hosts in a network it cannot reach
directly.

```
   site core  ←→  agent receiver  ←→  relay engine  →  fetchers  →  monitored hosts
              (socket)        (HTTPS, mTLS)     (child processes)
  └──────── inside the Checkmk site ────────┘      └── remote network ──┘
```

- The **agent receiver** runs inside the site as an HTTP service — the endpoint
  that relays and agents talk to: registration, certificate signing, task
  hand-out, data upload.
- The **relay engine** runs in the remote network as a daemon. It registers with
  the site, polls it for tasks, starts a fetcher process per task, and sends
  results back.

**Both are testable at component level, separately.** For the relay engine, the
site is replaced by a fake HTTP server speaking the same protocol and the
fetchers by fake binaries the test controls — so a test can disconnect the site
mid-cycle, make it answer with garbage, let a fetcher crash or hang, expire a
certificate, or stop the daemon with SIGTERM. For the agent receiver, the
core's socket is replaced by a mock socket and the relay side is just the test
making HTTP calls — so registration, certificate signing and the per-relay task
limit are all reachable.

**Not testable here:** the two of them talking to each other, the production
fetchers, and anything the site does in response. Those are system tests.

### Other kinds of component

Unlike the agent receiver and relay engine suites, the following two fake
nothing at all, because their dependency can be used as in production:

- **The metric backend** — a query and schema layer, tested against a ClickHouse
  server started by the test, so what queries return and whether a schema
  upgrade _and its downgrade_ work are directly checkable.
- **mk-oracle** — an agent plugin binary, tested against an Oracle database.

Together with the two relay suites, they show the range: a component can be a
daemon, an HTTP service, an agent plugin binary, or a query layer over a
database.

Several other parts have the right shape but no suite yet — the DCD daemon,
mknotifyd, the event console's event server, liveproxyd. And `cmk-agent-ctl` and
`mk-sql` already have tests of this kind without calling them component tests.

## Misleading naming

**The CI stage "All unit tests".** The name is confusing: the stage runs all
Bazel tests in the repository — with a few exceptions — so it covers both unit
and component tests.

**The Bazel tag `component`.** This tag is used only for the mk-oracle component
tests, to exclude them from "All unit tests" and run them in a separate stage.
There is no need to set it on other component tests.

**A "component test" in the frontend.** In the frontend, "component" means a
piece of UI — a Vue component such as a form field, a button, a dropdown or a
dialog. The vitest tests that mount such a component and check what it renders
are unit tests by this classification.

**A Checkmk component.** Checkmk also uses "component" for grouping code by
ownership and werks. Such a component is not necessarily what a component test
runs: one may contain several testable components, or none.
