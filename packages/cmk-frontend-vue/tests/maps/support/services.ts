/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Services for a component under test.
 *
 * The real ones are built by ``MapsApp`` and reach a component through
 * ``provide``, so a test provides its own instead of intercepting modules. What
 * a case cares about it passes in; everything else is a stub that resolves
 * empty, so a component can never reach a real endpoint from a test.
 */
import { render } from '@testing-library/vue'
import type { MapsPageLinks } from 'cmk-shared-typing/typescript/maps'
import type { BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import { vi } from 'vitest'
import { defineComponent, h, provide } from 'vue'

import { AuthoringSettingsApi } from '@/maps/api/authoringSettings'
import { CommandsApi } from '@/maps/api/commands'
import { ConnectionsApi } from '@/maps/api/connections'
import { FormSchemaApi } from '@/maps/api/formSchemas'
import { ImagesApi } from '@/maps/api/images'
import { MapConfigApi } from '@/maps/api/mapConfig'
import { MapStatesApi } from '@/maps/api/mapStates'
import { MetricInfoApi } from '@/maps/api/metricInfo'
import { MonitoringObjectsApi } from '@/maps/api/monitoringObjects'
import { TicketApi } from '@/maps/api/ticket'
import type { MapsCapabilities, MapsTicket } from '@/maps/api/ticket'
import { createMapsDaemonClient } from '@/maps/api/transport'
import { AuthoringSettingsService } from '@/maps/services/AuthoringSettingsService'
import { ConnectionsService } from '@/maps/services/ConnectionsService'
import { MapService } from '@/maps/services/MapService'
import { MapStatesService } from '@/maps/services/MapStatesService'
import { MapsAuthService } from '@/maps/services/MapsAuthService'
import { NavigationService } from '@/maps/services/NavigationService'
import { ToastService } from '@/maps/services/ToastService'
import { MAPS_SERVICES, type MapsApis, type MapsServices } from '@/maps/services/context'
import { MAPS_BREADCRUMB_ROOT } from '@/maps/shared/breadcrumb'
import { MAPS_PAGE_LINKS } from '@/maps/shared/pageLinks'

/** Capabilities of a user who may do everything, as a starting point. */
export function fullCapabilities(overrides: Partial<MapsCapabilities> = {}): MapsCapabilities {
  return {
    may_edit: true,
    configure: true,
    see_all: true,
    folder_see_all: true,
    contact_groups: [],
    publish_all: true,
    publish_to_groups: true,
    publish_to_foreign_groups: true,
    publish_to_sites: true,
    all_contact_groups: [],
    all_sites: [],
    commands: [],
    ...overrides
  }
}

export function aTicket(overrides: Partial<MapsTicket> = {}): MapsTicket {
  return {
    ticket: 'test-ticket',
    stream_token: 'test-stream-token',
    user_id: 'cmkadmin',
    language: 'en',
    capabilities: fullCapabilities(),
    ...overrides
  }
}

/**
 * What each of an api's async methods is made to resolve. Typed against the real
 * class: a renamed method or a changed return type fails the build here instead
 * of leaving a case asserting on a stub nobody calls any more.
 */
type ApiResults<T> = {
  [K in keyof T as T[K] extends (...args: never[]) => Promise<unknown> ? K : never]?: T[K] extends (
    ...args: never[]
  ) => Promise<infer R>
    ? R
    : never
}

/**
 * Replaces every callable member of an api with a resolved-empty stub — both the
 * prototype methods and the arrow-function fields an instance carries itself.
 * The sweep is by reflection so an unstubbed method can never reach the network;
 * what a case pins is type-checked.
 */
function stubApi<T extends object>(api: T, results: ApiResults<T>): T {
  const resolved = results as Record<string, unknown>
  const names = [
    ...Object.getOwnPropertyNames(Object.getPrototypeOf(api)),
    ...Object.getOwnPropertyNames(api)
  ]
  for (const name of names) {
    if (name === 'constructor' || typeof (api as Record<string, unknown>)[name] !== 'function') {
      continue
    }
    Object.defineProperty(api, name, {
      value: vi.fn().mockResolvedValue(resolved[name] ?? undefined),
      writable: true
    })
  }
  return api
}

/**
 * A full set of services on stubbed apis. Override individual ones per case; the
 * apis are plain vitest mocks, so a case can also re-point a single call.
 *
 * ``ticket`` is what the handshake returns — pass one to give the session
 * particular capabilities.
 */
export function fakeMapsServices(
  overrides: Partial<Omit<MapsServices, 'apis'>> & { apis?: Partial<MapsApis> } = {},
  ticket: MapsTicket = aTicket()
): MapsServices {
  // A real client, so the apis are constructed as they are in the app; every
  // method that would use it is stubbed, so nothing leaves the test.
  const daemon = createMapsDaemonClient({ headers: () => undefined })
  const ticketApi = stubApi(new TicketApi(), { fetchTicket: ticket })
  const mapConfig = stubApi(new MapConfigApi(), { list: [] })
  const mapStates = stubApi(new MapStatesApi(daemon), {
    fetchAutoObjects: [],
    fetchFolderHostServices: [],
    searchFolderServices: { matches: [], truncated: false, limit: 0 }
  })
  const connectionsApi = stubApi(new ConnectionsApi(daemon), { list: [], fetchTopology: [] })
  const objects = stubApi(new MonitoringObjectsApi(), {
    fetchObjects: [],
    fetchFolders: [],
    fetchSites: [],
    fetchAggregations: [],
    fetchAggregationStates: {},
    fetchGroupMembers: [],
    fetchDyngroupMembers: [],
    fetchPerfMetrics: { perf_data: '', check_command: '', metrics: [] },
    fetchAggregationTree: { tree: null, connection_ok: true },
    fetchHostGeo: null
  })
  const auth = new MapsAuthService(ticketApi)
  const settings = new AuthoringSettingsService(stubApi(new AuthoringSettingsApi(), {}))
  // The tile source as the site answers it at boot -- without one a geo map
  // deliberately draws no tiles at all.
  settings.tiles.value = {
    default_url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    allowed_sources: ['https://tile.openstreetmap.org/', 'https://*.tile.openstreetmap.org/']
  }
  const maps = new MapService(mapConfig, mapStates)
  const apis: MapsApis = {
    mapConfig,
    mapStates,
    connections: connectionsApi,
    objects,
    commands: stubApi(new CommandsApi(), {}),
    images: stubApi(new ImagesApi(), { list: [] }),
    metricInfo: stubApi(new MetricInfoApi(), {}),
    formSchemas: stubApi(new FormSchemaApi(), {})
  }
  return {
    auth,
    nav: new NavigationService(),
    toasts: new ToastService(),
    maps,
    states: new MapStatesService(mapStates, connectionsApi, objects, auth, maps),
    connections: new ConnectionsService(connectionsApi),
    settings,
    ...overrides,
    apis: { ...apis, ...overrides.apis }
  }
}

/**
 * Runs a composable inside a component that has the services provided, which is
 * where a composable using ``useMapsServices()`` (or any lifecycle hook) belongs.
 *
 * The body runs in a CHILD of the providing component: Vue resolves an injection
 * against the parent chain, so a component never sees what it provided itself.
 */
export function runWithServices<T>(services: MapsServices, body: () => T): T {
  return mountWithServices(services, body).result
}

/** {@link runWithServices}, plus the handle a teardown case needs. */
export function mountWithServices<T>(
  services: MapsServices,
  body: () => T
): { result: T; unmount: () => void } {
  let result!: T
  const child = defineComponent({
    setup() {
      result = body()
      return () => null
    }
  })
  const { unmount } = render(
    defineComponent({
      setup() {
        provide(MAPS_SERVICES, services)
        return () => h(child)
      }
    })
  )
  return { result, unmount }
}

/** The Checkmk URLs ``maps.py`` hands the app, as the page emits them. */
export function aPageLinks(overrides: Partial<MapsPageLinks> = {}): MapsPageLinks {
  return {
    settings: 'maps_settings.py',
    ...overrides
  }
}

/**
 * The ``global`` render option for a component under test: the services it
 * injects, plus whatever the case stubs out.
 */
export function mapsGlobal(stubs = {}, services: MapsServices = fakeMapsServices()) {
  return { ...provideServices(services).global, stubs }
}

/** The breadcrumb levels above the SPA, as ``maps.py`` emits them. */
export function aBreadcrumbRoot(): BreadcrumbItem[] {
  return [{ title: 'Customize', link: null }]
}

/**
 * ``global`` options that provide what ``MapsApp`` provides -- the services, the
 * page's links and the breadcrumb root -- to spread into a render call:
 * ``render(Component, { ...provideServices(services) })``.
 */
export function provideServices(
  services: MapsServices,
  links: MapsPageLinks = aPageLinks(),
  breadcrumbRoot: BreadcrumbItem[] = aBreadcrumbRoot()
): {
  global: { provide: Record<symbol, MapsServices | MapsPageLinks | BreadcrumbItem[]> }
} {
  return {
    global: {
      provide: {
        [MAPS_SERVICES as symbol]: services,
        [MAPS_PAGE_LINKS as symbol]: links,
        [MAPS_BREADCRUMB_ROOT as symbol]: breadcrumbRoot
      }
    }
  }
}
