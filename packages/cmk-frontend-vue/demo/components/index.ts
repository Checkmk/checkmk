/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import DemoEmpty from '@demo/_demo/DemoEmpty.vue'
import { Folder, Page } from '@demo/_demo/page'
import DemoCmkWizard from '@demo/components/CmkWizard/DemoCmkWizard.vue'

import { pages as CmkAccordionPages } from './CmkAccordion'
import { pages as CmkAccordionStepPanelPages } from './CmkAccordionStepPanel'
import { pages as CmkIconPages } from './CmkIcon'
import { pages as CmkTabPages } from './CmkTabs'
import DemoCmkAlertBox from './DemoCmkAlertBox.vue'
import DemoCmkBadge from './DemoCmkBadge.vue'
import DemoCmkButton from './DemoCmkButton.vue'
import DemoCmkCatalogPanel from './DemoCmkCatalogPanel.vue'
import DemoCmkChip from './DemoCmkChip.vue'
import DemoCmkCode from './DemoCmkCode.vue'
import DemoCmkCollapsible from './DemoCmkCollapsible.vue'
import DemoCmkColorPicker from './DemoCmkColorPicker.vue'
import DemoCmkDialog from './DemoCmkDialog.vue'
import DemoCmkDropdown from './DemoCmkDropdown.vue'
import DemoCmkDualList from './DemoCmkDualList.vue'
import DemoCmkHtml from './DemoCmkHtml.vue'
import DemoCmkIndent from './DemoCmkIndent.vue'
import DemoCmkKeyboardKey from './DemoCmkKeyboardKey.vue'
import DemoCmkLinkCard from './DemoCmkLinkCard.vue'
import DemoCmkList from './DemoCmkList.vue'
import DemoCmkLoading from './DemoCmkLoading.vue'
import DemoCmkPerfometer from './DemoCmkPerfometer.vue'
import DemoCmkPopupDialog from './DemoCmkPopupDialog.vue'
import DemoCmkProgressbar from './DemoCmkProgressbar.vue'
import DemoCmkScrollContainer from './DemoCmkScrollContainer.vue'
import DemoCmkSkeleton from './DemoCmkSkeleton.vue'
import DemoCmkSlideIn from './DemoCmkSlideIn.vue'
import DemoCmkSlideInDialog from './DemoCmkSlideInDialog.vue'
import DemoCmkSpace from './DemoCmkSpace.vue'
import DemoCmkSwitch from './DemoCmkSwitch.vue'
import DemoCmkToggleButtonGroup from './DemoCmkToggleButtonGroup.vue'
import DemoCmkTooltip from './DemoCmkTooltip.vue'
import DemoCmkZebra from './DemoCmkZebra.vue'
import DemoErrorBoundary from './DemoErrorBoundary.vue'
import DemoHelp from './DemoHelp.vue'
import DemoTwoFactorAuth from './DemoTwoFactorAuthentication.vue'
import { pages as typographyPages } from './typography'
import { pages as userInputPages } from './user-input'

export const pages = [
  new Folder('CmkAccordion', DemoEmpty, CmkAccordionPages),
  new Folder('CmkAccordionStepPanel', DemoEmpty, CmkAccordionStepPanelPages),
  new Folder('CmkIcons', DemoEmpty, CmkIconPages),
  new Folder('CmkTabs', DemoEmpty, CmkTabPages),
  new Folder('typography', DemoEmpty, typographyPages),
  new Folder('user-input', DemoEmpty, userInputPages),
  new Page('CmkAlertBox', DemoCmkAlertBox),
  new Page('CmkBadge', DemoCmkBadge),
  new Page('CmkButton', DemoCmkButton),
  new Page('CmkCatalogPanel', DemoCmkCatalogPanel),
  new Page('CmkChip', DemoCmkChip),
  new Page('CmkCode', DemoCmkCode),
  new Page('CmkCollapsible', DemoCmkCollapsible),
  new Page('CmkColorPicker', DemoCmkColorPicker),
  new Page('CmkDialog', DemoCmkDialog),
  new Page('CmkDropdown', DemoCmkDropdown),
  new Page('CmkDualList', DemoCmkDualList),
  new Page('CmkErrorBoundary', DemoErrorBoundary),
  new Page('CmkHelpText', DemoHelp),
  new Page('CmkHtml', DemoCmkHtml),
  new Page('CmkKeyboardKey', DemoCmkKeyboardKey),
  new Page('CmkLinkCard', DemoCmkLinkCard),
  new Page('CmkList', DemoCmkList),
  new Page('CmkPerfometer', DemoCmkPerfometer),
  new Page('CmkPopupDialog', DemoCmkPopupDialog),
  new Page('CmkProgressbar', DemoCmkProgressbar),
  new Page('CmkSkeleton', DemoCmkSkeleton),
  new Page('CmkSlideInDialog', DemoCmkSlideInDialog),
  new Page('CmkSpace', DemoCmkSpace),
  new Page('CmkSwitch', DemoCmkSwitch),
  new Page('CmkWizard', DemoCmkWizard),
  new Page('CmkToggleButtonGroup', DemoCmkToggleButtonGroup),
  new Page('CmkLoading', DemoCmkLoading),
  new Page('CmkIndent', DemoCmkIndent),
  new Page('CmkZebra', DemoCmkZebra),
  new Page('CmkScrollContainer', DemoCmkScrollContainer),
  new Page('CmkSlideIn', DemoCmkSlideIn),
  new Page('CmkTooltip', DemoCmkTooltip),
  new Page('TwoFactorAuth', DemoTwoFactorAuth)
]
