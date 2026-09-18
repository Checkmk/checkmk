<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

export type ModificationFilter = 'all' | 'default' | 'modified'

const { _t } = usei18n()

const selected = defineModel<ModificationFilter>({ default: 'all' })

const options = computed(() => [
  { label: _t('All settings'), value: 'all' },
  { label: _t('Default only'), value: 'default' },
  { label: _t('Modified only'), value: 'modified' }
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
