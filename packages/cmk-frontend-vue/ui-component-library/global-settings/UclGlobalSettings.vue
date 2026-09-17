<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import { HttpResponse, http } from 'msw'

import GlobalSettingsApp from '@/global-settings/GlobalSettingsApp.vue'
import type { GlobalSettingsOrigin } from '@/global-settings/api'

import { globalSettingsPagePayload as data } from './globalSettingsPagePayload'

defineProps<{ screenshotMode: boolean }>()

const SETTING_PATH = '*/api/internal/objects/global_setting/:varname'

interface StoredValue {
  value: unknown
  origin: GlobalSettingsOrigin
}

const variables = data.topics.flatMap((topic) => topic.variables)
const stored = new Map<string, StoredValue>(
  variables.map((variable) => [
    variable.name,
    {
      value: structuredClone(variable.current.value),
      origin: variable.current.explicit ? 'global' : 'factory'
    }
  ])
)
const defaults = new Map<string, unknown>(
  variables.map((variable) => [variable.name, variable.factory_value])
)

function respond(varname: string): Response {
  const value = stored.get(varname)
  if (value === undefined) {
    return HttpResponse.json(
      { title: 'Not found', detail: `There is no setting named "${varname}".` },
      { status: 404 }
    )
  }
  return HttpResponse.json({ varname, ...value }, { headers: { ETag: '"demo"' } })
}

const { mockLoaded } = useMswWorker([
  http.get(SETTING_PATH, ({ params }) => respond(params['varname'] as string)),
  http.put(SETTING_PATH, async ({ params, request }) => {
    const varname = params['varname'] as string
    const body = (await request.json()) as { value: unknown }
    stored.set(varname, { value: body.value, origin: 'global' })
    return respond(varname)
  }),
  http.delete(SETTING_PATH, ({ params }) => {
    const varname = params['varname'] as string
    stored.set(varname, { value: structuredClone(defaults.get(varname)), origin: 'factory' })
    return new HttpResponse(null, { status: 204 })
  })
])
</script>

<template>
  <GlobalSettingsApp v-if="mockLoaded" v-bind="data" />
</template>
