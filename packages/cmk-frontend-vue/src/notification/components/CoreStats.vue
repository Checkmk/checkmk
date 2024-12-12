<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import type { CoreStats } from 'cmk-shared-typing/typescript/notifications'

defineProps<{
  stats: CoreStats
}>()
</script>

<template>
  <div class="core_stats">
    <h3 class="table">{{ stats['i18n']['title'] }}</h3>
    <div class="content">
      <p v-if="stats['sites'].length === 0">
        <CmkIcon name="checkmark" size="small" />
        {{ stats['i18n']['ok_msg'] }}
      </p>
      <p v-else>
        <CmkIcon name="crit-problem" size="small" />
        {{ stats['i18n']['warning_msg'] }}
      </p>
      <div v-if="stats['sites']!.length !== 0" class="table">
        <table class="data even0">
          <thead>
            <tr class="data even0">
              <th>{{ stats['i18n']['sites_column_title'] }}</th>
              <th>{{ stats['i18n']['status_column_title'] }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in stats['sites']!" :key="index" class="data even0">
              <td>{{ item }}</td>
              <td>
                <CmkIcon name="crit-problem" size="small" />
                {{ stats['i18n']['disabled_msg'] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.core_stats {
  padding-top: var(--spacing);
  border: 1px solid var(--default-border-color);

  .content {
    padding: 0;

    > p {
      padding: var(--spacing-half);
    }
  }

  .table {
    margin-top: 0;

    tr {
      th {
        background-color: unset;
      }

      td {
        background-color: var(--default-table-th-color);
      }
    }
  }
}
</style>
