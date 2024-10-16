<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import TopicsRenderer from '@/graph-designer/components/TopicsRenderer.vue'
import { type I18N } from '@/graph-designer/type_defs'
import { type Topic } from '@/graph-designer/components/type_defs'

const props = defineProps<{
  i18n: I18N
}>()

// Specs

const topics: Topic[] = [
  {
    ident: 'graph_lines',
    title: props.i18n.topics.graph_lines,
    elements: [
      { ident: 'metric', title: props.i18n.topics.metric },
      { ident: 'scalar', title: props.i18n.topics.scalar },
      { ident: 'constant', title: props.i18n.topics.constant }
    ]
  },
  {
    ident: 'graph_operations',
    title: props.i18n.topics.graph_operations,
    elements: [
      { ident: 'operations', title: props.i18n.topics.operations },
      { ident: 'transformation', title: props.i18n.topics.transformation }
    ]
  },
  {
    ident: 'graph_options',
    title: props.i18n.topics.graph_options,
    elements: [
      { ident: 'unit', title: props.i18n.topics.unit },
      { ident: 'vertical_range', title: props.i18n.topics.vertical_range },
      {
        ident: 'metrics_with_zero_values',
        title: props.i18n.topics.metrics_with_zero_values
      }
    ]
  }
]
</script>

<template>
  <TopicsRenderer :topics="topics"> </TopicsRenderer>
</template>
