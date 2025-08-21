/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import DemoEmpty from '@demo/_demo/DemoEmpty.vue'
import { Folder, Page } from '@demo/_demo/page'
import DemoCmkWizard from '@demo/components/DemoCmkWizard.vue'

import { pages as CmkAccordionPages } from './CmkAccordion'
import { pages as CmkAccordionStepPanelPages } from './CmkAccordionStepPanel'
import { pages as CmkTabPages } from './CmkTabs'
import DemoCmkAlertBox from './DemoCmkAlertBox.vue'
import DemoCmkBadge from './DemoCmkBadge.vue'
import DemoCmkButton from './DemoCmkButton.vue'
import DemoCmkChip from './DemoCmkChip.vue'
import DemoCmkCode from './DemoCmkCode.vue'
import DemoCmkCollapsible from './DemoCmkCollapsible.vue'
import DemoCmkColorPicker from './DemoCmkColorPicker.vue'
import DemoCmkDropdown from './DemoCmkDropdown.vue'
import DemoCmkDualList from './DemoCmkDualList.vue'
import DemoCmkHtml from './DemoCmkHtml.vue'
import DemoCmkIcon from './DemoCmkIcon.vue'
import DemoCmkKeyboardKey from './DemoCmkKeyboardKey.vue'
import DemoCmkLinkCard from './DemoCmkLinkCard.vue'
import DemoCmkList from './DemoCmkList.vue'
import DemoCmkMultitoneIcon from './DemoCmkMultitoneIcon.vue'
import DemoCmkProgressbar from './DemoCmkProgressbar.vue'
import DemoCmkSkeleton from './DemoCmkSkeleton.vue'
import DemoCmkSlideInDialog from './DemoCmkSlideInDialog.vue'
import DemoCmkSpace from './DemoCmkSpace.vue'
import DemoCmkSwitch from './DemoCmkSwitch.vue'
import DemoErrorBoundary from './DemoErrorBoundary.vue'
import DemoToggleButtonGroup from './DemoToggleButtonGroup.vue'
import { pages as typographyPages } from './typography'
import { pages as userInputPages } from './user-input'

export const pages = [
  new Folder('user-input', DemoEmpty, userInputPages),
  new Folder('typography', DemoEmpty, typographyPages),
  new Folder('CmkAccordion', DemoEmpty, CmkAccordionPages),
  new Folder('CmkAccordionStepPanel', DemoEmpty, CmkAccordionStepPanelPages),
  new Folder('CmkTabs', DemoEmpty, CmkTabPages),
  new Page('CmkAlertBox', DemoCmkAlertBox),
  new Page('CmkSlideInDialog', DemoCmkSlideInDialog),
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
  new Page('CmkSkeleton', DemoCmkSkeleton),
  new Page('CmkMultitoneIcon', DemoCmkMultitoneIcon),
  new Page('CmkWizard', DemoCmkWizard),
  new Page('CmkBadge', DemoCmkBadge),
  new Page('CmkChip', DemoCmkChip),
  new Page('CmkProgressbar', DemoCmkProgressbar),
  new Page('CmkList', DemoCmkList),
  new Page('CmkLinkCard', DemoCmkLinkCard),
  new Page('CmkCode', DemoCmkCode),
  new Page('CmkCollapsible', DemoCmkCollapsible),
  new Page('CmkKeyboardKey', DemoCmkKeyboardKey),
  new Page('CmkDualList', DemoCmkDualList)
]
