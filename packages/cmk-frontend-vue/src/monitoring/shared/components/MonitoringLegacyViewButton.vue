<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'

import { useIsDefaultPlacement } from '@/monitoring/shared/components/teleportPlacement'

const props = defineProps<{ title: string; url: string }>()

const isDefault = useIsDefaultPlacement()

function navigate(): void {
  window.location.href = props.url
}
</script>

<template>
  <CmkButton
    class="monitoring-legacy-view-button"
    :size="isDefault ? 'medium' : 'small'"
    :title="title"
    @click="navigate"
  >
    <CmkIcon name="back" class="monitoring-legacy-view-button__icon" />
    <span class="monitoring-legacy-view-button__label">{{ title }}</span>
  </CmkButton>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.monitoring-legacy-view-button {
  position: relative;
  white-space: nowrap;
}

.monitoring-legacy-view-button__icon {
  margin-right: var(--dimension-3);
}

/* Icon only when the title row is narrower than L (see MonitoringHeaderActions), the title stays
   available as tooltip. */
@include bp.container-below(l) {
  .monitoring-legacy-view-button__label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .monitoring-legacy-view-button__icon {
    margin-right: 0;
  }
}
</style>
