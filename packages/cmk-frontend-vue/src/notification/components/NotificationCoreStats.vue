<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import type { NotificationCoreStats } from 'cmk-shared-typing/typescript/notifications'

defineProps<{
  stats: NotificationCoreStats
}>()
</script>

<template>
  <div class="notification-core-stats">
    <h3>{{ stats['i18n']['title'] }}</h3>
    <div class="notification-core-stats__content">
      <p v-if="stats['sites'].length === 0">
        <CmkIcon name="checkmark" size="small" />
        {{ stats['i18n']['ok_msg'] }}
      </p>
      <p v-else>
        <CmkIcon name="crit-problem" size="small" />
        {{ stats['i18n']['warning_msg'] }}
      </p>
      <table v-if="stats['sites']!.length !== 0" class="notification-core-stats__table data even0">
        <thead>
          <tr class="data even0">
            <th>{{ stats['i18n']['sites_column_title'] }}</th>
            <th>{{ stats['i18n']['status_column_title'] }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in stats['sites']!" :key="index" class="data even0">
            <td :title="item">{{ item }}</td>
            <td>
              <CmkIcon name="crit-problem" size="small" />
              {{ stats['i18n']['disabled_msg'] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.notification-core-stats {
  padding-top: var(--spacing);
  border: 1px solid var(--default-border-color);

  h3 {
    font-size: var(--font-size-normal);
  }

  .notification-core-stats__content {
    padding: 0;

    > p {
      padding: var(--spacing-half);
    }
  }

  .notification-core-stats__table {
    thead,
    tbody tr {
      display: table;
      width: 100%;
      table-layout: fixed;
    }

    tbody {
      display: block;
      max-height: 120px;
      overflow-y: auto;
    }

    td:first-child {
      max-width: 50%;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }

    td:last-child {
      white-space: nowrap;
      width: 50%;
    }
  }
}
</style>
