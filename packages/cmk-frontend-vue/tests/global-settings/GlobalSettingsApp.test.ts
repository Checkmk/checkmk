/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type {
  GlobalSettingsApp as GlobalSettingsAppData,
  GlobalSettingsTopic
} from 'cmk-shared-typing/typescript/global_settings'
import { describe, expect, test } from 'vitest'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import GlobalSettingsApp from '@/global-settings/GlobalSettingsApp.vue'

initializeComponentRegistry()

const data: GlobalSettingsAppData = {
  title: 'Global settings',
  domain: 'global_settings',
  scope: { type: 'global' },
  topics: [
    {
      icon: 'users',
      headline: 'User management',
      subline: 'Configures user/authentication settings',
      warning: null,
      variables: [
        {
          name: 'lock_on_logon_failures',
          spec: {
            type: 'integer',
            title: 'Lock user accounts after N login failures',
            help: '',
            validators: [],
            label: null,
            unit: null,
            input_hint: null
          },
          value: 10,
          modified: false
        }
      ]
    }
  ]
}

const secondTopic: GlobalSettingsTopic = {
  icon: 'sites',
  headline: 'Site management',
  subline: 'Configures site settings',
  warning: null,
  variables: [
    {
      ...data.topics[0]!.variables[0]!,
      name: 'site_setting',
      spec: { ...data.topics[0]!.variables[0]!.spec, title: 'Site setting' },
      modified: true
    }
  ]
}

describe('GlobalSettingsApp accordion', () => {
  test('all topics start collapsed and the toggle expands and collapses them all', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    expect(screen.queryByText('Site setting')).not.toBeInTheDocument()
    expect(screen.queryByText('Lock user accounts after N login failures')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Toggle Expand all' }))
    expect(screen.getByText('Site setting')).toBeInTheDocument()
    expect(screen.getByText('Lock user accounts after N login failures')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Toggle Collapse all' }))
    expect(screen.queryByText('Site setting')).not.toBeInTheDocument()
  })

  test('the topic header shows singular variable count and the number of modified variables', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    expect(screen.getAllByText('1 variable')).toHaveLength(2)
    expect(screen.getByText('0 modified')).toBeInTheDocument()
    expect(screen.getByText('1 modified')).toBeInTheDocument()
  })

  test('the topic reset button is disabled while nothing is modified', () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    const [untouched, modified] = screen.getAllByRole('button', { name: 'Reset' })
    expect(untouched).toBeDisabled()
    expect(modified).toBeEnabled()
  })

  test('only modified rows are marked', async () => {
    render(GlobalSettingsApp, { props: { ...data, topics: [...data.topics, secondTopic] } })
    await userEvent.click(screen.getByRole('button', { name: 'Toggle Expand all' }))
    expect(screen.getAllByText('(modified)')).toHaveLength(1)
    expect(
      screen.getByText('Site setting').closest('.global-settings-variable-row')
    ).toHaveTextContent('(modified)')
  })
})
