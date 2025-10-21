<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

const { _t } = usei18n()
const customGraph = defineModel<string | null>('customGraph', { required: true })

interface CmkAutocompleteServiceProps {
  hostName?: string | null
  placeholder?: TranslatedString
}

const props = defineProps<CmkAutocompleteServiceProps>()

const customGraphAutocompleter = computed(() => {
  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: 'custom_graphs',
      params: {
        strict: true,
        context: {}
      }
    }
  }
  return autocompleter
})
</script>

<template>
  <FormAutocompleter
    v-model="customGraph"
    :autocompleter="customGraphAutocompleter"
    :size="0"
    :placeholder="props.placeholder || _t('Select custom graph')"
  />
</template>
