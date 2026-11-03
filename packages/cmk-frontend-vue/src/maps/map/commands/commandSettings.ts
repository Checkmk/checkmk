/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How the site has its acknowledge and downtime dialogs set up -- option
 * defaults, durations, the edition's recurrences -- handed in by the page that
 * mounts the SPA, the way the monitoring pages get theirs.
 */
import type { MapsCommandSettings } from 'cmk-shared-typing/typescript/maps'
import { type InjectionKey, inject, provide } from 'vue'

export const MAPS_COMMAND_SETTINGS: InjectionKey<MapsCommandSettings> =
  Symbol('mapsCommandSettings')

export function provideMapsCommandSettings(settings: MapsCommandSettings): void {
  provide(MAPS_COMMAND_SETTINGS, settings)
}

export function useMapsCommandSettings(): MapsCommandSettings {
  const settings = inject(MAPS_COMMAND_SETTINGS)
  if (!settings) {
    throw new Error('no provider for MapsCommandSettings')
  }
  return settings
}
