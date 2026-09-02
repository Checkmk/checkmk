/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Monitoring commands issued from a map.
 *
 * Acknowledgements, downtimes and comments go to Checkmk's own REST API, for one
 * object as for a whole group. Rescheduling a check and the notification and
 * active-check toggles have no such endpoint yet, so they go through Maps' own
 * internal one, which fires them through Checkmk's command layer over the
 * configured sites, with real permissions and explicit site scoping.
 *
 * All of it rides the GUI session, not the maps ticket: the daemon owns live
 * state and never writes to monitoring.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { createClient, unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { API_ROOT } from 'cmk-ui-library/lib/rest-api-client/constants'

import type { DowntimeEntry } from '@/maps/types/api'
import { stripCheckmkBase } from '@/maps/utils/mapNavigation'

/** Acknowledging a problem, however many objects it is applied to. */
export interface AcknowledgeOptions {
  comment: string
  sticky: boolean
  notify: boolean
  persistent: boolean
}

/** Scheduling a downtime, however many objects it is applied to. */
export interface DowntimeOptions {
  /** When it begins, as an ISO timestamp (``useDowntimeWindow``'s ``asIso``). */
  startTime: string
  /** When it ends, as an ISO timestamp. */
  endTime: string
  comment: string
}

type MapCommandVerb = components['schemas']['MapsCommandRequest']['action']

type RestClient = ReturnType<typeof createClient>

/**
 * The typed REST client for one connection's site.
 *
 * Which site a command lands on is the object's connection, not the page's, so
 * the base URL is per connection -- ``openapi-fetch`` takes one per instance.
 * The versioned ``1.0`` family rather than the internal one: a connection may
 * point at an older site, where only the versioned API is promised.
 */
const restClients = new Map<string, RestClient>()

function restClient(checkmkUrl: string): RestClient {
  const baseUrl = `${stripCheckmkBase(checkmkUrl)}/check_mk/${API_ROOT}`
  const existing = restClients.get(baseUrl)
  if (existing) {
    return existing
  }
  const created = createClient({ baseUrl })
  restClients.set(baseUrl, created)
  return created
}

/**
 * A plain downtime window: it starts when it says it does (``duration: 0``) and
 * does not repeat. The endpoints default to this; the schema asks for it anyway.
 */
const DOWNTIME_DEFAULTS = { duration: 0, recur: 'fixed' } as const

/** A comment that does not outlive a core restart; the same holds as above. */
const COMMENT_DEFAULTS = { persistent: false } as const

/** Every command body is JSON, which the endpoints ask for by header. */
const JSON_BODY = { params: { header: { 'Content-Type': 'application/json' } } } as const

function toDowntimeEntry(
  id: string,
  extensions: components['schemas']['DowntimeExtensionsModel']
): DowntimeEntry {
  return {
    id,
    site_id: extensions.site_id,
    host_name: extensions.host_name,
    ...(extensions.service_description !== undefined
      ? { service_description: extensions.service_description }
      : {}),
    author: extensions.author,
    comment: extensions.comment,
    start_time: extensions.start_time,
    end_time: extensions.end_time,
    type: extensions.is_service ? 'service' : 'host'
  }
}

async function listDowntimes(
  checkmkUrl: string,
  query: { host_name: string; service_description?: string; downtime_type: string }
): Promise<DowntimeEntry[]> {
  const collection = unwrap(
    await restClient(checkmkUrl).GET('/domain-types/downtime/collections/all', {
      params: { query }
    })
  )
  // ``id`` is optional in the schema, and an entry without one cannot be acted on.
  return collection.value.flatMap((downtime) =>
    downtime.id === undefined ? [] : [toDowntimeEntry(downtime.id, downtime.extensions)]
  )
}

/**
 * A verb Maps runs itself. An object off a map the site could not be resolved
 * for carries no site; a reschedule then goes to the local site, a toggle is
 * refused.
 */
async function mapCommand(
  action: MapCommandVerb,
  hostname: string,
  serviceDescription: string | null,
  siteId?: string | null
): Promise<void> {
  unwrap(
    await client.POST('/domain-types/maps_command/actions/run/invoke', {
      ...JSON_BODY,
      body: {
        action,
        host_name: hostname,
        ...(serviceDescription !== null ? { service_description: serviceDescription } : {}),
        ...(siteId ? { site_id: siteId } : {})
      }
    })
  )
}

/**
 * A command about one object goes to the page's own site, which finds the object
 * on the configured sites by itself; a group command and the downtime list go to
 * the connection's site.
 */
export class CommandsApi {
  public async acknowledgeHost(hostname: string, options: AcknowledgeOptions): Promise<void> {
    unwrap(
      await client.POST('/domain-types/acknowledge/collections/host', {
        ...JSON_BODY,
        body: { acknowledge_type: 'host', host_name: hostname, ...options }
      })
    )
  }

  public async acknowledgeService(
    hostname: string,
    serviceDescription: string,
    options: AcknowledgeOptions
  ): Promise<void> {
    unwrap(
      await client.POST('/domain-types/acknowledge/collections/service', {
        ...JSON_BODY,
        body: {
          acknowledge_type: 'service',
          host_name: hostname,
          service_description: serviceDescription,
          ...options
        }
      })
    )
  }

  public async downtimeHost(hostname: string, options: DowntimeOptions): Promise<void> {
    unwrap(
      await client.POST('/domain-types/downtime/collections/host', {
        ...JSON_BODY,
        body: {
          downtime_type: 'host',
          host_name: hostname,
          start_time: options.startTime,
          end_time: options.endTime,
          comment: options.comment,
          ...DOWNTIME_DEFAULTS
        }
      })
    )
  }

  public async downtimeService(
    hostname: string,
    serviceDescription: string,
    options: DowntimeOptions
  ): Promise<void> {
    unwrap(
      await client.POST('/domain-types/downtime/collections/service', {
        ...JSON_BODY,
        body: {
          downtime_type: 'service',
          host_name: hostname,
          service_descriptions: [serviceDescription],
          start_time: options.startTime,
          end_time: options.endTime,
          comment: options.comment,
          ...DOWNTIME_DEFAULTS
        }
      })
    )
  }

  public async removeDowntimeHost(checkmkUrl: string, hostname: string): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/downtime/actions/delete/invoke', {
        ...JSON_BODY,
        body: { delete_type: 'params', host_name: hostname, service_descriptions: null }
      })
    )
  }

  public async removeDowntimeService(
    checkmkUrl: string,
    hostname: string,
    serviceDescription: string
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/downtime/actions/delete/invoke', {
        ...JSON_BODY,
        body: {
          delete_type: 'params',
          host_name: hostname,
          service_descriptions: [serviceDescription]
        }
      })
    )
  }

  public listDowntimesHost(checkmkUrl: string, hostname: string): Promise<DowntimeEntry[]> {
    return listDowntimes(checkmkUrl, { host_name: hostname, downtime_type: 'host' })
  }

  public listDowntimesService(
    checkmkUrl: string,
    hostname: string,
    serviceDescription: string
  ): Promise<DowntimeEntry[]> {
    return listDowntimes(checkmkUrl, {
      host_name: hostname,
      service_description: serviceDescription,
      downtime_type: 'service'
    })
  }

  public async removeDowntimeById(
    checkmkUrl: string,
    downtimeId: string,
    siteId: string
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/downtime/actions/delete/invoke', {
        ...JSON_BODY,
        body: { delete_type: 'by_id', downtime_id: downtimeId, site_id: siteId }
      })
    )
  }

  public forceCheckHost = (hostname: string, siteId?: string | null) =>
    mapCommand('force_check', hostname, null, siteId)

  public forceCheckService = (
    hostname: string,
    serviceDescription: string,
    siteId?: string | null
  ) => mapCommand('force_check', hostname, serviceDescription, siteId)

  public async addCommentHost(hostname: string, comment: string): Promise<void> {
    unwrap(
      await client.POST('/domain-types/comment/collections/host', {
        ...JSON_BODY,
        body: { comment_type: 'host', host_name: hostname, comment, ...COMMENT_DEFAULTS }
      })
    )
  }

  public async addCommentService(
    hostname: string,
    serviceDescription: string,
    comment: string
  ): Promise<void> {
    unwrap(
      await client.POST('/domain-types/comment/collections/service', {
        ...JSON_BODY,
        body: {
          comment_type: 'service',
          host_name: hostname,
          service_description: serviceDescription,
          comment,
          ...COMMENT_DEFAULTS
        }
      })
    )
  }

  public removeAcknowledgementHost = async (hostname: string): Promise<void> => {
    unwrap(
      await client.POST('/domain-types/acknowledge/actions/delete/invoke', {
        ...JSON_BODY,
        body: { acknowledge_type: 'host', host_name: hostname }
      })
    )
  }

  public removeAcknowledgementService = async (
    hostname: string,
    serviceDescription: string
  ): Promise<void> => {
    unwrap(
      await client.POST('/domain-types/acknowledge/actions/delete/invoke', {
        ...JSON_BODY,
        body: {
          acknowledge_type: 'service',
          host_name: hostname,
          service_description: serviceDescription
        }
      })
    )
  }

  // ── Group bulk-actions ─────────────────────────────────────────────────
  // CMK's REST API supports ``acknowledge_type=hostgroup|servicegroup`` and
  // ``downtime_type=hostgroup|servicegroup`` so a single call applies to
  // every member of the group. This is dramatically faster (and safer in
  // terms of partial failures) than looping per-member from the UI.

  public async acknowledgeHostgroup(
    checkmkUrl: string,
    groupName: string,
    options: AcknowledgeOptions
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/acknowledge/collections/host', {
        ...JSON_BODY,
        body: { acknowledge_type: 'hostgroup', hostgroup_name: groupName, ...options }
      })
    )
  }

  public async acknowledgeServicegroup(
    checkmkUrl: string,
    groupName: string,
    options: AcknowledgeOptions
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/acknowledge/collections/service', {
        ...JSON_BODY,
        body: { acknowledge_type: 'servicegroup', servicegroup_name: groupName, ...options }
      })
    )
  }

  public async downtimeHostgroup(
    checkmkUrl: string,
    groupName: string,
    options: DowntimeOptions
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/downtime/collections/host', {
        ...JSON_BODY,
        body: {
          downtime_type: 'hostgroup',
          hostgroup_name: groupName,
          start_time: options.startTime,
          end_time: options.endTime,
          comment: options.comment,
          ...DOWNTIME_DEFAULTS
        }
      })
    )
  }

  public async downtimeServicegroup(
    checkmkUrl: string,
    groupName: string,
    options: DowntimeOptions
  ): Promise<void> {
    unwrap(
      await restClient(checkmkUrl).POST('/domain-types/downtime/collections/service', {
        ...JSON_BODY,
        body: {
          downtime_type: 'servicegroup',
          servicegroup_name: groupName,
          start_time: options.startTime,
          end_time: options.endTime,
          comment: options.comment,
          ...DOWNTIME_DEFAULTS
        }
      })
    )
  }

  public enableNotificationsHost = (hostname: string, siteId?: string | null) =>
    mapCommand('enable_notifications', hostname, null, siteId)

  public disableNotificationsHost = (hostname: string, siteId?: string | null) =>
    mapCommand('disable_notifications', hostname, null, siteId)

  public enableNotificationsService = (
    hostname: string,
    serviceDescription: string,
    siteId?: string | null
  ) => mapCommand('enable_notifications', hostname, serviceDescription, siteId)

  public disableNotificationsService = (
    hostname: string,
    serviceDescription: string,
    siteId?: string | null
  ) => mapCommand('disable_notifications', hostname, serviceDescription, siteId)

  public enableChecksHost = (hostname: string, siteId?: string | null) =>
    mapCommand('enable_checks', hostname, null, siteId)

  public disableChecksHost = (hostname: string, siteId?: string | null) =>
    mapCommand('disable_checks', hostname, null, siteId)

  public enableChecksService = (
    hostname: string,
    serviceDescription: string,
    siteId?: string | null
  ) => mapCommand('enable_checks', hostname, serviceDescription, siteId)

  public disableChecksService = (
    hostname: string,
    serviceDescription: string,
    siteId?: string | null
  ) => mapCommand('disable_checks', hostname, serviceDescription, siteId)
}
