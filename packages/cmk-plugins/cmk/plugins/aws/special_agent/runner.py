#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import abc
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import override

import boto3
import botocore
from botocore.client import BaseClient

from .config import AWSConfig, LOGGER
from .sections.aws_lambda import (
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
    LambdaProvisionedConcurrency,
    LambdaRegionLimits,
    LambdaSummary,
)
from .sections.cloudfront import CloudFront, CloudFrontSummary
from .sections.cloudwatch import CloudwatchAlarms, CloudwatchAlarmsLimits
from .sections.core import AWSSection, AWSSectionResult, ResultDistributor
from .sections.costs_and_usage import CostsAndUsage, ReservationUtilization
from .sections.dynamodb import (
    DynamoDB,
    DynamoDBLabelsGeneric,
    DynamoDBLimits,
    DynamoDBSummary,
    DynamoDBTable,
)
from .sections.ebs import EBS, EBSLimits, EBSSummary
from .sections.ec2 import EC2, EC2Labels, EC2Limits, EC2SecurityGroups, EC2Summary
from .sections.ecs import ECS, ECSLimits, ECSSummary
from .sections.elasticache import ElastiCache, ElastiCacheLimits, ElastiCacheSummary
from .sections.elb import ELB, ELBHealth, ELBLabelsGeneric, ELBLimits, ELBSummaryGeneric
from .sections.elbv2 import (
    ELBv2Application,
    ELBv2ApplicationTargetGroupsHTTP,
    ELBv2ApplicationTargetGroupsLambda,
    ELBv2Limits,
    ELBv2Network,
    ELBv2TargetGroups,
)
from .sections.glacier import Glacier, GlacierLimits
from .sections.rds import RDS, RDSLimits, RDSSummary
from .sections.route53 import Route53Cloudwatch, Route53HealthChecks
from .sections.s3 import ResultDistributorS3Limits, S3, S3Limits, S3Requests, S3Summary
from .sections.sns import SNS, SNSLimits, SNSSMS, SNSSummary, SNSTopicsFetcher
from .sections.wafv2 import WAFV2Limits, WAFV2Summary, WAFV2WebACL

Results = dict[tuple[str, float, float], Sequence["AWSSectionResult"]]


def datetime_serializer(obj):
    """Custom serializer to pass to json dump functions"""
    if isinstance(obj, datetime):
        return str(obj)
    # fall back to json default behaviour:
    raise TypeError("%r is not JSON serializable" % obj)


# Overview of sections and dependencies

# CostsAndUsage

# ReservationUtilization

# EC2Limits
# |
# '-- EC2Summary
#     |
#     |-- EC2Labels
#     |
#     |-- EC2SecurityGroups
#     |
#     '-- EC2

# EBSLimits,EC2Summary
# |
# '-- EBSSummary
#     |
#     '-- EBS

# S3Limits
# |
# '-- S3Summary
#     |
#     |-- S3
#     |
#     '-- S3Requests

# GlacierLimits
# |
# '-- Glacier

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
#     '-- ELBv2Application, ELBv2ApplicationTargetGroupsHTTP, ELBv2ApplicationTargetGroupsLambda, ELBv2Network

# RDSLimits

# RDSSummary
# |
# '-- RDS

# CloudFrontSummary
# |
# '-- CloudFront

# CloudwatchAlarmsLimits
# |
# '-- CloudwatchAlarms

# DynamoDBLimits
# |
# '-- DynamoDBSummary
#     |
#     '-- DynamoDBTable

# WAFV2Limits
# |
# '-- WAFV2Summary
#     |
#     '-- WAFV2WebACL

# LambdaSummary, LambdaRegionLimits
# |
# '-- LambdaProvisionedConcurrency
#     |
#     |-- LambdaCloudwatch
#     |
#     '-- LambdaCloudwatchInsights

# Route53HealthChecks
# |
# '-- Route53Cloudwatch

# SNSLimits
# |
# |-- SNSSMS
# |
# '-- SNSSummary
#     |
#     '-- SNS

# ECSLimits
# |
# '-- ECSSummary
#     |
#     '-- ECS

# ElastiCacheLimits
# |
# '-- ElastiCacheSummary
#     |
#     '-- ElastiCache


class AWSSections(abc.ABC):
    def __init__(
        self,
        hostname: str,
        session: boto3.session.Session,
        account_id: str,
        debug: bool = False,
        config: botocore.config.Config | None = None,
    ) -> None:
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections: list[AWSSection] = []
        self.config = config
        self.account_id = account_id

    @abc.abstractmethod
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        pass

    def _init_client(self, client_key: str) -> BaseClient:
        try:
            # TODO: The signature of the client() method depends on the literal(!) value of its
            # first argument, so using a plain str here is wrong.
            return self._session.client(client_key, config=self.config)
        except (
            ValueError,
            botocore.exceptions.ClientError,
            botocore.exceptions.UnknownServiceError,
        ) as e:
            # If region name is not valid we get a ValueError
            # but not in all cases, eg.:
            # 1. 'eu-central-' raises a ValueError
            # 2. 'foobar' does not raise a ValueError
            # In the second case we get an exception raised by botocore
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs)-> None:
            # - botocore.exceptions.EndpointConnectionError
            LOGGER.info(
                "Invalid region name or client key %(client_key)s: %(error)s",
                {"client_key": client_key, "error": e},
            )
            raise

    def run(self, use_cache: bool = True) -> None:
        exceptions: list[AssertionError | Exception] = []
        results: Results = {}

        for section in self._sections:
            try:
                section_result = section.run(use_cache=use_cache)
            except AssertionError as e:
                LOGGER.info(e)
                if self._debug:
                    raise
            except Exception as e:
                LOGGER.info(
                    "%(class_name)s: %(error)s",
                    {"class_name": section.__class__.__name__, "error": e},
                )
                if self._debug:
                    raise
                exceptions.append(e)
            else:
                results.setdefault(
                    (section.name, section_result.cache_timestamp, section.cache_interval),
                    section_result.results,
                )

        self._write_exceptions(exceptions)
        self._write_host_labels(results)
        self._write_section_results(results)

    def _collect_static_host_labels(self) -> Mapping[str, str]:
        """Labels every host will be labelled with regardless of type"""
        return {"cmk/aws/account": self.account_id}

    def _is_piggyback_host_result(self, section_result: AWSSectionResult) -> bool:
        return section_result.piggyback_hostname not in {None, "", self._hostname}

    def _collect_piggyback_host_labels(
        self, results: Results, static_labels: Mapping[str, str]
    ) -> Mapping[str, Mapping[str, str]]:
        """Labels dependent on the type of piggyback host"""
        host_labels: dict[str, dict[str, str]] = defaultdict(lambda: {**static_labels})
        for result in results.values():
            for row in result:
                if self._is_piggyback_host_result(row) and row.piggyback_host_labels:
                    host_labels[str(row.piggyback_hostname)].update(row.piggyback_host_labels)
        return host_labels

    def _write_host_labels(self, results: Results) -> None:
        static_host_labels = self._collect_static_host_labels()
        sys.stdout.write(f"<<<labels:sep(0)>>>\n{json.dumps(static_host_labels)}\n")

        piggyback_host_labels = self._collect_piggyback_host_labels(results, static_host_labels)
        for hostname, host_labels in piggyback_host_labels.items():
            sys.stdout.write(
                f"<<<<{hostname}>>>>\n<<<labels:sep(0)>>>\n{json.dumps(host_labels)}\n<<<<>>>>\n"
            )

    def _safe_exception(self, exception: Exception) -> str:
        """
        Secure proper exception output.
        boto3 sometimes throws unpropper exceptions without a 'message' parameter.
        TODO: Avoid using aws_exception-section
        """
        if hasattr(exception, "message"):
            return exception.message

        return repr(exception)

    def _write_exceptions(self, exceptions: Sequence) -> None:
        sys.stdout.write("<<<aws_exceptions>>>\n")

        if exceptions:
            out = "\n".join([self._safe_exception(e) for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write(f"{self.__class__.__name__}: {out}\n")

    def _write_section_results(self, results: Results) -> None:
        if not results:
            LOGGER.info(
                "%(class_name)s: No results or cached data",
                {"class_name": self.__class__.__name__},
            )
            return

        for (section_name, cache_timestamp, section_interval), result in results.items():
            if not result:
                LOGGER.info("%(section_name)s: No results", {"section_name": section_name})
                continue

            if not isinstance(result, list):
                LOGGER.info(
                    "%(section_name)s: Section result must be of type 'list' containing 'AWSSectionResults'",
                    {"section_name": section_name},
                )
                continue

            cached_suffix = ""
            if section_interval > 60:
                cached_suffix = f":cached({int(cache_timestamp)},{int(section_interval + 60)})"

            if any(r.content for r in result):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(
        self, section_name: str, cached_suffix: str, result: Sequence[AWSSectionResult]
    ) -> None:
        if section_name.endswith("labels"):
            section_header = f"<<<{section_name}:sep(0){cached_suffix}>>>\n"
        else:
            section_header = f"<<<aws_{section_name}{cached_suffix}>>>\n"

        for row in result:
            write_piggyback_header = self._is_piggyback_host_result(row)
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % str(row.piggyback_hostname))
            sys.stdout.write(section_header)
            sys.stdout.write("%s\n" % json.dumps(row.content, default=datetime_serializer))
            if write_piggyback_header:
                sys.stdout.write("<<<<>>>>\n")


class AWSSectionsUSEast(AWSSections):
    """
    Some clients like CostExplorer only work with US East region:
    https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html
    US East is the AWS Standard region.
    """

    @override
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        if "ce" in services:
            ce_client = self._init_client("ce")
            self._sections.append(CostsAndUsage(ce_client, region, config))
            self._sections.append(ReservationUtilization(ce_client, region, config))

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        if "wafv2" in services and config.service_config["wafv2_cloudfront"]:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "CLOUDFRONT", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, False)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "route53" in services:
            route53_client = self._init_client("route53")
            route53_health_checks, route53_cloudwatch = _create_route53_sections(
                route53_client, cloudwatch_client, region, config, distributor
            )
            self._sections.append(route53_health_checks)
            self._sections.append(route53_cloudwatch)

        if "cloudfront" in services:
            cloudfront_client = self._init_client("cloudfront")
            cloudfront_summary = CloudFrontSummary(
                cloudfront_client, tagging_client, region, config, distributor
            )
            cloudfront = CloudFront(
                cloudwatch_client,
                region,
                config,
                config.service_config["cloudfront_host_assignment"],
            )
            distributor.add(cloudfront_summary.name, cloudfront)
            self._sections.append(cloudfront_summary)
            self._sections.append(cloudfront)


def _create_lamdba_sections(
    lambda_client: BaseClient,
    cloudwatch_client: BaseClient,
    cloudwatch_logs_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[
    LambdaRegionLimits,
    LambdaSummary,
    LambdaProvisionedConcurrency,
    LambdaCloudwatch,
    LambdaCloudwatchInsights,
]:
    lambda_limits = LambdaRegionLimits(lambda_client, region, config, distributor=distributor)
    lambda_summary = LambdaSummary(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_limits.name, lambda_summary)
    lambda_provisioned_concurrency_configuration = LambdaProvisionedConcurrency(
        lambda_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_summary.name, lambda_provisioned_concurrency_configuration)
    lambda_cloudwatch = LambdaCloudwatch(cloudwatch_client, region, config)
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch)
    lambda_cloudwatch_insights = LambdaCloudwatchInsights(
        cloudwatch_logs_client,
        region,
        config,
        distributor,
    )
    distributor.add(lambda_provisioned_concurrency_configuration.name, lambda_cloudwatch_insights)

    return (
        lambda_limits,
        lambda_summary,
        lambda_provisioned_concurrency_configuration,
        lambda_cloudwatch,
        lambda_cloudwatch_insights,
    )


def _create_route53_sections(
    route53_client: BaseClient,
    cloudwatch_client: BaseClient,
    region: str,
    config: AWSConfig,
    distributor: ResultDistributor,
) -> tuple[Route53HealthChecks, Route53Cloudwatch]:
    route53_health_checks = Route53HealthChecks(route53_client, region, config, distributor)
    route53_cloudwatch = Route53Cloudwatch(cloudwatch_client, region, config, distributor=None)
    distributor.add(route53_health_checks.name, route53_cloudwatch)
    return route53_health_checks, route53_cloudwatch


class AWSSectionsGeneric(AWSSections):
    @override
    def init_sections(
        self,
        services: Sequence[str],
        region: str,
        config: AWSConfig,
        s3_limits_distributor: ResultDistributorS3Limits,
    ) -> None:
        distributor = ResultDistributor()

        cloudwatch_client = self._init_client("cloudwatch")
        tagging_client = self._init_client("resourcegroupstaggingapi")
        ec2_client = self._init_client("ec2")
        ebs_summary = EBSSummary(ec2_client, region, config, distributor)

        if "ec2" in services:
            ec2_summary = EC2Summary(ec2_client, region, config, distributor)
            ec2_labels = EC2Labels(ec2_client, region, config)
            ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
            ec2 = EC2(cloudwatch_client, region, config)
            distributor.add("ec2_limits", ec2_summary)
            distributor.add(ec2_summary.name, ec2_labels)
            distributor.add(ec2_summary.name, ec2_security_groups)
            distributor.add(ec2_summary.name, ec2)
            distributor.add(ec2_summary.name, ebs_summary)
            if config.service_config.get("ec2_limits"):
                self._sections.append(
                    EC2Limits(
                        ec2_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )
            self._sections.append(ec2_summary)
            self._sections.append(ec2_labels)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if "ebs" in services:
            ebs = EBS(cloudwatch_client, region, config)
            distributor.add("ebs_limits", ebs_summary)
            distributor.add(ebs_summary.name, ebs)
            if config.service_config.get("ebs_limits"):
                self._sections.append(EBSLimits(ec2_client, region, config, distributor))
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if "elb" in services:
            elb_client = self._init_client("elb")
            elb_labels = ELBLabelsGeneric(elb_client, region, config, resource="elb")
            elb_health = ELBHealth(elb_client, region, config)
            elb = ELB(cloudwatch_client, region, config)
            elb_summary = ELBSummaryGeneric(elb_client, region, config, distributor, resource="elb")
            distributor.add("elb_limits", elb_summary)
            distributor.add(elb_summary.name, elb_labels)
            distributor.add(elb_summary.name, elb_health)
            distributor.add(elb_summary.name, elb)
            if config.service_config.get("elb_limits"):
                self._sections.append(ELBLimits(elb_client, region, config, distributor))
            self._sections.append(elb_summary)
            self._sections.append(elb_labels)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if "elbv2" in services:
            elbv2_client = self._init_client("elbv2")
            elbv2_limits = ELBv2Limits(elbv2_client, region, config, distributor)
            elbv2_summary = ELBSummaryGeneric(
                elbv2_client, region, config, distributor, resource="elbv2"
            )
            elbv2_labels = ELBLabelsGeneric(elbv2_client, region, config, resource="elbv2")
            elbv2_target_groups = ELBv2TargetGroups(elbv2_client, region, config)
            elbv2_application = ELBv2Application(cloudwatch_client, region, config)
            elbv2_application_target_groups_http = ELBv2ApplicationTargetGroupsHTTP(
                cloudwatch_client, region, config
            )
            elbv2_application_target_groups_lambda = ELBv2ApplicationTargetGroupsLambda(
                cloudwatch_client, region, config
            )
            elbv2_network = ELBv2Network(cloudwatch_client, region, config)
            distributor.add(elbv2_limits.name, elbv2_summary)
            distributor.add(elbv2_summary.name, elbv2_labels)
            distributor.add(elbv2_summary.name, elbv2_target_groups)
            distributor.add(elbv2_summary.name, elbv2_application)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_http)
            distributor.add(elbv2_summary.name, elbv2_application_target_groups_lambda)
            distributor.add(elbv2_summary.name, elbv2_network)
            if config.service_config.get("elbv2_limits"):
                self._sections.append(elbv2_limits)
            self._sections.append(elbv2_summary)
            self._sections.append(elbv2_labels)
            self._sections.append(elbv2_target_groups)
            self._sections.append(elbv2_application)
            self._sections.append(elbv2_application_target_groups_http)
            self._sections.append(elbv2_application_target_groups_lambda)
            self._sections.append(elbv2_network)

        if "s3" in services:
            # S3 is special because there are no per-region limits, but only a global per-account limit.
            # The list of buckets can be queried from any region, however, the metrics for the
            # individual buckets must be queried from the region the bucket resides in. Therefore, we
            # only want to run S3Limits once, namely for the first region (does not matter which region
            # that is). The results will then be distributed to the S3Summary objects across all regions
            # using the special distributor for S3 limits.
            s3_client = self._init_client("s3")
            if s3_limits_distributor.is_empty():
                s3_limits: S3Limits | None = S3Limits(
                    s3_client, region, config, s3_limits_distributor
                )
            else:
                s3_limits = None
            s3_summary = S3Summary(s3_client, region, config, distributor)

            s3_limits_distributor.add("s3_limits", s3_summary)
            s3 = S3(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3)
            s3_requests = S3Requests(cloudwatch_client, region, config)
            distributor.add(s3_summary.name, s3_requests)
            if config.service_config.get("s3_limits") and s3_limits:
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config["s3_requests"]:
                self._sections.append(s3_requests)

        if "glacier" in services:
            glacier_client = self._init_client("glacier")
            glacier_limits = GlacierLimits(glacier_client, region, config, distributor)
            glacier_summary = Glacier(glacier_client, region, config)
            distributor.add(glacier_limits.name, glacier_summary)
            if config.service_config.get("glacier_limits"):
                self._sections.append(glacier_limits)
            self._sections.append(glacier_summary)

        if "rds" in services:
            rds_client = self._init_client("rds")
            rds_summary = RDSSummary(rds_client, region, config, distributor)
            rds_limits = RDSLimits(rds_client, region, config)
            rds = RDS(cloudwatch_client, region, config)
            distributor.add(rds_summary.name, rds)
            if config.service_config.get("rds_limits"):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)

        if "cloudwatch_alarms" in services:
            cloudwatch_alarms = CloudwatchAlarms(cloudwatch_client, region, config)
            cloudwatch_alarms_limits = CloudwatchAlarmsLimits(
                cloudwatch_client, region, config, distributor
            )
            distributor.add(cloudwatch_alarms_limits.name, cloudwatch_alarms)
            if config.service_config.get("cloudwatch_alarms_limits"):
                self._sections.append(cloudwatch_alarms_limits)
            if "cloudwatch_alarms" in config.service_config:
                self._sections.append(cloudwatch_alarms)

        if "dynamodb" in services:
            dynamodb_client = self._init_client("dynamodb")
            dynamodb = DynamoDB(dynamodb_client, region, config)
            dynamodb_labels = DynamoDBLabelsGeneric(
                dynamodb_client, region, config, resource="dynamodb"
            )
            dynamodb_limits = DynamoDBLimits(dynamodb_client, region, config, distributor)
            dynamodb_summary = DynamoDBSummary(dynamodb_client, region, config, distributor)
            dynamodb_table = DynamoDBTable(cloudwatch_client, region, config)
            distributor.add(dynamodb_limits.name, dynamodb_summary)
            distributor.add(dynamodb_summary.name, dynamodb_labels)
            distributor.add(dynamodb_summary.name, dynamodb)
            distributor.add(dynamodb_summary.name, dynamodb_table)
            if config.service_config.get("dynamodb_limits"):
                self._sections.append(dynamodb_limits)
            self._sections.append(dynamodb_summary)
            self._sections.append(dynamodb_labels)
            self._sections.append(dynamodb)
            self._sections.append(dynamodb_table)

        if "wafv2" in services:
            wafv2_client = self._init_client("wafv2")
            wafv2_limits = WAFV2Limits(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            wafv2_summary = WAFV2Summary(
                wafv2_client, region, config, "REGIONAL", distributor=distributor
            )
            distributor.add(wafv2_limits.name, wafv2_summary)
            wafv2_web_acl = WAFV2WebACL(cloudwatch_client, region, config, True)
            distributor.add(wafv2_summary.name, wafv2_web_acl)
            if config.service_config.get("wafv2_limits"):
                self._sections.append(wafv2_limits)
            self._sections.append(wafv2_summary)
            self._sections.append(wafv2_web_acl)

        if "lambda" in services:
            (
                lambda_limits,
                lambda_summary,
                lambda_provisioned_concurrency_configuration,
                lambda_cloudwatch,
                lambda_cloudwatch_insights,
            ) = _create_lamdba_sections(
                self._init_client("lambda"),
                cloudwatch_client,
                self._init_client("logs"),
                region,
                config,
                distributor,
            )
            if config.service_config.get("lambda_limits"):
                self._sections.append(lambda_limits)
            self._sections.append(lambda_summary)
            self._sections.append(lambda_provisioned_concurrency_configuration)
            self._sections.append(lambda_cloudwatch)
            self._sections.append(lambda_cloudwatch_insights)

        if "sns" in services:
            sns_client = self._init_client("sns")
            sns_topics_fetcher = SNSTopicsFetcher(sns_client, tagging_client, region, config)
            sns_summary = SNSSummary(
                sns_client, region, config, sns_topics_fetcher, distributor=distributor
            )
            sns_cloudwatch = SNS(cloudwatch_client, region, config)
            distributor.add(sns_summary.name, sns_cloudwatch)
            sns_sms_cloudwatch = SNSSMS(cloudwatch_client, region, config)
            if config.service_config.get("sns_limits"):
                sns_limits = SNSLimits(
                    sns_client, region, config, sns_topics_fetcher, distributor=distributor
                )
                distributor.add(sns_limits.name, sns_summary)
                distributor.add(sns_limits.name, sns_cloudwatch)
                self._sections.append(sns_limits)
            # sns_cloudwatch section should always be after sns_limits because it gets the data from
            # there through the distributor
            self._sections.append(sns_summary)
            self._sections.append(sns_cloudwatch)
            self._sections.append(sns_sms_cloudwatch)

        if "ecs" in services:
            ecs_client = self._init_client("ecs")
            if config.service_config.get("ecs_limits"):
                self._sections.append(
                    ECSLimits(
                        ecs_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            ecs_summary = ECSSummary(ecs_client, region, config, distributor)
            distributor.add("ecs_limits", ecs_summary)
            self._sections.append(ecs_summary)

            ecs = ECS(cloudwatch_client, region, config)
            distributor.add("ecs_summary", ecs)
            self._sections.append(ecs)

        if "elasticache" in services:
            elasticache_client = self._init_client("elasticache")
            if config.service_config.get("elasticache_limits"):
                self._sections.append(
                    ElastiCacheLimits(
                        elasticache_client,
                        region,
                        config,
                        distributor,
                        self._init_client("service-quotas"),
                    )
                )

            elasticache_summary = ElastiCacheSummary(
                elasticache_client, tagging_client, region, config, distributor
            )
            distributor.add("elasticache_limits", elasticache_summary)
            self._sections.append(elasticache_summary)

            elasticache = ElastiCache(cloudwatch_client, region, config)
            distributor.add("elasticache_summary", elasticache)
            self._sections.append(elasticache)
