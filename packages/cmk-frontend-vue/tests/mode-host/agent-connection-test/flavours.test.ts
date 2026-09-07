/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type AgentSlideoutPayload,
  buildFlavours
} from '@/mode-host/agent-connection-test/lib/flavours'
import type { AgentFlavour } from '@/mode-host/agent-connection-test/lib/types'

import { installCmds, registrationCmds, statusCmds } from './fixtures'

const payload: AgentSlideoutPayload = {
  installCmds,
  registrationCmds,
  statusCmds,
  legacyAgentUrl: undefined,
  unbakedFallback: null
}

function flavour(id: string, overrides: Partial<AgentSlideoutPayload> = {}): AgentFlavour {
  const found = buildFlavours({ ...payload, ...overrides }).find((f) => f.id === id)
  if (found === undefined) {
    throw new Error(`no flavour "${id}"`)
  }
  return found
}

describe('buildFlavours', () => {
  test('offers the four platforms in a fixed order', () => {
    expect(buildFlavours(payload).map((f) => f.id)).toEqual(['windows', 'linux', 'solaris', 'aix'])
  })

  test('installs Windows from a shell choice', () => {
    const install = flavour('windows').install
    expect(install?.kind).toBe('shell-variants')
    expect(install?.kind === 'shell-variants' && install.variants.map((v) => v.id)).toEqual([
      'powershell',
      'cmd'
    ])
  })

  test('installs Linux from a package choice', () => {
    const install = flavour('linux').install
    expect(install?.kind).toBe('package-choice')
    expect(install?.kind === 'package-choice' && install.choices.map((c) => c.id)).toEqual([
      'deb',
      'rpm',
      'tgz'
    ])
  })

  test('omits a package the site does not offer', () => {
    const install = flavour('linux', {
      installCmds: { ...installCmds, linux_rpm: '' }
    }).install
    expect(install?.kind === 'package-choice' && install.choices.map((c) => c.id)).toEqual([
      'deb',
      'tgz'
    ])
  })

  test('prefers the bakery fallback over the packages', () => {
    const install = flavour('linux', {
      unbakedFallback: { intro: 'No baked agents.', commands: ['wget one', 'wget two'] }
    }).install
    expect(install?.kind).toBe('unbaked-fallback')
    expect(install?.kind === 'unbaked-fallback' && install.blocks.map((b) => b.command)).toEqual([
      'wget one',
      'wget two'
    ])
  })

  test('falls back to the legacy agent documentation when nothing is installable', () => {
    const install = flavour('linux', {
      legacyAgentUrl: 'https://docs.example.test/legacy',
      installCmds: { ...installCmds, linux_deb: '', linux_rpm: '', linux_tgz_download: '' }
    }).install
    expect(install?.kind).toBe('external-doc')
    expect(install?.kind === 'external-doc' && install.link.url).toBe(
      'https://docs.example.test/legacy'
    )
  })

  test('omits the install step when nothing is installable and no docs are linked', () => {
    const built = flavour('linux', {
      legacyAgentUrl: undefined,
      installCmds: { ...installCmds, linux_deb: '', linux_rpm: '', linux_tgz_download: '' }
    })
    expect(built.install).toBeUndefined()
    expect(built.register).toBeDefined()
  })

  test('installs AIX from a download and an extract command', () => {
    const install = flavour('aix').install
    expect(install?.kind === 'commands' && install.blocks.map((b) => b.command)).toEqual([
      installCmds.aix_download,
      installCmds.aix_extract
    ])
  })

  test('warns about the root extraction only on the extract command', () => {
    const install = flavour('aix').install
    expect(
      install?.kind === 'commands' && install.blocks.map((b) => b.warning !== undefined)
    ).toEqual([false, true])
  })

  test('registers and tests every platform', () => {
    for (const built of buildFlavours(payload)) {
      expect(built.register).toBeDefined()
      expect(built.status).toBeDefined()
    }
  })

  test('offers the registration-user fallback on every platform', () => {
    for (const built of buildFlavours(payload)) {
      expect(built.register?.troubleshooting).toBe('registration-user')
    }
  })
})
