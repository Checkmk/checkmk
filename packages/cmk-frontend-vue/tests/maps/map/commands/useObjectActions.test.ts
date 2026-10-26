/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'

import {
  OBJECT_ACTION_IDS,
  type ObjectActions,
  useObjectActions
} from '@/maps/map/commands/useObjectActions'
import type { MapElement } from '@/maps/types/api'
import { defaultScheduleDowntimeValues } from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'

import { anObject } from '../../support/fixtures'
import { fakeMapsServices, provideServices } from '../../support/services'

// Not runWithServices: the command forms also need the site's command settings.
function setup(object: MapElement) {
  const services = fakeMapsServices()
  let actions!: ObjectActions
  render(
    defineComponent({
      setup() {
        actions = useObjectActions({
          object: () => object,
          state: () => undefined,
          checkmkUrl: () => 'http://remote/site/check_mk/'
        })
        return () => null
      }
    }),
    provideServices(services)
  )
  return { commands: services.apis.commands, actions }
}

describe('useObjectActions', () => {
  it('schedules a host and its child hosts in one request', async () => {
    const { commands, actions } = setup(
      anObject({ id: 'core01', type: 'host', host_name: 'core01' })
    )
    vi.mocked(commands.childHosts).mockResolvedValue(['access01'])

    actions.select(OBJECT_ACTION_IDS.scheduleDowntime)
    await actions.submit({
      ...defaultScheduleDowntimeValues([]),
      comment: 'switch swap',
      includeChildHosts: true
    })

    expect(commands.downtimeHosts).toHaveBeenCalledExactlyOnceWith(
      null,
      ['core01', 'access01'],
      expect.objectContaining({ comment: 'switch swap' })
    )
    expect(commands.downtimeHost).not.toHaveBeenCalled()
  })

  // The slide-in's member list may still be loading or leave members out.
  it('takes a host group child hosts from the group on its site', async () => {
    const { commands, actions } = setup(
      anObject({ id: 'g1', type: 'hostgroup', group_name: 'switches' })
    )
    vi.mocked(commands.hostgroupHosts).mockResolvedValue(['core01'])
    vi.mocked(commands.childHosts).mockResolvedValue(['access01'])

    actions.select(OBJECT_ACTION_IDS.scheduleDowntime)
    await actions.submit({
      ...defaultScheduleDowntimeValues([]),
      comment: 'switch swap',
      includeChildHosts: true
    })

    expect(commands.hostgroupHosts).toHaveBeenCalledWith('http://remote/site/check_mk/', 'switches')
    expect(commands.childHosts).toHaveBeenCalledWith('http://remote/site/check_mk/', ['core01'])
    expect(commands.downtimeHostgroup).toHaveBeenCalledExactlyOnceWith(
      'http://remote/site/check_mk/',
      'switches',
      expect.objectContaining({ comment: 'switch swap' }),
      ['access01']
    )
  })
})
