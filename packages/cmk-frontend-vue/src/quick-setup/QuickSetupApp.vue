<script setup lang="ts">
import QuickSetup from '@/quick-setup/QuickSetup.vue'

export interface QuickSetupAppProperties {
  /** @property {string} quick_setup_id - The quick setup id  */
  quick_setup_id: string
}

defineProps<QuickSetupAppProperties>()
</script>

<template>
  <QuickSetup :quick_setup_id="quick_setup_id" />
</template>

<style lang="scss" scoped></style>
