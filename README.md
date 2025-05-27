# misconfig-ConfigTemplateEnforcer
Validates configuration files against predefined templates, ensuring adherence to organizational standards and preventing the use of deprecated or unsupported settings. - Focused on Check for misconfigurations in configuration files or infrastructure definitions

## Install
`git clone https://github.com/ShadowStrikeHQ/misconfig-configtemplateenforcer`

## Usage
`./misconfig-configtemplateenforcer [params]`

## Parameters
- `-h`: Show help message and exit
- `--file_type`: No description provided
- `--lint`: No description provided
- `--strict`: Enable strict validation: all template keys must be present in the config file.
- `--ignore_missing`: Ignore missing keys in the config file if not present in the template.

## License
Copyright (c) ShadowStrikeHQ
