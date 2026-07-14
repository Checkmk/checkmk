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
import os
import pickle
from labelpicker_ng import CleanupConfig, logger, HostLabels
from pprint import pformat
from pathlib import Path

class DataRetention:
    """
    Handles data retention tasks including managing retention settings, saving serialized
    data, and loading serialized data. The primary purpose of this class is to facilitate
    persistence and organized retention of serialized data (in pickle format) in a specific
    directory.

    It uses a defined retention mechanism to maintain a fixed number of serialized files,
    automatically cleaning up older files beyond the retention limit. This ensures that
    the storage is efficiently managed while retaining recent data as per the retention
    settings. Directory structure is validated and created when necessary.

    :ivar config: Configuration object of type CleanupConfig that holds necessary
                  settings for retention, file naming, and directory management.
    :type config: CleanupConfig
    """
    config: CleanupConfig

    def __init__(
            self,
            config: CleanupConfig
    ):
        """
        Initializes the CleanupTask instance and sets up necessary configuration and data directory.
        If the directory is not provided in the configuration, a default path based on the "OMD_ROOT"
        environment variable is determined.

        :param config: An instance of CleanupConfig containing the necessary configurations
                       including the directory for data processing.
        :type config: CleanupConfig
        """
        self.config = config
        self.check_directory()

    @staticmethod
    def is_real_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def check_directory(
            self
    ) -> Path | bool:
        """
        Check if the specified data directory exists, and create it if it does not.

        This method ensures the existence of a data directory at the specified path. If
        the directory does not exist, it attempts to create it, logging the outcome.
        In case of failure during the creation of the directory, an exception is raised.

        :raises Exception: If the directory creation fails for any reason.
        :return: Path object representing the data directory if it exists or is created
                 successfully, or `False` if not.
        :rtype: Path | bool
        """
        directory = self.config.retention_path
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created data directory: {directory}")
                return Path(directory)
            except Exception as e:
                logger.error(f"Failed to create data directory: {directory}\n{pformat(e, indent=4)}")
                raise
        return Path(directory)

    def save_pickle_rotating_in_dir(
            self,
            data: HostLabels,
    ) -> bool:
        """
        Saves a pickle file with a rotating naming scheme in the specified directory. This function manages
        a set number of retention files, renaming and deleting older files as needed according to the
        retention settings in the configuration. The newest file overwrites the oldest file once the
        retention limit is reached.

        :param data: An instance of HostLabels containing data to be serialized and saved.
        :type data: HostLabels
        :return: A boolean indicating whether the operation was successful. Returns True if the pickle
                 file was successfully saved, False otherwise.
        :rtype: bool
        """
        if directory:=self.check_directory():
            # Extension erzwingen, falls nicht vorhanden
            base_name = self.config.filename_prefix if self.config.filename_prefix.endswith(
                ".pkl") else self.config.filename_prefix + ".pkl"

            base = Path.joinpath(directory, base_name)  # vollständiger Pfad zur Hauptdatei

            if self.config.retention_files > 0:
                # Älteste Version löschen
                oldest = Path(str(base) + f".{self.config.retention_files}")
                if oldest.exists():
                    oldest.unlink()

                # Versionen rückwärts verschieben
                for i in range(self.config.retention_files - 1, 0, -1):
                    src = Path(str(base) + f".{i}")
                    dst = Path(str(base) + f".{i + 1}")
                    if src.exists():
                        src.rename(dst)

                # current -> .1
                if base.exists():
                    base.rename(Path(str(base) + ".1"))

            # Neue Datei schreiben (kein mkdir!)
            with base.open("wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.debug(f"Saved data to {base}")
            return True
        return False

    def load_data(
            self,
            file: int = None
    ):
        """
        Loads data from a specified pickle file. The function retrieves data using
        the provided file identifier or a default filename derived from the
        configured `filename_prefix`. If the file does not exist, an empty
        dictionary is returned. If the file exists, the dictionary stored inside
        the pickle file is read and returned.

        :param file: An optional identifier to specify which file to load.
                     Default is None, in which case the default
                     `filename_prefix` is used.
        :return: A dictionary containing the data loaded from the pickle file.
        :rtype: dict
        """
        base_name = self.config.filename_prefix if self.config.filename_prefix.endswith(
            ".pkl") else self.config.filename_prefix + ".pkl"

        backup_extension = file if self.is_real_int(file) else ""
        base = Path(f"{base_name}.{backup_extension}")

        base = Path.joinpath(Path('/', self.config.retention_path), base)  # vollständiger Pfad zur Hauptdatei

        if not base.exists():
            return {}

        with open(base, "rb") as f:
            data: HostLabels = pickle.load(f)
            logger.debug(f"Loaded data from {base_name}")
        return data
