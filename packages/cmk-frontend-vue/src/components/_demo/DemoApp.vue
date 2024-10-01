<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import DemoAlertBox from './DemoAlertBox.vue'
import DemoIconButton from './DemoIconButton.vue'
import DemoSlideIn from './DemoSlideIn.vue'
import DemoFormEditAsync from './DemoFormEditAsync.vue'

const demo = ref('')

function renderDemo() {
  switch (demo.value) {
    case 'alertbox':
      return h(DemoAlertBox)
    case 'iconbutton':
      return h(DemoIconButton)
    case 'slidein':
      return h(DemoSlideIn)
    case 'formeditasync':
      return h(DemoFormEditAsync)
  }
  return h('i', 'choose demo from navigation')
}

function setTheme(name: 'modern-dark' | 'facelift') {
  document.getElementsByTagName('body')[0]!.dataset['theme'] = name
}

onMounted(() => {
  setTheme('facelift')
})
</script>

<template>
  <div class="demo">
    <nav>
      <button @click="setTheme('modern-dark')">dark</button>
      <button @click="setTheme('facelift')">light</button>
      <ul>
        <li><a href="#" @click.prevent="demo = ''">home</a></li>
        <li><a href="#" @click.prevent="demo = 'alertbox'">alert box</a></li>
        <li><a href="#" @click.prevent="demo = 'iconbutton'">icon button</a></li>
        <li><a href="#" @click.prevent="demo = 'slidein'">slide in</a></li>
        <li><a href="#" @click.prevent="demo = 'formeditasync'">form edit async</a></li>
      </ul>
    </nav>
    <main>
      <h1>{{ demo }}</h1>
      <div class="demo-area">
        <renderDemo />
      </div>
    </main>
  </div>
</template>

<style scoped>
.demo {
  display: flex;
}
main .demo-area {
  background-color: white;
  padding: 1em;
}
nav {
  flex: 0 200px;
}
</style>
