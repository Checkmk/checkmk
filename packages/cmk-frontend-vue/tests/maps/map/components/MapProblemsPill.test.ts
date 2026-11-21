/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapProblemsPill, { type ProblemCounts } from '@/maps/map/components/MapProblemsPill.vue'

function problems(overrides: Partial<ProblemCounts>): ProblemCounts {
  return {
    down: 0,
    unreachable: 0,
    critical: 0,
    warning: 0,
    unknown: 0,
    hostsWithProblems: 0,
    ...overrides
  }
}

describe('MapProblemsPill', () => {
  it('names only the states something is in', () => {
    render(MapProblemsPill, {
      props: { problems: problems({ down: 1, critical: 3, hostsWithProblems: 2 }) }
    })

    expect(screen.getByText('1 DOWN · 3 CRIT')).toBeInTheDocument()
  })

  it('counts in words on hover', () => {
    render(MapProblemsPill, {
      props: {
        problems: problems({ down: 1, unreachable: 99, critical: 60, hostsWithProblems: 1 })
      }
    })

    expect(
      screen.getByTitle('1 host down, 99 hosts unreachable; 60 service problems on one host')
    ).toBeInTheDocument()
  })
})
