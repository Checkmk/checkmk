# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#.
#   .--for imports---------------------------------------------------------.
#   |         __              _                            _               |
#   |        / _| ___  _ __  (_)_ __ ___  _ __   ___  _ __| |_ ___         |
#   |       | |_ / _ \| '__| | | '_ ` _ \| '_ \ / _ \| '__| __/ __|        |
#   |       |  _| (_) | |    | | | | | | | |_) | (_) | |  | |_\__ \        |
#   |       |_|  \___/|_|    |_|_| |_| |_| .__/ \___/|_|   \__|___/        |
#   |                                    |_|                               |
#   '----------------------------------------------------------------------'
#   .--regions--------------------------------------------------------------

AWSRegions = [
    ("ap-south-1", "Asia Pacific (Mumbai)"),
    ("ap-northeast-3", "Asia Pacific (Osaka-Local)"),
    ("ap-northeast-2", "Asia Pacific (Seoul)"),
    ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ("ap-southeast-2", "Asia Pacific (Sydney)"),
    ("ap-northeast-1", "Asia Pacific (Tokyo)"),
    ("ca-central-1", "Canada (Central)"),
    ("cn-north-1", "China (Beijing)"),
    ("cn-northwest-1", "China (Ningxia)"),
    ("eu-central-1", "EU (Frankfurt)"),
    ("eu-west-1", "EU (Ireland)"),
    ("eu-west-2", "EU (London)"),
    ("eu-west-3", "EU (Paris)"),
    ("eu-north-1", "EU (Stockholm)"),
    ("sa-east-1", "South America (Sao Paulo)"),
    ("us-east-2", "US East (Ohio)"),
    ("us-east-1", "US East (N. Virginia)"),
    ("us-west-1", "US West (N. California)"),
    ("us-west-2", "US West (Oregon)"),
]

#.
#   .--EC2 instance types---------------------------------------------------

AWSEC2InstGeneralTypes = [
    'a1.2xlarge',
    'a1.4xlarge',
    'a1.large',
    'a1.medium',
    'a1.xlarge',
    't2.nano',
    't2.micro',
    't2.small',
    't2.medium',
    't2.large',
    't2.xlarge',
    't2.2xlarge',
    't3.nano',
    't3.micro',
    't3.small',
    't3.medium',
    't3.large',
    't3.xlarge',
    't3.2xlarge',
    'm3.medium',
    'm3.large',
    'm3.xlarge',
    'm3.2xlarge',
    'm4.large',
    'm4.xlarge',
    'm4.2xlarge',
    'm4.4xlarge',
    'm4.10xlarge',
    'm4.16xlarge',
    'm5.12xlarge',
    'm5.24xlarge',
    'm5.2xlarge',
    'm5.4xlarge',
    'm5.large',
    'm5.xlarge',
    'm5d.12xlarge',
    'm5d.24xlarge',
    'm5d.2xlarge',
    'm5d.4xlarge',
    'm5d.large',
    'm5d.xlarge',
    'm5a.12xlarge',
    'm5a.24xlarge',
    'm5a.2xlarge',
    'm5a.4xlarge',
    'm5a.large',
    'm5a.xlarge',
]

AWSEC2InstPrevGeneralTypes = [
    't1.micro',
    'm1.small',
    'm1.medium',
    'm1.large',
    'm1.xlarge',
]

AWSEC2InstMemoryTypes = [
    'r3.2xlarge',
    'r3.4xlarge',
    'r3.8xlarge',
    'r3.large',
    'r3.xlarge',
    'r4.2xlarge',
    'r4.4xlarge',
    'r4.8xlarge',
    'r4.16xlarge',
    'r4.large',
    'r4.xlarge',
    'r5.2xlarge',
    'r5.4xlarge',
    'r5.8xlarge',
    'r5.12xlarge',
    'r5.16xlarge',
    'r5.24xlarge',
    'r5.large',
    'r5.metal',
    'r5.xlarge',
    'r5a.12xlarge',
    'r5a.24xlarge',
    'r5a.2xlarge',
    'r5a.4xlarge',
    'r5a.large',
    'r5a.xlarge',
    'r5d.2xlarge',
    'r5d.4xlarge',
    'r5d.8xlarge',
    'r5d.12xlarge',
    'r5d.16xlarge',
    'r5d.24xlarge',
    'r5d.large',
    'r5d.metal',
    'r5d.xlarge',
    'x1.16xlarge',
    'x1.32xlarge',
    'x1e.2xlarge',
    'x1e.4xlarge',
    'x1e.8xlarge',
    'x1e.16xlarge',
    'x1e.32xlarge',
    'x1e.xlarge',
    'z1d.2xlarge',
    'z1d.3xlarge',
    'z1d.6xlarge',
    'z1d.12xlarge',
    'z1d.large',
    'z1d.xlarge',
]

AWSEC2InstPrevMemoryTypes = [
    'm2.xlarge',
    'm2.2xlarge',
    'm2.4xlarge',
    'cr1.8xlarge',
]

AWSEC2InstComputeTypes = [
    'c3.large',
    'c3.xlarge',
    'c3.2xlarge',
    'c3.4xlarge',
    'c3.8xlarge',
    'c4.large',
    'c4.xlarge',
    'c4.2xlarge',
    'c4.4xlarge',
    'c4.8xlarge',
    'c5.18xlarge',
    'c5.2xlarge',
    'c5.4xlarge',
    'c5.9xlarge',
    'c5.large',
    'c5.xlarge',
    'c5d.18xlarge',
    'c5d.2xlarge',
    'c5d.4xlarge',
    'c5d.9xlarge',
    'c5d.large',
    'c5d.xlarge',
    'c5n.18xlarge',
    'c5n.2xlarge',
    'c5n.4xlarge',
    'c5n.9xlarge',
    'c5n.large',
    'c5n.xlarge',
]

AWSEC2InstPrevComputeTypes = [
    'c1.medium',
    'c1.xlarge',
    'cc2.8xlarge',
    'cc1.4xlarge',
]

AWSEC2InstAcceleratedComputeTypes = [
    'f1.4xlarge',
    'p2.xlarge',
    'p2.8xlarge',
    'p2.16xlarge',
    'p3.16xlarge',
    'p3.2xlarge',
    'p3.8xlarge',
    'p3dn.24xlarge',
]

AWSEC2InstStorageTypes = [
    'i2.xlarge',
    'i2.2xlarge',
    'i2.4xlarge',
    'i2.8xlarge',
    'i3.large',
    'i3.xlarge',
    'i3.2xlarge',
    'i3.4xlarge',
    'i3.8xlarge',
    'i3.16xlarge',
    'i3.metal',
    'h1.16xlarge',
    'h1.2xlarge',
    'h1.4xlarge',
    'h1.8xlarge',
]

# 'hi1.4xlarge' is no longer in the instance type listings,
# but some accounts might still have a limit for it
AWSEC2InstPrevStorageTypes = [
    'hi1.4xlarge',
    'hs1.8xlarge',
]

AWSEC2InstDenseStorageTypes = [
    'd2.xlarge',
    'd2.2xlarge',
    'd2.4xlarge',
    'd2.8xlarge',
]

AWSEC2InstGPUTypes = [
    'g2.2xlarge',
    'g2.8xlarge',
    'g3.16xlarge',
    'g3.4xlarge',
    'g3.8xlarge',
    'g3s.xlarge',
]

AWSEC2InstPrevGPUTypes = [
    'cg1.4xlarge',
]

# note, as of 2016-12-17, these are still in Developer Preview;
# there isn't a published instance limit yet, so we'll assume
# it's the default...
AWSEC2InstFPGATypes = [
    'f1.2xlarge',
    'f1.16xlarge',
]

AWSEC2InstFamilies = {
    'f': 'Running On-Demand F instances',
    'g': 'Running On-Demand G instances',
    'p': 'Running On-Demand P instances',
    'x': 'Running On-Demand X instances',
    '_': 'Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances'
}

AWSEC2InstTypes = (AWSEC2InstGeneralTypes + AWSEC2InstPrevGeneralTypes + AWSEC2InstMemoryTypes +
                   AWSEC2InstPrevMemoryTypes + AWSEC2InstComputeTypes + AWSEC2InstPrevComputeTypes +
                   AWSEC2InstAcceleratedComputeTypes + AWSEC2InstStorageTypes +
                   AWSEC2InstPrevStorageTypes + AWSEC2InstDenseStorageTypes + AWSEC2InstGPUTypes +
                   AWSEC2InstPrevGPUTypes + AWSEC2InstFPGATypes)

# (On-Demand, Reserved, Spot)
AWSEC2LimitsDefault = (20, 20, 5)

AWSEC2LimitsSpecial = {
    'c4.4xlarge': (10, 20, 5),
    'c4.8xlarge': (5, 20, 5),
    'c5.4xlarge': (10, 20, 5),
    'c5.9xlarge': (5, 20, 5),
    'c5.18xlarge': (5, 20, 5),
    'cg1.4xlarge': (2, 20, 5),
    'cr1.8xlarge': (2, 20, 5),
    'd2.4xlarge': (10, 20, 5),
    'd2.8xlarge': (5, 20, 5),
    'g2.2xlarge': (5, 20, 5),
    'g2.8xlarge': (2, 20, 5),
    'g3.4xlarge': (1, 20, 5),
    'g3.8xlarge': (1, 20, 5),
    'g3.16xlarge': (1, 20, 5),
    'h1.8xlarge': (10, 20, 5),
    'h1.16xlarge': (5, 20, 5),
    'hi1.4xlarge': (2, 20, 5),
    'hs1.8xlarge': (2, 20, 0),
    'i2.2xlarge': (8, 20, 0),
    'i2.4xlarge': (4, 20, 0),
    'i2.8xlarge': (2, 20, 0),
    'i2.xlarge': (8, 20, 0),
    'i3.2xlarge': (2, 20, 0),
    'i3.4xlarge': (2, 20, 0),
    'i3.8xlarge': (2, 20, 0),
    'i3.16xlarge': (2, 20, 0),
    'i3.large': (2, 20, 0),
    'i3.xlarge': (2, 20, 0),
    'm4.4xlarge': (10, 20, 5),
    'm4.10xlarge': (5, 20, 5),
    'm4.16xlarge': (5, 20, 5),
    'm5.4xlarge': (10, 20, 5),
    'm5.12xlarge': (5, 20, 5),
    'm5.24xlarge': (5, 20, 5),
    'p2.8xlarge': (1, 20, 5),
    'p2.16xlarge': (1, 20, 5),
    'p2.xlarge': (1, 20, 5),
    'p3.2xlarge': (1, 20, 5),
    'p3.8xlarge': (1, 20, 5),
    'p3.16xlarge': (1, 20, 5),
    'p3dn.24xlarge': (1, 20, 5),
    'r3.4xlarge': (10, 20, 5),
    'r3.8xlarge': (5, 20, 5),
    'r4.4xlarge': (10, 20, 5),
    'r4.8xlarge': (5, 20, 5),
    'r4.16xlarge': (1, 20, 5),
    'f_vcpu': (128, None, None),
    'g_vcpu': (128, None, None),
    'p_vcpu': (128, None, None),
    'x_vcpu': (128, None, None),
    '__vcpu': (1152, None, None),
}
