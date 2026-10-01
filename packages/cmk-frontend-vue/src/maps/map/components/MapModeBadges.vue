<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Why the map is not behaving the way the operator expects: they are in edit
mode, and their clicks are selecting rather than drilling down.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  editing?: boolean
}>()
</script>

<template>
  <span v-if="editing" class="maps-map-mode-badges__badge maps-map-mode-badges__badge--editing">
    <CmkIcon name="edit" size="xsmall" />
    {{ _t('Editing') }}
  </span>
</template>

<style scoped>
.maps-map-mode-badges__badge {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  border-radius: var(--dimension-4);
}

.maps-map-mode-badges__badge--editing {
  color: var(--color-state-warning);
  background: color-mix(in srgb, var(--color-state-warning) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-state-warning) 30%, transparent);
}
</style>
