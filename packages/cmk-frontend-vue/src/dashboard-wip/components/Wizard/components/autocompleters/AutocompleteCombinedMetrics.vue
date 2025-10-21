<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

const { _t } = usei18n()

const combinedMetrics = defineModel<string | null>('combinedMetrics', { required: true })

const combinedMetricsAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: {
    ident: 'graph_template_for_combined_graph',
    params: {
      strict: true,
      show_independent_of_context: true,
      escape_regex: false
    }
  }
}
</script>

<template>
  <FormAutocompleter
    v-model="combinedMetrics"
    :autocompleter="combinedMetricsAutocompleter"
    :size="0"
    :placeholder="_t('Select graph')"
  />
</template>
