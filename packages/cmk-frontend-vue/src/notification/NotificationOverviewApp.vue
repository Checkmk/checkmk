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
} from 'cmk-shared-typing/typescript/notifications'
import NotificationStatsComponent from '@/notification/components/NotificationStats.vue'
import CoreStatistics from '@/notification/components/CoreStats.vue'
import NotificationRules from '@/notification/components/NotificationRules.vue'
import FallbackWarningComponent from '@/notification/components/FallbackWarning.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import { ref, onMounted } from 'vue'

const props = defineProps<{
  overview_title_i18n: string
  fallback_warning: FallbackWarning | null
  notification_stats: NotificationStats
  core_stats: CoreStats
  rule_sections: RuleSection[]
  user_id: string
}>()
const isContentVisible = ref(true)
const localStorageKey = (userId: string) => `${userId}-notificationOverviewVisibility`

function hideContent() {
  isContentVisible.value = false
  localStorage.setItem(localStorageKey(props.user_id), 'hidden')
}

function showContent() {
  isContentVisible.value = true
  localStorage.removeItem(localStorageKey(props.user_id))
}

onMounted(() => {
  const savedState = localStorage.getItem(localStorageKey(props.user_id))
  if (savedState === 'hidden') {
    isContentVisible.value = false
  }
})

function toggleContent() {
  return isContentVisible.value ? hideContent() : showContent()
}
</script>

<template>
  <FallbackWarningComponent
    v-if="fallback_warning"
    :properties="fallback_warning"
    :user_id="user_id"
  ></FallbackWarningComponent>
  <h3 class="table overview_header" @click.prevent="toggleContent()">
    <CmkIconButton name="tree_closed" size="xsmall" :rotate="isContentVisible ? 90 : 0" />
    {{ overview_title_i18n }}
  </h3>
  <div v-if="isContentVisible" class="overview_container">
    <div class="stats_container">
      <NotificationStatsComponent
        :notification_stats="notification_stats"
        :toggle_content="toggleContent"
      ></NotificationStatsComponent>
      <CoreStatistics :stats="core_stats"></CoreStatistics>
    </div>
    <NotificationRules :rule_sections="rule_sections" :collapse="toggleContent"></NotificationRules>
  </div>
</template>

<style scoped>
.overview_container {
  display: flex;
  margin-bottom: 24px;
}
.h3 {
  background-color: none;
}
.overview_header {
  margin: 0 0 12px 0;
  cursor: pointer;
}
.button {
  height: 8px;
  width: 8px;
  padding: 0px 8px;
}
</style>
