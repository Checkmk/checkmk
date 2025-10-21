<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkIcon from '@/components/CmkIcon'

type AlertType = 'error' | 'warning' | 'success' | 'info'

interface CmkAlertBoxProps {
  variant?: AlertType
}

const props = withDefaults(defineProps<CmkAlertBoxProps>(), {
  variant: 'info'
})

const alertIconName = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'alert-crit'
    case 'warning':
      return 'alert-warn'
    case 'success':
      return 'alert-up'
    default:
      return 'about-checkmk'
  }
})

/* TODO: change these classes to proper variants */
const alertClass = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    case 'success':
      return 'success'
    default:
      return 'message'
  }
})
</script>

<template>
  <div class="cmk-alert-box" :class="alertClass">
    <CmkIcon :name="alertIconName" variant="inline" size="large" />
    <div class="content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* TODO: try to unify this component with component FormValidation. the styling should be the same
         for all error messages, so the same base component should be used. */
.cmk-alert-box {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  margin: 12px 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & > .content {
    margin-left: 7px;
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.error {
    color: var(--font-color);
    background-color: var(--error-msg-bg-color);
  }
}
</style>
