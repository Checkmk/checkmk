<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CmkSimpleError } from 'cmk-ui-library/lib/error'
import { provide, toRaw } from 'vue'

import GlobalSettingsApp from '@/global-settings/GlobalSettingsApp.vue'
import {
  GLOBAL_SETTINGS_SERVICE,
  type GlobalSettingsService,
  type ReceivedValue
} from '@/global-settings/api'

import { globalSettingsPagePayload as data } from './globalSettingsPagePayload'

defineProps<{ screenshotMode: boolean }>()

const demoSettings = new Map<string, ReceivedValue>(
  data.topics
    .flatMap((topic) => topic.variables)
    .map((variable) => [
      variable.name,
      { value: structuredClone(variable.value), isDefault: !variable.modified, etag: 'demo' }
    ])
)
const demoDefaults = new Map<string, unknown>(
  data.topics
    .flatMap((topic) => topic.variables)
    .map((variable) => [variable.name, variable.default_value])
)

const demoService: GlobalSettingsService = {
  async load(_scope, varname) {
    const stored = demoSettings.get(varname)
    if (stored === undefined) {
      throw new CmkSimpleError(`There is no setting named "${varname}".`)
    }
    return { ...stored, value: structuredClone(stored.value) }
  },
  async save(_scope, varname, value) {
    const stored: ReceivedValue = {
      value: structuredClone(toRaw(value)),
      isDefault: false,
      etag: 'demo'
    }
    demoSettings.set(varname, stored)
    return { ...stored, value: structuredClone(stored.value) }
  },
  async reset(_scope, varname) {
    demoSettings.set(varname, {
      value: structuredClone(demoDefaults.get(varname)),
      isDefault: true,
      etag: 'demo'
    })
  }
}

provide(GLOBAL_SETTINGS_SERVICE, demoService)
</script>

<template>
  <GlobalSettingsApp v-bind="data" />
</template>
