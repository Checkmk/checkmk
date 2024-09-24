<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import NotificationRules from '@/notification/components/NotificationRules.vue'
import type { RuleSection } from '@/form/components/vue_formspec_components'

defineProps<{
  notification_parameters: RuleSection[]
}>()
</script>

<template>
  <NotificationRules :rule_sections="notification_parameters"></NotificationRules>
</template>

<style scoped>
.overview_container {
  display: flex;
  margin-bottom: 24px;
}
</style>
