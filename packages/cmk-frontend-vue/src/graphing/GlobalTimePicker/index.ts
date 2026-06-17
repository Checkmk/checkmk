/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export { default as GlobalTimePicker } from './GlobalTimePicker.vue'
export { default as GlobalTimePickerApp } from './GlobalTimePickerApp.vue'

export { useGlobalTimeRange } from './useGlobalTimeRange'
export type { ActiveTimeRange, GlobalTimeRange } from './useGlobalTimeRange'

export type {
  CustomGraphTimeRange,
  GlobalTimePickerProps
} from 'cmk-shared-typing/typescript/global_time_picker'
