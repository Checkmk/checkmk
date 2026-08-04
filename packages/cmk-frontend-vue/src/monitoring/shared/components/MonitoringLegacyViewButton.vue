<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringPageLinkButton } from 'cmk-shared-typing/typescript/monitoring/page_link_button'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'

const props = defineProps<MonitoringPageLinkButton>()

function navigate(): void {
  window.location.href = props.url
}
</script>

<template>
  <Teleport defer to=".titlebar">
    <CmkButton class="monitoring-legacy-view-button" @click="navigate">
      <CmkIcon name="back" class="monitoring-legacy-view-button__icon" />
      {{ title }}
    </CmkButton>
  </Teleport>
</template>

<style scoped>
.monitoring-legacy-view-button {
  right: var(--dimension-4);
  white-space: nowrap;
  align-self: center;
}

.monitoring-legacy-view-button__icon {
  margin-right: var(--dimension-3);
}
</style>
