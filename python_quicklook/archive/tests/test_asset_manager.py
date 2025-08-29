"""
Comprehensive tests for AssetManager class.
"""

import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.asset_manager import (
    AssetInfo,
    AssetManager,
    AssetManagerConfig,
)


class TestAssetInfo:
    """Test AssetInfo dataclass."""

    def test_asset_info_creation(self):
        """Test creating AssetInfo object."""
        path = Path("test.png")
        relative_path = Path("assets/test.png")

        asset_info = AssetInfo(
            path=path,
            asset_type="diagram",
            relative_path=relative_path,
            size_bytes=1024,
            created=True
        )

        assert asset_info.path == path
        assert asset_info.asset_type == "diagram"
        assert asset_info.relative_path == relative_path
        assert asset_info.size_bytes == 1024
        assert asset_info.created is True

    def test_asset_info_defaults(self):
        """Test AssetInfo default values."""
        path = Path("test.png")
        relative_path = Path("assets/test.png")

        asset_info = AssetInfo(
            path=path,
            asset_type="image",
            relative_path=relative_path
        )

        assert asset_info.size_bytes is None
        assert asset_info.created is False


class TestAssetManagerConfig:
    """Test AssetManagerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AssetManagerConfig()

        assert config.asset_dir_name == "assets"
        assert config.clean_on_start is False
        assert config.preserve_existing is True
        assert config.max_file_size_mb == 10
        assert ".png" in config.allowed_extensions
        assert ".svg" in config.allowed_extensions

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AssetManagerConfig(
            asset_dir_name="custom_assets",
            clean_on_start=True,
            preserve_existing=False,
            max_file_size_mb=5,
            allowed_extensions={".jpg", ".png"}
        )

        assert config.asset_dir_name == "custom_assets"
        assert config.clean_on_start is True
        assert config.preserve_existing is False
        assert config.max_file_size_mb == 5
        assert config.allowed_extensions == {".jpg", ".png"}


class TestAssetManager:
    """Test AssetManager class."""

    @pytest.fixture
    def temp_report_dir(self):
        """Create a temporary report directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"fake png data for testing")
            temp_path = Path(temp_file.name)

        yield temp_path

        # Cleanup
        temp_path.unlink(missing_ok=True)

    def test_initialization_default_config(self, temp_report_dir):
        """Test AssetManager initialization with default config."""
        manager = AssetManager(temp_report_dir)

        assert manager.report_dir == temp_report_dir
        assert isinstance(manager.config, AssetManagerConfig)
        assert manager.asset_dir == temp_report_dir / "assets"
        assert manager.managed_assets == {}

    def test_initialization_custom_config(self, temp_report_dir):
        """Test AssetManager initialization with custom config."""
        config = AssetManagerConfig(asset_dir_name="custom_assets")
        manager = AssetManager(temp_report_dir, config)

        assert manager.config == config
        assert manager.asset_dir == temp_report_dir / "custom_assets"

    def test_setup_directories_creates_dirs(self, temp_report_dir):
        """Test that setup creates necessary directories."""
        asset_dir = temp_report_dir / "assets"

        # Directories should not exist initially
        assert not asset_dir.exists()

        manager = AssetManager(temp_report_dir)

        # Directories should be created
        assert temp_report_dir.exists()
        assert asset_dir.exists()
        assert manager.asset_dir.exists()

    def test_setup_directories_clean_on_start(self, temp_report_dir):
        """Test directory cleanup on start."""
        asset_dir = temp_report_dir / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)

        # Create some files that should be cleaned
        (asset_dir / "classes_project.png").touch()
        (asset_dir / "packages_project.png").touch()
        (asset_dir / "keep_this.txt").touch()  # Should not be cleaned

        config = AssetManagerConfig(clean_on_start=True)
        manager = AssetManager(temp_report_dir, config)

        # Diagram files should be cleaned, others preserved
        assert not (asset_dir / "classes_project.png").exists()
        assert not (asset_dir / "packages_project.png").exists()
        assert (asset_dir / "keep_this.txt").exists()  # Should be preserved

    def test_get_asset_path(self, temp_report_dir):
        """Test getting asset path."""
        manager = AssetManager(temp_report_dir)

        asset_path = manager.get_asset_path("test.png")
        expected_path = temp_report_dir / "assets" / "test.png"

        assert asset_path == expected_path

    def test_get_relative_path_inside_report_dir(self, temp_report_dir):
        """Test getting relative path for asset inside report directory."""
        manager = AssetManager(temp_report_dir)

        asset_path = temp_report_dir / "assets" / "test.png"
        relative_path = manager.get_relative_path(asset_path)

        assert relative_path == Path("assets/test.png")

    def test_get_relative_path_outside_report_dir(self, temp_report_dir):
        """Test getting relative path for asset outside report directory."""
        manager = AssetManager(temp_report_dir)

        external_path = Path("/tmp/external.png")
        relative_path = manager.get_relative_path(external_path)

        assert relative_path == Path("assets/external.png")

    def test_register_asset_success(self, temp_report_dir, sample_image_file):
        """Test successful asset registration."""
        manager = AssetManager(temp_report_dir)

        asset_info = manager.register_asset(sample_image_file, "diagram", created=True)

        assert asset_info is not None
        assert asset_info.path == sample_image_file
        assert asset_info.asset_type == "diagram"
        assert asset_info.created is True
        assert asset_info.size_bytes is not None
        assert asset_info.size_bytes > 0

    def test_register_asset_file_not_exists(self, temp_report_dir):
        """Test asset registration with non-existent file."""
        manager = AssetManager(temp_report_dir)

        non_existent = Path("/tmp/does_not_exist.png")
        asset_info = manager.register_asset(non_existent, "diagram")

        assert asset_info is None

    def test_register_asset_file_too_large(self, temp_report_dir):
        """Test asset registration with file too large."""
        config = AssetManagerConfig(max_file_size_mb=0)  # Very small limit
        manager = AssetManager(temp_report_dir, config)

        # Create a file with some content
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"data" * 1000)  # Will exceed 0 MB limit
            temp_path = Path(temp_file.name)

        try:
            asset_info = manager.register_asset(temp_path, "diagram")
            assert asset_info is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_register_asset_invalid_extension(self, temp_report_dir):
        """Test asset registration with invalid file extension."""
        manager = AssetManager(temp_report_dir)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"text data")
            temp_path = Path(temp_file.name)

        try:
            asset_info = manager.register_asset(temp_path, "diagram")
            assert asset_info is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_copy_asset_success(self, temp_report_dir, sample_image_file):
        """Test successful asset copying."""
        manager = AssetManager(temp_report_dir)

        asset_info = manager.copy_asset(sample_image_file, "copied_image.png", "image")

        assert asset_info is not None
        assert asset_info.asset_type == "image"
        assert asset_info.created is True

        # Verify file was copied
        copied_file = temp_report_dir / "assets" / "copied_image.png"
        assert copied_file.exists()
        assert copied_file.read_bytes() == sample_image_file.read_bytes()

    def test_copy_asset_default_name(self, temp_report_dir, sample_image_file):
        """Test asset copying with default filename."""
        manager = AssetManager(temp_report_dir)

        asset_info = manager.copy_asset(sample_image_file)

        assert asset_info is not None
        copied_file = temp_report_dir / "assets" / sample_image_file.name
        assert copied_file.exists()

    def test_copy_asset_source_not_exists(self, temp_report_dir):
        """Test asset copying with non-existent source."""
        manager = AssetManager(temp_report_dir)

        non_existent = Path("/tmp/does_not_exist.png")
        asset_info = manager.copy_asset(non_existent, "target.png")

        assert asset_info is None

    def test_move_asset_success(self, temp_report_dir, sample_image_file):
        """Test successful asset moving."""
        manager = AssetManager(temp_report_dir)

        # Read original content before move
        original_content = sample_image_file.read_bytes()
        original_path = sample_image_file

        asset_info = manager.move_asset(sample_image_file, "moved_image.png", "image")

        assert asset_info is not None
        assert asset_info.asset_type == "image"
        assert asset_info.created is True

        # Verify file was moved
        moved_file = temp_report_dir / "assets" / "moved_image.png"
        assert moved_file.exists()
        assert moved_file.read_bytes() == original_content
        assert not original_path.exists()  # Original should be gone

    def test_get_markdown_image_ref_managed_asset(self, temp_report_dir, sample_image_file):
        """Test getting markdown reference for managed asset."""
        manager = AssetManager(temp_report_dir)

        # Register an asset
        asset_info = manager.copy_asset(sample_image_file, "test_diagram.png", "diagram")
        assert asset_info is not None

        md_ref = manager.get_markdown_image_ref("test_diagram.png", "Test Diagram")

        assert md_ref == "![Test Diagram](assets/test_diagram.png)"

    def test_get_markdown_image_ref_unmanaged_asset(self, temp_report_dir):
        """Test getting markdown reference for unmanaged asset."""
        manager = AssetManager(temp_report_dir)

        md_ref = manager.get_markdown_image_ref("unknown.png", "Unknown Image")

        assert md_ref == "![Unknown Image](assets/unknown.png)"

    def test_get_markdown_image_ref_default_alt_text(self, temp_report_dir, sample_image_file):
        """Test getting markdown reference with default alt text."""
        manager = AssetManager(temp_report_dir)

        # Register an asset
        manager.copy_asset(sample_image_file, "test_diagram.png", "diagram")

        md_ref = manager.get_markdown_image_ref("test_diagram.png")

        assert md_ref == "![Generated diagram](assets/test_diagram.png)"

    def test_get_asset_stats_empty(self, temp_report_dir):
        """Test getting asset statistics when no assets are managed."""
        manager = AssetManager(temp_report_dir)

        stats = manager.get_asset_stats()

        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["asset_types"] == {}
        assert "assets" in stats["asset_directory"]

    def test_get_asset_stats_with_assets(self, temp_report_dir, sample_image_file):
        """Test getting asset statistics with managed assets."""
        manager = AssetManager(temp_report_dir)

        # Add some assets
        asset1 = manager.copy_asset(sample_image_file, "image1.png", "image")
        asset2 = manager.copy_asset(sample_image_file, "diagram1.png", "diagram")

        stats = manager.get_asset_stats()

        assert stats["total_files"] == 2
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] >= 0
        assert stats["asset_types"]["image"] == 1
        assert stats["asset_types"]["diagram"] == 1

    def test_list_assets_all(self, temp_report_dir, sample_image_file):
        """Test listing all managed assets."""
        manager = AssetManager(temp_report_dir)

        # Add some assets
        manager.copy_asset(sample_image_file, "image1.png", "image")
        manager.copy_asset(sample_image_file, "diagram1.png", "diagram")

        assets = manager.list_assets()

        assert len(assets) == 2
        asset_types = [asset.asset_type for asset in assets]
        assert "image" in asset_types
        assert "diagram" in asset_types

    def test_list_assets_filtered(self, temp_report_dir, sample_image_file):
        """Test listing assets filtered by type."""
        manager = AssetManager(temp_report_dir)

        # Add different types of assets
        manager.copy_asset(sample_image_file, "image1.png", "image")
        manager.copy_asset(sample_image_file, "diagram1.png", "diagram")
        manager.copy_asset(sample_image_file, "image2.png", "image")

        # Filter by image type
        image_assets = manager.list_assets("image")
        assert len(image_assets) == 2
        assert all(asset.asset_type == "image" for asset in image_assets)

        # Filter by diagram type
        diagram_assets = manager.list_assets("diagram")
        assert len(diagram_assets) == 1
        assert diagram_assets[0].asset_type == "diagram"

    def test_cleanup_created_assets(self, temp_report_dir, sample_image_file):
        """Test cleanup of created assets."""
        manager = AssetManager(temp_report_dir)

        # Add some assets (created by tool)
        asset1 = manager.copy_asset(sample_image_file, "created1.png", "diagram")
        asset2 = manager.copy_asset(sample_image_file, "created2.png", "image")

        # Verify files exist
        assert asset1.path.exists()
        assert asset2.path.exists()

        # Run cleanup
        manager.cleanup()

        # Files should be removed
        assert not asset1.path.exists()
        assert not asset2.path.exists()

    def test_cleanup_preserves_existing_assets(self, temp_report_dir, sample_image_file):
        """Test cleanup preserves assets not created by tool."""
        manager = AssetManager(temp_report_dir)

        # Manually copy a file (simulate existing asset)
        existing_file = temp_report_dir / "assets" / "existing.png"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_bytes(sample_image_file.read_bytes())

        # Register as existing (not created by tool)
        asset_info = manager.register_asset(existing_file, "image", created=False)
        assert asset_info is not None
        assert not asset_info.created

        # Run cleanup
        manager.cleanup()

        # Existing file should be preserved
        assert existing_file.exists()

    def test_cleanup_removes_empty_asset_dir(self, temp_report_dir):
        """Test cleanup removes empty asset directory."""
        manager = AssetManager(temp_report_dir)

        # Asset directory should exist but be empty
        assert manager.asset_dir.exists()
        assert not any(manager.asset_dir.iterdir())

        # Run cleanup
        manager.cleanup()

        # Empty asset directory should be removed
        assert not manager.asset_dir.exists()

    def test_path_handling_windows_style(self, temp_report_dir):
        """Test path handling works correctly with Windows-style paths."""
        manager = AssetManager(temp_report_dir)

        # Simulate a Windows-style path in relative_path
        fake_windows_path = Path("assets\\test_image.png")
        asset_info = AssetInfo(
            path=temp_report_dir / "assets" / "test_image.png",
            asset_type="image",
            relative_path=fake_windows_path
        )

        manager.managed_assets["test_image.png"] = asset_info

        # Get markdown reference - should convert backslashes to forward slashes
        md_ref = manager.get_markdown_image_ref("test_image.png", "Test")
        assert "assets/test_image.png" in md_ref
        assert "\\" not in md_ref


class TestAssetManagerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def temp_report_dir(self):
        """Create a temporary report directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"fake png data for testing")
            temp_path = Path(temp_file.name)

        yield temp_path

        # Cleanup
        temp_path.unlink(missing_ok=True)

    def test_asset_manager_with_readonly_directory(self):
        """Test asset manager behavior with read-only directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "readonly"
            report_dir.mkdir()

            # Make directory read-only (on Unix systems)
            import stat
            try:
                report_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

                # This should handle the permission error gracefully
                with pytest.raises((PermissionError, OSError)):
                    AssetManager(report_dir)

            except (OSError, NotImplementedError):
                # Skip test on systems that don't support chmod
                pytest.skip("Chmod not supported on this system")
            finally:
                # Restore permissions for cleanup
                try:
                    report_dir.chmod(stat.S_IRWXU)
                except (OSError, FileNotFoundError):
                    pass

    def test_register_asset_with_stat_error(self, temp_report_dir):
        """Test asset registration when stat() fails."""
        manager = AssetManager(temp_report_dir)

        # Create a file then immediately delete it to simulate stat error
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test data")

        # Delete the file to cause stat to fail
        temp_path.unlink()

        # This should return None (file doesn't exist)
        asset_info = manager.register_asset(temp_path, "diagram")
        assert asset_info is None

    @patch("shutil.copy2")
    def test_copy_asset_copy_fails(self, mock_copy, temp_report_dir, sample_image_file):
        """Test asset copying when shutil.copy2 fails."""
        mock_copy.side_effect = OSError("Permission denied")

        manager = AssetManager(temp_report_dir)
        asset_info = manager.copy_asset(sample_image_file, "target.png")

        assert asset_info is None

    @patch("shutil.move")
    def test_move_asset_move_fails(self, mock_move, temp_report_dir, sample_image_file):
        """Test asset moving when shutil.move fails."""
        mock_move.side_effect = OSError("Permission denied")

        manager = AssetManager(temp_report_dir)
        asset_info = manager.move_asset(sample_image_file, "target.png")

        assert asset_info is None

    def test_multiple_assets_same_name(self, temp_report_dir, sample_image_file):
        """Test handling multiple assets with same filename."""
        manager = AssetManager(temp_report_dir)

        # Register first asset
        asset1 = manager.copy_asset(sample_image_file, "duplicate.png", "diagram")
        assert asset1 is not None

        # Create another file with same name (should overwrite in dict)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"different content")
            temp_path = Path(temp_file.name)

        try:
            asset2 = manager.copy_asset(temp_path, "duplicate.png", "image")
            assert asset2 is not None
            assert asset2.asset_type == "image"

            # Should have only one entry in managed_assets
            assert len(manager.managed_assets) == 1
            assert manager.managed_assets["duplicate.png"].asset_type == "image"

        finally:
            temp_path.unlink(missing_ok=True)


class TestAssetManagerIntegration:
    """Integration tests for AssetManager."""

    @pytest.fixture
    def temp_report_dir(self):
        """Create a temporary report directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_full_workflow(self, temp_report_dir):
        """Test complete asset management workflow."""
        manager = AssetManager(temp_report_dir)

        # Create some test files
        test_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(f"test data {i}".encode())
                test_files.append(Path(temp_file.name))

        try:
            # Copy assets
            for i, test_file in enumerate(test_files):
                asset_info = manager.copy_asset(test_file, f"asset_{i}.png", "diagram")
                assert asset_info is not None

            # Verify all assets are managed
            assert len(manager.managed_assets) == 3

            # Get statistics
            stats = manager.get_asset_stats()
            assert stats["total_files"] == 3
            assert stats["asset_types"]["diagram"] == 3

            # Generate markdown references
            refs = []
            for i in range(3):
                ref = manager.get_markdown_image_ref(f"asset_{i}.png", f"Asset {i}")
                refs.append(ref)
                assert f"Asset {i}" in ref
                assert f"assets/asset_{i}.png" in ref

            # List assets
            assets = manager.list_assets("diagram")
            assert len(assets) == 3

            # Cleanup
            manager.cleanup()

            # Verify files are removed
            for i in range(3):
                asset_file = temp_report_dir / "assets" / f"asset_{i}.png"
                assert not asset_file.exists()

        finally:
            # Clean up test files
            for test_file in test_files:
                test_file.unlink(missing_ok=True)

    def test_asset_manager_with_subdirectories(self, temp_report_dir):
        """Test asset manager with complex directory structure."""
        # Create nested report structure
        sub_report_dir = temp_report_dir / "reports" / "project1"

        manager = AssetManager(sub_report_dir)

        # Should create nested directory structure
        assert sub_report_dir.exists()
        assert (sub_report_dir / "assets").exists()

        # Test relative path calculation
        asset_path = sub_report_dir / "assets" / "test.png"
        relative_path = manager.get_relative_path(asset_path)
        assert relative_path == Path("assets/test.png")


if __name__ == "__main__":
    pytest.main([__file__])
