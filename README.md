![Banner](banner.png)

# misconfig-ConfigTemplateEnforcer
Validates configuration files against predefined templates, ensuring adherence to organizational standards. Validation checks the shape of the configuration against the template: every template key must be present in the configuration, and each present value must have the same type as the template value. Template values themselves are not compared, and there is no list of deprecated or unsupported settings, so a configuration value that differs from the template value passes as long as its type matches. - Focused on Check for misconfigurations in configuration files or infrastructure definitions

## Install
`git clone https://github.com/ShadowStrikeHQ/misconfig-configtemplateenforcer`
`pip install -r requirements.txt`

## Usage
`python3 main.py <config_file> <template_file> [--file_type json|yaml] [--lint] [--strict] [--ignore_missing]`

The config and the template are each loaded in their own format, inferred from each file's own extension, so a JSON config can be validated against a YAML template and the other way round. `--file_type` applies to the config file. An empty config file or an empty template file is reported by name as an empty file and exits 1.

Presence enforcement is on by default: a missing template key fails the run at exit 1. `--ignore_missing` turns missing keys back into warnings. Extra config keys are warnings by default and failures under `--strict`.

## Parameters
- `-h`: Show help message and exit
- `config_file`: Path to the configuration file to validate.
- `template_file`: Path to the template file to use for validation.
- `--file_type`: Specify the configuration file type (json or yaml). If omitted, it is inferred from the config file extension. The template type is always inferred from the template file extension.
- `--lint`: Run linters (yamllint/jsonlint) before validation.
- `--strict`: Enable strict validation: missing template keys fail (the default) and extra config keys fail as well.
- `--ignore_missing`: Opt out of presence enforcement: missing template keys are warnings instead of failures.

## License
Copyright (c) ShadowStrikeHQ
