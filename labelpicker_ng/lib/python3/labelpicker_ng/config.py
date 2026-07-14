#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2025 SWR
# @author Frank Baier <frank.baier@swr.de>
#
# Based on:
# SPDX-FileCopyrightText: © 2023 PL Automation Monitoring GmbH <pl@automation-monitoring.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Checkmk Labelpicker project (https://labelpicker.mk)
import yaml
from yaml.scanner import ScannerError
from yaml.parser import ParserError
from yaml.reader import ReaderError
import os, sys, argparse
import base64
import zlib
from pprint import pformat
from labelpicker_ng import LabelpickerConfig, logger
from pathlib import Path
from string import Template
from pydantic import HttpUrl, SecretStr


def _get_automation_secret(
        omd_root: str,
        username: str = "automation"
) -> SecretStr | None:
    """
    Retrieves the automation secret for a specified user from the file system. Used for authentication
    or automation purposes. If the secret file does not exist, it returns False. The method reads the
    content of the secret file and strips any leading or trailing whitespace.

    :param omd_root: The root directory of OMD (Open Monitoring Distribution).
    :param username: The username whose automation secret is to be retrieved. Defaults to "automation".
    :return: The content of the automation secret file as a string, or False if the file does not exist.
    :rtype: SecretStr | None
    """
    secret_file = f"{omd_root}/var/check_mk/web/{username}/automation.secret"
    if os.path.isfile(secret_file):
        with open(secret_file, encoding="utf-8") as file:
            return SecretStr(file.read().strip())

    return None


class Config:
    """
    Provides functionality for managing and loading configuration files. This class handles
    the initialization, loading, and validation of LabelPicker configuration through command-line
    arguments, environment variables, and configuration files. It ensures that configuration data
    is properly organized and accessible for other components.

    :ivar args: Command-line arguments, typically of the type `argparse.Namespace`. Provides inputs used
        in determining the configuration behavior, such as paths, usernames, and other options.
    :ivar config_file: The path to the configuration file in use. This can be a user-specified custom
        file or the default `labelpicker.yml` file located under the OMD_ROOT directory.
    :type config_file: str
    :ivar config: The loaded configuration object, typically an instance of `LabelpickerConfig`.
        This is populated with configuration data parsed from the YAML file, potentially overridden
        by command-line arguments.
    :type config: LabelpickerConfig
    """

    def __init__(
            self,
            args: argparse.Namespace,
    ):
        """
        Initializes the configuration for the application based on CLI arguments, environment variables, and configuration files.
        This ensures the setup of CheckMK credentials, API URL, and other necessary parameters. The function prefers CLI arguments
        over YAML or autodetected settings.

        :param args: CLI arguments parsed into a Namespace object, containing user-provided options such as config file,
                     debug mode, username, and password.
        :type args: argparse.Namespace

        :raises FileNotFoundError: If the specified configuration file is not found.
        :raises yaml.YAMLError: If there is an error in parsing the YAML configuration file.
        :raises TypeError: If there is a mismatch between the expected and provided types in the configuration file.
        """
        omd_root = os.environ.get("OMD_ROOT", "")
        if args.config:
            if self.is_filename_only(args.config):
                # Use custom config file in {OMD_ROOT}/etc dir
                self.config_file = os.path.join(omd_root, "etc", str(args.config))
            else:
                self.config_file = str(args.config)
        else:
            # Use the default config file
            self.config_file = os.path.join(omd_root, "etc", "labelpicker_ng.yml")

        # Return if init is set to true, so we don't have to check for config file existence'
        if args.init:
            return

        """Read the config file"""
        # if the file ends with '.yaml' or '.yml' use the YAML loader
        if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = LabelpickerConfig(**yaml.safe_load(f))
            except  FileNotFoundError as e:
                logger.error(f"File not found error:\n{self.config_file}\n{pformat(e, indent=4)}")
                sys.exit(1)
            except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
                mark = e.problem_mark
                line_no = mark.line + 1  # 0-basierte Zeile → 1-basiert
                col_no = mark.column + 1  # 0-basierte Spalte → 1-basiert
                # Dateiinhalt für Kontext erneut lesen
                with open(self.config_file, "r", encoding="utf-8") as f2:
                    lines = f2.readlines()

                error_line = lines[mark.line].rstrip("\n")

                # Zeilen-Vorschau erstellen
                pointer = " " * (col_no - 1) + "^"

                out  = f'\n   YAML-Fehler in Datei: {self.config_file.strip()} '
                out += f'   Zeile {line_no}, Spalte {col_no}\n'
                out += f'   {e.problem}\n'
                out += f'   → {error_line}\n'
                out += f'     {pointer}'
                logger.error(out)
                sys.exit(1)
            except ReaderError as e:
                logger.error(f"YAML reader error:\n{pformat(e, indent=4)}")
                sys.exit(1)
            except yaml.YAMLError as e:
                logger.error(f"YAML error:\n{pformat(e, indent=4)}")
                sys.exit(1)
            except TypeError as e:
                logger.error(f"TypeError:\n{pformat(e, indent=4)}")
                sys.exit(1)

            config.cleanup.retention_path = Template(config.cleanup.retention_path).safe_substitute(omd_root=omd_root)
            config.logging.log_path = Template(config.logging.log_path).safe_substitute(omd_root=omd_root)

            """Create the config (prefer CLI before YAML configuration and before autoconfig"""
            # enable debugging if requested with --debug
            if args.debug:
                config.logging.log_level_file = "DEBUG"
                config.logging.log_level_console = "DEBUG"

            if not config.checkmk.omd_site:
                config.checkmk.omd_site = os.environ.get("OMD_SITE", "cmk")
            if not config.checkmk.omd_root:
                config.checkmk.omd_root = os.environ.get("OMD_ROOT", "")
            if args.username:
                config.checkmk.username = args.username

            if args.password:
                config.checkmk.password = args.password
            elif not config.checkmk.password and config.checkmk.username and config.checkmk.omd_root:
                config.checkmk.password = _get_automation_secret(config.checkmk.omd_root, config.checkmk.username)

            if not config.checkmk.password:
                logger.error(f"No password configured or found!")
                sys.exit(1)

            # set the prefix name for the cleanup files to the config file basename if cli gives another config filename
            if args.config:
                config.cleanup.filename_prefix = Path(args.config).stem

            # define the API-Url
            if not config.checkmk.api_url:
                port = f":{config.checkmk.port}" if config.checkmk.port else ""
                if config.checkmk.protocol and config.checkmk.server and config.checkmk.omd_site:
                    config.checkmk.api_url = HttpUrl(f"{config.checkmk.protocol}://{config.checkmk.server}{port}/{config.checkmk.omd_site}/check_mk/api/{config.checkmk.api_version}")
                else:
                    apache_file = f"{config.checkmk.omd_root}/etc/apache/listen-port.conf"
                    if config.checkmk.omd_root and os.path.isfile(apache_file):
                        cmk_local_apache: str = "localhost:5000"
                        # use local site url from $HOME/etc/apache/conf.d/listen-port.conf
                        f = open(f"{config.checkmk.omd_root}/etc/apache/listen-port.conf", "r").readlines()
                        for line in f:
                            if line.startswith("Listen"):
                                cmk_local_apache = line.split(" ")[1].strip()
                        site_url = f"http://{cmk_local_apache}/{config.checkmk.omd_site}"
                        config.checkmk.api_url = HttpUrl(f"{site_url}/check_mk/api/{config.checkmk.api_version}")

            if not config.checkmk.api_url:
                logger.error(f"Unable to create API-Url or API-Url not configured!")
                sys.exit(1)

            self.config = config
        else:
            logger.error(f"Unknown config file format: {self.config_file}")
            sys.exit(1)

    @staticmethod
    def is_filename_only(
            s: str
    ) -> bool:
        p = Path(s)
        return p.parent == Path('.')  # kein Ordner → nur Dateiname

    def get_cfg(
            self
    ) -> LabelpickerConfig:
        """
        Retrieves the current configuration object.

        This method is used to access the stored configuration instance of the
        class. The returned configuration provides necessary settings and
        parameters required for its functionality.

        :return: The configuration object for the class.
        :rtype: LabelpickerConfig
        """
        return self.config

    @staticmethod
    def generate_init_cfg(
            config_file: str = "",
    ) -> None:
        """
        Generates and processes the initial configuration file.

        This static method handles the generation of the initial configuration file by
        verifying the file's existence, reading its content, compressing it, and encoding
        the compressed content in Base64. It then prints the encoded content. If no custom
        configuration file name is provided, a default configuration file is used.

        :param config_file: Name of the configuration file to process. If not provided,
            a default configuration file 'labelpicker.dist.yml' is used.
        :type config_file: str
        :return: None
        """
        omd_root = os.environ.get("OMD_ROOT", '')
        if config_file:
            # Use the default config file
            config_file = os.path.join(omd_root, "etc", config_file)
        else:
            config_file = os.path.join(omd_root, "etc", "labelpicker_ng.dist.yml")

        # if the config file does not exist, read and encode it
        if os.path.exists(config_file):
            with open(config_file, "rb") as f:
                content = f.read()  # bytes
                # Encode the base64-encoded content
                compressed_content = zlib.compress(content)
                encoded_content = base64.b64encode(compressed_content)
                print(encoded_content)
        sys.exit(0)

    def init_cfg(
            self
    ) -> None:
        """
        Ensures the initialization of a configuration file. If the configuration file specified
        does not exist, it creates one by decoding, decompressing, and writing the initial
        configuration content. If the file already exists, the method logs this information
        and skips creation.

        :param self: Represents the instance of the class from which this method is called.
        :return: None
        """
        init_cfg = ('eJydV9ty2zYQfddXbKNOKXV0iZ2+hJ08qFLiuHVsjWWn04k9HIhciaxJggVAyZo439KX/kl+rAuApEldHLd6EYRdnL2dBVZtgP'
                    '7hT6sND3DG5hhPI/8OBYx5uoiWuWAq4ik8kPzp4y3S2MU8wRQFi8E3aAZmR8kP0b9L7lyS/R6pkOeqUO/BGmEdxTEosQGWK+7X'
                    'nRrAVYgw80WUKYgk8DTeAN6jnys2jxGiFBiMLTjISKGGVXivviNv2/AHz8FnpBNLDrlE4EngabUeSBQrFD29K1KWILA0gIxJue'
                    'YiAMWh9ANBhQY2Rd/kiWR6p7R6+XZ2BaPpqTHIssjLRWyMzlGDB+SjVMgC4Iua+SIhXsaF6kEmuA48Lt0iJBPpdd25aekcI58E'
                    '/pVHAgMbZwXsgp/c6Q2L4xbfA50VLjl9J1paBu2ajCcm1Xq/jN+tVma38M6FUKlM7xBktNh4UtLegpKLerOI3Wq5w+Gu6SE5Nz'
                    'SRe7Qg/eHR4CWRKubLZZQuNTuA1l6MK4w9Oih5TD7+Pro8Pz0/aUoXkRadnr+7KPczpkIXvv+scyE4V1+GKyaGJCELPpOoAckh'
                    'SbFaS7oTXDq6NgmHFYtzLH+32oyqvWIKvQUXGC1Tzw9ZukTpElNz1K0ADaoC6VmqxMjSPNNp81FK6KxDLFgkUGGqlYcZdSDxV0'
                    'chLf+JLlKRqaBL7loI42Z1pgjQ2YlQx5GZjvbSpaPPaFhdXy8TuIjuXWjqNGGNDy4c6UpAgAuWx8oeAHvcRFZDsGs6EmsymB+P'
                    'hrKdS4J+T5hikueC8rF7PxRymFmF/kwxoXAZke6W4VbwiOO2WgB1ZBfer2frK4H6PlFh1Z86PGC+KUXRuhHxgEgpNgTRB9sI75'
                    'kI1tRZ/RlfKLM4rWkBJDzINePiLJBeuJZrRZaMpJkALTLblhyuWdNxlmWG4vZn356yprn09KIQAWhkFz6VjvTgIkPNsXQJsw3d'
                    'JUkPzkn/tjpADeyH3lLwPNPVVERytxJqY5+cD5EvqAsXiu7fNOBrCTPTnnD88ugYLo+Bsp4GlAOnB84o9SMKvVS5mDm3z4XrDH'
                    '7sagjaLrdujp443mme70LnJvj805duBXRzBDfH8DaITI/14eZVhdZIInVbkPtqO4llWXtV6qZWcS8IFRnjb0N80GqNGjRRqHcX'
                    'dH3Q2yEqMIFLvPfMHVPUyIXO5O3Z2cP76cO7619Pr2bX3WeYrmHftp7bA49v1PMI3z7IeLq0rXQP69t12re3eN9+rP9OwivZM3'
                    'O+H4uuzpwonPqb/w94oJdqckvg89e/9cevX5UkNW+gc7urVyo4+2o10i8MwoTecV+nHTpnk9G0a269kEsFCSZzsh9Gmb65RhM4'
                    '0W7JehUtRr/C2FM685Bh0NTYKlMcsMzb2qMXPfACmg6ilOaItRgwOw5UMvvA0zvw6YVW6rOgv/vmv+jBiznz7/LsgPy2gTnXD3'
                    'VABifjN4VWzyyTR7W2VqxXiDrphw6f/0kBjmMaXN6cXF5cT7sdP33z2erpZH3pdpum6Obx9CREWZz09ai1K34ciEhlWpuJnuS2'
                    'd4eb4s3t07JOCysvRg1HTxJOXVwGtss5hxww5R85B0W/ON9y5fiwL5bD/9GZsbOH1x8T3WmwmmV68KmzdeXTBYPi5ZEXPXHXrG'
                    'R1cPueaYj2DXXVERfyLCtLusVs3VyezBcGcns2NpHTKLvbDfX5VtKAWzjTmHAFSrV1xDCsnLibMk2v5qxtP/X5+p2Zr3ezPJ59'
                    'rKfWlysP71mSxbgnpSTdl85q+xupTHlaeV7w5XB2JZpxhVPUzs8OaL9nfkgz9HyNEf0HW2Ly9Z+vfwO7UznGMSb0PzRA6Izlyv'
                    '4hHVQIVcOymMbywm09rFZ/Oox9Ct0OsXX6D1H5w1pWBjrYfwEFTqj9')

        # if the config file does not exist, create it
        if not os.path.isfile(self.config_file):
            # Decode the base64-encoded content
            decoded_content = base64.b64decode(init_cfg)
            decompressed_content = zlib.decompress(decoded_content).decode()

            # Write the decompressed content to a new file
            with open(self.config_file, "w") as file:
                file.write(decompressed_content)

            print(f"Config file {self.config_file} created.")
        else:
            print(f"Config file {self.config_file} already exists. Skipping init.")
        sys.exit(0)
