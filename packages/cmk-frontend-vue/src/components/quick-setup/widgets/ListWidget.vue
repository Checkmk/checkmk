<script setup lang="ts">
import { type ListWidgetProps } from './widget_types'
import { getWidget } from './utils'

const props = defineProps<ListWidgetProps>()
const ordered = props.list_type === 'ordered'
const is_custom_bullet = !['bullet', 'ordered'].includes(props?.list_type || '')

const getBullet = (): string => {
  if (!props.list_type) {
    return 'none'
  } else if (props.list_type === 'bullet') {
    return 'disc'
  } else if (props.list_type === 'major tom') {
    return "'🚀'"
  } else if (props.list_type === 'check') {
    return "'✓'"
  }

  return `'${props.list_type}'`
}
</script>

<template>
  <component :is="ordered ? 'ol' : 'ul'" :class="{ custom_bullet: is_custom_bullet }">
    <li v-for="({ widget_type, ...widget_props }, idx) in items" :key="idx">
      <component :is="getWidget(widget_type)" v-bind="widget_props" />
    </li>
  </component>
</template>

<style scoped>
.custom_bullet {
  list-style-type: v-bind('getBullet()');
}
</style>
