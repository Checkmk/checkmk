<script setup lang="ts">
import type {
  NotificationStats,
  CoreStats,
  RuleSection
} from '@/form/components/vue_formspec_components'
import NotificationStatsComponent from '@/notification/components/NotificationStats.vue'
import CoreStatistics from '@/notification/components/CoreStats.vue'
import NotificationRules from '@/notification/components/NotificationRules.vue'

defineProps<{
  notification_stats: NotificationStats
  core_stats: CoreStats
  rule_sections: RuleSection[]
}>()
</script>

<template>
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
