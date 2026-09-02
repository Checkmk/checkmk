/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How the SPA's services reach the components that use them.
 *
 * They are created once by ``MapsApp`` and provided behind typed keys, so their
 * lifetime is the app's: a custom element that is disconnected and reconnected
 * gets a fresh set, with its timers and stream subscriptions torn down in
 * between. The inject hooks throw rather than returning ``undefined``, because a
 * component reached without the app around it is a wiring bug, not a state to
 * render.
 */
import { type InjectionKey, inject, provide } from 'vue'

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
import { createMapsDaemonClient } from '@/maps/api/transport'
import { AuthoringSettingsService } from '@/maps/services/AuthoringSettingsService'
import { ConnectionsService } from '@/maps/services/ConnectionsService'
import { MapService } from '@/maps/services/MapService'
import { MapStatesService } from '@/maps/services/MapStatesService'
import { MapsAuthService } from '@/maps/services/MapsAuthService'
import { NavigationService } from '@/maps/services/NavigationService'
import { ToastService } from '@/maps/services/ToastService'

/**
 * The endpoint bindings, kept apart from the services on purpose: a surface
 * reaching for one of these talks to the transport itself, which is visible in
 * its ``useMapsApis()`` line instead of hiding among the services.
 */
export interface MapsApis {
  mapConfig: MapConfigApi
  mapStates: MapStatesApi
  connections: ConnectionsApi
  objects: MonitoringObjectsApi
  commands: CommandsApi
  images: ImagesApi
  metricInfo: MetricInfoApi
  formSchemas: FormSchemaApi
}

/** Everything a Maps surface can ask for. */
export interface MapsServices {
  auth: MapsAuthService
  nav: NavigationService
  toasts: ToastService
  maps: MapService
  states: MapStatesService
  connections: ConnectionsService
  settings: AuthoringSettingsService
  apis: MapsApis
}

/** Exported so a test can provide its own set without mounting the whole app. */
export const MAPS_SERVICES: InjectionKey<MapsServices> = Symbol('mapsServices')

/**
 * Builds the services and wires them together.
 *
 * This is the one place that knows the composition: the auth service supplies
 * the daemon transport's credential hook, so no api module and no component
 * handles a ticket.
 */
export function createMapsServices(): MapsServices {
  const auth = new MapsAuthService(new TicketApi())
  const daemon = createMapsDaemonClient({ headers: () => auth.daemonHeaders() })

  const mapConfig = new MapConfigApi()
  const mapStates = new MapStatesApi(daemon)
  const connectionsApi = new ConnectionsApi(daemon)
  const objects = new MonitoringObjectsApi()

  const maps = new MapService(mapConfig, mapStates)
  return {
    auth,
    nav: new NavigationService(),
    toasts: new ToastService(),
    maps,
    states: new MapStatesService(mapStates, connectionsApi, objects, auth, maps),
    connections: new ConnectionsService(connectionsApi),
    settings: new AuthoringSettingsService(new AuthoringSettingsApi()),
    apis: {
      mapConfig,
      mapStates,
      connections: connectionsApi,
      objects,
      commands: new CommandsApi(),
      images: new ImagesApi(),
      metricInfo: new MetricInfoApi(),
      formSchemas: new FormSchemaApi()
    }
  }
}

export function provideMapsServices(services: MapsServices): void {
  provide(MAPS_SERVICES, services)
}

/**
 * Takes the app's services down with it.
 *
 * The SPA is a custom element: it can be disconnected and reconnected, and every
 * listener, timer and stream a service holds has to end with the instance that
 * opened it, or the next one runs alongside the last. Every service therefore
 * has a ``dispose()`` and this calls all of them -- a hand-kept list would go
 * stale the moment a service grows a timer, and the type error a missing
 * ``dispose()`` raises here is the only thing that catches that.
 */
export function disposeMapsServices(services: MapsServices): void {
  const { apis: _apis, ...disposables } = services
  for (const service of Object.values(disposables)) {
    service.dispose()
  }
}

export function useMapsServices(): MapsServices {
  const services = inject(MAPS_SERVICES)
  if (!services) {
    throw new Error('no provider for MapsServices')
  }
  return services
}

export function useMapsApis(): MapsApis {
  return useMapsServices().apis
}

export function useAuth(): MapsAuthService {
  return useMapsServices().auth
}

export function useMaps(): MapService {
  return useMapsServices().maps
}

export function useStates(): MapStatesService {
  return useMapsServices().states
}

export function useConnections(): ConnectionsService {
  return useMapsServices().connections
}

export function useSettings(): AuthoringSettingsService {
  return useMapsServices().settings
}

export function useNavigation(): NavigationService {
  return useMapsServices().nav
}

export function useToast(): ToastService {
  return useMapsServices().toasts
}
