<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup generic="ItemsProps extends Record<string, unknown[]>" lang="ts">
import { ref } from 'vue'

import CmkSpace from '@/components/CmkSpace.vue'
import useDragging from '@/lib/useDragging'
import { immediateWatch } from '@/lib/watch'
import { type UnpackedArray } from '@/lib/typeUtils'
import CmkListItem from './CmkListItem.vue'
import CmkListAddButton from './CmkListAddButton.vue'

type ItemProps = { [K in keyof ItemsProps]: UnpackedArray<ItemsProps[K]> }

const {
  orientation = 'vertical',
  showAddButton = true,
  ...props
} = defineProps<{
  itemsProps: ItemsProps
  onAdd: (index: number) => boolean | void
  onDelete: (index: number) => boolean | void
  i18n: {
    addElementLabel: string
  }
  showAddButton?: boolean
  draggable?: { onReorder: (order: number[]) => void } | null
  orientation?: 'vertical' | 'horizontal'
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
  if (props.onDelete(dataIndex) === false) {
    return
  }
  const localIndex = localOrder.value.indexOf(dataIndex)
  localOrder.value = localOrder.value.map((_dataIndex, _localIndex) =>
    _localIndex > localIndex ? _dataIndex - 1 : _dataIndex
  )
  localOrder.value.splice(localIndex, 1)
}

function addElement() {
  if (props.onAdd(localOrder.value.length) === false) {
    return
  }
  localOrder.value.push(localOrder.value.length)
}

function getItemProps(dataIndex: number) {
  return Object.entries(props.itemsProps).reduce((singleItemProps, [key, value]) => {
    singleItemProps[key as keyof ItemProps] = value[dataIndex] as ItemProps[keyof ItemsProps]
    return singleItemProps
  }, {} as ItemProps)
}

function getStyle(index: number, length: number) {
  return index === 0 ? 'first' : index === length - 1 ? 'last' : null
}
</script>

<template>
  <div :class="{ cmk_list__container: true, horizontal: orientation === 'horizontal' }">
    <table ref="tableRef" class="cmk_list__table">
      <template v-if="orientation === 'vertical'">
        <tr v-for="(dataIndex, listIndex) in localOrder" :key="dataIndex">
          <td>
            <CmkListItem
              :remove-element="() => removeElement(dataIndex)"
              :style="getStyle(listIndex, localOrder.length)"
              :draggable="draggable ? { dragStart, dragEnd, dragging } : null"
            >
              <slot name="item-props" v-bind="{ index: dataIndex, ...getItemProps(dataIndex) }" />
            </CmkListItem>
          </td>
        </tr>
      </template>
      <template v-else>
        <tr>
          <td v-for="(dataIndex, listIndex) in localOrder" :key="dataIndex">
            <CmkListItem :button-padding="'8px'" :remove-element="() => removeElement(dataIndex)">
              <slot name="item-props" v-bind="{ index: dataIndex, ...getItemProps(dataIndex) }" />
              <CmkSpace direction="horizontal" />
              <CmkSpace v-if="listIndex !== localOrder.length - 1" direction="horizontal" />
            </CmkListItem>
          </td>
          <td>
            <CmkListAddButton
              v-if="showAddButton"
              class="cmk_list__add_button"
              :add-element-label="props.i18n.addElementLabel"
              :add-element="addElement"
            />
          </td>
        </tr>
      </template>
    </table>
    <CmkListAddButton
      v-if="showAddButton && orientation === 'vertical'"
      class="cmk_list__add_button"
      :add-element-label="props.i18n.addElementLabel"
      :add-element="addElement"
    />
  </div>
</template>

<style scoped>
.cmk_list__container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.cmk_list__table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: var(--spacing);

  td {
    height: 100%;
  }
}
.cmk_list__add_button {
  flex-shrink: 0;
}
.cmk_list__container.horizontal {
  flex-direction: row;

  .cmk_list__table {
    white-space: normal;
    margin-bottom: 0;
  }
  .cmk_list__table td {
    display: inline-block;
    vertical-align: top;
  }
  .cmk_list__add_button {
    padding-top: 4px;
  }
}
</style>
