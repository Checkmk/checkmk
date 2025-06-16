<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type GraphLines,
  type GraphOptions,
  type I18N
} from 'cmk-shared-typing/typescript/graph_designer'
import { graphRenderer } from '@/graph-designer/graph'
import GraphDesigner from '@/graph-designer/GraphDesigner.vue'

defineProps<{
  graph_id: string
  graph_lines: GraphLines
  graph_options: GraphOptions
  i18n: I18N
}>()
</script>

<template>
  <GraphDesigner
    :graph_id="graph_id"
    :graph_lines="graph_lines"
    :graph_options="graph_options"
    :i18n="i18n"
    :graph_renderer="graphRenderer"
  />
</template>
