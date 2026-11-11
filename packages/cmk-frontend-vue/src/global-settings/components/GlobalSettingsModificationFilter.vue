<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { GlobalSettingsScope } from '../api'
import type { ModificationFilter } from '../lib/values'

const { _t } = usei18n()

const props = defineProps<{ scope: GlobalSettingsScope; showSiteOverrides: boolean }>()

const selected = defineModel<ModificationFilter>({ default: 'all' })

const modifiedTooltip = _t('Show only settings modified globally for all sites')

const siteOverridesTooltip = computed<TranslatedString>(() =>
  props.scope.type === 'site'
    ? _t('Show only settings overridden on this site')
    : _t('Show only settings overridden on any site')
)

interface FilterOption {
  label: TranslatedString
  value: ModificationFilter
  tooltip: TranslatedString
}

const options = computed<FilterOption[]>(() => {
  const shown: FilterOption[] = [
    { label: _t('All settings'), value: 'all', tooltip: _t('Show all settings') },
    { label: _t('Modified globally'), value: 'modified', tooltip: modifiedTooltip }
  ]
  if (props.showSiteOverrides) {
    shown.push({
      label: props.scope.type === 'site' ? _t('Overridden by site') : _t('Overridden by sites'),
      value: 'site',
      tooltip: siteOverridesTooltip.value
    })
  }
  return shown
})
</script>

<template>
  <div
    class="global-settings-modification-filter"
    role="toolbar"
    :aria-label="_t('Filter settings')"
  >
    <CmkChip
      v-for="option in options"
      :key="option.value"
      :color="selected === option.value ? 'success' : 'others'"
      :variant="selected === option.value ? 'fill' : 'outline'"
      :aria-pressed="selected === option.value"
      :title="option.tooltip"
      @click="selected = option.value"
    >
      {{ option.label }}
    </CmkChip>
  </div>
</template>

<style scoped>
.global-settings-modification-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
