<script setup lang="ts">
import QuickSetup from '@/components/quick-setup/QuickSetup.vue'
import { type QuickSetupAppProperties } from '@/quick_setup_types'

defineProps<QuickSetupAppProperties>()
</script>

<template>
  <QuickSetup :quick_setup_id="quick_setup_id" />
</template>

<style lang="scss" scoped></style>
