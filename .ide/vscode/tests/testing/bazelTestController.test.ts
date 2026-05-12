/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { parseJunitXml } from '../../src/testing/bazelTestController'
import { vitestCaseLeafName } from '../../src/testing/runners/vitest'

describe('parseJunitXml', () => {
  it('parses a single passing testcase', () => {
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
      <testsuites>
        <testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.unit.cmk.test_smoke" name="test_imports" time="0.123" />
        </testsuite>
      </testsuites>`
    const cases = parseJunitXml(xml)
    expect(cases).toHaveLength(1)
    expect(cases[0]).toMatchObject({
      classname: 'tests.unit.cmk.test_smoke',
      name: 'test_imports',
      time: 0.123,
      status: 'passed'
    })
  })

  it('parses a failed testcase with traceback details', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="tests.unit.cmk.gui.test_login" name="test_bad_pass" time="0.05">
        <failure message="AssertionError: nope">Traceback&#10;  File "a.py", line 4&#10;    assert False</failure>
      </testcase>
    </testsuite></testsuites>`
    const cases = parseJunitXml(xml)
    expect(cases).toHaveLength(1)
    expect(cases[0].status).toBe('failed')
    expect(cases[0].message).toBe('AssertionError: nope')
    expect(cases[0].details).toContain('Traceback')
    expect(cases[0].details).toContain('assert False')
  })

  it('distinguishes errors from failures', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="t.x" name="boom" time="0">
        <error message="ImportError">stack...</error>
      </testcase>
    </testsuite></testsuites>`
    expect(parseJunitXml(xml)[0].status).toBe('error')
  })

  it('parses skipped testcases', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="t.x" name="missing_dep" time="0">
        <skipped message="needs network" />
      </testcase>
    </testsuite></testsuites>`
    const c = parseJunitXml(xml)[0]
    expect(c.status).toBe('skipped')
    expect(c.message).toBe('needs network')
  })

  it('handles file/line attributes from pytest --junit-xml', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="t.x" name="t" time="0" file="tests/unit/x.py" line="42" />
    </testsuite></testsuites>`
    const c = parseJunitXml(xml)[0]
    expect(c.file).toBe('tests/unit/x.py')
    expect(c.line).toBe(42)
  })

  it('decodes XML entities in messages', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="t.x" name="t" time="0">
        <failure message="expected &lt;A&gt; got &amp;B&amp;" />
      </testcase>
    </testsuite></testsuites>`
    const c = parseJunitXml(xml)[0]
    expect(c.message).toBe('expected <A> got &B&')
  })

  it('returns empty array on empty input', () => {
    expect(parseJunitXml('')).toEqual([])
  })

  it('parses many testcases in one report', () => {
    const xml = `<testsuites><testsuite>
      <testcase classname="t.a" name="t1" time="0.01" />
      <testcase classname="t.a" name="t2" time="0.02"><failure message="x"/></testcase>
      <testcase classname="t.b" name="t3" time="0.03"><skipped message="y"/></testcase>
    </testsuite></testsuites>`
    const cases = parseJunitXml(xml)
    expect(cases).toHaveLength(3)
    expect(cases.map((c) => c.status)).toEqual(['passed', 'failed', 'skipped'])
  })
})

describe('vitestCaseLeafName', () => {
  it('returns the bare it-name when no describe is present', () => {
    expect(vitestCaseLeafName('returns null on unsupported platforms')).toBe(
      'returns null on unsupported platforms'
    )
  })

  it('strips a single describe prefix', () => {
    expect(
      vitestCaseLeafName('detectJemallocPathAsync > returns null on unsupported platforms')
    ).toBe('returns null on unsupported platforms')
  })

  it('strips nested describe prefixes', () => {
    expect(vitestCaseLeafName('outer > inner > the actual test')).toBe('the actual test')
  })

  it('preserves " > " inside the leaf when it is the last segment', () => {
    // " > " only counts as a separator between describe levels in vitest's
    // JUnit name, so any " > " in the it-name itself appears at the tail.
    expect(vitestCaseLeafName('describe > a > b > c')).toBe('c')
  })
})
