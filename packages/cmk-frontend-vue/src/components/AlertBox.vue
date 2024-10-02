<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

type AlertType = 'error' | 'warning' | 'success' | 'info'

interface AlertBoxProps {
  variant?: AlertType
}

const props = withDefaults(defineProps<AlertBoxProps>(), {
  variant: 'info'
})

const alertIcon = computed(() => {
  const url = 'themes/facelift/images'
  switch (props.variant) {
    case 'error':
      return `${url}/icon_alert_crit.svg`
    case 'warning':
      return `${url}/icon_alert_warn.png`
    case 'success':
      return `${url}/icon_alert_up.png`
    default:
      return `${url}/icon_about_checkmk.svg`
  }
})

/* TODO: change these classes to proper variants */
const alertClass = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'error qs-alert-box'
    case 'warning':
      return 'warning qs-alert-box'
    case 'success':
      return 'success qs-alert-box'
    default:
      return 'message qs-alert-box'
  }
})
</script>

<template>
  <div :class="alertClass" :style="{ maxWidth: 'fit-content' }">
    <img :src="alertIcon" />
    <slot />
  </div>
</template>

<style scoped>
/* TODO: try to unify this component with component FormValidation. the styling should be the same
         for all error messages, so the same base component should be used. */
.qs-alert-box {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  margin: 12px 0;

  img {
    height: 18px;
    margin-right: 12px;
  }

  &.error {
    color: var(--font-color);
    background-color: var(--error-msg-bg-color);
  }
}
</style>
