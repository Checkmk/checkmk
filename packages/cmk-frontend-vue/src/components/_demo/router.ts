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
import DemoFormEditAsync from './DemoFormEditAsync.vue'
import DemoToggleButtonGroup from './DemoToggleButtonGroup.vue'
import DemoDropDown from './DemoDropDown.vue'
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
import DemoFormSingleChoiceEditable from './DemoFormSingleChoiceEditable.vue'
import DemoCmkSwitch from './DemoCmkSwitch.vue'
import DemoCmkColorPicker from './DemoCmkColorPicker.vue'
import DemoFormLabels from './DemoFormLabels.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
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
      path: '/formeditasync',
      name: 'FormEditAsync',
      component: DemoFormEditAsync
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
      name: 'DropDown',
      component: DemoDropDown
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
          path: 'formlabels',
          name: 'FormLabels',
          component: DemoFormLabels
        }
      ]
    }
  ]
})

export default router
