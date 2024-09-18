<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  NotificationStats,
  CoreStats,
  RuleSection,
  FallbackWarning
} from '@/form/components/vue_formspec_components'
import NotificationStatsComponent from '@/notification/components/NotificationStats.vue'
import CoreStatistics from '@/notification/components/CoreStats.vue'
import NotificationRules from '@/notification/components/NotificationRules.vue'
import FallbackWarningComponent from '@/notification/components/FallbackWarning.vue'

defineProps<{
  fallback_warning: FallbackWarning | null
  notification_stats: NotificationStats
  core_stats: CoreStats
  rule_sections: RuleSection[]
}>()
</script>

<template>
  <FallbackWarningComponent
    v-if="fallback_warning"
    :properties="fallback_warning"
  ></FallbackWarningComponent>
  <div class="overview_container">
    <div class="stats_container">
      <NotificationStatsComponent
        :notification_stats="notification_stats"
      ></NotificationStatsComponent>
      <CoreStatistics :stats="core_stats"></CoreStatistics>
    </div>
    <NotificationRules :rule_sections="rule_sections"></NotificationRules>
  </div>
</template>

<style scoped>
.overview_container {
  display: flex;
  margin-bottom: 24px;
}
</style>
