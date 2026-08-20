<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import {
  type MetricAttribute,
  attributeKindColumnLabel,
  sortedAttributes
} from './metricAttributes'

const props = defineProps<{
  attributes: MetricAttribute[]
}>()

const { _t } = usei18n()

const rows = computed(() => sortedAttributes(props.attributes))
</script>

<template>
  <table class="graphing-metric-attributes-table">
    <colgroup>
      <col class="graphing-metric-attributes-table__col--name" />
      <col />
      <col class="graphing-metric-attributes-table__col--kind" />
    </colgroup>
    <thead>
      <tr>
        <th>{{ _t('Attribute name') }}</th>
        <th>{{ _t('Attribute value') }}</th>
        <th>{{ _t('Attribute kind') }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="attribute in rows" :key="`${attribute.kind}:${attribute.name}`">
        <td>{{ attribute.name }}</td>
        <td class="graphing-metric-attributes-table__value">{{ attribute.value }}</td>
        <td>{{ attributeKindColumnLabel(attribute.kind) }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.graphing-metric-attributes-table {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;
  font-size: var(--font-size-normal);
  text-align: left;

  th,
  td {
    padding: var(--dimension-2) var(--dimension-4);
    vertical-align: top;
  }

  th {
    font-weight: var(--font-weight-bold);
  }

  tbody tr:hover {
    background: var(--graphing-attributes-row-hover);
  }
}

.graphing-metric-attributes-table__col--name {
  width: 20%;
}

.graphing-metric-attributes-table__col--kind {
  width: 15%;
}

/* Values can be long ids; wrapping keeps them out of the neighbouring columns. */
.graphing-metric-attributes-table__value {
  overflow-wrap: anywhere;
}

body[data-theme='facelift'] .graphing-metric-attributes-table {
  --graphing-attributes-row-hover: var(--ux-theme-4);
}

body[data-theme='modern-dark'] .graphing-metric-attributes-table {
  --graphing-attributes-row-hover: var(--color-white-10);
}
</style>
