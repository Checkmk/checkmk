/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'

import { useServiceActions } from '@/monitoring/shared/useServiceActions'

useMswServer(
  restApiHttp.get('/monitor/hosts/{hostname}/service/action_menu', ({ response }) =>
    response(200).json({
      items: [
        {
          ident: 'logwatch',
          icon_name: 'logwatch',
          title: 'Open log file viewer',
          url: 'view.py?view_name=logwatch&host=web-1&site=local',
          target: '_blank'
        }
      ]
    })
  )
)

test('offers rescheduling and a selection when the user may reschedule', () => {
  const actions = useServiceActions({
    actions: [{ ident: 'reschedule', title: 'Reschedule', icon: 'reload' }]
  })

  expect(actions.permittedActions.map((action) => action.id)).toEqual(['reschedule'])
  expect(actions.mayReschedule).toBe(true)
  expect(actions.mayActOnSelection).toBe(true)
})

test('offers neither rescheduling nor a selection without permitted actions', () => {
  const actions = useServiceActions({})

  expect(actions.permittedActions).toEqual([])
  expect(actions.mayReschedule).toBe(false)
  expect(actions.mayActOnSelection).toBe(false)
})

test('offers the commands implemented for services', () => {
  const actions = useServiceActions({})

  expect(Object.keys(actions.registry)).toEqual([
    'acknowledge',
    'reschedule',
    'schedule_downtimes',
    'add_comment',
    'send_custom_notification',
    'fake_check_result',
    'remove_acknowledgments',
    'remove_downtimes_hosts_services',
    'notifications',
    'toggle_active_checks',
    'toggle_passive_checks',
    'clear_modified_attributes',
    'ec_archive_events_of_host'
  ])
})

test('lists the action-menu links of a service as menu entries', async () => {
  const actions = useServiceActions({})

  const entries = await actions.loadActionMenu({ name: 'web-1', site_id: 'local' }, 'Log')

  expect(entries).toEqual([
    {
      id: 'Open log file viewer|view.py?view_name=logwatch&host=web-1&site=local',
      label: 'Open log file viewer',
      icon: 'logwatch',
      url: 'view.py?view_name=logwatch&host=web-1&site=local',
      target: '_blank',
      ident: 'logwatch'
    }
  ])
})
