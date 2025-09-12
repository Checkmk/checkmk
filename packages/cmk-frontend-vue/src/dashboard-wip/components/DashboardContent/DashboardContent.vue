<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Component } from 'vue'

import DashboardContentEmbeddedView from './DashboardContentEmbeddedView.vue'
import DashboardContentFigure from './DashboardContentFigure.vue'
import DashboardContentGraph from './DashboardContentGraph.vue'
import DashboardContentIFrame from './DashboardContentIFrame.vue'
import DashboardContentLinkedView from './DashboardContentLinkedView.vue'
import DashboardContentStaticText from './DashboardContentStaticText.vue'
import DashboardContentUserMessages from './DashboardContentUserMessages.vue'
import { CONTENT_FIGURE_TYPES, GRAPH_TYPES } from './types.ts'
import type { ContentProps } from './types.ts'

defineProps<ContentProps>()

function contentTypeToComponent(contentType: string): Component {
  switch (true) {
    case contentType === 'url':
      return DashboardContentIFrame
    case contentType === 'linked_view':
      return DashboardContentLinkedView
    case contentType === 'embedded_view':
      return DashboardContentEmbeddedView
    case contentType === 'static_text':
      return DashboardContentStaticText
    case contentType === 'user_messages':
      return DashboardContentUserMessages
    case CONTENT_FIGURE_TYPES.includes(contentType):
      return DashboardContentFigure
    case GRAPH_TYPES.includes(contentType):
      return DashboardContentGraph
    default:
      throw new Error(`Unknown dashboard content type: ${contentType}`)
  }
}
</script>

<template>
  <component
    :is="contentTypeToComponent(content.type)"
    :widget-id="widgetId"
    :general-settings="generalSettings"
    :content="content"
    :effective-filter-context="effectiveFilterContext"
    :dashboard-name="dashboardName"
  />
</template>
