<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
import type { Labels, Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormLabels from '@/form/components/forms/FormLabels.vue'
import { http, HttpResponse } from 'msw'
import { setupWorker } from 'msw/browser'
import FormReadonly from '@/form/components/FormReadonly.vue'

defineProps<{ screenshotMode: boolean }>()

type StringMapping = Record<string, string>
type LabelSources = 'explicit' | 'ruleset' | 'discovered'

const labelSource = ref<LabelSources>('explicit')

const autocompleter: Autocompleter = {
  data: { ident: 'label', params: { world: 'config' } },
  fetch_method: 'ajax_vs_autocomplete'
}

const spec = computed<Labels>(() => ({
  type: 'labels',
  title: 'some title',
  help: 'some help',
  i18n_base: { required: 'required' },
  i18n: {
    remove_label: 'i18n remove_label',
    add_some_labels: 'Add some labels',
    key_value_format_error: 'Key value format error',
    max_labels_reached: 'Max labels reached',
    uniqueness_error: 'Uniqueness error'
  },
  validators: [],
  max_labels: 5,
  label_source: labelSource.value,
  autocompleter: autocompleter
}))
const data = ref<StringMapping>({
  'cmk/check_mk_server': 'yes',
  'cmk/os_family': 'linux',
  'cmk/os_name': 'Ubuntu'
})

async function interceptor({ request }: { request: Request }) {
  const jsonData = (await request.formData()).get('request')
  const query = JSON.parse(jsonData as string).value
  const userProvided: Array<[string, string]> = []
  if (/^[^:]+:[^:]+$/.test(query)) {
    userProvided.push([query, query])
  }
  return HttpResponse.json({
    result: {
      choices: [
        ...userProvided,
        ['cmk/check_mk_server:yes', 'cmk/check_mk_server:yes'],
        ['cmk/os_family:linux', 'cmk/os_family:linux'],
        ['cmk/os_name:Ubuntu', 'cmk/os_name:Ubuntu'],
        ['cmk/os_platform:ubuntu', 'cmk/os_platform:ubuntu'],
        ['cmk/os_type:linux', 'cmk/os_type:linux'],
        ['cmk/os_version:22.04', 'cmk/os_version:22.04'],
        ['cmk/site:heute_cl', 'cmk/site:heute_cl']
      ].filter((key) => key[0]?.includes(query))
    },
    result_code: 0,
    severity: 'success'
  })
}
const worker = setupWorker(
  ...[
    http.post(
      new RegExp(`${location.protocol}//${location.host}/ajax_vs_autocomplete.py`),
      interceptor
    )
  ]
)

onBeforeMount(async () => {
  await worker.start()
  mockLoaded.value = true
})

onBeforeUnmount(() => {
  worker.stop()
})

const mockLoaded = ref<boolean>(false)
</script>

<template>
  <span v-if="mockLoaded">
    <FormLabels v-model:data="data" :spec="spec" :backend-validation="[]" />
    <pre>{{ data }}</pre>
  </span>

  <label>
    Label Source:
    <select v-model="labelSource">
      <option value="null">null</option>
      <option value="explicit">explicit</option>
      <option value="ruleset">ruleset</option>
      <option value="discovered">discovered</option>
    </select>
  </label>

  <FormReadonly :spec="spec" :data="data" :backend-validation="[]" />
</template>
