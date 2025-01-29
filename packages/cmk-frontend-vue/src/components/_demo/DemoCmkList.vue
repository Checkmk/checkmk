<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkList from '@/components/CmkList'
import { ref, type Ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

function setupList(): {
  data: Ref<string[]>
  addElement: () => boolean
  deleteElement: (index: number) => boolean
  reorderElements: (order: number[]) => void
} {
  const data = ref(['element 1', 'element 2', 'element 3'])

  function addElement() {
    data.value.push('new element')
    return true
  }

  function deleteElement(index: number) {
    data.value.splice(index, 1)
    return true
  }

  function reorderElements(order: number[]) {
    data.value = order.map((index) => data.value[index]!)
  }

  return {
    data,
    addElement,
    deleteElement,
    reorderElements
  }
}

const {
  data: data1,
  addElement: addElement1,
  deleteElement: deleteElement1,
  reorderElements: reorderElements1
} = setupList()

const { data: data2, addElement: addElement2, deleteElement: deleteElement2 } = setupList()
</script>

<template>
  <dl>
    <dt>
      <code>
        &lt;CmkList :orientation="'vertical'" :draggable="{ onReorder: reorderElements }" ...&gt;
      </code>
    </dt>
    <dd>
      <CmkList
        :items-props="{ itemData: data1 }"
        :draggable="{ onReorder: reorderElements1 }"
        :add="{
          show: true,
          tryAdd: addElement1,
          label: 'Add new entry'
        }"
        :try-delete="deleteElement1"
        :orientation="'vertical'"
      >
        <template #item-props="{ itemData }">
          {{ itemData }}
        </template>
      </CmkList>
    </dd>
    <dt>
      <code> &lt;CmkList :orientation="'horizontal'" ...&gt; </code>
    </dt>
    <dd>
      <CmkList
        :items-props="{ itemData: data2 }"
        :add="{
          show: true,
          tryAdd: addElement2,
          label: 'Add new entry'
        }"
        :try-delete="deleteElement2"
        :orientation="'horizontal'"
      >
        <template #item-props="{ itemData }">
          {{ itemData }}
        </template>
      </CmkList>
    </dd>
  </dl>
</template>

<style scoped>
code {
  white-space: pre-line;
}
dt {
  margin: 0 0 2em 0;
}
dd {
  margin: 0 0 2em 0;
  padding: 0;
}
</style>
