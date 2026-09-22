<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringPageLinkButton } from 'cmk-shared-typing/typescript/monitoring/page_link_button'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'

import { useTeleportPlacement } from '@/monitoring/shared/components/teleportPlacement'

const props = defineProps<MonitoringPageLinkButton>()

const { target, isDefault } = useTeleportPlacement('.titlebar', () => props.teleport_target)

function navigate(): void {
  window.location.href = props.url
}
</script>

<template>
  <Teleport defer :to="target">
    <CmkButton
      class="monitoring-legacy-view-button"
      :class="
        isDefault
          ? 'monitoring-legacy-view-button--titlebar'
          : 'monitoring-legacy-view-button--inline'
      "
      :size="isDefault ? 'medium' : 'small'"
      @click="navigate"
    >
      <CmkIcon name="back" class="monitoring-legacy-view-button__icon" />
      {{ title }}
    </CmkButton>
  </Teleport>
</template>

<style scoped>
.monitoring-legacy-view-button {
  white-space: nowrap;
}

.monitoring-legacy-view-button--titlebar {
  right: var(--dimension-4);
  align-self: center;
}

.monitoring-legacy-view-button--inline {
  margin-left: var(--dimension-4);
  vertical-align: middle;
}

.monitoring-legacy-view-button__icon {
  margin-right: var(--dimension-3);
}
</style>
