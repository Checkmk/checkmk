/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ComponentConfig,
  type ConfiguredFilters,
  type FilterDefinition,
  type FilterDefinitions,
  configuredFilters,
  unconfiguredFilters
} from 'cmk-ui-library/components/filter'
import { describe, expect, test } from 'vitest'

function filterDefinition(id: string, components: ComponentConfig[]): FilterDefinition {
  return {
    id,
    title: id,
    domainType: 'visual_filter',
    links: [],
    extensions: { info: 'host', group: null, is_show_more: false, components }
  }
}

const DEFINITIONS: FilterDefinitions = {
  hostregex: filterDefinition('hostregex', [{ component_type: 'text_input', id: 'host_regex' }]),
  wato_folder: filterDefinition('wato_folder', [
    {
      component_type: 'dropdown',
      id: 'wato_folder',
      choices: { '': 'Main', server: 'server' },
      default_value: ''
    }
  ]),
  host_state: filterDefinition('host_state', [
    {
      component_type: 'dropdown',
      id: 'host_state',
      choices: { '0': 'UP', '1': 'DOWN' },
      default_value: '0'
    }
  ]),
  host_num_services: filterDefinition('host_num_services', [
    {
      component_type: 'horizontal_group',
      components: [
        { component_type: 'text_input', id: 'host_num_services_from' },
        { component_type: 'text_input', id: 'host_num_services_until' }
      ]
    }
  ]),
  svcstate: filterDefinition('svcstate', [
    { component_type: 'checkbox_group', choices: { st0: 'OK', st1: 'WARN' } }
  ]),
  hostgroups: filterDefinition('hostgroups', [{ component_type: 'static_text', text: 'nothing' }])
}

function partition(context: ConfiguredFilters): { configured: string[]; unconfigured: string[] } {
  return {
    configured: configuredFilters(context, DEFINITIONS).map((definition) => definition.id!),
    unconfigured: unconfiguredFilters(context, DEFINITIONS).map((definition) => definition.id!)
  }
}

describe('a text input', () => {
  test('holds a value once it is not empty', () => {
    expect(partition({ hostregex: { host_regex: 'web' } })).toEqual({
      configured: ['hostregex'],
      unconfigured: []
    })
  })

  test('misses a value while it is empty', () => {
    expect(partition({ hostregex: { host_regex: '' } })).toEqual({
      configured: [],
      unconfigured: ['hostregex']
    })
  })

  test('misses a value while the context holds none for it', () => {
    expect(partition({ hostregex: {} })).toEqual({
      configured: [],
      unconfigured: ['hostregex']
    })
  })
})

describe('a dropdown', () => {
  test('takes an empty value as a selection, because the choices offer it', () => {
    expect(partition({ wato_folder: { wato_folder: '' } })).toEqual({
      configured: ['wato_folder'],
      unconfigured: []
    })
  })

  test('misses a value while it is empty and the choices do not offer it', () => {
    expect(partition({ host_state: { host_state: '' } })).toEqual({
      configured: [],
      unconfigured: ['host_state']
    })
  })
})

describe('a filter of several components', () => {
  test('holds a value once every one of its components does', () => {
    const values = { host_num_services_from: '5', host_num_services_until: '10' }
    expect(partition({ host_num_services: values })).toEqual({
      configured: ['host_num_services'],
      unconfigured: []
    })
  })

  test('misses a value while one of its components is empty', () => {
    const values = { host_num_services_from: '5', host_num_services_until: '' }
    expect(partition({ host_num_services: values })).toEqual({
      configured: [],
      unconfigured: ['host_num_services']
    })
  })
})

describe('a filter with nothing to fill in', () => {
  test('holds a value with every checkbox cleared, the group carrying no text', () => {
    expect(partition({ svcstate: { st0: '', st1: '' } })).toEqual({
      configured: ['svcstate'],
      unconfigured: []
    })
  })

  test('holds a value with static text alone', () => {
    expect(partition({ hostgroups: {} })).toEqual({
      configured: ['hostgroups'],
      unconfigured: []
    })
  })
})

test('a filter the definitions do not know is reported by neither function', () => {
  expect(partition({ no_such_filter: { x: 'y' } })).toEqual({ configured: [], unconfigured: [] })
})

test('an empty context has no filter to report', () => {
  expect(partition({})).toEqual({ configured: [], unconfigured: [] })
})

test('the two functions split the context between them', () => {
  expect(partition({ hostregex: { host_regex: 'web' }, host_state: { host_state: '' } })).toEqual({
    configured: ['hostregex'],
    unconfigured: ['host_state']
  })
})
