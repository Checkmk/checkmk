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
import { type UnpackedArray } from '@/lib/typeUtils'
import { immediateWatch } from '@/lib/watch'

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
  (itemProps) => {
    let length: number | undefined
    Object.values(itemProps).forEach((value) => {
      if (length === undefined) {
        length = value.length
        return
      }
      if (length !== value.length) {
        throw new Error('All itemProps must have the same length')
      }
    })
    if (length === undefined) {
      throw new Error('itemProps must not be empty')
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
  <table v-show="localOrder.length > 0" ref="tableRef" class="valuespec_listof">
    <template v-for="dataIndex in localOrder" :key="dataIndex">
      <tr class="listof_element">
        <td class="vlof_buttons">
          <template v-if="props.draggable!!">
            <CmkButton
              variant="transparent"
              aria-label="Drag to reorder"
              :draggable="true"
              @dragstart="dragStart"
              @drag="dragging"
              @dragend="dragEnd"
            >
              <CmkIcon name="drag" size="small" style="pointer-events: none" />
            </CmkButton>
            <CmkSpace direction="vertical" />
          </template>
          <CmkButton variant="transparent" @click.prevent="() => removeElement(dataIndex)">
            <CmkIcon name="close" size="small" />
          </CmkButton>
        </td>
        <td class="vlof_content">
          <slot name="item-props" v-bind="{ index: dataIndex, ...getItemProps(dataIndex) }" />
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
.valuespec_listof {
  border-collapse: collapse;
  margin-bottom: var(--spacing);

  > tbody > .listof_element,
  > .listof_element {
    --button-padding-top: 4px;

    > .vlof_buttons,
    > .vlof_content {
      vertical-align: top;
      padding: var(--spacing) 0;
    }

    > .vlof_content {
      padding-top: calc(var(--spacing) - var(--button-padding-top));
      padding-left: 8px;
    }

    &:first-child > .vlof_buttons {
      padding-top: var(--button-padding-top);
    }

    &:first-child > .vlof_content {
      padding-top: 0;
    }

    &:last-child > .vlof_buttons,
    &:last-child > .vlof_content {
      padding-bottom: 0;
    }
  }
}

.vlof_buttons > * {
  display: flex;
}
</style>
