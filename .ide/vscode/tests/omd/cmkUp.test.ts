/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { CmkUp } from '../../src/omd/cmkUp'

const SHIPPED_HEADER = [
  '#!/usr/bin/env -S uvx --from "cmk-werk-zeug@latest" cmk-up',
  '#',
  '# hint: to run the development version, change the shebang to',
  '#  #!/usr/bin/env -S uvx --from git+ssh://review.lan.tribe29.com:29418/cmk-werk-zeug@main cmk-up',
  '#',
  '# SUP-30030 in two phases: a frozen aggregation keeps the function it was frozen with',
  '#   cmk-up doc/example-playbooks/07-bi-phases.yaml --keep',
  '',
  'sites:'
].join('\n')

describe('CmkUp playbook header', () => {
  it('recognises the cmk-up shebang', () => {
    expect(CmkUp.isPlaybook(SHIPPED_HEADER)).toBe(true)
  })

  it('rejects other YAML files', () => {
    expect(CmkUp.isPlaybook('version: 2\nupdates: []\n')).toBe(false)
  })

  it('describes a playbook by its first comment sentence after the hint', () => {
    expect(CmkUp.describe(SHIPPED_HEADER)).toBe(
      'SUP-30030 in two phases: a frozen aggregation keeps the function it was frozen with'
    )
  })

  it('has no description without a comment header', () => {
    expect(CmkUp.describe('#!/usr/bin/env cmk-up\nsites: {}\n')).toBe('')
  })
})

describe('CmkUp.parsePhases', () => {
  it('reads name, sites and description of each --list-phases line', () => {
    const raw = 'freeze\tv300\tfreeze the stock aggregation\nchange\tv300,v250\tset it to "worst"\n'
    expect(CmkUp.parsePhases(raw)).toEqual([
      { name: 'freeze', sites: 'v300', description: 'freeze the stock aggregation' },
      { name: 'change', sites: 'v300,v250', description: 'set it to "worst"' }
    ])
  })
})

describe('CmkUp command line', () => {
  it('passes phases and ticked options to uvx cmk-up', () => {
    const args = CmkUp.runArgs('07-bi-phases', {
      phases: ['freeze', 'change'],
      keep: true,
      purge: false,
      dryRun: true,
      verify: false
    })
    expect(CmkUp.commandLine(args)).toBe(
      'uvx --from cmk-werk-zeug@latest cmk-up 07-bi-phases --phase freeze --phase change --keep --dry-run'
    )
  })

  it('enrolls a single site into the picked file', () => {
    expect(CmkUp.commandLine(CmkUp.enrollArgs('/ws/v300.yaml', 'v300'))).toBe(
      'uvx --from cmk-werk-zeug@latest cmk-up --enroll /ws/v300.yaml --only-site v300'
    )
  })

  it('quotes a playbook path with spaces', () => {
    expect(CmkUp.commandLine(['/home/me/My Playbooks/SUP-1.yaml'])).toBe(
      "uvx --from cmk-werk-zeug@latest cmk-up '/home/me/My Playbooks/SUP-1.yaml'"
    )
  })
})
