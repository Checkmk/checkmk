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

import { type HostServiceContext } from './types'

const { _t } = usei18n()
const serviceDescription = defineModel<string | null>('serviceDescription', { required: true })

interface CmkAutocompleteServiceProps {
  hostName?: string | null
  placeholder?: TranslatedString
}

const props = defineProps<CmkAutocompleteServiceProps>()

const serviceNameAutocompleter = computed(() => {
  const context: HostServiceContext = {}
  if (props.hostName) {
    context.host = { host: props.hostName }
  }

  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: 'monitored_service_description',
      params: {
        strict: true,
        context: context
      }
    }
  }
  return autocompleter
})
</script>

<template>
  <FormAutocompleter
    v-model="serviceDescription"
    :autocompleter="serviceNameAutocompleter"
    :size="0"
    :placeholder="props.placeholder || _t('Filter by service')"
  />
</template>
