"""
Asset manager for Python Quick Look tool.
Handles management of generated diagram files and other assets.
"""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AssetInfo:
    """Information about a managed asset."""

    path: Path
    asset_type: str  # 'diagram', 'image', 'document', etc.
    relative_path: Path  # Path relative to report location
    size_bytes: Optional[int] = None
    created: bool = False  # Whether this asset was created by this tool


@dataclass
class AssetManagerConfig:
    """Configuration for asset management."""

    asset_dir_name: str = "assets"  # Name of assets directory
    clean_on_start: bool = False  # Clean existing assets on initialization
    preserve_existing: bool = True  # Keep existing files that aren't managed
    max_file_size_mb: int = 10  # Maximum allowed file size in MB
    allowed_extensions: Set[str] = field(default_factory=lambda: {
        ".png", ".svg", ".pdf", ".jpg", ".jpeg", ".gif", ".webp"
    })


class AssetManager:
    """Manages assets (diagrams, images, etc.) for report generation."""

    def __init__(self, report_dir: Path, config: Optional[AssetManagerConfig] = None):
        """Initialize asset manager.

        Args:
            report_dir: Directory where the report will be saved
            config: Configuration for asset management
        """
        self.report_dir = Path(report_dir)
        self.config = config or AssetManagerConfig()
        self.asset_dir = self.report_dir / self.config.asset_dir_name
        self.managed_assets: Dict[str, AssetInfo] = {}

        # Ensure directories exist
        self._setup_directories()

    def _setup_directories(self) -> None:
        """Setup required directories."""
        try:
            # Create report directory if it doesn't exist
            self.report_dir.mkdir(parents=True, exist_ok=True)

            # Handle asset directory
            if self.config.clean_on_start and self.asset_dir.exists():
                self._clean_asset_directory()

            # Create asset directory
            self.asset_dir.mkdir(parents=True, exist_ok=True)

            logger.debug(f"Asset directories prepared: {self.asset_dir}")
        except Exception as e:
            logger.error(f"Failed to setup asset directories: {e}")
            raise

    def _clean_asset_directory(self) -> None:
        """Clean the asset directory of managed files."""
        if not self.asset_dir.exists():
            return

        try:
            # Only remove files we recognize as potentially created by this tool
            for file_path in self.asset_dir.iterdir():
                if file_path.is_file():
                    # Remove files with recognized diagram naming patterns
                    if (file_path.stem.startswith(("classes_", "packages_")) or
                        file_path.name in ["classes.png", "packages.png", "diagram.png"]):
                        file_path.unlink()
                        logger.debug(f"Cleaned asset file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean asset directory: {e}")

    def get_asset_path(self, asset_name: str) -> Path:
        """Get the full path for an asset.

        Args:
            asset_name: Name of the asset file

        Returns:
            Full path to the asset
        """
        return self.asset_dir / asset_name

    def get_relative_path(self, asset_path: Path) -> Path:
        """Get path relative to report directory.

        Args:
            asset_path: Full path to asset

        Returns:
            Path relative to report directory
        """
        try:
            return asset_path.relative_to(self.report_dir)
        except ValueError:
            # If asset is outside report dir, just return the filename
            return Path(self.config.asset_dir_name) / asset_path.name

    def register_asset(self, asset_path: Path, asset_type: str, created: bool = True) -> Optional[AssetInfo]:
        """Register an asset for management.

        Args:
            asset_path: Path to the asset file
            asset_type: Type of asset (diagram, image, etc.)
            created: Whether this asset was created by this tool

        Returns:
            AssetInfo object or None if registration failed
        """
        if not asset_path.exists():
            logger.warning(f"Asset file does not exist: {asset_path}")
            return None

        # Check file size
        try:
            file_size = asset_path.stat().st_size
            max_size = self.config.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                logger.warning(f"Asset file too large: {asset_path} ({file_size} bytes)")
                return None
        except Exception as e:
            logger.warning(f"Failed to check asset file size: {e}")
            file_size = None

        # Check extension
        if asset_path.suffix.lower() not in self.config.allowed_extensions:
            logger.warning(f"Asset file type not allowed: {asset_path}")
            return None

        # Create asset info
        asset_info = AssetInfo(
            path=asset_path,
            asset_type=asset_type,
            relative_path=self.get_relative_path(asset_path),
            size_bytes=file_size,
            created=created
        )

        # Register the asset
        asset_key = asset_path.name
        self.managed_assets[asset_key] = asset_info

        logger.debug(f"Registered asset: {asset_key} -> {asset_path}")
        return asset_info

    def copy_asset(self, source_path: Path, target_name: Optional[str] = None,
                   asset_type: str = "diagram") -> Optional[AssetInfo]:
        """Copy an external file to the assets directory.

        Args:
            source_path: Path to source file
            target_name: Target filename (default: use source filename)
            asset_type: Type of asset

        Returns:
            AssetInfo object or None if copy failed
        """
        if not source_path.exists():
            logger.error(f"Source asset file does not exist: {source_path}")
            return None

        target_name = target_name or source_path.name
        target_path = self.get_asset_path(target_name)

        try:
            # Copy the file
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied asset: {source_path} -> {target_path}")

            # Register the asset
            return self.register_asset(target_path, asset_type, created=True)

        except Exception as e:
            logger.error(f"Failed to copy asset {source_path} to {target_path}: {e}")
            return None

    def move_asset(self, source_path: Path, target_name: Optional[str] = None,
                   asset_type: str = "diagram") -> Optional[AssetInfo]:
        """Move an external file to the assets directory.

        Args:
            source_path: Path to source file
            target_name: Target filename (default: use source filename)
            asset_type: Type of asset

        Returns:
            AssetInfo object or None if move failed
        """
        if not source_path.exists():
            logger.error(f"Source asset file does not exist: {source_path}")
            return None

        target_name = target_name or source_path.name
        target_path = self.get_asset_path(target_name)

        try:
            # Move the file
            shutil.move(str(source_path), str(target_path))
            logger.info(f"Moved asset: {source_path} -> {target_path}")

            # Register the asset
            return self.register_asset(target_path, asset_type, created=True)

        except Exception as e:
            logger.error(f"Failed to move asset {source_path} to {target_path}: {e}")
            return None

    def get_markdown_image_ref(self, asset_name: str, alt_text: str = "") -> str:
        """Get markdown image reference for an asset.

        Args:
            asset_name: Name of the asset file
            alt_text: Alt text for the image

        Returns:
            Markdown image reference string
        """
        if asset_name in self.managed_assets:
            relative_path = self.managed_assets[asset_name].relative_path
            alt_text = alt_text or f"Generated {self.managed_assets[asset_name].asset_type}"
        else:
            relative_path = Path(self.config.asset_dir_name) / asset_name
            alt_text = alt_text or "Asset"

        # Use forward slashes for markdown paths (works on all platforms)
        path_str = str(relative_path).replace("\\", "/")
        return f"![{alt_text}]({path_str})"

    def get_asset_stats(self) -> Dict[str, any]:
        """Get statistics about managed assets.

        Returns:
            Dictionary with asset statistics
        """
        total_files = len(self.managed_assets)
        total_size = sum(
            asset.size_bytes for asset in self.managed_assets.values()
            if asset.size_bytes is not None
        )

        types = {}
        for asset in self.managed_assets.values():
            types[asset.asset_type] = types.get(asset.asset_type, 0) + 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size > 0 else 0,
            "asset_types": types,
            "asset_directory": str(self.asset_dir)
        }

    def list_assets(self, asset_type: Optional[str] = None) -> List[AssetInfo]:
        """List managed assets.

        Args:
            asset_type: Filter by asset type (optional)

        Returns:
            List of AssetInfo objects
        """
        assets = list(self.managed_assets.values())

        if asset_type:
            assets = [asset for asset in assets if asset.asset_type == asset_type]

        return sorted(assets, key=lambda a: a.path.name)

    def cleanup(self) -> None:
        """Clean up temporary or created assets."""
        removed_count = 0

        for asset_name, asset_info in list(self.managed_assets.items()):
            if asset_info.created and asset_info.path.exists():
                try:
                    asset_info.path.unlink()
                    removed_count += 1
                    logger.debug(f"Cleaned up asset: {asset_info.path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up asset {asset_info.path}: {e}")

        # Remove empty asset directory if we created it
        if self.asset_dir.exists() and not any(self.asset_dir.iterdir()):
            try:
                self.asset_dir.rmdir()
                logger.debug(f"Removed empty asset directory: {self.asset_dir}")
            except Exception as e:
                logger.debug(f"Could not remove asset directory: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} asset files")


def main():
    """Main entry point for testing asset management."""
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Test asset management functionality")
    parser.add_argument("--report-dir", default=".", help="Report directory path")
    parser.add_argument("--test", action="store_true", help="Run test operations")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    report_dir = Path(args.report_dir)
    manager = AssetManager(report_dir)

    print(f"📁 Asset manager initialized")
    print(f"   Report dir: {manager.report_dir}")
    print(f"   Asset dir: {manager.asset_dir}")

    if args.test:
        print("\n🧪 Running test operations...")

        # Create a test file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake png content for testing")

        try:
            # Test copy operation
            asset_info = manager.copy_asset(temp_path, "test_diagram.png", "diagram")
            if asset_info:
                print(f"✅ Copied test asset: {asset_info.relative_path}")

                # Test markdown reference
                md_ref = manager.get_markdown_image_ref("test_diagram.png", "Test Diagram")
                print(f"📝 Markdown reference: {md_ref}")

            # Show stats
            stats = manager.get_asset_stats()
            print(f"\n📊 Asset statistics: {stats}")

        finally:
            # Clean up test file
            temp_path.unlink(missing_ok=True)
            manager.cleanup()

    else:
        # Just show current state
        stats = manager.get_asset_stats()
        print(f"\n📊 Current asset statistics: {stats}")

        assets = manager.list_assets()
        if assets:
            print(f"\n📄 Managed assets:")
            for asset in assets:
                print(f"  - {asset.path.name} ({asset.asset_type})")


if __name__ == "__main__":
    main()
