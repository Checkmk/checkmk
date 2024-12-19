<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { provide, onBeforeUnmount, onBeforeMount, ref } from 'vue'
import FormSingleChoiceEditable from '@/form/components/forms/FormSingleChoiceEditable.vue'
import type { SingleChoiceEditable } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { configEntityAPI } from '@/form/components/utils/configuration_entity'

import { passthrough, bypass, http, HttpResponse } from 'msw'
import { setupWorker } from 'msw/browser'

import FormEditDispatcher from '@/form/components/FormEditDispatcher.vue'
import { dispatcherKey } from '@/form/private'

defineProps<{ screenshotMode: boolean }>()

async function loadSpec() {
  const specTemplate: SingleChoiceEditable = {
    type: 'single_choice_editable',
    title: 'some title',
    help: 'some help',
    validators: [],
    elements: [],
    config_entity_type: 'notification_parameter',
    config_entity_type_specifier: 'mail',
    allow_editing_existing_elements: true,
    i18n: {
      slidein_save_button: 'i18n slidein_save_button',
      slidein_cancel_button: 'i18n slidein_cancel_button',
      slidein_create_button: 'i18n slidein_create_button',
      edit: 'i18n edit',
      create: 'i18n create',
      loading: 'i18n loading',
      no_objects: 'i18n no_objects',
      no_selection: 'i18n_no_selection',
      validation_error: 'i18n validation_error',
      fatal_error: 'i18n fatal_error',
      fatal_error_reload: 'i18n fatal_error_reload',
      // TODO: save & create vs. new and edit!
      slidein_new_title: 'i18n_slidein_new_title',
      slidein_edit_title: 'i18n_slidein_edit_title',
      permanent_change_warning: 'i18n permanent_change_warning',
      permanent_change_warning_dismiss: 'i18n permanent_change_warning_dismiss'
    }
  }

  specTemplate.elements = (
    await configEntityAPI.listEntities('notification_parameter', 'mail')
  ).map(({ ident, description }: { ident: string; description: string }) => {
    return { name: ident, title: description }
  })

  spec.value = specTemplate
}

// demo stuff
function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function interceptor({ request }: { request: Request }) {
  await sleep(apiDelay.value)

  if (apiError.value) {
    if (apiError.value === 'proxy') {
      return HttpResponse.html(
        '<html><head><title>502 Proxy Error</title></head><body><h1>Proxy Error</h1></body></html>',
        { status: 502 }
      )
    } else if (apiError.value === 'crash') {
      return HttpResponse.json(
        // not complete!
        {
          detail:
            'AttributeError: "str" object has no attribute "get". Crash report generated. Please submit.',
          ext: {
            core: 'cmc',
            crash_type: 'rest_api',
            details: {
              check_mk_info: {},
              crash_report_url: {
                href: 'https://hos/site/check_mk/crash.py?crash_id=e152c11a-387b-11ef-bca0-00505688fb56&site=site',
                method: 'get',
                rel: 'cmk/crash-report',
                type: 'text/html'
              }
            }
          },
          status: 500,
          title: 'Internal Server Error'
        },
        { status: 500 }
      )
    } else if (apiError.value === 'error') {
      return HttpResponse.json(
        {
          title: 'An exception occurred',
          status: 500,
          detail: 'Some error message, maybe even with <b><tt>html</tt></b> tags'
        },
        { status: 500 }
      )
    } else {
      throw new Error()
    }
  }

  const headers = new Headers(request.headers)
  headers.set('Authorization', `Basic ${btoa(`${username.value}:${password.value}`)}`)

  const u = new URL(request.url)
  const proxyUrl = `/site-api/${site.value}/check_mk${u.pathname}${u.search}`

  let body = null
  if (request.method === 'PUT' || request.method === 'POST') {
    body = await request.text()
  }

  const r = new Request(proxyUrl, {
    method: request.method,
    headers: headers,
    body
  })
  const result = await fetch(bypass(r))
  return result
}

const apiRegExp = new RegExp(`${location.protocol}//${location.host}/api/.+`)

const handlers = [
  http.get(apiRegExp, interceptor),
  http.post(apiRegExp, interceptor),
  http.put(apiRegExp, interceptor),
  http.get(/.+/, () => {
    return passthrough()
  })
]
const worker = setupWorker(...handlers)

onBeforeMount(async () => {
  await worker.start()
  await loadSpec()
  mockLoaded.value = true
})

onBeforeUnmount(() => {
  worker.stop()
})

const data = ref<string | null>(null)

const mockLoaded = ref<boolean>(false)
const username = ref<string>('cmkadmin')
const password = ref<string>('cmk')
const site = ref<string>('heute')
const reloadCount = ref<number>(0)
const apiDelay = ref<number>(0)
const apiError = ref<false | 'proxy' | 'crash' | 'error'>(false)
const spec = ref<SingleChoiceEditable>()

provide(dispatcherKey, FormEditDispatcher)
</script>

<template>
  <div class="demo-control">
    <button @click="reloadCount += 1">reload</button>
    <label>TODO: number of elements to return</label>
    <fieldset>
      <legend>proxy</legend>
      <label>username<input v-model="username" /></label>
      <label>password<input v-model="password" /></label>
      <label>site<input v-model="site" /></label>
    </fieldset>
    <label>
      delay
      <select v-model="apiDelay">
        <option :value="0">No API delay</option>
        <option :value="3000">3 second api delay</option>
      </select>
    </label>
    <label>
      api errors
      <select v-model="apiError">
        <option :value="false">no error</option>
        <option :value="'proxy'">proxy error</option>
        <option :value="'crash'">crash report</option>
        <option :value="'error'">error</option>
      </select>
    </label>
  </div>
  <div v-if="mockLoaded && spec !== undefined">
    <FormSingleChoiceEditable
      :key="reloadCount"
      :spec="spec"
      :backend-validation="[]"
      :data="data"
    />
  </div>
  <div v-else>
    <h1>loading http mocking msw</h1>
  </div>
</template>

<style scoped>
.demo-control {
  margin-bottom: 1em;
  padding: 1em;
  display: flex;
  flex-direction: column;
}

.demo-control > * {
  display: flex;
  flex: 1 100%;
  margin-bottom: 0.5em;
}
</style>
