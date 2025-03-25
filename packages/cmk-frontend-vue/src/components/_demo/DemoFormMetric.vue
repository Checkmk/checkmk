<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { Metric } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormMetric from '@/form/components/forms/FormMetric.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<Metric>({
  type: 'metric',
  title: 'Metric',
  help: '',
  validators: [],
  i18n_base: {
    required: 'required'
  },
  label: null,
  input_hint: '(Select metric)',
  field_size: 'MEDIUM',
  autocompleter: {
    data: {
      ident: 'monitored_metrics',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  service_filter_autocompleter: {
    data: {
      ident: 'monitored_service_description',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  host_filter_autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  i18n: {
    host_input_hint: '(Select host)',
    host_filter: 'Filter selection by host name:',
    service_input_hint: '(Select service)',
    service_filter: 'Filter selection by service:'
  }
})
const data = ref<string>('')
</script>

<template>
  <FormMetric v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
