<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ListWidgetProps } from './widget_types'
import { getGetWidget } from '@/quick-setup/components/quick-setup/utils'
const getWidget = getGetWidget()

const props = defineProps<ListWidgetProps>()
const ordered = props.list_type === 'ordered'

const getBullet = (): string => {
  if (!props.list_type) {
    return 'none'
  } else if (['bullet', 'ordered'].includes(props.list_type)) {
    return 'revert' // apply the default list-style-type of ol/ul html tags
  } else if (props.list_type === 'check') {
    return "'✓ '"
  }

  return `'${props.list_type} '`
}
</script>

<template>
  <component :is="ordered ? 'ol' : 'ul'" class="qs-list-widget">
    <li v-for="({ widget_type, ...widget_props }, idx) in items" :key="idx">
      <component :is="getWidget(widget_type)" v-bind="widget_props" />
    </li>
  </component>
</template>

<style scoped>
.qs-list-widget {
  margin-bottom: var(--spacing);
  padding-left: 0px;
  line-height: 18px;
  list-style-type: v-bind('getBullet()');
  list-style-position: inside;
}
</style>
