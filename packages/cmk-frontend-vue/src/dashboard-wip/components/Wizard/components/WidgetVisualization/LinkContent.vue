<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

const { _t } = usei18n()

interface LinkContentProps {
  linkOptions: Suggestion[]
  linkValidation: TranslatedString[]
  targetOptions: Suggestion[]
}

const props = defineProps<LinkContentProps>()

const linkType = defineModel<string | null>('linkType', { required: true, default: null })
const linkTarget = defineModel<string | null>('linkTarget', { required: true })

const linkEnabled = computed({
  get: () => linkType.value !== null,
  set: (value: boolean) => {
    linkType.value = value ? props.linkOptions[0]!.name : null
  }
})

const isError = computed(() => props.linkValidation.length > 0)
</script>

<template>
  <CmkCheckbox v-model="linkEnabled" :label="_t('Link content to')" />
  <CmkIndent v-if="linkEnabled">
    <CmkDropdown
      v-model:selected-option="linkType"
      :label="_t('Select a category')"
      :options="{ type: 'fixed', suggestions: linkOptions }"
    />
    <CmkSpace />
    <CmkDropdown
      v-model:selected-option="linkTarget"
      :label="_t('Select a target')"
      :options="{ type: 'fixed', suggestions: targetOptions || [] }"
    />
    <div v-if="isError">
      <CmkInlineValidation :validation="linkValidation" />
    </div>
  </CmkIndent>
</template>
