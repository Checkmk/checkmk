/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TestProjectInlineConfiguration } from 'vitest/config'

const TEST_FILES = 'tests/**/*.test.ts'

export function testProjects(isolated: string[]): TestProjectInlineConfiguration[] {
  const project = (
    test: NonNullable<TestProjectInlineConfiguration['test']>
  ): TestProjectInlineConfiguration => ({
    extends: true,
    resolve: { dedupe: ['@testing-library/vue'] },
    test
  })
  return [
    project({ name: 'shared', include: [TEST_FILES], exclude: isolated, isolate: false }),
    project({ name: 'isolated', include: isolated })
  ]
}
