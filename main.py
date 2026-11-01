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
        help="Enable strict validation: missing template keys fail (the default) and extra config keys fail as well."
    )
    parser.add_argument(
        "--ignore_missing",
        action="store_true",
        help="Opt out of presence enforcement: missing template keys are warnings instead of failures."
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
            if ignore_missing:
                logging.warning(f"Missing key '{key}' in configuration (ignored because --ignore_missing was given).")
            else:
                logging.error(f"Missing key '{key}' in configuration.")
                valid = False

            continue # Skip value validation for a missing key

        config_value = config_data[key]

        # A template list gets no walk at all. The else branch below
        # compares list against list as bare types, so a config list
        # of the wrong item types, or the wrong length, passes a
        # template that spelled out exactly what its items should
        # look like.
        if isinstance(template_value, dict):
            if not isinstance(config_value, dict):
                logging.error(f"Type mismatch for key '{key}': Expected dict, got {type(config_value)}.")
                valid = False
                continue
            if not validate_config(config_value, template_value, strict, ignore_missing):
                valid = False
        else:
            # Simple type comparison
            # Only the type is compared, never the value. A template is
            # an exemplar in my hands: a config whose port is a string of
            # the right type in the template's sense passes with any
            # number at all, and a template written to pin a value down
            # to one allowed setting does not do that here.
            expected_type = type(template_value)
            actual_type = type(config_value)
            # Exact type identity cuts both ways across formats: a whole
            # number in a YAML template is an int, and the same number
            # written 1.0 in a JSON config is a float, so two spellings of
            # one value fail each other. Booleans at least stay distinct
            # from ints here, because type(True) is not type(1).
            if expected_type != actual_type:
                logging.error(f"Type mismatch for key '{key}': Expected {expected_type}, got {actual_type}.")
                valid = False

    # Check for extra keys in the config file that aren't in the template.
    # They are warnings by default and failures in strict mode.
    for key in config_data:
        if key not in template_data:
            if strict:
                logging.error(f"Extra key '{key}' found in configuration that isn't defined in the template (strict mode).")
                valid = False
            else:
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
            # Only the config is linted, never the template it is judged
            # against, and a missing linter binary counts the same as a
            # failed lint: the run aborts before any validation, with the
            # environment's gap reported as the config's failure.
            if not lint_file(args.config_file, file_type):
                logging.error("Linting failed. Aborting validation.")
                sys.exit(1)  # Exit with an error code

        # Load configuration and template files. Each file is loaded in
        # its own format: the config uses --file_type when given and its
        # own extension otherwise, and the template is always inferred
        # from the template file's own extension, so a JSON config can
        # be validated against a YAML template and the other way round.
        config_data = load_file(args.config_file, file_type)
        # The template is always inferred from its own suffix. The
        # file type option was applied to the config above and is
        # not passed here, so a template with an unrecognised suffix
        # cannot be rescued by the flag that rescued the config.
        template_data = load_file(args.template_file)

        # An empty file loads as None. Name it as empty instead of
        # letting it fail later with an internal NoneType message.
        if config_data is None:
            logging.error(f"Configuration file is empty: {args.config_file}")
            sys.exit(1)
        if template_data is None:
            logging.error(f"Template file is empty: {args.template_file}")
            sys.exit(1)
        if not isinstance(config_data, dict):
            logging.error(f"Configuration file did not contain a mapping of keys: {args.config_file}")
            sys.exit(1)
        if not isinstance(template_data, dict):
            logging.error(f"Template file did not contain a mapping of keys: {args.template_file}")
            sys.exit(1)

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