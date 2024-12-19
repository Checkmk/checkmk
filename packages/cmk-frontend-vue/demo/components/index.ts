/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import DemoCmkAlertBox from './DemoCmkAlertBox.vue'
import DemoCmkButton from './DemoCmkButton.vue'
import DemoCmkColorPicker from './DemoCmkColorPicker.vue'
import DemoCmkDropdown from './DemoCmkDropdown.vue'
import DemoCmkHtml from './DemoCmkHtml.vue'
import DemoCmkIcon from './DemoCmkIcon.vue'
import DemoCmkList from './DemoCmkList.vue'
import DemoCmkSpace from './DemoCmkSpace.vue'
import DemoCmkSwitch from './DemoCmkSwitch.vue'
import DemoErrorBoundary from './DemoErrorBoundary.vue'
import DemoSlideIn from './DemoCmkSlideInDialog.vue'
import DemoCmkSkeleton from './DemoCmkSkeleton.vue'
import DemoToggleButtonGroup from './DemoToggleButtonGroup.vue'

import DemoEmpty from '@demo/_demo/DemoEmpty.vue'
import { Page, Folder } from '@demo/_demo/page'

import { pages as userInputPages } from './user-input'
import { pages as typographyPages } from './typography'
import { pages as CmkAccordionStepPanelPages } from './CmkAccordionStepPanel'

export const pages = [
  new Folder('user-input', DemoEmpty, userInputPages),
  new Folder('typography', DemoEmpty, typographyPages),
  new Folder('CmkAccordionStepPanel', DemoEmpty, CmkAccordionStepPanelPages),
  new Page('CmkAlertBox', DemoCmkAlertBox),
  new Page('SlideIn', DemoSlideIn),
  new Page('CmkSpace', DemoCmkSpace),
  new Page('CmkIcon', DemoCmkIcon),
  new Page('CmkList', DemoCmkList),
  new Page('ToggleButtonGroup', DemoToggleButtonGroup),
  new Page('CmkButton', DemoCmkButton),
  new Page('CmkDropdown', DemoCmkDropdown),
  new Page('ErrorBoundary', DemoErrorBoundary),
  new Page('CmkSwitch', DemoCmkSwitch),
  new Page('CmkColorPicker', DemoCmkColorPicker),
  new Page('CmkHtml', DemoCmkHtml),
  new Page('CmkSkeleton', DemoCmkSkeleton)
]
