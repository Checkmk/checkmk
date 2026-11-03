/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CommandObjectName from '@/maps/map/commands/CommandObjectName.vue'

import { anObject } from '../../support/fixtures'

describe('CommandObjectName', () => {
  it('names a line bound to a host as the host it acts on', () => {
    render(CommandObjectName, {
      props: { object: anObject({ id: 'l1', type: 'line', host_name: 'web-01' }) }
    })

    expect(screen.getByText('Host')).toBeInTheDocument()
    expect(screen.getByText('web-01')).toBeInTheDocument()
    expect(screen.queryByText('Line')).not.toBeInTheDocument()
  })

  it('names an unnamed object only by its kind', () => {
    render(CommandObjectName, {
      props: { object: anObject({ id: 'dyngroup_1', type: 'dyngroup' }) }
    })

    expect(screen.getAllByText('Dynamic group')).toHaveLength(1)
  })
})
