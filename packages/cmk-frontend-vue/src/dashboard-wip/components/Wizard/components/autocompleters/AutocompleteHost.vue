<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { ButtonVariants } from '@/components/CmkDropdown/CmkDropdownButton.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

const { _t } = usei18n()

interface AutocompleteHostProps {
  placeholder?: TranslatedString
  width?: ButtonVariants['width']
}

defineProps<AutocompleteHostProps>()

const hostName = defineModel<string | null>('hostName', { required: true })

const hostNameAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: {
    ident: 'monitored_hostname',
    params: { strict: true }
  }
}
</script>

<template>
  <FormAutocompleter
    v-model="hostName"
    :autocompleter="hostNameAutocompleter"
    :size="0"
    :placeholder="placeholder || _t('Filter by host name')"
    :width="width || 'wide'"
  />
</template>
