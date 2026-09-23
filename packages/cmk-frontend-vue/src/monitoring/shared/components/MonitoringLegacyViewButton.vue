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
    @click="navigate"
  >
    <CmkIcon name="back" class="monitoring-legacy-view-button__icon" />
    {{ title }}
  </CmkButton>
</template>

<style scoped>
.monitoring-legacy-view-button {
  white-space: nowrap;
}

.monitoring-legacy-view-button__icon {
  margin-right: var(--dimension-3);
}
</style>
