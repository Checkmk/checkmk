# -*- encoding: utf-8
# yapf: disable


checkname = '3par_hosts'


info = [[u'{"total":21,"members":[{"id":0,"name":"SUPER-VM","descriptors":{},"FCPaths":[{"wwn":"WWN123","portPos":{"node":3,"slot":2,"cardPort":3},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":3,"slot":2,"cardPort":1},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":2,"slot":2,"cardPort":3},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":2,"slot":2,"cardPort":1},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":1,"slot":2,"cardPort":3},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":1,"slot":2,"cardPort":1},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":0,"slot":2,"cardPort":3},"hostSpeed":0},{"wwn":"WWN123","portPos":{"node":0,"slot":2,"cardPort":1},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":3,"slot":2,"cardPort":4},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":3,"slot":2,"cardPort":2},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":2,"slot":2,"cardPort":4},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":2,"slot":2,"cardPort":2},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":1,"slot":2,"cardPort":4},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":1,"slot":2,"cardPort":2},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":0,"slot":2,"cardPort":4},"hostSpeed":0},{"wwn":"WWN456","portPos":{"node":0,"slot":2,"cardPort":2},"hostSpeed":0}],"iSCSIPaths":[],"persona":8,"links":[{"href":"https://1.2.3.4:8080/api/v1/hostpersonas?query=\\"wsapiAssignedId136\\"","rel":"personaInfo"}],"initiatorChapEnabled":false,"targetChapEnabled":false}]}']]


discovery = {'': [(u'SUPER-VM', None)]}


checks = {'': [(u'SUPER-VM', {}, [(0, 'ID: 0', []), (0, 'FC Paths: 16', [])])]}