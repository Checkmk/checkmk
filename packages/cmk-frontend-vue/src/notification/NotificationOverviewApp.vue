<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as NotificationTypes from 'cmk-shared-typing/typescript/notifications'
import NotificationStats from '@/notification/components/NotificationStats.vue'
import NotificationCoreStats from '@/notification/components/NotificationCoreStats.vue'
import NotificationRules from '@/notification/components/NotificationRules.vue'
import NotificationFallbackWarning from '@/notification/components/NotificationFallbackWarning.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import { ref, onMounted } from 'vue'

const props = defineProps<{
  overview_title_i18n: string
  fallback_warning: NotificationTypes.NotificationFallbackWarning | null
  notification_stats: NotificationTypes.NotificationStats
  core_stats: NotificationTypes.NotificationCoreStats
  rule_sections: NotificationTypes.RuleSection[]
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
  <NotificationFallbackWarning
    v-if="fallback_warning"
    :properties="fallback_warning"
  ></NotificationFallbackWarning>
  <h3 class="table overview_header" @click.prevent="toggleContent()">
    <CmkIconButton name="tree_closed" size="xsmall" :rotate="isContentVisible ? 90 : 0" />
    {{ overview_title_i18n }}
  </h3>
  <div v-if="isContentVisible" class="overview_container">
    <div class="stats_container">
      <NotificationStats
        :notification_stats="notification_stats"
        :toggle_content="toggleContent"
      ></NotificationStats>
      <NotificationCoreStats :stats="core_stats"></NotificationCoreStats>
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
.stats_container {
  max-width: min-content;
}
.button {
  height: 8px;
  width: 8px;
  padding: 0px 8px;
}
</style>
