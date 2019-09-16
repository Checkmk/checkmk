#!/usr/bin/env python
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
"""
Special agent for monitoring Amazon web services (AWS) with Check_MK.
"""

import abc
import argparse
import json
import logging
import sys
import time
from typing import (  # pylint: disable=unused-import
    Union, NamedTuple, Any, List,
)
from pathlib2 import Path
import boto3  # type: ignore
import botocore  # type: ignore
from cmk.utils.paths import tmp_dir
import cmk.utils.password_store
from cmk.special_agents.utils import (
    datetime_serializer,
    DataCache,
)

AWSStrings = Union[bytes, unicode]

# TODO
# Rewrite API calls from low-level client to high-level resource:
# Boto3 has two distinct levels of APIs. Client (or "low-level") APIs provide
# one-to-one mappings to the underlying HTTP API operations. Resource APIs hide
# explicit network calls but instead provide resource objects and collections to
# access attributes and perform actions.

# Note that in this case you do not have to make a second API call to get the
# objects; they're available to you as a collection on the bucket. These
# collections of subresources are lazily-loaded.

# TODO limits
# - per account (S3)
# - per region (EC2, EBS, ELB, RDS)

#   .--overview------------------------------------------------------------.
#   |                                        _                             |
#   |               _____   _____ _ ____   _(_) _____      __              |
#   |              / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /              |
#   |             | (_) \ V /  __/ |   \ V /| |  __/\ V  V /               |
#   |              \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Overview of sections and dependencies                                |
#   '----------------------------------------------------------------------'

# CostsAndUsage

# EC2Limits
# |
# '-- EC2Summary
#     |
#     |-- EC2Labels
#     |
#     |-- EC2SecurityGroups
#     |
#     '-- EC2

# S3Limits
# |
# '-- S3Summary
#     |
#     |-- S3
#     |
#     '-- S3Requests

# ELBLimits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBHealth
#     |
#     '-- ELB

# ELBv2Limits
# |
# '-- ELBSummaryGeneric
#     |
#     |-- ELBLabelsGeneric
#     |
#     |-- ELBv2TargetGroups
#     |
#     '-- ELBv2Application, ELBv2Network

# EBSLimits,EC2Summary
# |
# '-- EBSSummary
#     |
#     '-- EBS

# RDSLimits

# RDSSummary
# |
# '-- RDS

# CloudwatchAlarmsLimits
# |
# '-- CloudwatchAlarms

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
}

#.

#.
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _chunks(list_, length=100):
    return [list_[i:i + length] for i in xrange(0, len(list_), length)]


def _get_ec2_piggyback_hostname(inst, region):
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    return u"%s-%s-%s" % (inst['PrivateIpAddress'], region, inst['InstanceId'])


#.
#   .--section API---------------------------------------------------------.
#   |                       _   _                  _    ____ ___           |
#   |         ___  ___  ___| |_(_) ___  _ __      / \  |  _ \_ _|          |
#   |        / __|/ _ \/ __| __| |/ _ \| '_ \    / _ \ | |_) | |           |
#   |        \__ \  __/ (__| |_| | (_) | | | |  / ___ \|  __/| |           |
#   |        |___/\___|\___|\__|_|\___/|_| |_| /_/   \_\_|  |___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---result distributor---------------------------------------------------


class ResultDistributor(object):
    """
    Mediator which distributes results from sections
    in order to reduce queries to AWS account.
    """
    def __init__(self):
        self._colleagues = []

    def add(self, colleague):
        self._colleagues.append(colleague)

    def distribute(self, sender, result):
        for colleague in self._colleagues:
            if colleague.name != sender.name:
                colleague.receive(sender, result)


#   ---sections/colleagues--------------------------------------------------

AWSSectionResults = NamedTuple("AWSSectionResults", [
    ("results", List),
    ("cache_timestamp", float),
])

AWSSectionResult = NamedTuple("AWSSectionResult", [
    ("piggyback_hostname", AWSStrings),
    ("content", Any),
])

AWSLimit = NamedTuple("AWSLimit", [
    ("key", AWSStrings),
    ("title", AWSStrings),
    ("limit", int),
    ("amount", int),
])

AWSColleagueContents = NamedTuple("AWSColleagueContents", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSRawContent = NamedTuple("AWSRawContent", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSComputedContent = NamedTuple("AWSComputedContent", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSCacheFilePath = Path(tmp_dir) / "agents" / "agent_aws"


class AWSSection(DataCache):
    __metaclass__ = abc.ABCMeta

    def __init__(self, client, region, config, distributor=None):
        cache_dir = AWSCacheFilePath / region / config.hostname
        super(AWSSection, self).__init__(cache_dir, self.name)
        self._client = client
        self._region = region
        self._config = config
        self._distributor = ResultDistributor() if distributor is None else distributor
        self._received_results = {}

    @abc.abstractproperty
    def name(self):
        pass

    @abc.abstractproperty
    def cache_interval(self):
        """
        In general the default resolution of AWS metrics is 5 min (300 sec)
        The default resolution of AWS S3 metrics is 1 day (86400 sec)
        We use interval property for cached section.
        """
        pass

    @property
    def period(self):
        return 2 * self.cache_interval

    def _send(self, content):
        self._distributor.distribute(self, content)

    def receive(self, sender, content):
        self._received_results.setdefault(sender.name, content)

    def run(self, use_cache=False):
        colleague_contents = self._get_colleague_contents()
        assert isinstance(
            colleague_contents, AWSColleagueContents
        ), "%s: Colleague contents must be of type 'AWSColleagueContents'" % self.name
        assert isinstance(
            colleague_contents.cache_timestamp,
            float), "%s: Cache timestamp of colleague contents must be of type 'float'" % self.name

        raw_data = self.get_data(colleague_contents, use_cache=use_cache)
        raw_content = AWSRawContent(raw_data, self.cache_timestamp if use_cache else time.time())
        assert isinstance(
            raw_content,
            AWSRawContent), "%s: Raw content must be of type 'AWSRawContent'" % self.name
        assert isinstance(
            raw_content.cache_timestamp,
            float), "%s: Cache timestamp of raw content must be of type 'float'" % self.name

        computed_content = self._compute_content(raw_content, colleague_contents)
        assert isinstance(computed_content, AWSComputedContent
                         ), "%s: Computed content must be of type 'AWSComputedContent'" % self.name
        assert isinstance(
            computed_content.cache_timestamp,
            float), "%s: Cache timestamp of computed content must be of type 'float'" % self.name

        self._send(computed_content)
        created_results = self._create_results(computed_content)
        assert isinstance(created_results,
                          list), "%s: Created results must be fo type 'list'" % self.name

        final_results = []
        for result in created_results:
            assert isinstance(
                result,
                AWSSectionResult), "%s: Result must be of type 'AWSSectionResult'" % self.name

            if not result.content:
                logging.info("%s: Result is empty or None", self.name)
                continue

            assert isinstance(
                result.piggyback_hostname, (unicode, str)
            ), "%s: Piggyback hostname of created result must be of type 'unicode' or 'str'" % self.name

            # In the related check plugin aws.include we parse these results and
            # extend list of json-loaded results, except for labels sections.
            self._validate_result_content(result.content)

            final_results.append(result)
        return AWSSectionResults(final_results, computed_content.cache_timestamp)

    def get_validity_from_args(self, colleague_contents):  # pylint: disable=arguments-differ
        my_cache_timestamp = self.cache_timestamp
        if my_cache_timestamp is None:
            return False
        if colleague_contents.cache_timestamp > my_cache_timestamp:
            logging.info("Colleague data is newer than cache file %s", self._cache_file)
            return False
        return True

    @abc.abstractmethod
    def _get_colleague_contents(self):
        # type: (Any) -> AWSColleagueContents
        """
        Receive section contents from colleagues. The results are stored in
        self._receive_results: {<KEY>: AWSComputedContent}.
        The relation between two sections must be declared in the related
        distributor in advance to make this work.
        Use max. cache_timestamp of all received results for
        AWSColleagueContents.cache_timestamp
        """
        pass

    @abc.abstractmethod
    def get_live_data(self, colleague_contents):  # pylint: disable=arguments-differ
        """
        Call API methods, eg. 'response = ec2_client.describe_instances()' and
        extract content from raw content.  Raw contents basically consist of
        two sub results:
        - 'ResponseMetadata'
        - '<KEY>'
        Return raw_result['<KEY>'].
        """
        pass

    @abc.abstractmethod
    def _compute_content(self, raw_content, colleague_contents):
        # type: (AWSRawContent, Any) -> AWSComputedContent
        """
        Compute the final content of this section based on the raw content of
        this section and the content received from the optional colleague
        sections.
        """
        pass

    @abc.abstractmethod
    def _create_results(self, computed_content):
        # type: (Any) -> List[AWSSectionResult]
        pass

    def _get_response_content(self, response, key, dflt=None):
        if dflt is None:
            dflt = []
        try:
            return response[key]
        except KeyError:
            logging.info("%s: KeyError; Available keys are %s", self.name, response.keys())
            return dflt

    def _validate_result_content(self, content):
        assert isinstance(content, list), "%s: Result content must be of type 'list'" % self.name

    def _prepare_tags_for_api_response(self, tags):
        """
        We need to change the format, in order to filter out instances with specific
        tags if and only if we already fetched instances, eg. by limits section.
        The format:
        [{'Key': KEY, 'Value': VALUE}, ...]
        """
        if not tags:
            return
        prepared_tags = []
        for tag in tags:
            tag_name = tag['Name']
            if tag_name.startswith('tag:'):
                tag_key = tag_name[4:]
            else:
                tag_key = tag_name
            prepared_tags.extend([{'Key': tag_key, 'Value': v} for v in tag['Values']])
        return prepared_tags


class AWSSectionLimits(AWSSection):
    __metaclass__ = abc.ABCMeta

    def __init__(self, client, region, config, distributor=None):
        super(AWSSectionLimits, self).__init__(client, region, config, distributor=distributor)
        self._limits = {}

    def _add_limit(self, piggyback_hostname, limit):
        assert isinstance(limit, AWSLimit), "%s: Limit must be of type 'AWSLimit'" % self.name
        self._limits.setdefault(piggyback_hostname, []).append(limit)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, limits)
            for piggyback_hostname, limits in self._limits.iteritems()
        ]


class AWSSectionLabels(AWSSection):
    __metaclass__ = abc.ABCMeta

    def _create_results(self, computed_content):
        assert isinstance(
            computed_content.content,
            dict), "%s: Computed result of Labels section must be of type 'dict'" % self.name
        for pb in computed_content.content.iterkeys():
            assert bool(pb), "%s: Piggyback hostname is not allowed to be empty" % self.name
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]

    def _validate_result_content(self, content):
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


class AWSSectionGeneric(AWSSection):
    __metaclass__ = abc.ABCMeta


class AWSSectionCloudwatch(AWSSection):
    __metaclass__ = abc.ABCMeta

    def get_live_data(self, colleague_contents):
        end_time = time.time()
        start_time = end_time - self.period
        metrics = self._get_metrics(colleague_contents)
        if not metrics:
            return []

        # A single GetMetricData call can include up to 100 MetricDataQuery structures
        # There's no pagination for this operation:
        # self._client.can_paginate('get_metric_data') = False
        raw_content = []
        for chunk in _chunks(metrics):
            if not chunk:
                continue
            response = self._client.get_metric_data(
                MetricDataQueries=chunk,
                StartTime=start_time,
                EndTime=end_time,
            )

            metrics = self._get_response_content(response, 'MetricDataResults')
            if not metrics:
                continue
            raw_content.extend(metrics)
        return raw_content

    @abc.abstractmethod
    def _get_metrics(self, colleague_contents):
        pass

    def _create_id_for_metric_data_query(self, index, metric_name, *args):
        """
        ID field must be unique in a single call.
        The valid characters are letters, numbers, and underscore.
        The first character must be a lowercase letter.
        Regex: ^[a-z][a-zA-Z0-9_]*$
        """
        return "_".join(["id", str(index)] + list(args) + [metric_name])


#.
#   .--costs/usage---------------------------------------------------------.
#   |                      _          __                                   |
#   |         ___ ___  ___| |_ ___   / /   _ ___  __ _  __ _  ___          |
#   |        / __/ _ \/ __| __/ __| / / | | / __|/ _` |/ _` |/ _ \         |
#   |       | (_| (_) \__ \ |_\__ \/ /| |_| \__ \ (_| | (_| |  __/         |
#   |        \___\___/|___/\__|___/_/  \__,_|___/\__,_|\__, |\___|         |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

# Interval between 'Start' and 'End' must be a DateInterval. 'End' is exclusive.
# Example:
# 2017-01-01 - 2017-05-01; cost and usage data is retrieved from 2017-01-01 up
# to and including 2017-04-30 but not including 2017-05-01.
# The GetCostAndUsageRequest operation supports only DAILY and MONTHLY granularities.


class CostsAndUsage(AWSSectionGeneric):
    @property
    def name(self):
        return "costs_and_usage"

    @property
    def cache_interval(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        fmt = "%Y-%m-%d"
        now = time.time()
        response = self._client.get_cost_and_usage(
            TimePeriod={
                'Start': time.strftime(fmt, time.gmtime(now - self.cache_interval)),
                'End': time.strftime(fmt, time.gmtime(now)),
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{
                'Type': 'DIMENSION',
                'Key': 'LINKED_ACCOUNT'
            }, {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }],
        )
        return self._get_response_content(response, 'ResultsByTime')

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class EC2Limits(AWSSectionLimits):
    @property
    def name(self):
        return "ec2_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._client.describe_instances()
        reservations = self._get_response_content(response, 'Reservations')

        response = self._client.describe_reserved_instances()
        reserved_instances = self._get_response_content(response, 'ReservedInstances')

        response = self._client.describe_addresses()
        addresses = self._get_response_content(response, 'Addresses')

        response = self._client.describe_security_groups()
        security_groups = self._get_response_content(response, 'SecurityGroups')

        response = self._client.describe_network_interfaces()
        interfaces = self._get_response_content(response, 'NetworkInterfaces')

        response = self._client.describe_spot_instance_requests()
        spot_inst_requests = self._get_response_content(response, 'SpotInstanceRequests')

        response = self._client.describe_spot_fleet_requests()
        spot_fleet_requests = self._get_response_content(response, 'SpotFleetRequestConfigs')

        return reservations, reserved_instances, addresses, security_groups, interfaces, spot_inst_requests, spot_fleet_requests

    def _compute_content(self, raw_content, colleague_contents):
        reservations, reserved_instances, addresses, security_groups, interfaces, spot_inst_requests, spot_fleet_requests = raw_content.content
        instances = {inst['InstanceId']: inst for res in reservations for inst in res['Instances']}
        res_instances = {inst['ReservedInstancesId']: inst for inst in reserved_instances}

        self._add_instance_limits(instances, res_instances, spot_inst_requests)
        self._add_addresses_limits(addresses)
        self._add_security_group_limits(instances, security_groups)
        self._add_interface_limits(instances, interfaces)
        self._add_spot_inst_limits(spot_inst_requests)
        self._add_spot_fleet_limits(spot_fleet_requests)
        return AWSComputedContent(reservations, raw_content.cache_timestamp)

    def _add_instance_limits(self, instances, res_instances, spot_inst_requests):
        inst_limits = self._get_inst_limits(instances, spot_inst_requests)
        res_limits = self._get_res_inst_limits(res_instances)

        total_ris = 0
        running_ris = 0
        ondemand_limits = {}
        # subtract reservations from instance usage
        for inst_az, inst_types in inst_limits.iteritems():
            if inst_az not in res_limits:
                for inst_type, count in inst_types.iteritems():
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                continue

            # else we have reservations for this AZ
            for inst_type, count in inst_types.iteritems():
                if inst_type not in res_limits[inst_az]:
                    # no reservations for this type
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                    continue

                amount_res_inst_type = res_limits[inst_az][inst_type]
                ondemand = count - amount_res_inst_type
                total_ris += amount_res_inst_type
                if count < amount_res_inst_type:
                    running_ris += count
                else:
                    running_ris += amount_res_inst_type
                if ondemand < 0:
                    # we have unused reservations
                    continue
                ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + ondemand

        dflt_ondemand_limit, _reserved_limit, _spot_limit = AWSEC2LimitsDefault
        total_instances = 0
        for inst_type, count in ondemand_limits.iteritems():
            total_instances += count
            ondemand_limit, _reserved_limit, _spot_limit = AWSEC2LimitsSpecial.get(
                inst_type, AWSEC2LimitsDefault)
            self._add_limit(
                "",
                AWSLimit("running_ondemand_instances_%s" % inst_type,
                         "Running On-Demand %s Instances" % inst_type, ondemand_limit, count))
        self._add_limit(
            "",
            AWSLimit("running_ondemand_instances_total", "Total Running On-Demand Instances",
                     dflt_ondemand_limit, total_instances))

    def _get_inst_limits(self, instances, spot_inst_requests):
        spot_instance_ids = [inst['InstanceId'] for inst in spot_inst_requests]
        inst_limits = {}
        for inst_id, inst in instances.iteritems():
            if inst_id in spot_instance_ids:
                continue
            if inst['State']['Name'] in ['stopped', 'terminated']:
                continue
            inst_type = inst['InstanceType']
            inst_az = inst['Placement']['AvailabilityZone']
            inst_limits.setdefault(
                inst_az, {})[inst_type] = inst_limits.get(inst_az, {}).get(inst_type, 0) + 1
        return inst_limits

    def _get_res_inst_limits(self, res_instances):
        res_limits = {}
        for res_inst in res_instances.itervalues():
            if res_inst['State'] != 'active':
                continue
            inst_type = res_inst['InstanceType']
            if inst_type not in AWSEC2InstTypes:
                logging.info("%s: Unknown instance type '%s'", self.name, inst_type)
                continue

            inst_az = res_inst['AvailabilityZone']
            res_limits.setdefault(inst_az, {})[inst_type] = res_limits.get(inst_az, {}).get(
                inst_type, 0) + res_inst['InstanceCount']
        return res_limits

    def _add_addresses_limits(self, addresses):
        # Global limits
        vpc_addresses = 0
        std_addresses = 0
        for address in addresses:
            domain = address['Domain']
            if domain == "vpc":
                vpc_addresses += 1
            elif domain == "standard":
                std_addresses += 1
        self._add_limit(
            "", AWSLimit("vpc_elastic_ip_addresses", "VPC Elastic IP Addresses", 5, vpc_addresses))
        self._add_limit("",
                        AWSLimit("elastic_ip_addresses", "Elastic IP Addresses", 5, std_addresses))

    def _add_security_group_limits(self, instances, security_groups):
        # Security groups for EC2-Classic per instance
        # Rules per security group for EC2-Classic
        sgs_per_vpc = {}
        for sec_group in security_groups:
            vpc_id = sec_group['VpcId']
            if not vpc_id:
                continue
            inst = self._get_inst_assignment(instances, 'VpcId', vpc_id)
            if inst is None:
                continue
            inst_id = _get_ec2_piggyback_hostname(inst, self._region)
            key = (inst_id, vpc_id)
            sgs_per_vpc[key] = sgs_per_vpc.get(key, 0) + 1
            self._add_limit(
                inst_id,
                AWSLimit("vpc_sec_group_rules",
                         "Rules of VPC security group %s" % sec_group['GroupName'], 50,
                         len(sec_group['IpPermissions'])))

        for (inst_id, vpc_id), count in sgs_per_vpc.iteritems():
            self._add_limit(
                inst_id, AWSLimit("vpc_sec_groups", "Security Groups of VPC %s" % vpc_id, 500,
                                  count))

    def _get_inst_assignment(self, instances, key, assignment):
        for inst in instances.itervalues():
            if inst.get(key) == assignment:
                return inst

    def _add_interface_limits(self, instances, interfaces):
        # These limits are per security groups and
        # security groups are per instance
        for iface in interfaces:
            inst = self._get_inst_assignment(instances, 'VpcId', iface.get('VpcId'))
            if inst is None:
                continue
            self._add_limit(
                _get_ec2_piggyback_hostname(inst, self._region),
                AWSLimit(
                    "if_vpc_sec_group", "VPC security groups of elastic network interface %s" %
                    iface['NetworkInterfaceId'], 5, len(iface['Groups'])))

    def _add_spot_inst_limits(self, spot_inst_requests):
        count_spot_inst_reqs = 0
        for spot_inst_req in spot_inst_requests:
            if spot_inst_req['State'] in ['open', 'active']:
                count_spot_inst_reqs += 1
        self._add_limit(
            "", AWSLimit('spot_inst_requests', 'Spot Instance Requests', 20, count_spot_inst_reqs))

    def _add_spot_fleet_limits(self, spot_fleet_requests):
        active_spot_fleet_requests = 0
        total_target_cap = 0
        for spot_fleet_req in spot_fleet_requests:
            if spot_fleet_req['SpotFleetRequestState'] != 'active':
                continue

            active_spot_fleet_requests += 1
            total_target_cap += spot_fleet_req['SpotFleetRequestConfig']['TargetCapacity']

        self._add_limit(
            "",
            AWSLimit('active_spot_fleet_requests', 'Active Spot Fleet Requests', 1000,
                     active_spot_fleet_requests))
        self._add_limit(
            "",
            AWSLimit('spot_fleet_total_target_capacity',
                     'Spot Fleet Requests Total Target Capacity', 5000, total_target_cap))


class EC2Summary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EC2Summary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ec2_names']
        self._tags = self._config.service_config['ec2_tags']

    @property
    def name(self):
        return "ec2_summary"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_limits')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, colleague_contents):
        if self._tags is None and self._names is not None:
            return self._fetch_instances_filtered_by_names(colleague_contents.content)
        if self._tags is not None:
            return self._fetch_instances_filtered_by_tags(colleague_contents.content)
        return self._fetch_instances_without_filter()

    def _fetch_instances_filtered_by_names(self, col_reservations):
        if col_reservations:
            instances = [
                inst for res in col_reservations for inst in res['Instances']
                if inst['InstanceId'] in self._names
            ]
        else:
            response = self._client.describe_instances(InstanceIds=self._names)
            instances = [
                inst for res in self._get_response_content(response, 'Reservations')
                for inst in res['Instances']
            ]
        return instances

    def _fetch_instances_filtered_by_tags(self, col_reservations):
        if col_reservations:
            tags = self._prepare_tags_for_api_response(self._tags)
            instances = [
                inst for res in col_reservations
                for inst in res['Instances'] for tag in inst['Tags'] if tag in tags
            ]
        else:
            response = self._client.describe_instances(Filters=self._tags)
            instances = [
                inst for res in self._get_response_content(response, 'Reservations')
                for inst in res['Instances']
            ]
        return instances

    def _fetch_instances_without_filter(self):
        response = self._client.describe_instances()
        return [
            inst for res in self._get_response_content(response, 'Reservations')
            for inst in res['Instances']
        ]

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(self._format_instances(raw_content.content),
                                  raw_content.cache_timestamp)

    def _format_instances(self, instances):
        return {_get_ec2_piggyback_hostname(inst, self._region): inst for inst in instances}

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class EC2Labels(AWSSectionLabels):
    @property
    def name(self):
        return "ec2_labels"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._client.describe_tags(Filters=[{
            'Name': 'resource-id',
            'Values': [inst['InstanceId'] for inst in colleague_contents.content.itervalues()],
        }])
        return self._get_response_content(response, 'Tags')

    def _compute_content(self, raw_content, colleague_contents):
        inst_id_to_ec2_piggyback_hostname_map = {
            inst['InstanceId']: ec2_instance_id
            for ec2_instance_id, inst in colleague_contents.content.iteritems()
        }

        computed_content = {}
        for tag in raw_content.content:
            ec2_piggyback_hostname = inst_id_to_ec2_piggyback_hostname_map.get(tag['ResourceId'])
            if not ec2_piggyback_hostname:
                continue
            computed_content.setdefault(ec2_piggyback_hostname,
                                        {}).setdefault(tag['Key'], tag['Value'])

        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class EC2SecurityGroups(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EC2SecurityGroups, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ec2_names']
        self._tags = self._config.service_config['ec2_tags']

    @property
    def name(self):
        return "ec2_security_groups"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._describe_security_groups()
        return {
            group['GroupId']: group
            for group in self._get_response_content(response, 'SecurityGroups')
        }

    def _describe_security_groups(self):
        if self._names is not None:
            return self._client.describe_security_groups(InstanceIds=self._names)
        elif self._tags is not None:
            return self._client.describe_security_groups(Filters=self._tags)
        return self._client.describe_security_groups()

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for instance_name, instance in colleague_contents.content.iteritems():
            for security_group_from_instance in instance.get('SecurityGroups', []):
                security_group = raw_content.content.get(security_group_from_instance['GroupId'])
                if security_group is None:
                    continue
                content_by_piggyback_hosts.setdefault(instance_name, []).append(security_group)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


class EC2(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ec2"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (instance_name, instance) in enumerate(colleague_contents.content.iteritems()):
            instance_id = instance['InstanceId']
            for metric_name, unit in [
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("CPUUtilization", "Percent"),
                ("DiskReadOps", "Count"),
                ("DiskWriteOps", "Count"),
                ("DiskReadBytes", "Bytes"),
                ("DiskWriteBytes", "Bytes"),
                ("NetworkIn", "Bytes"),
                ("NetworkOut", "Bytes"),
                ("StatusCheckFailed_Instance", "Count"),
                ("StatusCheckFailed_System", "Count"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "InstanceId",
                                'Value': instance_id,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                        'Unit': unit,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# EBS are attached to EC2 instances. Thus we put the content to related EC2
# instance as piggyback host.


class EBSLimits(AWSSectionLimits):
    @property
    def name(self):
        return "ebs_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._client.describe_volumes()
        volumes = self._get_response_content(response, 'Volumes')

        response = self._client.describe_snapshots()
        snapshots = self._get_response_content(response, 'Snapshots')
        return volumes, snapshots

    def _compute_content(self, raw_content, colleague_contents):
        volumes, snapshots = raw_content.content

        vol_storage_standard = 0
        vol_storage_io1 = 0
        vol_storage_gp2 = 0
        vol_storage_sc1 = 0
        vol_storage_st1 = 0
        vol_iops_io1 = 0
        for volume in volumes:
            vol_type = volume['VolumeType']
            vol_size = volume['Size']
            if vol_type == 'standard':
                vol_storage_standard += vol_size
            elif vol_type == 'io1':
                vol_storage_io1 += vol_size
                vol_iops_io1 += volume['Iops']
            elif vol_type == 'gp2':
                vol_storage_gp2 += vol_size
            elif vol_type == 'sc1':
                vol_storage_sc1 += vol_size
            elif vol_type == 'st1':
                vol_storage_st1 += vol_size
            else:
                logging.info("%s: Unhandled volume type: '%s'", self.name, vol_type)

        # These are total limits and not instance specific
        # Space values are in TiB.
        self._add_limit(
            "", AWSLimit('block_store_snapshots', 'Block store snapshots', 100000, len(snapshots)))
        self._add_limit(
            "",
            AWSLimit('block_store_space_standard', 'Magnetic volumes space', 300,
                     vol_storage_standard))
        self._add_limit(
            "", AWSLimit('block_store_space_io1', 'Provisioned IOPS SSD space', 300,
                         vol_storage_io1))
        self._add_limit(
            "",
            AWSLimit('block_store_iops_io1', 'Provisioned IOPS SSD IO operations per second',
                     300000, vol_storage_io1))
        self._add_limit(
            "", AWSLimit('block_store_space_gp2', 'General Purpose SSD space', 300,
                         vol_storage_gp2))
        self._add_limit("", AWSLimit('block_store_space_sc1', 'Cold HDD space', 300,
                                     vol_storage_sc1))
        self._add_limit(
            "",
            AWSLimit('block_store_space_st1', 'Throughput Optimized HDD space', 300,
                     vol_storage_st1))
        return AWSComputedContent(volumes, raw_content.cache_timestamp)


class EBSSummary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EBSSummary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ebs_names']
        self._tags = self._config.service_config['ebs_tags']

    @property
    def name(self):
        return "ebs_summary"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ebs_limits')
        volumes = []
        max_cache_timestamp = 0.0
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            volumes = colleague.content

        colleague = self._received_results.get('ec2_summary')
        instances = []
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            instances = colleague.content

        return AWSColleagueContents((volumes, instances), max_cache_timestamp)

    def get_live_data(self, colleague_contents):
        col_volumes, _col_instances = colleague_contents.content
        if self._tags is None and self._names is not None:
            volumes = self._fetch_volumes_filtered_by_names(col_volumes)
        elif self._tags is not None:
            volumes = self._fetch_volumes_filtered_by_tags(col_volumes)
        else:
            volumes = self._fetch_volumes_without_filter()

        for vol_id, vol in volumes.iteritems():
            response = self._client.describe_volume_status(VolumeIds=[vol_id])
            for state in self._get_response_content(response, 'VolumeStatuses'):
                if state['VolumeId'] == vol_id:
                    vol.setdefault('VolumeStatus', state['VolumeStatus'])
        return volumes

    def _fetch_volumes_filtered_by_names(self, col_volumes):
        if col_volumes:
            return {vol['VolumeId']: vol for vol in col_volumes if vol['VolumeId'] in self._names}
        return self._format_volumes(self._client.describe_volumes(VolumeIds=self._names))

    def _fetch_volumes_filtered_by_tags(self, col_volumes):
        if col_volumes:
            tags = self._prepare_tags_for_api_response(self._tags)
            return {
                vol['VolumeId']: vol for vol in col_volumes for tag in vol['Tags'] if tag in tags
            }
        return self._format_volumes(self._client.describe_volumes(Filters=self._tags))

    def _fetch_volumes_without_filter(self):
        return self._format_volumes(self._client.describe_volumes())

    def _format_volumes(self, response):
        return {r['VolumeId']: r for r in self._get_response_content(response, 'Volumes')}

    def _compute_content(self, raw_content, colleague_contents):
        _col_volumes, col_instances = colleague_contents.content
        instance_name_mapping = {v['InstanceId']: k for k, v in col_instances.iteritems()}

        content_by_piggyback_hosts = {}
        for vol in raw_content.content.itervalues():
            instance_names = []
            for attachment in vol['Attachments']:
                # Just for security
                if vol['VolumeId'] != attachment['VolumeId']:
                    continue
                instance_name = instance_name_mapping.get(attachment['InstanceId'])
                if instance_name is None:
                    instance_name = ""
                instance_names.append(instance_name)

            # Should be attached to max. one instance
            for instance_name in instance_names:
                content_by_piggyback_hosts.setdefault(instance_name, [vol])
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


class EBS(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ebs"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ebs_summary')
        if colleague and colleague.content:
            return AWSColleagueContents([(instance_name, row['VolumeId'], row['VolumeType'])
                                         for instance_name, rows in colleague.content.iteritems()
                                         for row in rows], colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (instance_name, volume_name, volume_type) in enumerate(colleague_contents.content):
            for metric_name, unit, volume_types in [
                ("VolumeReadOps", "Count", []),
                ("VolumeWriteOps", "Count", []),
                ("VolumeReadBytes", "Bytes", []),
                ("VolumeWriteBytes", "Bytes", []),
                ("VolumeQueueLength", "Count", []),
                ("BurstBalance", "Percent", ["gp2", "st1", "sc1"]),
                    #("VolumeThroughputPercentage", "Percent", ["io1"]),
                    #("VolumeConsumedReadWriteOps", "Count", ["io1"]),
                    #("VolumeTotalReadTime", "Seconds", []),
                    #("VolumeTotalWriteTime", "Seconds", []),
                    #("VolumeIdleTime", "Seconds", []),
                    #("VolumeStatus", None, []),
                    #("IOPerformance", None, ["io1"]),
            ]:
                if volume_types and volume_type not in volume_types:
                    continue
                metric = {
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EBS',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "VolumeID",
                                'Value': volume_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                    },
                }
                if unit:
                    metric['MetricStat']['Unit'] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class S3Limits(AWSSectionLimits):
    @property
    def name(self):
        return "s3_limits"

    @property
    def cache_interval(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        """
        There's no API method for getting account limits thus we have to
        fetch all buckets.
        """
        response = self._client.list_buckets()
        return self._get_response_content(response, 'Buckets')

    def _compute_content(self, raw_content, colleague_contents):
        self._add_limit("", AWSLimit('buckets', 'Buckets', 100, len(raw_content.content)))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class S3Summary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(S3Summary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['s3_names']
        self._tags = self._prepare_tags_for_api_response(self._config.service_config['s3_tags'])

    @property
    def name(self):
        return "s3_summary"

    @property
    def cache_interval(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_limits')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, colleague_contents):
        found_buckets = []
        for bucket in self._list_buckets(colleague_contents):
            bucket_name = bucket['Name']

            # We can request buckets globally but if a bucket is located in
            # another region we do not get any results
            response = self._client.get_bucket_location(Bucket=bucket_name)
            location = self._get_response_content(response, 'LocationConstraint', dflt="")
            if location != self._region:
                continue
            bucket['LocationConstraint'] = location

            #TODO
            # Why do we get the following error while calling these methods:
            #_response = self._client.get_public_access_block(Bucket=bucket_name)
            #_response = self._client.get_bucket_policy_status(Bucket=bucket_name)
            # 'S3' object has no attribute 'get_bucket_policy_status'
            try:
                response = self._client.get_bucket_tagging(Bucket=bucket_name)
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.info("%s/%s: No tags set, %s", self.name, bucket_name, e)
                response = {}

            tagging = self._get_response_content(response, 'TagSet')
            if self._matches_tag_conditions(tagging):
                bucket['Tagging'] = tagging
                found_buckets.append(bucket)
        return found_buckets

    def _list_buckets(self, colleague_contents):
        if self._tags is None and self._names is not None:
            if colleague_contents.content:
                return [
                    bucket for bucket in colleague_contents.content if bucket['Name'] in self._names
                ]
            return [{'Name': n} for n in self._names]

        response = self._client.list_buckets()
        return self._get_response_content(response, 'Buckets')

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent({bucket['Name']: bucket for bucket in raw_content.content},
                                  raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", None)]


class S3(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3"

    @property
    def cache_interval(self):
        # BucketSizeBytes and NumberOfObjects are available per day
        # and must include 00:00h
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit, storage_classes in [
                ("BucketSizeBytes", "Bytes", [
                    "StandardStorage",
                    "StandardIAStorage",
                    "ReducedRedundancyStorage",
                ]),
                ("NumberOfObjects", "Count", ["AllStorageTypes"]),
            ]:
                for storage_class in storage_classes:
                    metrics.append({
                        'Id': self._create_id_for_metric_data_query(idx, metric_name,
                                                                    storage_class),
                        'Label': bucket_name,
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/S3',
                                'MetricName': metric_name,
                                'Dimensions': [{
                                    'Name': "BucketName",
                                    'Value': bucket_name,
                                }, {
                                    'Name': 'StorageType',
                                    'Value': storage_class,
                                }]
                            },
                            'Period': self.period,
                            'Stat': 'Average',
                            'Unit': unit,
                        },
                    })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row['Label'])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


class S3Requests(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3_requests"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit in [
                ("AllRequests", "Count"),
                ("GetRequests", "Count"),
                ("PutRequests", "Count"),
                ("DeleteRequests", "Count"),
                ("HeadRequests", "Count"),
                ("PostRequests", "Count"),
                ("SelectRequests", "Count"),
                ("SelectScannedBytes", "Bytes"),
                ("SelectReturnedBytes", "Bytes"),
                ("ListRequests", "Count"),
                ("BytesDownloaded", "Bytes"),
                ("BytesUploaded", "Bytes"),
                ("4xxErrors", "Count"),
                ("5xxErrors", "Count"),
                ("FirstByteLatency", "Milliseconds"),
                ("TotalRequestLatency", "Milliseconds"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': bucket_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/S3',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "BucketName",
                                'Value': bucket_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Sum',  #reports per period
                        'Unit': unit,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row['Label'])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBLimits(AWSSectionLimits):
    @property
    def name(self):
        return "elb_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        """
        The AWS/ELB API method 'describe_account_limits' provides limit values
        but no values about the usage per limit thus we have to gather the usage
        values from 'describe_load_balancers'.
        """
        response = self._client.describe_load_balancers()
        load_balancers = self._get_response_content(response, 'LoadBalancerDescriptions')

        response = self._client.describe_account_limits()
        limits = self._get_response_content(response, 'Limits')
        return load_balancers, limits

    def _compute_content(self, raw_content, colleague_contents):
        load_balancers, limits = raw_content.content
        limits = {r["Name"]: int(r['Max']) for r in limits}

        self._add_limit(
            "",
            AWSLimit("load_balancers", "Load balancers", limits['classic-load-balancers'],
                     len(load_balancers)))

        for load_balancer in load_balancers:
            dns_name = load_balancer['DNSName']
            self._add_limit(
                dns_name,
                AWSLimit("load_balancer_listeners", "Listeners", limits['classic-listeners'],
                         len(load_balancer['ListenerDescriptions'])))
            self._add_limit(
                dns_name,
                AWSLimit("load_balancer_registered_instances", "Registered instances",
                         limits['classic-registered-instances'], len(load_balancer['Instances'])))
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBSummaryGeneric(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None, resource=""):
        self._resource = resource
        super(ELBSummaryGeneric, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['%s_names' % resource]
        self._tags = self._prepare_tags_for_api_response(self._config.service_config['%s_tags' %
                                                                                     resource])

    @property
    def name(self):
        return "%s_summary" % self._resource

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('%s_limits' % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, colleague_contents):
        found_load_balancers = []
        for load_balancer in self._describe_load_balancers(colleague_contents):
            response = self._get_load_balancer_tags(load_balancer)
            tagging = [
                tag for tag_descr in self._get_response_content(response, 'TagDescriptions')
                for tag in tag_descr['Tags']
            ]
            if self._matches_tag_conditions(tagging):
                load_balancer['TagDescriptions'] = tagging
                found_load_balancers.append(load_balancer)
        return found_load_balancers

    def _get_load_balancer_tags(self, load_balancer):
        try:
            if self._resource == "elb":
                return self._client.describe_tags(
                    LoadBalancerNames=[load_balancer['LoadBalancerName']])
            elif self._resource == "elbv2":
                return self._client.describe_tags(ResourceArns=[load_balancer['LoadBalancerArn']])
            return {}
        except botocore.exceptions.ClientError as e:
            # If there are no tags attached to a bucket we receive a 'ClientError'
            logging.info("%s/%s: No tags set, %s", self.name, load_balancer['LoadBalancerName'], e)
            return {}

    def _describe_load_balancers(self, colleague_contents):
        if self._tags is None and self._names is not None:
            if colleague_contents.content:
                return [
                    load_balancer for load_balancer in colleague_contents.content
                    if load_balancer['LoadBalancerName'] in self._names
                ]
            response = self._client.describe_load_balancers(LoadBalancerNames=self._names)

        else:
            if colleague_contents.content:
                return colleague_contents.content

            response = self._client.describe_load_balancers()

        if self._resource == "elb":
            response_key = "LoadBalancerDescriptions"
        elif self._resource == "elbv2":
            response_key = "LoadBalancers"
        else:
            response_key = None
        return self._get_response_content(response, response_key)

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for load_balancer in raw_content.content:
            content_by_piggyback_hosts.setdefault(load_balancer['DNSName'], load_balancer)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class ELBLabelsGeneric(AWSSectionLabels):
    def __init__(self, client, region, config, distributor=None, resource=""):
        self._resource = resource
        super(ELBLabelsGeneric, self).__init__(client, region, config, distributor=distributor)

    @property
    def name(self):
        return "%s_generic_labels" % self._resource

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('%s_summary' % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, colleague_contents):
        return colleague_contents.content

    def _compute_content(self, raw_content, colleague_contents):
        computed_content = {
            elb_instance_id: {tag['Key']: tag['Value'] for tag in data.get('TagDescriptions', [])
                             } for elb_instance_id, data in raw_content.content.iteritems()
        }
        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class ELBHealth(AWSSectionGeneric):
    @property
    def name(self):
        return "elb_health"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elb_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, colleague_contents):
        load_balancers = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.iteritems():
            load_balancer_name = load_balancer['LoadBalancerName']
            response = self._client.describe_instance_health(LoadBalancerName=load_balancer_name)
            states = self._get_response_content(response, 'InstanceStates')
            if states:
                load_balancers.setdefault(load_balancer_dns_name, states)
        return load_balancers

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.iteritems()
        ]


class ELB(AWSSectionCloudwatch):
    @property
    def name(self):
        return "elb"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elb_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (load_balancer_dns_name,
                  load_balancer) in enumerate(colleague_contents.content.iteritems()):
            load_balancer_name = load_balancer['LoadBalancerName']
            for metric_name, stat in [
                ("RequestCount", "Sum"),
                ("SurgeQueueLength", "Maximum"),
                ("SpilloverCount", "Sum"),
                ("Latency", "Average"),
                ("HTTPCode_ELB_4XX", "Sum"),
                ("HTTPCode_ELB_5XX", "Sum"),
                ("HTTPCode_Backend_2XX", "Sum"),
                ("HTTPCode_Backend_3XX", "Sum"),
                ("HTTPCode_Backend_4XX", "Sum"),
                ("HTTPCode_Backend_5XX", "Sum"),
                ("HealthyHostCount", "Average"),
                ("UnHealthyHostCount", "Average"),
                ("BackendConnectionErrors", "Sum"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': load_balancer_dns_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ELB',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "LoadBalancerName",
                                'Value': load_balancer_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': stat,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--ELBv2---------------------------------------------------------------.
#   |                    _____ _     ____       ____                       |
#   |                   | ____| |   | __ )_   _|___ \                      |
#   |                   |  _| | |   |  _ \ \ / / __) |                     |
#   |                   | |___| |___| |_) \ V / / __/                      |
#   |                   |_____|_____|____/ \_/ |_____|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Limits(AWSSectionLimits):
    @property
    def name(self):
        return "elbv2_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        """
        The AWS/ELBv2 API method 'describe_account_limits' provides limit values
        but no values about the usage per limit thus we have to gather the usage
        values from 'describe_load_balancers'.
        """
        response = self._client.describe_load_balancers()
        load_balancers = self._get_response_content(response, 'LoadBalancers')

        for load_balancer in load_balancers:
            lb_arn = load_balancer['LoadBalancerArn']

            response = self._client.describe_target_groups(LoadBalancerArn=lb_arn)
            load_balancer['TargetGroups'] = self._get_response_content(response, 'TargetGroups')

            response = self._client.describe_listeners(LoadBalancerArn=lb_arn)
            listeners = self._get_response_content(response, 'Listeners')
            load_balancer['Listeners'] = listeners

            if load_balancer['Type'] == "application":
                rules = []
                for listener in listeners:
                    response = self._client.describe_rules(ListenerArn=listener['ListenerArn'])
                    rules.extend(self._get_response_content(response, 'Rules'))

                # Limit 100 holds for rules which are not default, see AWS docs:
                # https://docs.aws.amazon.com/de_de/general/latest/gr/aws_service_limits.html
                # > Limits für Elastic Load Balancing
                load_balancer['Rules'] = [rule for rule in rules if not rule['IsDefault']]

        response = self._client.describe_account_limits()
        limits = self._get_response_content(response, 'Limits')
        return load_balancers, limits

    def _compute_content(self, raw_content, colleague_contents):
        load_balancers, limits = raw_content.content
        limits = {r["Name"]: int(r['Max']) for r in limits}

        alb_count = 0
        nlb_count = 0
        target_groups_count = 0
        for load_balancer in load_balancers:
            lb_dns_name = load_balancer['DNSName']
            lb_type = load_balancer['Type']

            lb_listeners_count = len(load_balancer.get('Listeners', []))
            lb_target_groups_count = len(load_balancer.get('TargetGroups', []))
            target_groups_count += lb_target_groups_count

            if lb_type == "application":
                alb_count += 1
                key = 'application'
                title = 'Application'
                self._add_limit(
                    lb_dns_name,
                    AWSLimit("application_load_balancer_rules", "Application Load Balancer Rules",
                             limits['rules-per-application-load-balancer'],
                             len(load_balancer.get('Rules', []))))

                self._add_limit(
                    lb_dns_name,
                    AWSLimit(
                        "application_load_balancer_certificates",
                        "Application Load Balancer Certificates", 25,
                        len([
                            cert for cert in load_balancer.get('Certificates', [])
                            if not cert['IsDefault']
                        ])))

            elif lb_type == "network":
                nlb_count += 1
                key = 'network'
                title = 'Network'

            else:
                continue

            self._add_limit(
                lb_dns_name,
                AWSLimit("%s_load_balancer_listeners" % key, "%s Load Balancer Listeners" % title,
                         limits['listeners-per-%s-load-balancer' % key], lb_listeners_count))

            self._add_limit(
                lb_dns_name,
                AWSLimit("%s_load_balancer_target_groups" % key,
                         "%s Load Balancer Target Groups" % title,
                         limits['targets-per-%s-load-balancer' % key], lb_target_groups_count))

        self._add_limit(
            "",
            AWSLimit("application_load_balancers", "Application Load balancers",
                     limits['application-load-balancers'], alb_count))

        self._add_limit(
            "",
            AWSLimit("network_load_balancers", "Network Load balancers",
                     limits['network-load-balancers'], nlb_count))

        self._add_limit(
            "",
            AWSLimit("load_balancer_target_groups", "Load balancers Target Groups",
                     limits['target-groups'], target_groups_count))
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBv2TargetGroups(AWSSectionGeneric):
    @property
    def name(self):
        return "elbv2_target_groups"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elbv2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def get_live_data(self, colleague_contents):
        load_balancers = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.iteritems():
            load_balancer_type = load_balancer.get('Type')
            if load_balancer_type not in ['application', 'network']:
                # Just to be sure, that we do not describe target groups of other lbs
                continue

            if 'TargetGroups' not in load_balancer:
                response = self._client.describe_target_groups(
                    LoadBalancerArn=load_balancer['LoadBalancerArn'])
                load_balancer['TargetGroups'] = self._get_response_content(response, 'TargetGroups')

            target_groups = load_balancer.get('TargetGroups', [])
            for target_group in target_groups:
                response = self._client.describe_target_health(
                    TargetGroupArn=target_group['TargetGroupArn'])
                target_group_health_descrs = self._get_response_content(
                    response, 'TargetHealthDescriptions')
                target_group['TargetHealthDescriptions'] = target_group_health_descrs

            load_balancers.setdefault(load_balancer_dns_name, []).append(
                (load_balancer_type, target_groups))
        return load_balancers

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.iteritems()
        ]


#.
#   .--Application ELB-----------------------------------------------------.
#   |            _                _ _           _   _                      |
#   |           / \   _ __  _ __ | (_) ___ __ _| |_(_) ___  _ __           |
#   |          / _ \ | '_ \| '_ \| | |/ __/ _` | __| |/ _ \| '_ \          |
#   |         / ___ \| |_) | |_) | | | (_| (_| | |_| | (_) | | | |         |
#   |        /_/   \_\ .__/| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|         |
#   |                |_|   |_|                                             |
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Application(AWSSectionCloudwatch):
    @property
    def name(self):
        return "elbv2_application"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elbv2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (load_balancer_dns_name,
                  load_balancer) in enumerate(colleague_contents.content.iteritems()):
            # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/load-balancer-name/load-balancer-id
            # We need: app/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
            load_balancer_dim = "/".join(load_balancer['LoadBalancerArn'].split("/")[-3:])
            for metric_name, stat in [
                ('ActiveConnectionCount', 'Sum'),
                ('ClientTLSNegotiationErrorCount', 'Sum'),
                ('ConsumedLCUs', 'Sum'),
                ('HTTP_Fixed_Response_Count', 'Sum'),
                ('HTTP_Redirect_Count', 'Sum'),
                ('HTTP_Redirect_Url_Limit_Exceeded_Count', 'Sum'),
                ('HTTPCode_ELB_3XX_Count', 'Sum'),
                ('HTTPCode_ELB_4XX_Count', 'Sum'),
                ('HTTPCode_ELB_5XX_Count', 'Sum'),
                ('HTTPCode_ELB_500_Count', 'Sum'),
                ('HTTPCode_ELB_502_Count', 'Sum'),
                ('HTTPCode_ELB_503_Count', 'Sum'),
                ('HTTPCode_ELB_504_Count', 'Sum'),
                ('IPv6ProcessedBytes', 'Sum'),
                ('IPv6RequestCount', 'Sum'),
                ('NewConnectionCount', 'Sum'),
                ('ProcessedBytes', 'Sum'),
                ('RejectedConnectionCount', 'Sum'),
                ('RequestCount', 'Sum'),
                ('RuleEvaluations', 'Sum'),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': load_balancer_dns_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ApplicationELB',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "LoadBalancer",
                                'Value': load_balancer_dim,
                            }]
                        },
                        'Period': self.period,
                        'Stat': stat,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--Network ELB---------------------------------------------------------.
#   |     _   _      _                      _      _____ _     ____        |
#   |    | \ | | ___| |___      _____  _ __| | __ | ____| |   | __ )       |
#   |    |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / |  _| | |   |  _ \       |
#   |    | |\  |  __/ |_ \ V  V / (_) | |  |   <  | |___| |___| |_) |      |
#   |    |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |_____|_____|____/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBv2Network(AWSSectionCloudwatch):
    @property
    def name(self):
        return "elbv2_network"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elbv2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (load_balancer_dns_name,
                  load_balancer) in enumerate(colleague_contents.content.iteritems()):
            # arn:aws:elasticloadbalancing:region:account-id:loadbalancer/net/load-balancer-name/load-balancer-id
            # We need: net/LOAD-BALANCER-NAME/LOAD-BALANCER-ID
            load_balancer_dim = "/".join(load_balancer['LoadBalancerArn'].split("/")[-3:])
            for metric_name, stat in [
                ('ActiveFlowCount', 'Average'),
                ('ActiveFlowCount_TLS', 'Average'),
                ('ClientTLSNegotiationErrorCount', 'Sum'),
                ('ConsumedLCUs', 'Sum'),
                ('HealthyHostCount', 'Maximum'),
                ('NewFlowCount', 'Sum'),
                ('NewFlowCount_TLS', 'Sum'),
                ('ProcessedBytes', 'Sum'),
                ('ProcessedBytes_TLS', 'Sum'),
                ('TargetTLSNegotiationErrorCount', 'Sum'),
                ('TCP_Client_Reset_Count', 'Sum'),
                ('TCP_ELB_Reset_Count', 'Sum'),
                ('TCP_Target_Reset_Count', 'Sum'),
                ('UnHealthyHostCount', 'Maximum'),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': load_balancer_dns_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/NetworkELB',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "LoadBalancer",
                                'Value': load_balancer_dim,
                            }]
                        },
                        'Period': self.period,
                        'Stat': stat,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AWSRDSLimitNameMap = {
    "DBClusters": ("db_clusters", "DB clusters"),
    "DBClusterParameterGroups": ("db_cluster_parameter_groups", "DB cluster parameter groups"),
    "DBInstances": ("db_instances", "DB instances"),
    "EventSubscriptions": ("event_subscriptions", "Event subscriptions"),
    "ManualSnapshots": ("manual_snapshots", "Manual snapshots"),
    "OptionGroups": ("option_groups", "Option groups"),
    "DBParameterGroups": ("db_parameter_groups", "DB parameter groups"),
    "ReadReplicasPerMaster": ("read_replica_per_master", "Read replica per master"),
    "ReservedDBInstances": ("reserved_db_instances", "Reserved DB instances"),
    "DBSecurityGroups": ("db_security_groups", "DB security groups"),
    "DBSubnetGroups": ("db_subnet_groups", "DB subnet groups"),
    "SubnetsPerDBSubnetGroup": ("subnet_per_db_subnet_groups", "Subnet per DB subnet groups"),
    "AllocatedStorage": ("allocated_storage", "Allocated storage"),
    "AuthorizationsPerDBSecurityGroup":
        ("auths_per_db_security_groups", "Authorizations per DB security group"),
    "DBClusterRoles": ("db_cluster_roles", "DB cluster roles"),
}


class RDSLimits(AWSSectionLimits):
    @property
    def name(self):
        return "rds_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        """
        AWS/RDS API method 'describe_account_attributes' already sends
        limit and usage values.
        """
        response = self._client.describe_account_attributes()
        return self._get_response_content(response, 'AccountQuotas')

    def _compute_content(self, raw_content, colleague_contents):
        for limit in raw_content.content:
            quota_name = limit['AccountQuotaName']
            key, title = AWSRDSLimitNameMap.get(quota_name, (None, None))
            if key is None or title is None:
                logging.info("%s: Unhandled account quota name: '%s'", self.name, quota_name)
                continue
            self._add_limit("", AWSLimit(key, title, int(limit['Max']), int(limit['Used'])))
        return AWSComputedContent(None, 0.0)


class RDSSummary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(RDSSummary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['rds_names']
        self._tags = self._config.service_config['rds_tags']

    @property
    def name(self):
        return "rds_summary"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._describe_db_instances()
        return self._get_response_content(response, 'DBInstances')

    def _describe_db_instances(self):
        if self._names is not None:
            return [
                self._client.describe_db_instances(DBInstanceIdentifier=name)
                for name in self._names
            ]
        elif self._tags is not None:
            return [self._client.describe_db_instances(Filters=self._tags) for name in self._names]
        return self._client.describe_db_instances()

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            {instance['DBInstanceIdentifier']: instance for instance in raw_content.content},
            raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class RDS(AWSSectionCloudwatch):
    @property
    def name(self):
        return "rds"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('rds_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, instance_id in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit in [
                ("BinLogDiskUsage", "Bytes"),
                ("BurstBalance", "Percent"),
                ("CPUUtilization", "Percent"),
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("DatabaseConnections", "Count"),
                ("DiskQueueDepth", "Count"),
                ("FailedSQLServerAgentJobsCount", "Count/Second"),
                ("NetworkReceiveThroughput", "Bytes/Second"),
                ("NetworkTransmitThroughput", "Bytes/Second"),
                ("OldestReplicationSlotLag", "Megabytes"),
                ("ReadIOPS", "Count/Second"),
                ("ReadLatency", "Seconds"),
                ("ReadThroughput", "Bytes/Second"),
                ("ReplicaLag", "Seconds"),
                ("ReplicationSlotDiskUsage", "Megabytes"),
                ("TransactionLogsDiskUsage", "Megabytes"),
                ("TransactionLogsGeneration", "Megabytes/Second"),
                ("WriteIOPS", "Count/Second"),
                ("WriteLatency", "Seconds"),
                ("WriteThroughput", "Bytes/Second"),
                    #("FreeableMemory", "Bytes"),
                    #("SwapUsage", "Bytes"),
                    #("FreeStorageSpace", "Bytes"),
                    #("MaximumUsedTransactionIDs", "Count"),
            ]:
                metric = {
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_id,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/RDS',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "DBInstanceIdentifier",
                                'Value': instance_id,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                    },
                }
                if unit:
                    metric['MetricStat']['Unit'] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            row.update(colleague_contents.content.get(row['Label'], {}))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--Cloudwatch----------------------------------------------------------.
#   |         ____ _                 _               _       _             |
#   |        / ___| | ___  _   _  __| |_      ____ _| |_ ___| |__          |
#   |       | |   | |/ _ \| | | |/ _` \ \ /\ / / _` | __/ __| '_ \         |
#   |       | |___| | (_) | |_| | (_| |\ V  V / (_| | || (__| | | |        |
#   |        \____|_|\___/ \__,_|\__,_| \_/\_/ \__,_|\__\___|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CloudwatchAlarmsLimits(AWSSectionLimits):
    @property
    def name(self):
        return "cloudwatch_alarms_limits"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def get_live_data(self, colleague_contents):
        response = self._client.describe_alarms()
        return self._get_response_content(response, 'MetricAlarms')

    def _compute_content(self, raw_content, colleague_contents):
        self._add_limit(
            "", AWSLimit('cloudwatch_alarms', 'Cloudwatch Alarms', 5000, len(raw_content.content)))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class CloudwatchAlarms(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(CloudwatchAlarms, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['cloudwatch_alarms']

    @property
    def name(self):
        return "cloudwatch_alarms"

    @property
    def cache_interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('cloudwatch_alarms_limits')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def get_live_data(self, colleague_contents):
        if self._names:
            if colleague_contents.content:
                return [
                    alarm for alarm in colleague_contents.content
                    if alarm['AlarmName'] in self._names
                ]
            response = self._client.describe_alarms(AlarmNames=self._names)
        else:
            response = self._client.describe_alarms()
        return self._get_response_content(response, 'MetricAlarms')

    def _compute_content(self, raw_content, colleague_contents):
        if raw_content.content:
            return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)
        dflt_alarms = [{'AlarmName': 'Check_MK/Cloudwatch Alarms', 'StateValue': 'NO_ALARMS'}]
        return AWSComputedContent(dflt_alarms, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--sections------------------------------------------------------------.
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSSections(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, hostname, session, debug=False):
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections = []

    @abc.abstractmethod
    def init_sections(self, services, region, config):
        pass

    def _init_client(self, client_key):
        try:
            return self._session.client(client_key)
        except (ValueError, botocore.exceptions.ClientError,
                botocore.exceptions.UnknownServiceError) as e:
            # If region name is not valid we get a ValueError
            # but not in all cases, eg.:
            # 1. 'eu-central-' raises a ValueError
            # 2. 'foobar' does not raise a ValueError
            # In the second case we get an exception raised by botocore
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs):
            # - botocore.exceptions.EndpointConnectionError
            logging.info("Invalid region name or client key %s: %s", client_key, e)
            raise

    def run(self, use_cache=True):
        exceptions = []
        results = {}
        for section in self._sections:
            try:
                section_result = section.run(use_cache=use_cache)
            except AssertionError as e:
                logging.info(e)
                if self._debug:
                    raise
            except Exception as e:
                logging.info("%s: %s", section.__class__.__name__, e)
                if self._debug:
                    raise
                exceptions.append(e)
            else:
                results.setdefault(
                    (section.name, section_result.cache_timestamp, section.cache_interval),
                    section_result.results)

        self._write_exceptions(exceptions)
        self._write_section_results(results)

    def _write_exceptions(self, exceptions):
        sys.stdout.write("<<<aws_exceptions>>>\n")
        if exceptions:
            out = "\n".join([e.message for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write("%s: %s\n" % (self.__class__.__name__, out))

    def _write_section_results(self, results):
        if not results:
            logging.info("%s: No results or cached data", self.__class__.__name__)
            return

        for (section_name, cache_timestamp, section_interval), result in results.iteritems():
            if not result:
                logging.info("%s: No results", section_name)
                continue

            if not isinstance(result, list):
                logging.info(
                    "%s: Section result must be of type 'list' containing 'AWSSectionResults'",
                    section_name)
                continue

            cached_suffix = ""
            if section_interval > 60:
                cached_suffix = ":cached(%s,%s)" % (int(cache_timestamp), section_interval + 60)

            if any([r.content for r in result]):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(self, section_name, cached_suffix, result):
        if section_name.endswith("labels"):
            section_header = "<<<%s:sep(0)%s>>>\n" % (section_name, cached_suffix)
        else:
            section_header = "<<<aws_%s%s>>>\n" % (section_name, cached_suffix)

        for row in result:
            write_piggyback_header = row.piggyback_hostname\
                                     and row.piggyback_hostname != self._hostname
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % row.piggyback_hostname)
            sys.stdout.write(section_header)
            sys.stdout.write("%s\n" % json.dumps(row.content, default=datetime_serializer))
            if write_piggyback_header:
                sys.stdout.write("<<<<>>>>\n")


class AWSSectionsUSEast(AWSSections):
    """
    Some clients like CostExplorer only work with US East region:
    https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html
    """
    def init_sections(self, services, region, config):
        #---clients---------------------------------------------------------
        ce_client = self._init_client('ce')

        #---distributors----------------------------------------------------

        #---sections with distributors--------------------------------------

        #---sections--------------------------------------------------------
        ce = CostsAndUsage(ce_client, region, config)

        #---register sections to distributors-------------------------------

        #---register sections for execution---------------------------------
        if 'ce' in services:
            self._sections.append(ce)


class AWSSectionsGeneric(AWSSections):
    def init_sections(self, services, region, config):
        #---clients---------------------------------------------------------
        ec2_client = self._init_client('ec2')
        elb_client = self._init_client('elb')
        elbv2_client = self._init_client('elbv2')
        s3_client = self._init_client('s3')
        rds_client = self._init_client('rds')
        cloudwatch_client = self._init_client('cloudwatch')

        #---distributors----------------------------------------------------
        ec2_limits_distributor = ResultDistributor()
        ec2_summary_distributor = ResultDistributor()

        elb_limits_distributor = ResultDistributor()
        elb_summary_distributor = ResultDistributor()

        elbv2_limits_distributor = ResultDistributor()
        elbv2_summary_distributor = ResultDistributor()

        ebs_limits_distributor = ResultDistributor()
        ebs_summary_distributor = ResultDistributor()

        s3_limits_distributor = ResultDistributor()
        s3_summary_distributor = ResultDistributor()

        rds_summary_distributor = ResultDistributor()

        cloudwatch_alarms_limits_distributor = ResultDistributor()

        #---sections with distributors--------------------------------------
        ec2_limits = EC2Limits(ec2_client, region, config, ec2_limits_distributor)
        ec2_summary = EC2Summary(ec2_client, region, config, ec2_summary_distributor)

        ebs_limits = EBSLimits(ec2_client, region, config, ebs_limits_distributor)
        ebs_summary = EBSSummary(ec2_client, region, config, ebs_summary_distributor)

        elb_limits = ELBLimits(elb_client, region, config, elb_limits_distributor)
        elb_summary = ELBSummaryGeneric(elb_client,
                                        region,
                                        config,
                                        elb_summary_distributor,
                                        resource='elb')

        elbv2_limits = ELBv2Limits(elbv2_client, region, config, elbv2_limits_distributor)
        elbv2_summary = ELBSummaryGeneric(elbv2_client,
                                          region,
                                          config,
                                          elbv2_summary_distributor,
                                          resource='elbv2')

        s3_limits = S3Limits(s3_client, region, config, s3_limits_distributor)
        s3_summary = S3Summary(s3_client, region, config, s3_summary_distributor)

        rds_summary = RDSSummary(rds_client, region, config, rds_summary_distributor)

        cloudwatch_alarms_limits = CloudwatchAlarmsLimits(cloudwatch_client, region, config,
                                                          cloudwatch_alarms_limits_distributor)

        #---sections--------------------------------------------------------
        ec2_labels = EC2Labels(ec2_client, region, config)
        ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
        ec2 = EC2(cloudwatch_client, region, config)

        ebs = EBS(cloudwatch_client, region, config)

        elb_labels = ELBLabelsGeneric(elb_client, region, config, resource='elb')
        elb_health = ELBHealth(elb_client, region, config)
        elb = ELB(cloudwatch_client, region, config)

        elbv2_labels = ELBLabelsGeneric(elbv2_client, region, config, resource='elbv2')
        elbv2_target_groups = ELBv2TargetGroups(elbv2_client, region, config)
        elbv2_application = ELBv2Application(cloudwatch_client, region, config)
        elbv2_network = ELBv2Network(cloudwatch_client, region, config)

        s3 = S3(cloudwatch_client, region, config)
        s3_requests = S3Requests(cloudwatch_client, region, config)

        rds_limits = RDSLimits(rds_client, region, config)
        rds = RDS(cloudwatch_client, region, config)

        cloudwatch_alarms = CloudwatchAlarms(cloudwatch_client, region, config)

        #---register sections to distributors-------------------------------
        ec2_limits_distributor.add(ec2_summary)
        ec2_summary_distributor.add(ec2_labels)
        ec2_summary_distributor.add(ec2_security_groups)
        ec2_summary_distributor.add(ec2)
        ec2_summary_distributor.add(ebs_summary)

        ebs_limits_distributor.add(ebs_summary)
        ebs_summary_distributor.add(ebs)

        elb_limits_distributor.add(elb_summary)
        elb_summary_distributor.add(elb_labels)
        elb_summary_distributor.add(elb_health)
        elb_summary_distributor.add(elb)

        elbv2_limits_distributor.add(elbv2_summary)
        elbv2_summary_distributor.add(elbv2_labels)
        elbv2_summary_distributor.add(elbv2_target_groups)
        elbv2_summary_distributor.add(elbv2_application)
        elbv2_summary_distributor.add(elbv2_network)

        s3_limits_distributor.add(s3_summary)
        s3_summary_distributor.add(s3)
        s3_summary_distributor.add(s3_requests)

        rds_summary_distributor.add(rds)

        cloudwatch_alarms_limits_distributor.add(cloudwatch_alarms)

        #---register sections for execution---------------------------------
        if 'ec2' in services:
            if config.service_config.get('ec2_limits'):
                self._sections.append(ec2_limits)
            self._sections.append(ec2_summary)
            self._sections.append(ec2_labels)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if 'ebs' in services:
            if config.service_config.get('ebs_limits'):
                self._sections.append(ebs_limits)
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if 'elb' in services:
            if config.service_config.get('elb_limits'):
                self._sections.append(elb_limits)
            self._sections.append(elb_summary)
            self._sections.append(elb_labels)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if 'elbv2' in services:
            if config.service_config.get('elbv2_limits'):
                self._sections.append(elbv2_limits)
            self._sections.append(elbv2_summary)
            self._sections.append(elbv2_labels)
            self._sections.append(elbv2_target_groups)
            #TODO enable when checks are ready
            #self._sections.append(elbv2_application)
            #self._sections.append(elbv2_network)

        if 's3' in services:
            if config.service_config.get('s3_limits'):
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config['s3_requests']:
                self._sections.append(s3_requests)

        if 'rds' in services:
            if config.service_config.get('rds_limits'):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)

        if 'cloudwatch' in services:
            if config.service_config.get('cloudwatch_alarms_limits'):
                self._sections.append(cloudwatch_alarms_limits)
            if 'cloudwatch_alarms' in config.service_config:
                self._sections.append(cloudwatch_alarms)


#.
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AWSServiceAttributes = NamedTuple("AWSServiceAttributes", [
    ("key", str),
    ("title", str),
    ("global_service", bool),
    ("filter_by_names", bool),
    ("filter_by_tags", bool),
    ("limits", bool),
])

AWSServices = [
    AWSServiceAttributes(key="ce",
                         title="Costs and usage",
                         global_service=True,
                         filter_by_names=False,
                         filter_by_tags=False,
                         limits=False),
    AWSServiceAttributes(key="ec2",
                         title="Elastic Compute Cloud (EC2)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="ebs",
                         title="Elastic Block Storage (EBS)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="s3",
                         title="Simple Storage Service (S3)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="elb",
                         title="Classic Load Balancing (ELB)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="elbv2",
                         title="Application and Network Load Balancing (ELBv2)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="rds",
                         title="Relational Database Service (RDS)",
                         global_service=False,
                         filter_by_names=True,
                         filter_by_tags=True,
                         limits=True),
    AWSServiceAttributes(key="cloudwatch",
                         title="Cloudwatch",
                         global_service=False,
                         filter_by_names=False,
                         filter_by_tags=False,
                         limits=True),
]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument("--verbose",
                        action="store_true",
                        help="Log messages from AWS library 'boto3' and 'botocore'.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Execute all sections, do not rely on cached data. Cached data will not be overwritten."
    )

    parser.add_argument("--access-key-id",
                        required=True,
                        help="The access key ID for your AWS account.")
    parser.add_argument("--secret-access-key",
                        required=True,
                        help="The secret access key for your AWS account.")
    parser.add_argument("--regions",
                        nargs='+',
                        help="Regions to use:\n%s" %
                        "\n".join(["%-15s %s" % e for e in AWSRegions]))

    parser.add_argument(
        "--global-services",
        nargs='+',
        help="Global services to monitor:\n%s" %
        "\n".join(["%-15s %s" % (e.key, e.title) for e in AWSServices if e.global_service]))

    parser.add_argument(
        "--services",
        nargs='+',
        help="Services per region to monitor:\n%s" %
        "\n".join(["%-15s %s" % (e.key, e.title) for e in AWSServices if not e.global_service]))

    for service in AWSServices:
        if service.filter_by_names:
            parser.add_argument('--%s-names' % service.key,
                                nargs='+',
                                help="Names for %s" % service.title)
        if service.filter_by_tags:
            parser.add_argument('--%s-tag-key' % service.key,
                                nargs=1,
                                action='append',
                                help="Tag key for %s" % service.title)
            parser.add_argument('--%s-tag-values' % service.key,
                                nargs='+',
                                action='append',
                                help="Tag values for %s" % service.title)
        if service.limits:
            parser.add_argument('--%s-limits' % service.key,
                                action="store_true",
                                help="Monitor limits for %s" % service.title)

    parser.add_argument(
        "--s3-requests",
        action="store_true",
        help="You have to enable requests metrics in AWS/S3 console. This is a paid feature.")

    parser.add_argument("--cloudwatch-alarms", nargs='*')

    parser.add_argument('--overall-tag-key', nargs=1, action='append', help="Overall tag key")
    parser.add_argument('--overall-tag-values',
                        nargs='+',
                        action='append',
                        help="Overall tag values")

    parser.add_argument("--hostname", required=True)
    return parser.parse_args(argv)


def setup_logging(opt_debug, opt_verbose):
    logger = logging.getLogger()
    logger.disabled = True
    fmt = '%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s'
    lvl = logging.INFO
    if opt_verbose:
        logger.disabled = False
        lvl = logging.DEBUG
    elif opt_debug:
        logger.disabled = False
    logging.basicConfig(level=lvl, format=fmt)


def create_session(access_key_id, secret_access_key, region):
    return boto3.session.Session(aws_access_key_id=access_key_id,
                                 aws_secret_access_key=secret_access_key,
                                 region_name=region)


class AWSConfig(object):
    def __init__(self, hostname, overall_tags):
        self.hostname = hostname
        self._overall_tags = self._prepare_tags(overall_tags)
        self.service_config = {}

    def add_service_tags(self, tags_key, tags):
        """Convert commandline input
        from
            ([['foo'], ['aaa'], ...], [['bar', 'baz'], ['bbb', 'ccc'], ...])
        to
            Filters=[{'Name': 'tag:foo', 'Values': ['bar', 'baz']},
                     {'Name': 'tag:aaa', 'Values': ['bbb', 'ccc']}, ...]
        as we need in API methods if and only if keys AND values are set.
        """
        self.service_config.setdefault(tags_key, None)
        if tags != (None, None):
            self.service_config[tags_key] = self._prepare_tags(tags)
        elif self._overall_tags:
            self.service_config[tags_key] = self._overall_tags

    def _prepare_tags(self, tags):
        keys, values = tags
        if keys and values:
            return [{
                'Name': 'tag:%s' % k,
                'Values': v
            } for k, v in zip([k[0] for k in keys], values)]
        return

    def add_single_service_config(self, key, value):
        self.service_config.setdefault(key, value)


def main(args=None):
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]

    args = parse_arguments(args)
    setup_logging(args.debug, args.verbose)
    hostname = args.hostname

    aws_config = AWSConfig(hostname, (args.overall_tag_key, args.overall_tag_values))
    for service_key, service_names, service_tags, service_limits in [
        ("ec2", args.ec2_names, (args.ec2_tag_key, args.ec2_tag_values), args.ec2_limits),
        ("ebs", args.ebs_names, (args.ebs_tag_key, args.ebs_tag_values), args.ebs_limits),
        ("s3", args.s3_names, (args.s3_tag_key, args.s3_tag_values), args.s3_limits),
        ("elb", args.elb_names, (args.elb_tag_key, args.elb_tag_values), args.elb_limits),
        ("elbv2", args.elbv2_names, (args.elbv2_tag_key, args.elbv2_tag_values), args.elbv2_limits),
        ("rds", args.rds_names, (args.rds_tag_key, args.rds_tag_values), args.rds_limits),
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    aws_config.add_single_service_config("s3_requests", args.s3_requests)
    aws_config.add_single_service_config("cloudwatch_alarms", args.cloudwatch_alarms)

    has_exceptions = False
    for aws_services, aws_regions, aws_sections in [
        (args.global_services, ["us-east-1"], AWSSectionsUSEast),
        (args.services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue
        for region in aws_regions:
            try:
                session = create_session(args.access_key_id, args.secret_access_key, region)
                sections = aws_sections(hostname, session, debug=args.debug)
                sections.init_sections(aws_services, region, aws_config)
                sections.run(use_cache=not args.no_cache)
            except AssertionError:
                if args.debug:
                    return 1
            except Exception as e:
                logging.info(e)
                has_exceptions = True
                if args.debug:
                    return 1
    if has_exceptions:
        return 1
    return 0
