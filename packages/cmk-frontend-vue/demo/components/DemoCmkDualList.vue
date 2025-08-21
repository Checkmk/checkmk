<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'
import { type DualListElement } from '@/components/CmkDualList/index.ts'

defineProps<{ screenshotMode: boolean }>()

function pad(num: number, len: number): string {
  let numStr = num.toString()
  while (numStr.length < len) {
    numStr = `0${numStr}`
  }
  return numStr
}

const data = ref<DualListElement[]>([{ name: 'test_name_003', title: 'Test Name 3' }])
const elements = ref<DualListElement[]>(
  Array.from({ length: 30 }, (_, i) => ({
    name: `test_name_${pad(i + 1, 3)}`,
    title: `Test Name ${i + 1}`
  }))
)

const data2 = ref<DualListElement[]>([])
const elements2 = ref<DualListElement[]>(
  Array.from({ length: 30 }, (_, i) => ({
    name: `second_name_${i + 1}`,
    title: `Second Name ${i + 1}`
  }))
)
</script>

<template>
  <h2>Demo: CmkDualList</h2>
  <div>
    <div>
      <div>
        <h3>Config example 1</h3>
        <code>
          * Elements: Test Name [1...30] / test_name_[1...30]<br />
          * Title: CMK Dual List Component Demo<br />
          * Loading & Validation are empty<br />
        </code>
      </div>
      <h3>Data</h3>
      <pre>{{ JSON.stringify(data).replace(/},/g, '},\n') }}</pre>
    </div>
    <CmkDualList
      v-model:data="data"
      :elements="elements"
      :title="'CMK Dual List Component Demo'"
      :validators="[]"
      :backend-validation="[]"
    />
  </div>
  <div>
    <div>
      <div>
        <h3>Config example 2</h3>
        <code>
          * Elements: Second Name [1...30] / second_name_[1...30]<br />
          * Title: CMK Dual List Component Demo 2<br />
          * Loading & Validation are empty<br />
        </code>
      </div>
      <h3>Data</h3>
      <pre>{{ JSON.stringify(data2).replace(/},/g, '},\n') }}</pre>
    </div>
    <CmkDualList
      v-model:data="data2"
      :elements="elements2"
      :title="'CMK Dual List Component Demo 2'"
      :validators="[]"
      :backend-validation="[]"
    />
  </div>
</template>

<style scoped>
code {
  white-space: pre-line;
}
</style>
