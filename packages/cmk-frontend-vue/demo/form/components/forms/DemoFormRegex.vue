<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { setupWorker } from 'msw/browser'
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'

import FormEdit from '@/form/FormEdit.vue'

async function interceptor({ request }: { request: Request }) {
  const jsonData = (await request.formData()).get('request')
  const parsed = JSON.parse(jsonData as string)

  const query = parsed.value ?? ''
  const inputType = parsed.input_type ?? parsed.context?.input_type ?? 'regex'

  const isRegex = inputType === 'regex'
  const isText = inputType === 'text'
  const allChoices = [
    'linux01',
    'linux02',
    'linux03',
    'windows01',
    'windows02',
    'windows03',
    'snmp01',
    'snmp02',
    'snmp03',
    'db01',
    'db02',
    'db03',
    'web01',
    'web02',
    'web03',
    'mail01',
    'mail02',
    'mail03',
    'proxy01',
    'proxy02',
    'backup01',
    'backup02',
    'printer01',
    'printer02',
    'router01',
    'switch',
    'proxy',
    'backup',
    'printer',
    'router',
    'switch'
  ]

  let filtered: string[]
  if (isRegex) {
    try {
      const regex = new RegExp(query, 'i')
      filtered = allChoices.filter((choice) => regex.test(choice))
    } catch (e) {
      console.error(e)
      filtered = allChoices
    }
  } else {
    const lowerQuery = query.toLowerCase()
    filtered = allChoices.filter((choice) => choice.toLowerCase().includes(lowerQuery))
  }

  if (isText && query && !filtered.includes(query)) {
    filtered.unshift(query)
    data.value = query
  }

  const choices = filtered.map((choice) => [choice, choice])
  return HttpResponse.json({
    result: { choices, total: allChoices.length },
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

defineProps<{ screenshotMode: boolean }>()

const regexSpec: Regex = {
  type: 'regex',
  title: '',
  help: 'help',
  validators: [],
  label: '',
  input_type: 'regex',
  no_results_hint: 'No matches found',
  autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        input_hint: ''
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  }
}

const data = ref('')
</script>

<template>
  <span v-if="mockLoaded">
    <section style="margin-bottom: 2em">
      <h2>Single Regex Input</h2>
      <FormEdit v-model:data="data" :spec="regexSpec" :backend-validation="[]" />
    </section>
  </span>
</template>
