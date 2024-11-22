/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { createRouter, createWebHistory } from 'vue-router'

import DemoEmpty from './DemoEmpty.vue'
import DemoAlertBox from './DemoAlertBox.vue'
import DemoSlideIn from './DemoSlideIn.vue'
import DemoCmkSpace from './DemoCmkSpace.vue'
import DemoFormSingleChoiceEditableEditAsync from './DemoFormSingleChoiceEditableEditAsync.vue'
import DemoToggleButtonGroup from './DemoToggleButtonGroup.vue'
import DemoCmkDropdown from './DemoCmkDropdown.vue'
import DemoCmkButton from './DemoCmkButton.vue'
import DemoCmkList from './DemoCmkList.vue'
import DemoCmkIcon from './DemoCmkIcon.vue'
import DemoCmkCheckbox from './DemoCmkCheckbox.vue'
import DemoFormList from './DemoFormList.vue'
import DemoForm from './DemoForm.vue'
import DemoFormBooleanChoice from './DemoFormBooleanChoice.vue'
import DemoFormCascadingSingleChoice from './DemoFormCascadingSingleChoice.vue'
import DemoFormOptionalChoice from './DemoFormOptionalChoice.vue'
import DemoFormDictionary from './DemoFormDictionary.vue'
import DemoFormCheckboxListChoice from './DemoFormCheckboxListChoice.vue'
import DemoFormSingleChoiceEditable from './DemoFormSingleChoiceEditable.vue'
import DemoCmkSwitch from './DemoCmkSwitch.vue'
import DemoCmkColorPicker from './DemoCmkColorPicker.vue'
import DemoFormSingleChoice from './DemoFormSingleChoice.vue'
import DemoFormTuple from './DemoFormTuple.vue'
import DemoFormLabels from './DemoFormLabels.vue'
import type { Component } from 'vue'

interface Route {
  path: string
  name: string
  component: Component<{ screenshotMode: boolean }>
  children?: Route[]
}

const routes: Route[] = [
  {
    path: '/',
    name: 'home',
    component: DemoEmpty
  },
  {
    path: '/alertbox',
    name: 'AlertBox',
    component: DemoAlertBox
  },
  {
    path: '/slidein',
    name: 'SlideIn',
    component: DemoSlideIn
  },
  {
    path: '/cmkspace',
    name: 'CmkSpace',
    component: DemoCmkSpace
  },
  {
    path: '/cmkicon',
    name: 'CmkIcon',
    component: DemoCmkIcon
  },
  {
    path: '/cmklist',
    name: 'CmkList',
    component: DemoCmkList
  },
  {
    path: '/cmkcheckbox',
    name: 'CmkCheckbox',
    component: DemoCmkCheckbox
  },
  {
    path: '/togglebuttongroup',
    name: 'ToggleButtonGroup',
    component: DemoToggleButtonGroup
  },
  {
    path: '/button',
    name: 'CmkButton',
    component: DemoCmkButton
  },
  {
    path: '/dropdown',
    name: 'CmkDropdown',
    component: DemoCmkDropdown
  },
  {
    path: '/cmk_switch',
    name: 'CmkSwitch',
    component: DemoCmkSwitch
  },
  {
    path: '/cmk_color_picker',
    name: 'CmkColorPicker',
    component: DemoCmkColorPicker
  },
  {
    path: '/form',
    name: 'Form',
    component: DemoForm,
    children: [
      {
        path: 'formsinglechoiceeditable',
        name: 'FormSingleChoiceEditable',
        component: DemoFormSingleChoiceEditable
      },
      {
        path: 'formcascadingsinglechoice',
        name: 'FormCascadingSingleChoice',
        component: DemoFormCascadingSingleChoice
      },
      {
        path: 'formlist',
        name: 'FormList',
        component: DemoFormList
      },
      {
        path: 'formbooleanchoice',
        name: 'FormBoleanChoice',
        component: DemoFormBooleanChoice
      },
      {
        path: 'formoptionalchoice',
        name: 'FormOptionalChoice',
        component: DemoFormOptionalChoice
      },
      {
        path: 'formodictionary',
        name: 'FormDictionary',
        component: DemoFormDictionary
      },
      {
        path: 'formcheckboxlistchoice',
        name: 'FormCheckboxListChoice',
        component: DemoFormCheckboxListChoice
      },
      {
        path: 'formsinglechoice',
        name: 'FormSingleChoice',
        component: DemoFormSingleChoice
      },
      {
        path: 'formtuple',
        name: 'FormTuple',
        component: DemoFormTuple
      },
      {
        path: 'formlabels',
        name: 'FormLabels',
        component: DemoFormLabels
      },
      {
        path: 'formeditasync',
        name: 'FormSingleChoiceEditableEditAsync',
        component: DemoFormSingleChoiceEditableEditAsync
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
