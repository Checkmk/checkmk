<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Component } from 'vue'

import DashboardContentEmbeddedView from './DashboardContentEmbeddedView.vue'
import DashboardContentFigure from './DashboardContentFigure.vue'
import DashboardContentGraph from './DashboardContentGraph.vue'
import DashboardContentIFrame from './DashboardContentIFrame.vue'
import DashboardContentLinkedView from './DashboardContentLinkedView.vue'
import DashboardContentNtop from './DashboardContentNtop.vue'
import DashboardContentSidebarElement from './DashboardContentSidebarElement.vue'
import DashboardContentStaticText from './DashboardContentStaticText.vue'
import DashboardContentTopList from './DashboardContentTopList.vue'
import DashboardContentUserMessages from './DashboardContentUserMessages.vue'
import { CONTENT_FIGURE_TYPES, GRAPH_TYPES, NTOP_TYPES } from './types.ts'
</script>

<script setup lang="ts">
import type { WidgetContent } from '@/dashboard/types/widget'

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
    case contentType === 'top_list':
      return DashboardContentTopList
    case contentType === 'user_messages':
      return DashboardContentUserMessages
    case contentType === 'sidebar_element':
      return DashboardContentSidebarElement
    case CONTENT_FIGURE_TYPES.includes(contentType):
      return DashboardContentFigure
    case GRAPH_TYPES.includes(contentType):
      return DashboardContentGraph
    case NTOP_TYPES.includes(contentType):
      return DashboardContentNtop
    default:
      throw new Error(`Unknown dashboard content type: ${contentType}`)
  }
}

function componentKey(content: WidgetContent): string {
  if (content.type === 'alert_timeline' || content.type === 'notification_timeline') {
    return `${content.type}-${content.render_mode.type}`
  }
  return content.type
}
</script>

<template>
  <component
    :is="contentTypeToComponent(content.type)"
    :key="componentKey(content)"
    :widget_id="widget_id"
    :general_settings="general_settings"
    :content="content"
    :effective-title="effectiveTitle"
    :effective_filter_context="effective_filter_context"
    :dashboard-key="dashboardKey"
    :is-preview="isPreview"
  />
</template>
