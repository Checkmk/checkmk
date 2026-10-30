/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { Playbook } from '../../../src/omd/cmkUp'
import { render } from '../../../src/sidebar/playbooks'
import type { StateCache } from '../../../src/sidebar/types'

const stateWith = (playbooks: Playbook[], playbooksScanned = true) =>
  ({ playbooks, playbooksScanned }) as unknown as StateCache

describe('CMK Playbooks section', () => {
  it('offers New Playbook when no playbook is found', () => {
    const html = render(stateWith([]))
    expect(html).toContain('No cmk-up playbooks found')
    expect(html).toContain('data-action="playbook-new"')
  })

  it('shows the scan in progress instead of the empty state', () => {
    const html = render(stateWith([], false))
    expect(html).toContain('Scanning for playbooks')
    expect(html).not.toContain('No cmk-up playbooks found')
  })

  it('runs a shipped example by name and a workspace playbook by path', () => {
    const html = render(
      stateWith([
        {
          name: 'SUP-1',
          target: '/ws/SUP-1.yaml',
          file: '/ws/SUP-1.yaml',
          source: 'workspace',
          description: 'reproduce SUP-1'
        },
        {
          name: '01-minimal',
          target: '01-minimal',
          file: '/uv/cwz/example-playbooks/01-minimal.yaml',
          source: 'shipped',
          description: ''
        }
      ])
    )
    expect(html).toContain('data-action="playbook-run" data-target="/ws/SUP-1.yaml"')
    expect(html).toContain('data-action="playbook-run" data-target="01-minimal"')
    expect(html.indexOf('Workspace')).toBeLessThan(html.indexOf('Shipped examples'))
  })
})
