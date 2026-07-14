#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2026 SWR
# @author Frank Baier <frank.baier@swr.de>
#
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl, SecretStr

LabelPrefix = str
LabelKey = str
LabelValue = str
Labels = Dict[LabelKey, LabelValue]
Host = str
HostLabels = Dict[Host, Labels]

class CheckmkConfig(BaseModel):
    """
    Represents the configuration for Checkmk.

    This class is used to define the configuration settings required to interact
    with a Checkmk environment. It includes parameters like server details, site
    information, authentication credentials, and API-specific details.

    :ivar omd_root: The root directory of the OMD (Open Monitoring Distribution)
        installation, if applicable.
    :type omd_root: str | None
    :ivar omd_site: The site name for the Checkmk installation, if applicable.
    :type omd_site: str | None
    :ivar protocol: The protocol used for communication with the Checkmk server.
    :type protocol: Literal["http", "https"]
    :ivar server: The hostname or IP address of the Checkmk server.
    :type server: str | None
    :ivar port: The port number used to connect to the Checkmk server.
    :type port: int | None
    :ivar username: The username used for authentication. The Default is "automation".
    :type username: str
    :ivar password: The password used for authentication.
    :type password: SecretStr | None
    :ivar verify_ssl: Determines if SSL certificate verification should be enforced.
        Defaults to True.
    :type verify_ssl: bool
    :ivar api_version: The version of the Checkmk API to use. The Default is "1.0".
    :type api_version: Literal["1.0"]
    :ivar api_url: The complete URL for the Checkmk API, if pre-defined.
    :type api_url: Optional[HttpUrl] | None
    """
    omd_root: str | None = None
    omd_site: str | None = None
    protocol: Literal["http", "https"] = "http"
    server: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str = "automation"
    password: SecretStr | None = None
    verify_ssl: bool = True
    api_version: Literal["1.0"] = "1.0"
    api_url: HttpUrl | None = None


class LoggingConfig(BaseModel):
    """
    Configuration for logging in the application.

    Defines the logging levels for the console and file outputs,
    as well as the log file name and log file path to be used.

    :ivar log_level_console: Logging level for console output.
    :type log_level_console: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    :ivar log_level_file: Logging level for file output.
    :type log_level_file: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    :ivar log_file: Name of the log file used for file-based logging.
    :type log_file: str
    :ivar log_path: Path where the log file will be stored.
    :type log_path: str
    """
    log_level_console: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"
    log_level_file: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: str = "labelpicker_ng.log"
    log_path: str = "${omd_root}/var/log"


class CaseConversionConfig(BaseModel):
    """
    Represents the configuration for case conversion.

    This configuration class is used to store the settings for case conversion.
    It allows specifying a label and a value, which determine how the case
    conversion should be applied.

    :ivar label: Gewünschte Groß-/Kleinschreibung für Label-Namen. Erlaubte Werte:
                 "lower", "upper", "none". Standard: "lower".
    :type label: Literal["lower", "upper", "none"]
    :ivar value: Gewünschte Groß-/Kleinschreibung für Label-Werte. Erlaubte Werte:
                 "lower", "upper", "none". Standard: "lower".
    :type value: Literal["lower", "upper", "none"]
    """
    label: Literal["lower", "upper", 'none'] = "lower"
    value: Literal["lower", "upper", 'none'] = "lower"

class DatasourceConfig(BaseModel):
    """
    Represents a configuration for a datasource.

    This class defines attributes and their types essential for configuring
    a datasource. It includes settings for module identification, label
    prefixing, cleanup strategies, case conversion, additional configuration,
    and table row mapping. The class allows users to customize how the
    datasource should behave or integrate into a system.

    :ivar name: The unique name of the datasource configuration.
    :type name: str
    :ivar module: The associated module for the datasource.
    :type module: str
    :ivar label_prefix: An optional label prefix for datasource items.
    :type label_prefix: Optional[str]
    :ivar case_conversion: The case conversion strategy configuration.
    :type case_conversion: CaseConversionConfig
    :ivar config: A dictionary containing additional configuration for the
        datasource.
    :type config: Dict[str, Any]
    """
    name: str
    module: str
    label_prefix: Optional[str] = None
    case_conversion: CaseConversionConfig = Field(default_factory=CaseConversionConfig)
    config: Dict[str, Any] = Field(default_factory=dict)


class CleanupConfig(BaseModel):
    """
    Represents configuration settings for cleanup operations.

    The `CleanupConfig` class provides configuration options to perform cleanup
    operations. It allows specifying the cleanup strategy, target directory,
    filename prefix, and a retention policy for files. This class facilitates
    managing and maintaining clear and concise cleanup behavior.

    :ivar retention_path: Directory where cleanup will be applied. If set to ``None``,
        a default directory may be used.
    :ivar filename_prefix: Prefix used for filenames involved in the cleanup
        process. Defaults to "labelpicker_ng".
    :ivar retention_files: Number of files to retain when performing cleanup.
        Files exceeding this number may be removed.
    :type retention_files: int
    """
    retention_path: str = "${omd_root}/var/labelpicker_ng"
    filename_prefix: str = "labelpicker_ng"
    retention_files: int = 10


class LabelpickerConfig(BaseModel):
    """
    Configuration object for the Labelpicker application.

    This class manages the configurations required to initialize and run the
    Labelpicker application. It encapsulates all the necessary settings for
    integration, logging, cleanup operations, label handling, and datasource
    management. Default values are provided for most configurations, ensuring
    sensible defaults for typical use cases.

    :ivar checkmk: Configuration related to Checkmk integration.
    :type checkmk: CheckmkConfig
    :ivar logging: Logging configuration details.
    :type logging: LoggingConfig
    :ivar label_prefix: Prefix used for labels generated or managed by the application.
    :type label_prefix: str
    :ivar cleanup: Configuration settings for cleanup operations.
    :type cleanup: CleanupConfig
    :ivar case_conversion: Configuration controlling case conversion operations for labels.
    :type case_conversion: CaseConversionConfig
    :ivar activate_foreign_changes: Indicates whether to activate changes from foreign
        sources.
    :type activate_foreign_changes: bool
    :ivar datasources: List of datasource configurations.
    :type datasources: List[DatasourceConfig]
    """
    checkmk: CheckmkConfig = Field(default_factory=CheckmkConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    label_prefix: str = "lp"
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    case_conversion: CaseConversionConfig = Field(default_factory=CaseConversionConfig)
    activate_foreign_changes: bool = True
    datasources: List[DatasourceConfig] = Field(default_factory=list)
