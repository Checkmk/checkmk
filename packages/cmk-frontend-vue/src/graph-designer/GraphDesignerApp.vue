<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type GraphLines, type GraphOptions } from 'cmk-shared-typing/typescript/graph_designer'

import GraphDesigner from '@/graph-designer/private/GraphDesigner.vue'
import { graphRenderer } from '@/graph-designer/private/graph'

defineProps<{
  graph_id: string
  graph_lines: GraphLines
  graph_options: GraphOptions
  create_services_available: boolean
  graph_renderer?: typeof graphRenderer
}>()
</script>

<template>
  <GraphDesigner
    :graph_id="graph_id"
    :graph_lines="graph_lines"
    :graph_options="graph_options"
    :create_services_available="create_services_available"
    :graph_renderer="graph_renderer || graphRenderer"
  />
</template>
