<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import type { String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { HttpResponse, http, passthrough } from 'msw'
import { ref } from 'vue'

import FormEdit from '@/form/FormEdit.vue'

const apiReturnsError = ref<boolean>(false)

const ALL: Array<string> = []
for (let i = 0; i < 200; i++) {
  ALL.push(randomId())
}

async function interceptor({ request }: { request: Request }) {
  if (apiReturnsError.value) {
    return HttpResponse.json(
      {
        title: 'Invalid input',
        detail:
          'some error very very very very very very very very very very very very very very very very very very very very very long message'
      },
      { status: 400 }
    )
  }

  const { value } = (await request.json()) as { value: string }

  return HttpResponse.json({
    choices: ALL.filter((element: string) => element.includes(value)).map((element) => ({
      id: element,
      value: element
    }))
  })
}
const { mockLoaded } = useMswWorker([
  http.post('*/api/internal/objects/autocomplete/:ident', interceptor),
  http.get(/.+/, () => passthrough())
])

defineProps<{ screenshotMode: boolean }>()

const spec: String = {
  type: 'string',
  title: '',
  help: '',
  validators: [],
  label: null,
  input_hint: '',
  field_size: 'medium',
  autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: true,
        world: 'world',
        context: {}
      }
    },
    fetch_method: 'rest_autocomplete'
  }
}

const data = ref<string>('some thing')
</script>

<template>
  <input type="text" value="unrelated input field you can tab into" />
  <h2>With autocompleter</h2>
  <CmkCheckbox v-model="apiReturnsError" label="error in autocompleter" />
  <pre>{{ JSON.stringify(data) }}</pre>
  <span v-if="mockLoaded">
    <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  </span>
  <br />
  <input type="text" value="unrelated input field you can tab into" />
  <br />
  <select>
    <option>asd</option>
    <option>bsd</option>
  </select>
  <br />
  <input type="text" value="unrelated input field you can tab into" />
  <br />
</template>
