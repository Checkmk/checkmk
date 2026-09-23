/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type AgentSlideoutPayload,
  type KubernetesPayload,
  buildFlavours
} from '@/mode-host/agent-connection-test/lib/flavours'
import type { AgentFlavour } from '@/mode-host/agent-connection-test/lib/types'

import {
  installCmds,
  kubernetesHelmCommand,
  kubernetesValues,
  registrationCmds,
  statusCmds
} from './fixtures'

const payload: AgentSlideoutPayload = {
  installCmds,
  registrationCmds,
  statusCmds,
  legacyAgentUrl: undefined,
  unbakedFallback: null,
  kubernetes: null
}

const kubernetes: KubernetesPayload = {
  helmCommand: kubernetesHelmCommand,
  values: kubernetesValues,
  docUrl: 'https://docs.example.test/kubernetes'
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

  test('offers Kubernetes after the four platforms when the payload carries it', () => {
    expect(buildFlavours({ ...payload, kubernetes }).map((f) => f.id)).toEqual([
      'windows',
      'linux',
      'solaris',
      'aix',
      'kubernetes'
    ])
  })

  test('registers Kubernetes without install or test connection', () => {
    const built = flavour('kubernetes', { kubernetes })
    expect(built.install).toBeUndefined()
    expect(built.status).toBeUndefined()
  })

  test('troubleshoots Kubernetes by checking for the push certificate secret', () => {
    expect(flavour('kubernetes', { kubernetes }).register?.troubleshooting).toBe(
      'kubernetes-secret'
    )
  })

  test('shows the values.yaml and the monitoring guide before the Helm command', () => {
    const config = flavour('kubernetes', { kubernetes }).register?.config
    expect(config?.code.text).toBe(kubernetes.values)
    expect(config?.doc?.url).toBe(kubernetes.docUrl)
  })
})
