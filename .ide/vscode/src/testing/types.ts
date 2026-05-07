/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export type RuleKind = 'py_test' | 'py_doc_test' | 'vitest_test' | 'rust_test' | 'cc_test'

export interface DiscoveredTarget {
  label: string
  kind: RuleKind
}

export interface DiscoveredTest {
  file: string
  line: number
  name: string
  classname: string
}

export interface JUnitTestCase {
  classname: string
  name: string
  file?: string
  line?: number
  time: number
  status: 'passed' | 'failed' | 'skipped' | 'error'
  message?: string
  details?: string
}

export interface RunOptions {
  edition: string
  kFilter?: string
}

export interface RuleScope {
  kind: RuleKind
  scopedFilesRel?: string[]
  scopedTestNames?: string[]
}
