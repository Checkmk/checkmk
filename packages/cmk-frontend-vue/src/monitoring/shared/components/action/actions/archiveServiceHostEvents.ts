/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { ArchiveEventsApi } from '@/monitoring/shared/api/actions/archiveEvents'
import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

import { createConfirmedAction } from './confirmed'

export const ARCHIVE_EVENTS_ACTION_ID = 'ec_archive_events_of_host'

/** The hosts of the services, each once. */
export function hostsOf(services: readonly ServiceRef[]): HostRef[] {
  return [
    ...new Map(
      services.map((service) => [`${service.host.site_id}:${service.host.name}`, service.host])
    ).values()
  ]
}

/** Archives the open Event Console events of the hosts the selected services belong to. */
export function useArchiveServiceHostEventsAction(): MonitoringAction<
  Record<string, never>,
  ServiceRef
> {
  const { _t, _tn } = usei18n()
  const api = new ArchiveEventsApi()

  return createConfirmedAction<ServiceRef>(
    {
      id: ARCHIVE_EVENTS_ACTION_ID,
      title: _t('Archive events of hosts'),
      confirm: {
        detail: (_count, services) =>
          _tn(
            'All events of the host will be removed from the open events list. You can still access them in the archive.',
            'All events of the hosts will be removed from the open events list. You can still access them in the archive.',
            hostsOf(services).length
          ),
        submitLabel: () => _t('Archive events')
      }
    },
    {
      run: (services) => api.archiveHostEvents(hostsOf(services)),
      successMessage: (_count, services) =>
        _tn(
          'Events are archived for the selected host',
          'Events are archived for the selected hosts',
          hostsOf(services).length
        ),
      errorHeading: _t('Could not archive the events of the selected hosts')
    }
  )
}
