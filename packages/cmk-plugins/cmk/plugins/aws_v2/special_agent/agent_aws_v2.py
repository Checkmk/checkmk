#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-untyped-call"

"""agent_aws_v2

Checkmk special agent for monitoring Amazon Web Services (AWS).
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from typing import NamedTuple

import botocore

from cmk.password_store.v1 import parser_add_secret_option, resolve_secret_option
from cmk.plugins.aws_v2.constants import AWS_REGIONS
from cmk.server_side_programs.v1 import configure_logging, report_agent_crashes, vcrtrace

from .config import (
    AGENT,
    AwsAccessError,
    AWSConfig,
    LOGGER,
    NamingConvention,
    TagsImportPatternOption,
)
from .credentials import (
    AccessKey,
    AssumedRole,
    AwsCredentials,
    DefaultCredentials,
    HubCredentials,
)
from .runner import AWSSectionsGeneric, AWSSectionsUSEast
from .sections.s3 import ResultDistributorS3Limits

__version__ = "3.0.0b1"


ACCESS_KEY_SECRET_OPTION = "secret"

PROXY_SECRET_OPTION = "proxysecret"


#   ---result distributor---------------------------------------------------


#   ---sections/colleagues--------------------------------------------------


# Interval between 'Start' and 'End' must be a DateInterval. 'End' is exclusive.
# Example:
# 2017-01-01 - 2017-05-01; cost and usage data is retrieved from 2017-01-01 up
# to and including 2017-04-30 but not including 2017-05-01.
# The GetCostAndUsage operation supports DAILY | MONTHLY | HOURLY granularities.
# The GetReservationUtilization operation supports only DAILY and MONTHLY granularities.


# EBS are attached to EC2 instances. Thus we put the content to related EC2
# instance as piggyback host.


# SNS is a messaging service that follows the event-producers -> topics -> subscriptions model
# producers and topics have a many-to-many-relationship.
# topics and subscriptions also have a many-to-many-relationship.
# It therefore makes sense to monitor Subscriptions, Topics, and Producers as the three central
# building blocks of AWS SNS. Subscriptions and Topics have specific limits per account so they
# are handled in the limits section. For producers it is more important to look at what exactly
# they are producing, so the cloudwatch section monitors detailed metrics about incoming traffic.


class AWSServiceAttributes(NamedTuple):
    key: str
    title: str
    global_service: bool
    filter_by_names: bool
    filter_by_tags: bool
    limits: bool


AWS_SERVICES = [
    AWSServiceAttributes(
        key="ce",
        title="Costs and usage",
        global_service=True,
        filter_by_names=False,
        filter_by_tags=False,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ec2",
        title="Elastic Compute Cloud (EC2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="ebs",
        title="Elastic Block Storage (EBS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="s3",
        title="Simple Storage Service (S3)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="glacier",
        title="Simple Storage Service Glacier (Glacier)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elb",
        title="Classic Load Balancing (ELB)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elbv2",
        title="Application and Network Load Balancing (ELBv2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="rds",
        title="Relational Database Service (RDS)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudwatch_alarms",
        title="CloudWatch Alarms",
        global_service=False,
        filter_by_names=False,
        filter_by_tags=False,
        limits=True,
    ),
    AWSServiceAttributes(
        key="dynamodb",
        title="DynamoDB",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="wafv2",
        title="Web Application Firewall (WAFV2)",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="lambda",
        title="Lambda",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="route53",
        title="Route53",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="sns",
        title="SNS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="cloudfront",
        title="CloudFront",
        global_service=True,
        filter_by_names=True,
        filter_by_tags=True,
        limits=False,
    ),
    AWSServiceAttributes(
        key="ecs",
        title="ECS",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
    AWSServiceAttributes(
        key="elasticache",
        title="ElastiCache",
        global_service=False,
        filter_by_names=True,
        filter_by_tags=True,
        limits=True,
    ),
]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase log verbosity. Use -vv for debug output of 'boto3' and 'botocore'.",
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_post_data_parameters=[("client_secret", "****")]),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Execute all sections, do not rely on cached data. Cached data will not be overwritten.",
    )
    parser.add_argument(
        "--access-key-identity",
        required=False,
        help="The AWS identity of your AWS account access key",
    )
    parser_add_secret_option(
        parser,
        long=f"--{ACCESS_KEY_SECRET_OPTION}",
        required=False,
        help="The secret AWS access key for your AWS account.",
    )
    parser.add_argument("--proxy-host", help="The address of the proxy server")
    parser.add_argument("--proxy-port", help="The port of the proxy server")
    parser.add_argument("--proxy-user", help="The username for authentication of the proxy server")
    parser_add_secret_option(
        parser,
        long=f"--{PROXY_SECRET_OPTION}",
        required=False,
        help="The password for authentication of the proxy server.",
    )
    parser.add_argument(
        "--global-service-region",
        help="Set this to your region when you are in 'us-gov-*' or 'cn-*' regions.",
        default="us-east-1",
    )
    parser.add_argument(
        "--assume-role",
        action="store_true",
        help="Use STS AssumeRole to assume a different IAM role",
    )
    parser.add_argument("--role-arn", help="The ARN of the IAM role to assume")
    parser.add_argument(
        "--external-id", help="Unique identifier to assume a role in another account"
    )
    parser.add_argument(
        "--region",
        dest="regions",
        action="append",
        help="Regions to use:\n%s" % "\n".join(["%-15s %s" % e for e in AWS_REGIONS]),
    )
    parser.add_argument(
        "--global-service",
        dest="global_services",
        action="append",
        help="Global services to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWS_SERVICES if e.global_service]),
    )
    parser.add_argument(
        "--service",
        dest="services",
        action="append",
        help="Services per region to monitor:\n%s"
        % "\n".join(["%-15s %s" % (e.key, e.title) for e in AWS_SERVICES if not e.global_service]),
    )
    parser.add_argument(
        "--s3-requests",
        action="store_true",
        help="You have to enable requests metrics in AWS/S3 console. This is a paid feature.",
    )
    parser.add_argument(
        "--cloudwatch-alarm",
        dest="cloudwatch_alarms",
        action="append",
    )
    parser.add_argument(
        "--overall-tag-key",
        dest="overall_tag_keys",
        action="append",
        help="Overall tag key",
    )
    parser.add_argument(
        "--overall-tag-value",
        dest="overall_tag_values",
        action="append",
        help="Overall tag values",
    )
    parser.add_argument(
        "--wafv2-cloudfront",
        action="store_true",
        help="Also monitor global WAFs in front of CloudFront resources.",
    )
    parser.add_argument(
        "--cloudfront-host-assignment",
        help="Assign CloudFront services to the AWS host or to the origin domain host",
    )
    parser.add_argument("--hostname", required=True)
    parser.add_argument(
        "--piggyback-naming-convention",
        type=NamingConvention,
        required=True,
        help="For each running EC2 instance a piggyback host is created. This option changes the "
        "naming of these hosts. Note, that not every host name is pingable. Moreover, "
        "changes in the piggyback name will cause the piggyback host to be reset. "
        "If you choose `ip_region_instance`, then the name includes the private IP "
        "address, the region and the instance ID: {Private IPv4 address}-{region}-{Instance ID}. ",
    )

    group_import_tags = parser.add_mutually_exclusive_group()
    group_import_tags.add_argument(
        "--ignore-all-tags",
        action="store_const",
        const=TagsImportPatternOption.ignore_all,
        dest="tag_key_pattern",
        help="By default, all AWS tags are written to the agent output, validated to meet the "
        "Checkmk label requirements and added as host labels to their respective piggyback host "
        "and/or as service labels to the respective service using the syntax "
        "'cmk/aws/tag/{key}:{value}'. With this option you can disable the import of AWS "
        "tags.",
    )
    group_import_tags.add_argument(
        "--import-matching-tags-as-labels",
        dest="tag_key_pattern",
        help="You can restrict the imported tags by specifying a pattern which the agent searches "
        "for in the key of the tag.",
    )
    group_import_tags.set_defaults(tag_key_pattern=TagsImportPatternOption.import_all)

    for service in AWS_SERVICES:
        if service.filter_by_names:
            parser.add_argument(
                f"--{service.key}-name",
                dest=f"{service.key}_names",
                action="append",
                help=f"Names for {service.title}",
            )
        if service.filter_by_tags:
            parser.add_argument(
                f"--{service.key}-tag-key",
                dest=f"{service.key}_tag_keys",
                action="append",
                help="Tag key for %s" % service.title,
            )
            parser.add_argument(
                f"--{service.key}-tag-value",
                dest=f"{service.key}_tag_values",
                action="append",
                help="Tag values for %s" % service.title,
            )
        if service.limits:
            parser.add_argument(
                "--%s-limits" % service.key,
                action="store_true",
                help="Monitor limits for %s" % service.title,
            )

    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Run a connection test. No further agent code is executed.",
    )

    args = parser.parse_args(argv)
    if args.access_key_identity and args.secret is None and args.secret_id is None:
        parser.error("--access-key-identity requires --secret or --secret-id")
    return args


def _setup_logging(opt_debug: bool, opt_verbose: int) -> None:
    logging.getLogger().disabled = not (opt_debug or opt_verbose)
    configure_logging(logging.DEBUG if opt_verbose > 1 else logging.INFO)


def _sanitize_aws_services_params(
    g_aws_services: Sequence[str],
    r_aws_services: Sequence[str],
    r_and_g_aws_services: tuple[str] | tuple[()] = (),
) -> tuple[Sequence[str], Sequence[str]]:
    """
    Sort service keys into global and regional services by checking
    the service configuration of AWSServices.
    This abstracts the AWS structure from the GUI configuration.
    :param g_aws_services: all services in --global-services
    :param r_aws_services: all services in --services
    :param r_and_g_aws_services: services in --services which should also be run globally, e.g.
                                 WAFV2, which has regional and global firewalls; the regional ones
                                 can only be accessed from the corresponding region, the global
                                 ones only from us-east-1
    :return: two lists of global and regional services
    """
    aws_service_keys: set[str] = set()
    if g_aws_services is not None:
        aws_service_keys = aws_service_keys.union(g_aws_services)

    if r_aws_services is not None:
        aws_service_keys = aws_service_keys.union(r_aws_services)

    aws_services_map = {e.key: e for e in AWS_SERVICES}
    global_services = []
    regional_services = []
    for service_key in aws_service_keys:
        service_attrs = aws_services_map.get(service_key)
        if service_attrs is None:
            continue
        if service_attrs.global_service:
            global_services.append(service_key)
        else:
            regional_services.append(service_key)
            if service_key in r_and_g_aws_services:
                global_services.append(service_key)
    return global_services, regional_services


def _proxy_address(
    server_address: str,
    port: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    address = server_address
    authentication = ""
    if port:
        address += f":{port}"
    if username and password:
        authentication = f"{username}:{password}@"
    return f"{authentication}{address}"


def _get_proxy(args: argparse.Namespace) -> botocore.config.Config | None:
    if args.proxy_host:
        return botocore.config.Config(
            proxies={
                "https": _proxy_address(
                    args.proxy_host,
                    args.proxy_port,
                    args.proxy_user,
                    (
                        resolve_secret_option(args, PROXY_SECRET_OPTION).reveal()
                        if args.proxysecret is not None or args.proxysecret_id is not None
                        else None
                    ),
                )
            }
        )
    return None


def _configure_aws(args: argparse.Namespace) -> AWSConfig:
    aws_config = AWSConfig(
        args.hostname,
        args,
        (args.overall_tag_keys, args.overall_tag_values),
        args.piggyback_naming_convention,
        args.tag_key_pattern,
    )
    for service_key, service_names, service_tags, service_limits in [
        ("ec2", args.ec2_names, (args.ec2_tag_keys, args.ec2_tag_values), args.ec2_limits),
        ("ebs", args.ebs_names, (args.ebs_tag_keys, args.ebs_tag_values), args.ebs_limits),
        ("s3", args.s3_names, (args.s3_tag_keys, args.s3_tag_values), args.s3_limits),
        (
            "glacier",
            args.glacier_names,
            (args.glacier_tag_keys, args.glacier_tag_values),
            args.glacier_limits,
        ),
        ("elb", args.elb_names, (args.elb_tag_keys, args.elb_tag_values), args.elb_limits),
        (
            "elbv2",
            args.elbv2_names,
            (args.elbv2_tag_keys, args.elbv2_tag_values),
            args.elbv2_limits,
        ),
        ("rds", args.rds_names, (args.rds_tag_keys, args.rds_tag_values), args.rds_limits),
        (
            "dynamodb",
            args.dynamodb_names,
            (args.dynamodb_tag_keys, args.dynamodb_tag_values),
            args.dynamodb_limits,
        ),
        (
            "wafv2",
            args.wafv2_names,
            (args.wafv2_tag_keys, args.wafv2_tag_values),
            args.wafv2_limits,
        ),
        (
            "lambda",
            args.lambda_names,
            (args.lambda_tag_keys, args.lambda_tag_values),
            args.lambda_limits,
        ),
        ("route53", args.route53_names, (args.route53_tag_keys, args.route53_tag_values), None),
        ("sns", args.sns_names, (args.sns_tag_keys, args.sns_tag_values), args.sns_limits),
        (
            "cloudfront",
            args.cloudfront_names,
            (args.cloudfront_tag_keys, args.cloudfront_tag_values),
            None,
        ),
        ("ecs", args.ecs_names, (args.ecs_tag_keys, args.ecs_tag_values), args.ecs_limits),
        (
            "elasticache",
            args.elasticache_names,
            (args.elasticache_tag_keys, args.elasticache_tag_values),
            args.elasticache_limits,
        ),
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    for arg in [
        "s3_requests",
        "cloudwatch_alarms_limits",
        "cloudwatch_alarms",
        "wafv2_cloudfront",
        "cloudfront_host_assignment",
    ]:
        aws_config.add_single_service_config(arg, getattr(args, arg))

    return aws_config


def _hub_credentials_from_args(args: argparse.Namespace) -> HubCredentials:
    login: AccessKey | DefaultCredentials = (
        AccessKey(
            args.access_key_identity,
            resolve_secret_option(args, ACCESS_KEY_SECRET_OPTION).reveal(),
        )
        if args.access_key_identity
        else DefaultCredentials()
    )
    role = AssumedRole(args.role_arn, args.external_id or None) if args.assume_role else None
    return HubCredentials(login, role)


def _test_connection(credentials: AwsCredentials) -> int:
    try:
        credentials.account_id()
    except AwsAccessError as ae:
        error_msg = f"Connection failed with: {ae}\n"
        sys.stderr.write(error_msg)
        return 2
    return 0


def agent_aws_main(args: argparse.Namespace) -> int:
    _setup_logging(args.debug, args.verbose)

    proxy_config = _get_proxy(args)
    # One credential owner for the whole run. The connection test and the agent run take
    # the same one, so both resolve credentials through the same path.
    credentials = AwsCredentials(
        _hub_credentials_from_args(args), args.global_service_region, proxy_config
    )

    if args.connection_test:
        return _test_connection(credentials)

    try:
        account_id = credentials.account_id()
    except AwsAccessError as ae:
        # can not access AWS, retreat
        sys.stdout.write("<<<aws_v2_exceptions>>>\n")
        sys.stdout.write("Exception: %s\n" % ae)
        return 0

    aws_config = _configure_aws(args)

    global_services, regional_services = _sanitize_aws_services_params(
        args.global_services, args.services, r_and_g_aws_services=("wafv2",)
    )

    use_cache = aws_config.is_up_to_date() and not args.no_cache

    # Special distributor for S3 limits which distributes results across different regions
    s3_limits_distributor = ResultDistributorS3Limits()

    if regional_services and not args.regions:
        LOGGER.error(
            (
                "You have to specify a region for the services: %(services)s."
                " Otherwise data for these services cannot be fetched."
            ),
            {"services": ", ".join(regional_services)},
        )

    has_exceptions = False
    for aws_services, aws_regions, aws_sections in [
        (global_services, [args.global_service_region], AWSSectionsUSEast),
        (regional_services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue

        for region in aws_regions:
            try:
                # The same session for every region. init_sections below tells the
                # sections which region their clients belong to.
                sections = aws_sections(
                    args.hostname,
                    credentials.session(),
                    account_id,
                    debug=args.debug,
                    config=proxy_config,
                )
                sections.init_sections(aws_services, region, aws_config, s3_limits_distributor)
                sections.run(use_cache=use_cache)
            except AwsAccessError as ae:
                # can not access AWS, retreat
                sys.stdout.write("<<<aws_v2_exceptions>>>\n")
                sys.stdout.write("Exception: %s\n" % ae)
                return 0
            except AssertionError:
                if args.debug:
                    raise
            except Exception as e:
                LOGGER.info(e)
                has_exceptions = True
                if args.debug:
                    raise

    return 1 if has_exceptions else 0


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return agent_aws_main(parse_arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
