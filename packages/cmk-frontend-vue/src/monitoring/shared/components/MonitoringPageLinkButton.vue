<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type MonitoringPageLinkButton } from 'cmk-shared-typing/typescript/monitoring/page_link_button'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'

import { useTeleportPlacement } from '@/monitoring/shared/components/teleportPlacement'

const props = defineProps<MonitoringPageLinkButton>()

const { target, isDefault } = useTeleportPlacement('.page_state', () => props.teleport_target)

function navigate(): void {
  window.location.href = props.url
}
</script>

<template>
  <Teleport defer :to="target">
    <CmkButton
      class="monitoring-page-link-button"
      :class="
        isDefault
          ? 'monitoring-page-link-button--page-state'
          : 'monitoring-page-link-button--inline'
      "
      :size="isDefault ? 'medium' : 'small'"
      @click="navigate"
    >
      <CmkMultitoneIcon
        name="experiment"
        primary-color="font"
        secondary-color="hosts"
        size="large"
        class="monitoring-page-link-button__icon"
      />
      {{ title }}
    </CmkButton>
  </Teleport>
</template>

<style scoped>
.monitoring-page-link-button {
  white-space: nowrap;
}

.monitoring-page-link-button--page-state {
  position: absolute;
  right: 50px;
}

.monitoring-page-link-button--inline {
  margin-left: var(--dimension-4);
  vertical-align: middle;
}

.monitoring-page-link-button__icon {
  margin-right: var(--dimension-3);
}
</style>
