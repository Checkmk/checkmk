<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCode from '@/components/CmkCode.vue'

defineProps<{ screenshotMode: boolean }>()

const shortCodeText = `sudo cmk-agent-ctl register`
const longCodeText = `sudo cmk-agent-ctl register --hostname heute --server localhost --site heute --user agent_registration --password 'mypasswd'`
const multilineCodeText = `C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe" ^
  register ^
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
sudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long text
sudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long textsudo dpkg -i check-mk-agent.deb very long long text`
const multilineShortCodeText = `C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe" ^
  register ^
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
  --hostname mynewhost ^
  --server cmkserver --site mysite ^
  --user agent_registration --password "PASSWD"
  `
</script>

<template>
  <div class="demo-code-container">
    <h2>Short code</h2>
    <br />
    <CmkCode title="Some title" :code_txt="shortCodeText" />
    <h2>Long code</h2>
    <br />
    <CmkCode title="Some title" :code_txt="longCodeText" />
    <h2>Multiline code</h2>
    <br />
    <CmkCode title="Super title" :code_txt="multilineCodeText" />
    <h2>Multiline short code</h2>
    <br />
    <CmkCode title="Super title" :code_txt="multilineShortCodeText" />
  </div>
</template>

<style scoped>
.demo-code-container {
  max-width: 800px;
  width: 100%;
}
</style>
