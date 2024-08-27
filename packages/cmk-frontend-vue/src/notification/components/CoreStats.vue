<script setup lang="ts">
import type { CoreStats } from '@/form/components/vue_formspec_components'

defineProps<{
  stats: CoreStats
}>()
</script>

<template>
  <div class="core_stats">
    <h3 class="table">{{ stats['i18n']['title'] }}</h3>
    <div class="content">
      <p v-if="stats['sites'].length == 0">
        <img class="checkmark" />
        {{ stats['i18n']['ok_msg'] }}
      </p>
      <p v-else>
        <img class="problem" />
        {{ stats['i18n']['warning_msg'] }}
      </p>
      <div v-if="stats['sites']!.length != 0" class="table">
        <table class="data even0">
          <tr class="data even0">
            <th>{{ stats['i18n']['sites_column_title'] }}</th>
            <th>{{ stats['i18n']['status_column_title'] }}</th>
          </tr>
          <tr v-for="(item, index) in stats['sites']!" :key="index" class="data even0">
            <td>{{ item }}</td>
            <td>
              <img class="problem" />
              {{ stats['i18n']['disabled_msg'] }}
            </td>
          </tr>
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

    :first-child {
      padding: var(--spacing-half);
    }

    img {
      width: 12px;
      align-content: center;
    }

    img.checkmark {
      content: var(--icon-checkmark);
      padding: 0px;
    }

    img.problem {
      content: var(--icon-crit-problem);
      padding: 0px;
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
