<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'

import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import SelectorSingleInfo from '@/dashboard-wip/components/selectors/SelectorSingleInfo.vue'
import { RestrictedToSingle } from '@/dashboard-wip/types/shared.ts'

const { _t } = usei18n()

type SpecificObjectOption = {
  name: RestrictedToSingle
  title: TranslatedString
}

const SPECIFIC_OBJECT_OPTIONS: SpecificObjectOption[] = [
  { name: RestrictedToSingle.NO, title: _t('No restrictions to specific objects') },
  { name: RestrictedToSingle.HOST, title: _t('Restrict to a single host') },
  { name: RestrictedToSingle.CUSTOM, title: _t('Configure restrictions manually') }
]

const props = withDefaults(
  defineProps<{
    contextInfos: string[]
    readOnly?: boolean // TODO: needs to be included once component has been adapted
  }>(),
  {
    readOnly: false
  }
)

const mode = defineModel<RestrictedToSingle>('mode', { default: RestrictedToSingle.NO })
const restrictedIds = defineModel<string[]>('restrictedIds', { default: [] })

const dropdownOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: SPECIFIC_OBJECT_OPTIONS.map((o) => ({
    name: o.name,
    title: o.title
  }))
}))
</script>

<template>
  <div>
    <h2>{{ _t('Specific object type') }}</h2>
    <ContentSpacer :height="10" />
    <CmkDropdown
      v-model:selected-option="mode"
      :options="dropdownOptions"
      :disabled="props.readOnly"
      :label="_t('Select specific object type')"
    />
    <ContentSpacer />
    <SelectorSingleInfo
      v-if="mode === RestrictedToSingle.CUSTOM"
      v-model:selected-ids="restrictedIds"
      :only-ids="props.contextInfos"
    />
  </div>
</template>
