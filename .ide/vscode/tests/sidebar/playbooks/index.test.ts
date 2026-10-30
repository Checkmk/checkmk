/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { Playbook } from '../../../src/omd/cmkUp'
import { render } from '../../../src/sidebar/playbooks'
import type { StateCache } from '../../../src/sidebar/types'

const stateWith = (
  playbooks: Playbook[],
  playbookDirectories: string[] = [],
  cwzInstalled: boolean | null = true,
  playbooksScanned = true
) => ({ playbooks, playbookDirectories, cwzInstalled, playbooksScanned }) as unknown as StateCache

describe('CMK Playbooks section', () => {
  it('offers New Playbook when no playbook is found', () => {
    const html = render(stateWith([]))
    expect(html).toContain('No cmk-up playbooks found')
    expect(html).toContain('data-action="playbook-new"')
  })

  it('shows the scan in progress instead of the empty state', () => {
    const html = render(stateWith([], [], true, false))
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

  it('searches the local and the shipped playbooks, not the workspace ones', () => {
    const html = render(
      stateWith(
        [
          {
            name: 'SUP-1',
            target: '/ws/SUP-1.yaml',
            file: '/ws/SUP-1.yaml',
            source: 'workspace',
            description: ''
          },
          {
            name: 'repro',
            target: '/local/repro.yaml',
            file: '/local/repro.yaml',
            source: 'directory',
            description: 'local repro'
          },
          {
            name: '07-BI-Phases',
            target: '07-BI-Phases',
            file: '/uv/cwz/example-playbooks/07-BI-Phases.yaml',
            source: 'shipped',
            description: 'SUP-30030 in two phases'
          }
        ],
        ['/local']
      )
    )
    const search = html.indexOf('data-filter="')
    expect(html.match(/data-filter="/g)).toHaveLength(1)
    expect(search).toBeGreaterThan(html.indexOf('SUP-1'))
    expect(search).toBeLessThan(html.indexOf('repro'))
    expect(html).toContain('data-search="repro local repro"')
    expect(html).toContain('data-search="07-bi-phases sup-30030 in two phases"')
  })

  it('shows each playbook folder with a reveal button, also when it is empty', () => {
    const html = render(stateWith([], ['/local/playbooks']))
    expect(html).toContain('data-action="playbook-folder" data-dir="/local/playbooks"')
    expect(html).toContain('No playbooks in this folder yet')
    expect(html).toContain('data-action="playbook-configure"')
  })

  it('tells local playbooks and shipped examples apart by icon', () => {
    const html = render(
      stateWith(
        [
          {
            name: 'repro',
            target: '/local/repro.yaml',
            file: '/local/repro.yaml',
            source: 'directory',
            description: ''
          },
          {
            name: '01-minimal',
            target: '01-minimal',
            file: '/uv/cwz/example-playbooks/01-minimal.yaml',
            source: 'shipped',
            description: ''
          }
        ],
        ['/local']
      )
    )
    expect(html).toContain('codicon-file-code playbook-icon')
    expect(html).toContain('codicon-library playbook-icon')
  })

  it('offers to install cmk-werk-zeug only once the scan found it missing', () => {
    expect(render(stateWith([], [], false))).toContain('data-action="playbook-install-cwz"')
    expect(render(stateWith([], [], null))).not.toContain('data-action="playbook-install-cwz"')
    expect(render(stateWith([], [], true))).not.toContain('data-action="playbook-install-cwz"')
  })
})
