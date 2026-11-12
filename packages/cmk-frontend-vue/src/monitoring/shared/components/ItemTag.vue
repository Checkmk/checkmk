<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTag, {
  type CmkTagAction,
  type Sizes,
  type Spacings
} from 'cmk-ui-library/components/CmkTag.vue'
import { computed } from 'vue'

import {
  type ItemAction,
  type LabelCellItem,
  labelItemContent,
  labelItemText,
  labelItemValue
} from './cell/labelCellItem'

const props = defineProps<{
  item: LabelCellItem
  size?: Sizes | undefined
  spacing?: Spacings | undefined
  action?: ItemAction | undefined
}>()

const emit = defineEmits<{ select: [item: LabelCellItem] }>()

const tagAction = computed((): CmkTagAction | undefined => {
  if (props.action === undefined) {
    return undefined
  }
  const href = props.action.href?.(props.item)
  return href === undefined ? { type: 'button' } : { type: 'link', href, target: '_top' }
})

const title = computed(() =>
  props.action ? props.action.title(props.item) : labelItemText(props.item)
)

function select(): void {
  if (tagAction.value?.type === 'button') {
    emit('select', props.item)
  }
}
</script>

<template>
  <CmkTag
    :size="size"
    :spacing="spacing"
    :variant="item.variant ?? 'fill'"
    :color="item.color ?? 'default'"
    :content="labelItemContent(item)"
    :value="labelItemValue(item)"
    :action="tagAction"
    :title="title"
    @click="select"
  />
</template>
