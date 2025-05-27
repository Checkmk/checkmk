<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import type { NotificationStats } from 'cmk-shared-typing/typescript/notifications'

defineProps<{
  notification_stats: NotificationStats
}>()
</script>

<template>
  <div class="notification-stats">
    <div class="notification-stats__section">
      <h3 class="table">{{ notification_stats['i18n']['failed_notifications'] }}</h3>
      <div class="notification-stats__content content">
        <p
          v-if="notification_stats['num_failed_notifications'] === 0"
          class="notification-stats__count"
        >
          <CmkIcon name="checkmark" size="xlarge" />
          {{ notification_stats['num_failed_notifications'] }}
        </p>
        <p v-else class="notification-stats__count">
          <CmkIcon name="crit-problem" size="xlarge" />
          {{ notification_stats['num_failed_notifications'] }}
        </p>
        <a
          v-if="notification_stats['num_failed_notifications'] !== 0"
          :href="notification_stats['failed_notification_link']"
          >{{ notification_stats['i18n']['failed_notifications_link_title'] }}</a
        >
      </div>
    </div>
    <div class="notification-stats__section">
      <h3 class="table">{{ notification_stats['i18n']['sent_notifications'] }}</h3>
      <div class="notification-stats__content content">
        <p class="notification-stats__count">
          {{ notification_stats['num_sent_notifications'] }}
        </p>
        <a
          v-if="notification_stats['num_sent_notifications'] !== 0"
          :href="notification_stats['sent_notification_link']"
          >{{ notification_stats['i18n']['sent_notifications_link_title'] }}</a
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.notification-stats {
  height: 134px;
  width: 355px;
  display: flex;
  flex-grow: 2;

  .notification-stats__section {
    margin: 0;
    flex-grow: 1;
    border: 1px solid var(--default-border-color);

    &:first-child {
      margin-right: 4px;
    }

    .table {
      margin-top: 0;
    }
  }

  .notification-stats__content {
    height: 113px;
    align-content: center;
    text-align: center;

    .notification-stats__count {
      font-size: 24px;
      margin-top: var(--spacing-half);
      margin-bottom: var(--spacing-half);
    }
  }
}
</style>
