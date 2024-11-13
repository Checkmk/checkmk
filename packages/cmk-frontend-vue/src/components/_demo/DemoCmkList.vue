<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkList from '@/components/CmkList'
import { ref } from 'vue'

const data = ref(['element 1', 'element 2', 'element 3'])

function addElement() {
  data.value.push('new element')
}

function deleteElement(index: number) {
  data.value.splice(index, 1)
}

function reorderElements(order: number[]) {
  data.value = order.map((index) => data.value[index]!)
}
</script>

<template>
  <dl>
    <dt>
      <code> &lt;CmkList :draggable="{ onReorder: reorderElements }" ...&gt; </code>
    </dt>
    <dd>
      <CmkList
        :items-props="{ data }"
        :draggable="{ onReorder: reorderElements }"
        :on-add="addElement"
        :on-delete="deleteElement"
        :i18n="{
          addElementLabel: 'Add new entry'
        }"
      >
        <template #item-props="{ data: itemData }">
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
  margin-bottom: 2em;
}
dd {
  margin: 0;
  padding: 0;
}
</style>
