<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { GlobalSettingsScope } from '../api'
import type { ModificationFilter } from '../lib/origin'

const { _t } = usei18n()

const props = defineProps<{ scope: GlobalSettingsScope; showSiteOverrides: boolean }>()

const selected = defineModel<ModificationFilter>({ default: 'all' })

const modifiedTooltip = computed<TranslatedString>(() =>
  props.scope.type === 'site'
    ? _t('Show only settings configured for this site whether globally or as a site override')
    : _t('Show only settings modified globally for all sites')
)

const siteOverridesTooltip = computed<TranslatedString>(() =>
  props.scope.type === 'site'
    ? _t('Show only settings overridden on this site')
    : _t('Show only settings overridden on any site')
)

const options = computed<ToggleButtonOption[]>(() => [
  { label: _t('All settings'), value: 'all', tooltip: _t('Show all settings') },
  { label: _t('Modified only'), value: 'modified', tooltip: modifiedTooltip.value },
  ...(props.showSiteOverrides
    ? [{ label: _t('Site overrides only'), value: 'site', tooltip: siteOverridesTooltip.value }]
    : [])
])
</script>

<template>
  <CmkToggleButtonGroup
    :options="options"
    :model-value="selected"
    spacing="none"
    @update:model-value="selected = $event as ModificationFilter"
  />
</template>
