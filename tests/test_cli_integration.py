#!/usr/bin/env python3
"""
Integration tests for CLI module - testing end-to-end functionality
"""

from unittest.mock import Mock, patch

import pytest

from github_inventory.cli import (
    collect_repository_data,
    generate_outputs,
    main,
    open_directory,
    print_summary,
)
from github_inventory.exceptions import (
    AuthenticationError,
    ConfigurationError,
    GitHubCLIError,
)


class TestOpenDirectory:
    """Test directory opening functionality"""

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_macos(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform
    ):
        """Test opening directory on macOS"""
        mock_platform.return_value = "Darwin"
        mock_exists.return_value = True

        open_directory("/test/path")

        mock_subprocess.assert_called_once_with(["open", "/test/path"], check=True)

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_windows(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform
    ):
        """Test opening directory on Windows"""
        mock_platform.return_value = "Windows"
        mock_exists.return_value = True

        open_directory("/test/path")

        mock_subprocess.assert_called_once_with(["explorer", "/test/path"], check=True)

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_linux(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform
    ):
        """Test opening directory on Linux"""
        mock_platform.return_value = "Linux"
        mock_exists.return_value = True

        open_directory("/test/path")

        mock_subprocess.assert_called_once_with(["xdg-open", "/test/path"], check=True)

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_creates_missing_directory(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform
    ):
        """Test that missing directory is created"""
        mock_platform.return_value = "Darwin"
        mock_exists.return_value = False

        open_directory("/test/path")

        mock_makedirs.assert_called_once_with("/test/path", exist_ok=True)


class TestMainFunctionIntegration:
    """Integration tests for main CLI function"""

    @patch("github_inventory.cli.open_directory")
    @patch("github_inventory.cli.PathManager")
    @patch("sys.argv", ["ghscan", "--open"])
    def test_main_open_command(self, mock_path_manager, mock_open_directory):
        """Test main function with --open command"""
        mock_path_manager_instance = Mock()
        mock_path_manager_instance.output_base = "/test/docs"
        mock_path_manager.return_value = mock_path_manager_instance

        main()

        mock_open_directory.assert_called_once_with("/test/docs")

    @patch("github_inventory.cli.read_csv_data")
    @patch("github_inventory.cli.generate_markdown_report")
    @patch("github_inventory.cli.print_summary")
    @patch("sys.argv", ["ghscan", "--report-only"])
    def test_main_report_only_mode(
        self, mock_print_summary, mock_generate_report, mock_read_csv
    ):
        """Test main function with --report-only mode"""
        # Mock data
        owned_data = [{"name": "repo1", "visibility": "public"}]
        starred_data = [{"name": "repo2", "visibility": "public"}]

        mock_read_csv.side_effect = [owned_data, starred_data]
        mock_generate_report.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_generate_report.assert_called_once()
        mock_print_summary.assert_called_once_with(owned_data, starred_data)

    @patch("github_inventory.cli.read_csv_data")
    @patch("sys.argv", ["ghscan", "--report-only"])
    def test_main_report_only_no_data(self, mock_read_csv, capsys):
        """Test main function with --report-only mode when no CSV files exist"""
        mock_read_csv.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No existing CSV files found" in captured.out

    @patch("github_inventory.cli.handle_batch_processing")
    @patch("sys.argv", ["ghscan", "--batch"])
    def test_main_batch_processing(self, mock_handle_batch):
        """Test main function with batch processing"""
        main()
        mock_handle_batch.assert_called_once()

    @patch("github_inventory.cli.create_github_client")
    @patch("sys.argv", ["ghscan", "--client-type", "api"])
    def test_main_client_setup_error(self, mock_create_client, capsys):
        """Test main function with client setup error"""
        mock_create_client.side_effect = AuthenticationError("Authentication failed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Client setup error" in captured.out

    @patch("github_inventory.cli.create_github_client")
    @patch("github_inventory.cli.collect_repository_data")
    @patch("sys.argv", ["ghscan"])
    def test_main_authentication_error(
        self, mock_collect_data, mock_create_client, capsys
    ):
        """Test main function with authentication error during data collection"""
        mock_create_client.return_value = Mock()
        mock_collect_data.side_effect = AuthenticationError(
            "GitHub authentication failed"
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "GitHub authentication failed" in captured.out
        assert "gh auth login" in captured.out


class TestCollectRepositoryData:
    """Test repository data collection functionality"""

    def test_collect_owned_only(self):
        """Test collecting only owned repositories"""
        args = Mock()
        args.user = "testuser"
        args.limit = None
        args.owned_only = False
        args.starred_only = True  # Only starred, skip owned
        args.owned_csv = "owned.csv"
        args.starred_csv = "starred.csv"

        path_manager = Mock()
        path_manager.get_owned_csv_path.return_value = "owned.csv"
        path_manager.get_starred_csv_path.return_value = "starred.csv"

        mock_client = Mock()

        with patch(
            "github_inventory.cli.collect_owned_repositories"
        ) as mock_collect_owned:
            with patch(
                "github_inventory.cli.collect_starred_repositories"
            ) as mock_collect_starred:
                with patch("github_inventory.cli.write_to_csv"):
                    mock_collect_owned.return_value = []
                    mock_collect_starred.return_value = [{"name": "starred_repo"}]

                    owned, starred = collect_repository_data(
                        args, path_manager, mock_client
                    )

                    # Should not call collect_owned_repositories when starred_only=True
                    mock_collect_owned.assert_not_called()
                    mock_collect_starred.assert_called_once_with(
                        "testuser", None, mock_client
                    )


class TestGenerateOutputs:
    """Test output generation functionality"""

    def test_generate_outputs_success(self):
        """Test successful output generation"""
        owned_repos = [{"name": "repo1"}]
        starred_repos = [{"name": "repo2"}]
        args = Mock()
        args.user = "testuser"
        args.limit = None
        args.no_report = False
        args.report_md = "report.md"

        path_manager = Mock()
        path_manager.get_report_md_path.return_value = "report.md"

        with patch("github_inventory.cli.generate_markdown_report") as mock_generate:
            with patch("github_inventory.cli.print_summary") as mock_print:
                mock_generate.return_value = True

                result = generate_outputs(
                    owned_repos, starred_repos, args, path_manager
                )

                assert result is True
                mock_generate.assert_called_once()
                mock_print.assert_called_once_with(owned_repos, starred_repos)

    def test_generate_outputs_no_report_flag(self):
        """Test output generation with --no-report flag"""
        owned_repos = [{"name": "repo1"}]
        starred_repos: list = []
        args = Mock()
        args.user = "testuser"
        args.limit = None
        args.no_report = True

        path_manager = Mock()

        with patch("github_inventory.cli.generate_markdown_report") as mock_generate:
            with patch("github_inventory.cli.print_summary") as mock_print:
                result = generate_outputs(
                    owned_repos, starred_repos, args, path_manager
                )

                assert result is True
                mock_generate.assert_not_called()  # Should skip report generation
                mock_print.assert_called_once_with(owned_repos, starred_repos)

    def test_generate_outputs_no_data(self):
        """Test output generation with no data"""
        owned_repos: list = []
        starred_repos: list = []
        args = Mock()
        path_manager = Mock()

        result = generate_outputs(owned_repos, starred_repos, args, path_manager)

        assert result is False


class TestPrintSummary:
    """Test summary printing functionality"""

    def test_print_summary_with_owned_repos(self, capsys):
        """Test printing summary with owned repositories"""
        owned_repos = [
            {"visibility": "public", "is_fork": "false", "primary_language": "Python"},
            {
                "visibility": "private",
                "is_fork": "true",
                "primary_language": "JavaScript",
            },
            {"visibility": "public", "is_fork": "false", "primary_language": "Python"},
        ]
        starred_repos: list = []

        print_summary(owned_repos, starred_repos)

        captured = capsys.readouterr()
        assert "Your repositories: 3" in captured.out
        assert "Public: 2 | Private: 1" in captured.out
        assert "Original: 2 | Forks: 1" in captured.out
        assert "Python: 2" in captured.out

    def test_print_summary_with_starred_repos(self, capsys):
        """Test printing summary with starred repositories"""
        owned_repos: list = []
        starred_repos = [
            {"visibility": "public", "archived": "false", "primary_language": "Go"},
            {"visibility": "public", "archived": "true", "primary_language": "Rust"},
        ]

        print_summary(owned_repos, starred_repos)

        captured = capsys.readouterr()
        assert "Starred repositories: 2" in captured.out
        assert "Public: 2 | Private: 0 | Archived: 1" in captured.out
        assert "Go: 1" in captured.out
        assert "Rust: 1" in captured.out


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch("github_inventory.cli.handle_batch_processing")
    @patch("sys.argv", ["ghscan", "--batch"])
    def test_main_configuration_error(self, mock_handle_batch, capsys):
        """Test main function with configuration error in batch processing"""
        mock_handle_batch.side_effect = ConfigurationError("Invalid config format")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Configuration error" in captured.out

    @patch("github_inventory.cli.handle_batch_processing")
    @patch("sys.argv", ["ghscan", "--batch"])
    def test_main_runtime_error_in_batch(self, mock_handle_batch):
        """Test main function with runtime error in batch processing"""
        mock_handle_batch.side_effect = RuntimeError("Batch processing failed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("github_inventory.cli.create_github_client")
    @patch("github_inventory.cli.collect_repository_data")
    @patch("sys.argv", ["ghscan"])
    def test_main_github_cli_error(self, mock_collect_data, mock_create_client, capsys):
        """Test main function with GitHub CLI error"""
        mock_create_client.return_value = Mock()
        mock_collect_data.side_effect = GitHubCLIError("GitHub CLI command failed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "GitHub CLI error" in captured.out
        assert "GitHub CLI installation" in captured.out

    @patch("github_inventory.cli.create_github_client")
    @patch("github_inventory.cli.collect_repository_data")
    @patch("github_inventory.cli.generate_outputs")
    @patch("sys.argv", ["ghscan"])
    def test_main_output_generation_error(
        self, mock_generate_outputs, mock_collect_data, mock_create_client, capsys
    ):
        """Test main function with output generation error"""
        from github_inventory.exceptions import GitHubInventoryError

        mock_create_client.return_value = Mock()
        mock_collect_data.return_value = ([], [])
        mock_generate_outputs.side_effect = GitHubInventoryError(
            "Failed to generate outputs"
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error generating outputs" in captured.out

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_subprocess_error(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform, capsys
    ):
        """Test open_directory with subprocess error"""
        from subprocess import CalledProcessError

        mock_platform.return_value = "Darwin"
        mock_exists.return_value = True
        mock_subprocess.side_effect = CalledProcessError(1, ["open"])

        open_directory("/test/path")

        captured = capsys.readouterr()
        assert "Could not open directory" in captured.out

    @patch("platform.system")
    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_open_directory_file_not_found_error(
        self, mock_makedirs, mock_exists, mock_subprocess, mock_platform, capsys
    ):
        """Test open_directory with FileNotFoundError"""
        mock_platform.return_value = "Darwin"
        mock_exists.return_value = True
        mock_subprocess.side_effect = FileNotFoundError("Command not found")

        open_directory("/test/path")

        captured = capsys.readouterr()
        assert "Could not find file manager" in captured.out

    @patch("github_inventory.cli.read_csv_data")
    @patch("github_inventory.cli.generate_markdown_report")
    @patch("sys.argv", ["ghscan", "--report-only"])
    def test_main_report_only_generation_error(
        self, mock_generate_report, mock_read_csv, capsys
    ):
        """Test main function with report generation error in report-only mode"""
        from github_inventory.exceptions import GitHubInventoryError

        mock_read_csv.return_value = [{"name": "test"}]
        mock_generate_report.side_effect = GitHubInventoryError(
            "Failed to write report"
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error generating report" in captured.out


class TestBatchProcessingHandling:
    """Test batch processing error handling"""

    def test_handle_batch_processing_conflicting_args(self, capsys):
        """Test batch processing with conflicting arguments"""
        from github_inventory.cli import handle_batch_processing

        args = Mock()
        args.batch = True
        args.config = "config.yaml"

        with pytest.raises(SystemExit) as exc_info:
            handle_batch_processing(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Cannot use --batch and --config together" in captured.out

    @patch("github_inventory.cli.get_default_configs")
    @patch("github_inventory.cli.run_batch_processing")
    def test_handle_batch_processing_default_configs(
        self, mock_run_batch, mock_get_configs
    ):
        """Test batch processing with default configurations"""
        from github_inventory.cli import handle_batch_processing

        args = Mock()
        args.batch = True
        args.config = None

        mock_configs = [{"account": "user1"}, {"account": "user2"}]
        mock_get_configs.return_value = mock_configs

        handle_batch_processing(args)

        mock_get_configs.assert_called_once()
        mock_run_batch.assert_called_once_with(mock_configs)

    @patch("github_inventory.cli.load_config_from_file")
    @patch("github_inventory.cli.run_batch_processing")
    def test_handle_batch_processing_custom_config(
        self, mock_run_batch, mock_load_config
    ):
        """Test batch processing with custom configuration file"""
        from github_inventory.cli import handle_batch_processing

        args = Mock()
        args.batch = False
        args.config = "custom.yaml"

        mock_configs = [{"account": "user1"}]
        mock_load_config.return_value = mock_configs

        handle_batch_processing(args)

        mock_load_config.assert_called_once_with("custom.yaml")
        mock_run_batch.assert_called_once_with(mock_configs)
