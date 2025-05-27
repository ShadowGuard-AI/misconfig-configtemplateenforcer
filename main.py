#!/usr/bin/env python3

import argparse
import logging
import os
import json
import yaml
import subprocess
import sys
from typing import Optional, Union


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_argparse() -> argparse.ArgumentParser:
    """
    Sets up the argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Validates configuration files against predefined templates, ensuring adherence to organizational standards."
    )

    parser.add_argument(
        "config_file",
        help="Path to the configuration file to validate."
    )
    parser.add_argument(
        "template_file",
        help="Path to the template file to use for validation."
    )
    parser.add_argument(
        "--file_type",
        choices=["json", "yaml"],
        default=None,
        help="Specify the configuration file type (json or yaml). If omitted, attempts to infer from file extension."
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linters (yamllint/jsonlint) before validation."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation: all template keys must be present in the config file."
    )
    parser.add_argument(
        "--ignore_missing",
        action="store_true",
        help="Ignore missing keys in the config file if not present in the template."
    )

    return parser


def load_file(file_path: str, file_type: Optional[str] = None) -> Union[dict, list]:
    """
    Loads a JSON or YAML file.

    Args:
        file_path (str): Path to the file.
        file_type (Optional[str]): File type ("json" or "yaml"). If None, infers from extension.

    Returns:
        Union[dict, list]: The loaded data as a dictionary or list.

    Raises:
        ValueError: If the file type is invalid or cannot be inferred.
        FileNotFoundError: If the file does not exist.
        Exception: If there's an error during file loading.
    """
    try:
        with open(file_path, 'r') as f:
            if file_type is None:
                if file_path.endswith(".json"):
                    file_type = "json"
                elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                    file_type = "yaml"
                else:
                    raise ValueError("Could not infer file type. Please specify using --file_type.")

            if file_type == "json":
                return json.load(f)
            elif file_type == "yaml":
                return yaml.safe_load(f)
            else:
                raise ValueError("Invalid file type. Must be 'json' or 'yaml'.")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error in {file_path}: {e}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"YAML decoding error in {file_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        raise


def lint_file(file_path: str, file_type: str) -> bool:
    """
    Lints a JSON or YAML file using yamllint or jsonlint.

    Args:
        file_path (str): Path to the file.
        file_type (str): File type ("json" or "yaml").

    Returns:
        bool: True if linting passed, False otherwise.
    """
    try:
        if file_type == "yaml":
            result = subprocess.run(["yamllint", file_path], capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"yamllint failed for {file_path}:\n{result.stderr}")
                return False
            else:
                logging.info(f"yamllint passed for {file_path}")
                return True
        elif file_type == "json":
            result = subprocess.run(["jsonlint", "-q", file_path], capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"jsonlint failed for {file_path}:\n{result.stderr}")
                return False
            else:
                logging.info(f"jsonlint passed for {file_path}")
                return True
        else:
            logging.error(f"Unsupported file type: {file_type}")
            return False
    except FileNotFoundError as e:
        logging.error(f"Linter not found: {e}")
        return False
    except Exception as e:
        logging.error(f"Error during linting: {e}")
        return False


def validate_config(config_data: dict, template_data: dict, strict: bool = False, ignore_missing: bool = False) -> bool:
    """
    Validates the configuration data against the template.

    Args:
        config_data (dict): The configuration data to validate.
        template_data (dict): The template data to use for validation.
        strict (bool): If True, enforces that all template keys must exist in the config.
        ignore_missing (bool): If True, ignores missing config keys.

    Returns:
        bool: True if the configuration is valid, False otherwise.
    """

    valid = True
    for key, template_value in template_data.items():
        if key not in config_data:
            if strict:
                logging.error(f"Missing key '{key}' in configuration (strict mode).")
                valid = False
            elif not ignore_missing:
                logging.warning(f"Missing key '{key}' in configuration.")

            continue # Skip validation if the key is missing and not strict

        config_value = config_data[key]

        if isinstance(template_value, dict):
            if not isinstance(config_value, dict):
                logging.error(f"Type mismatch for key '{key}': Expected dict, got {type(config_value)}.")
                valid = False
                continue
            if not validate_config(config_value, template_value, strict, ignore_missing):
                valid = False
        else:
            # Simple type comparison
            expected_type = type(template_value)
            actual_type = type(config_value)
            if expected_type != actual_type:
                logging.error(f"Type mismatch for key '{key}': Expected {expected_type}, got {actual_type}.")
                valid = False

    if not strict and not ignore_missing:
      # Check for extra keys in the config file that aren't in the template
      for key in config_data:
        if key not in template_data:
          logging.warning(f"Extra key '{key}' found in configuration that isn't defined in the template.")

    return valid


def main() -> None:
    """
    Main function to parse arguments, load files, and validate the configuration.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    try:
        # Determine file type
        file_type = args.file_type
        if file_type is None:
            if args.config_file.endswith(".json"):
                file_type = "json"
            elif args.config_file.endswith(".yaml") or args.config_file.endswith(".yml"):
                file_type = "yaml"
            else:
                parser.error("Could not infer config file type. Please specify using --file_type.")
                return # Exit early

        # Run linters if requested
        if args.lint:
            if not lint_file(args.config_file, file_type):
                logging.error("Linting failed. Aborting validation.")
                sys.exit(1)  # Exit with an error code

        # Load configuration and template files
        config_data = load_file(args.config_file, file_type)
        template_data = load_file(args.template_file, file_type)

        # Validate the configuration
        if validate_config(config_data, template_data, args.strict, args.ignore_missing):
            logging.info("Configuration is valid.")
        else:
            logging.error("Configuration is invalid.")
            sys.exit(1)  # Exit with an error code

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit with an error code


if __name__ == "__main__":
    main()