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
      return `${url}/icon_alert_crit.png`
    case 'warning':
      return `${url}/icon_alert_warn.png`
    case 'success':
      return `${url}/icon_alert_up.png`
    default:
      return `${url}/icon_about_checkmk.svg`
  }
})

const alertClass = computed(() => {
  switch (props.variant) {
    case 'error':
      return 'error AlertBox'
    case 'warning':
      return 'warning AlertBox'
    case 'success':
      return 'success AlertBox'
    default:
      return 'message AlertBox'
  }
})
</script>

<template>
  <div :class="alertClass" :style="{ maxWidth: 'fit-content' }">
    <img class="loading" :height="32" :src="alertIcon" />
    <slot />
  </div>
</template>

<style scoped>
.AlertBox {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.AlertBox img {
  margin-right: 1rem;
}
</style>
