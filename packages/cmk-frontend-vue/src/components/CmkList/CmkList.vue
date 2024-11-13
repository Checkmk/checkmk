<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup generic="ItemsProps extends Record<string, unknown[]>" lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import useDragging from '@/lib/useDragging'
import { immediateWatch } from '@/lib/watch'
import { type UnpackedArray } from '@/lib/typeUtils'
import CmkListItem from './CmkListItem.vue'

type ItemProps = { [K in keyof ItemsProps]: UnpackedArray<ItemsProps[K]> }

const props = defineProps<{
  itemsProps: ItemsProps
  onAdd: (index: number) => void
  onDelete: (index: number) => void
  i18n: {
    addElementLabel: string
  }
  draggable?: { onReorder: (order: number[]) => void } | null
}>()

const localOrder = ref<number[]>([])

immediateWatch(
  () => props.itemsProps,
  (itemsProps) => {
    let length: number | undefined
    Object.values(itemsProps).forEach((value) => {
      if (length === undefined) {
        length = value.length
        return
      }
      if (length !== value.length) {
        throw new Error('All itemsProps must have the same length')
      }
    })
    if (length === undefined) {
      throw new Error('itemsProps must not be empty')
    }
    localOrder.value = Array.from({ length }, (_, i) => i)
  }
)

const { tableRef, dragStart, dragEnd: _dragEnd, dragging: _dragging } = useDragging()

function dragging(event: DragEvent) {
  const dragReturn = _dragging(event)
  if (dragReturn === null) {
    return
  }
  const movedEntry = localOrder.value.splice(dragReturn.draggedIndex, 1)[0]!
  localOrder.value.splice(dragReturn.targetIndex, 0, movedEntry)
}

function dragEnd(event: DragEvent) {
  _dragEnd(event)
  props.draggable?.onReorder(localOrder.value)
}

function removeElement(dataIndex: number) {
  props.onDelete(dataIndex)
  const localIndex = localOrder.value.indexOf(dataIndex)
  localOrder.value = localOrder.value.map((_dataIndex, _localIndex) =>
    _localIndex > localIndex ? _dataIndex - 1 : _dataIndex
  )
  localOrder.value.splice(localIndex, 1)
}

function addElement() {
  props.onAdd(localOrder.value.length)
  localOrder.value.push(localOrder.value.length)
}

function getItemProps(dataIndex: number) {
  return Object.entries(props.itemsProps).reduce((singleItemProps, [key, value]) => {
    singleItemProps[key as keyof ItemProps] = value[dataIndex] as ItemProps[keyof ItemsProps]
    return singleItemProps
  }, {} as ItemProps)
}
</script>

<template>
  <table v-show="localOrder.length > 0" ref="tableRef" class="cmk_list__table">
    <template v-for="(dataIndex, listIndex) in localOrder" :key="dataIndex">
      <tr>
        <td>
          <CmkListItem
            :remove-element="() => removeElement(dataIndex)"
            :style="listIndex === 0 ? 'first' : listIndex === localOrder.length - 1 ? 'last' : null"
            :draggable="draggable ? { dragStart, dragEnd, dragging } : null"
          >
            <slot name="item-props" v-bind="{ index: dataIndex, ...getItemProps(dataIndex) }" />
          </CmkListItem>
        </td>
      </tr>
    </template>
  </table>
  <CmkButton variant="minimal" size="small" @click.prevent="addElement">
    <CmkIcon name="plus" />
    <CmkSpace size="small" />
    {{ props.i18n.addElementLabel }}
  </CmkButton>
</template>

<style scoped>
.cmk_list__table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: var(--spacing);
}
</style>
