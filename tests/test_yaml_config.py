#!/usr/bin/env python3
"""
Tests for YAML configuration functionality
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from github_inventory.batch import (
    ConfigsToRun,
    RunConfig,
    get_default_configs,
    load_config_from_file,
)


class TestYAMLConfiguration:
    """Test YAML configuration parsing functionality"""

    def test_load_valid_yaml_config(self):
        """Test loading a valid YAML configuration file"""
        yaml_content = """
configs:
  - account: langchain-ai
    limit: 10
  - account: aider-ai
  - account: danny-avila
    limit: 25
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert isinstance(result, ConfigsToRun)
            assert len(result.configs) == 3

            # Check first config with limit
            assert result.configs[0].account == "langchain-ai"
            assert result.configs[0].limit == 10

            # Check second config without limit
            assert result.configs[1].account == "aider-ai"
            assert result.configs[1].limit is None

            # Check third config with limit
            assert result.configs[2].account == "danny-avila"
            assert result.configs[2].limit == 25

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_load_valid_yaml_with_yml_extension(self):
        """Test loading YAML with .yml extension"""
        yaml_content = """
configs:
  - account: test-user
    limit: 5
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert isinstance(result, ConfigsToRun)
            assert len(result.configs) == 1
            assert result.configs[0].account == "test-user"
            assert result.configs[0].limit == 5

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_load_minimal_yaml_config(self):
        """Test loading minimal YAML configuration with just accounts"""
        yaml_content = """
configs:
  - account: user1
  - account: user2
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 2
            assert result.configs[0].account == "user1"
            assert result.configs[0].limit is None
            assert result.configs[1].account == "user2"
            assert result.configs[1].limit is None

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestJSONConfiguration:
    """Test JSON configuration parsing for backward compatibility"""

    def test_load_valid_json_config(self):
        """Test loading a valid JSON configuration file"""
        json_content = {
            "configs": [
                {"account": "langchain-ai", "limit": 10},
                {"account": "aider-ai"},
                {"account": "danny-avila", "limit": 25},
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as temp_file:
            json.dump(json_content, temp_file)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert isinstance(result, ConfigsToRun)
            assert len(result.configs) == 3
            assert result.configs[0].account == "langchain-ai"
            assert result.configs[0].limit == 10
            assert result.configs[1].account == "aider-ai"
            assert result.configs[1].limit is None
            assert result.configs[2].account == "danny-avila"
            assert result.configs[2].limit == 25

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_load_minimal_json_config(self):
        """Test loading minimal JSON configuration"""
        json_content = {"configs": [{"account": "test-user"}]}

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as temp_file:
            json.dump(json_content, temp_file)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 1
            assert result.configs[0].account == "test-user"
            assert result.configs[0].limit is None

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestConfigurationErrorHandling:
    """Test error handling for configuration files"""

    def test_missing_file(self):
        """Test handling of missing configuration file"""
        non_existent_file = "/tmp/non_existent_config.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config_from_file(non_existent_file)

        assert "Configuration file not found" in str(exc_info.value)

    def test_unsupported_file_extension(self):
        """Test handling of unsupported file extensions"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as temp_file:
            temp_file.write("some content")
            temp_file_path = temp_file.name

        try:
            with pytest.raises(ValueError) as exc_info:
                load_config_from_file(temp_file_path)

            assert "Unsupported file format '.txt'" in str(exc_info.value)
            assert "Supported formats: .json, .yaml, .yml" in str(exc_info.value)

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_invalid_yaml_syntax(self, capsys):
        """Test handling of invalid YAML syntax"""
        invalid_yaml = """
configs:
  - account: user1
    limit: [invalid: yaml: syntax}
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(invalid_yaml)
            temp_file_path = temp_file.name

        try:
            with pytest.raises(SystemExit):
                load_config_from_file(temp_file_path)

            captured = capsys.readouterr()
            assert "Error loading configuration file" in captured.out
            assert "Invalid YAML format" in captured.out

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_invalid_json_syntax(self, capsys):
        """Test handling of invalid JSON syntax"""
        invalid_json = '{"configs": [{"account": "user1", "limit": invalid}]}'

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as temp_file:
            temp_file.write(invalid_json)
            temp_file_path = temp_file.name

        try:
            with pytest.raises(SystemExit):
                load_config_from_file(temp_file_path)

            captured = capsys.readouterr()
            assert "Error loading configuration file" in captured.out
            assert "Invalid JSON format" in captured.out

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_empty_yaml_file(self, capsys):
        """Test handling of empty YAML file"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write("")
            temp_file_path = temp_file.name

        try:
            with pytest.raises(SystemExit):
                load_config_from_file(temp_file_path)

            captured = capsys.readouterr()
            assert "Error loading configuration file" in captured.out
            assert "Empty or invalid YAML file" in captured.out

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_yaml_with_null_content(self, capsys):
        """Test handling of YAML file that parses to None"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write("---\n")  # Valid YAML that parses to None
            temp_file_path = temp_file.name

        try:
            with pytest.raises(SystemExit):
                load_config_from_file(temp_file_path)

            captured = capsys.readouterr()
            assert "Error loading configuration file" in captured.out
            assert "Empty or invalid YAML file" in captured.out

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_non_dict_content(self, capsys):
        """Test handling of non-dictionary content"""
        yaml_content = """
- account: user1
- account: user2
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            with pytest.raises(SystemExit):
                load_config_from_file(temp_file_path)

            captured = capsys.readouterr()
            assert "Error loading configuration file" in captured.out
            assert "Configuration file must contain a JSON/YAML object" in captured.out
            assert "got list" in captured.out

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestConfigurationValidation:
    """Test Pydantic model validation of configuration structures"""

    @patch("sys.exit")
    def test_missing_configs_key(self, mock_exit):
        """Test handling of missing 'configs' key"""
        yaml_content = """
accounts:
  - name: user1
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            load_config_from_file(temp_file_path)
            mock_exit.assert_called_once_with(1)

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    @patch("sys.exit")
    def test_missing_account_field(self, mock_exit):
        """Test handling of missing 'account' field"""
        yaml_content = """
configs:
  - limit: 10
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            load_config_from_file(temp_file_path)
            mock_exit.assert_called_once_with(1)

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    @patch("sys.exit")
    def test_invalid_limit_type(self, mock_exit):
        """Test handling of invalid limit type"""
        yaml_content = """
configs:
  - account: user1
    limit: "invalid"
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            load_config_from_file(temp_file_path)
            mock_exit.assert_called_once_with(1)

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_valid_limit_zero(self):
        """Test that limit of zero is valid"""
        yaml_content = """
configs:
  - account: user1
    limit: 0
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 1
            assert result.configs[0].account == "user1"
            assert result.configs[0].limit == 0

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_valid_negative_limit(self):
        """Test that negative limit is handled (should be valid by Pydantic)"""
        yaml_content = """
configs:
  - account: user1
    limit: -1
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 1
            assert result.configs[0].account == "user1"
            assert result.configs[0].limit == -1

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestExampleConfigurations:
    """Test the exact configurations from example files"""

    def test_example_yaml_format(self):
        """Test the exact YAML format from config_example.yaml"""
        yaml_content = """
configs:
  - account: langchain-ai
    limit: 10
  - account: aider-ai
  - account: danny-avila
    limit: 25
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 3

            # Verify exact structure from example
            assert result.configs[0].account == "langchain-ai"
            assert result.configs[0].limit == 10

            assert result.configs[1].account == "aider-ai"
            assert result.configs[1].limit is None

            assert result.configs[2].account == "danny-avila"
            assert result.configs[2].limit == 25

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_example_json_format(self):
        """Test the exact JSON format from config_example.json"""
        json_content = {
            "configs": [
                {"account": "langchain-ai", "limit": 10},
                {"account": "aider-ai"},
                {"account": "danny-avila", "limit": 25},
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as temp_file:
            json.dump(json_content, temp_file)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 3

            # Verify exact structure from example
            assert result.configs[0].account == "langchain-ai"
            assert result.configs[0].limit == 10

            assert result.configs[1].account == "aider-ai"
            assert result.configs[1].limit is None

            assert result.configs[2].account == "danny-avila"
            assert result.configs[2].limit == 25

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestMixedAccountConfigurations:
    """Test configurations with mixed account types"""

    def test_mixed_accounts_with_and_without_limits(self):
        """Test configuration with accounts that have and don't have limits"""
        yaml_content = """
configs:
  - account: unlimited-user
  - account: limited-user-1
    limit: 50
  - account: another-unlimited
  - account: limited-user-2
    limit: 100
  - account: zero-limit-user
    limit: 0
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml", encoding="utf-8"
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 5

            # Check unlimited accounts
            assert result.configs[0].account == "unlimited-user"
            assert result.configs[0].limit is None

            assert result.configs[2].account == "another-unlimited"
            assert result.configs[2].limit is None

            # Check limited accounts
            assert result.configs[1].account == "limited-user-1"
            assert result.configs[1].limit == 50

            assert result.configs[3].account == "limited-user-2"
            assert result.configs[3].limit == 100

            # Check zero limit account
            assert result.configs[4].account == "zero-limit-user"
            assert result.configs[4].limit == 0

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_large_configuration_list(self):
        """Test loading a large configuration with many accounts"""
        configs = []
        for i in range(20):
            config = {"account": f"user-{i:02d}"}
            if i % 3 == 0:  # Every third user gets a limit
                config["limit"] = (i + 1) * 10
            configs.append(config)

        yaml_content = {"configs": configs}

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as temp_file:
            json.dump(yaml_content, temp_file)
            temp_file_path = temp_file.name

        try:
            result = load_config_from_file(temp_file_path)

            assert len(result.configs) == 20

            # Check some specific accounts
            assert result.configs[0].account == "user-00"
            assert result.configs[0].limit == 10  # i=0, (0+1)*10=10

            assert result.configs[1].account == "user-01"
            assert result.configs[1].limit is None

            assert result.configs[3].account == "user-03"
            assert result.configs[3].limit == 40  # i=3, (3+1)*10=40

        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestPydanticModels:
    """Test the Pydantic models directly"""

    def test_run_config_model_valid(self):
        """Test RunConfig model with valid data"""
        # Test with limit
        config = RunConfig(account="testuser", limit=50)
        assert config.account == "testuser"
        assert config.limit == 50

        # Test without limit
        config = RunConfig(account="testuser")
        assert config.account == "testuser"
        assert config.limit is None

    def test_run_config_model_validation_error(self):
        """Test RunConfig model validation errors"""
        # Test missing required field
        with pytest.raises(ValidationError):
            RunConfig()

        # Test invalid limit type
        with pytest.raises(ValidationError):
            RunConfig(account="testuser", limit="invalid")

    def test_configs_to_run_model(self):
        """Test ConfigsToRun model"""
        configs = [
            RunConfig(account="user1", limit=10),
            RunConfig(account="user2"),
        ]

        config_container = ConfigsToRun(configs=configs)

        assert len(config_container.configs) == 2
        assert config_container.configs[0].account == "user1"
        assert config_container.configs[0].limit == 10
        assert config_container.configs[1].account == "user2"
        assert config_container.configs[1].limit is None

    def test_get_default_configs(self):
        """Test the get_default_configs function"""
        default_configs = get_default_configs()

        assert isinstance(default_configs, ConfigsToRun)
        assert len(default_configs.configs) == 3

        # Check specific default values
        assert default_configs.configs[0].account == "microsoft"
        assert default_configs.configs[0].limit == 50

        assert default_configs.configs[1].account == "google"
        assert default_configs.configs[1].limit == 50

        assert default_configs.configs[2].account == "facebook"
        assert default_configs.configs[2].limit == 50


@pytest.mark.parametrize("file_extension", [".yaml", ".yml", ".json"])
def test_file_format_detection(file_extension):
    """Test that file format is correctly detected based on extension"""
    if file_extension == ".json":
        content = {"configs": [{"account": "testuser"}]}
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=file_extension, encoding="utf-8"
        ) as temp_file:
            json.dump(content, temp_file)
            temp_file_path = temp_file.name
    else:
        content = "configs:\n  - account: testuser\n"
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=file_extension, encoding="utf-8"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

    try:
        result = load_config_from_file(temp_file_path)

        assert isinstance(result, ConfigsToRun)
        assert len(result.configs) == 1
        assert result.configs[0].account == "testuser"

    finally:
        Path(temp_file_path).unlink(missing_ok=True)


@pytest.mark.parametrize(
    "content,expected_error",
    [
        ("invalid: yaml: [syntax", "Invalid YAML format"),
        ('{"invalid": json syntax}', "Invalid JSON format"),
        ("", "Empty or invalid YAML file"),
        ("[]", "Configuration file must contain a JSON/YAML object"),
        ('"just a string"', "Configuration file must contain a JSON/YAML object"),
    ],
)
def test_error_cases_parametrized(content, expected_error, capsys):
    """Test various error cases with parametrized inputs"""
    # Determine file extension based on content
    extension = (
        ".json"
        if content.startswith("{") or content.startswith("[") or content.startswith('"')
        else ".yaml"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=extension, encoding="utf-8"
    ) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        with pytest.raises(SystemExit):
            load_config_from_file(temp_file_path)

        captured = capsys.readouterr()
        assert expected_error in captured.out

    finally:
        Path(temp_file_path).unlink(missing_ok=True)
