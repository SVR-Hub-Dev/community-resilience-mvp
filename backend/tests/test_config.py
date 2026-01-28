"""Tests for deployment configuration."""

import os
import pytest
from unittest.mock import patch


class TestDeploymentConfig:
    """Test DeploymentConfig behavior."""

    def test_default_mode_is_cloud(self):
        """Default deployment mode should be cloud."""
        # Need to reload config with clean environment
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get fresh config
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig, DeploymentMode

            assert DeploymentConfig.DEPLOYMENT_MODE == DeploymentMode.CLOUD

    def test_cloud_mode_disables_docling(self):
        """Cloud mode should disable Docling features."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "cloud"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.DOCLING_ENABLED is False
            assert DeploymentConfig.FULL_OCR_ENABLED is False
            assert DeploymentConfig.OFFICE_CONVERSION_ENABLED is False

    def test_local_mode_enables_docling(self):
        """Local mode should enable Docling features."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "local"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.DOCLING_ENABLED is True
            assert DeploymentConfig.FULL_OCR_ENABLED is True
            assert DeploymentConfig.OFFICE_CONVERSION_ENABLED is True

    def test_cloud_upload_size_limit(self):
        """Cloud mode should have smaller upload limit."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "cloud"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.MAX_UPLOAD_SIZE_MB == 10

    def test_local_upload_size_limit(self):
        """Local mode should have larger upload limit."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "local"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.MAX_UPLOAD_SIZE_MB == 50

    def test_cloud_supported_extensions(self):
        """Cloud mode should support limited file types."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "cloud"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            extensions = DeploymentConfig.get_supported_extensions()
            assert ".pdf" in extensions
            assert ".txt" in extensions
            assert ".md" in extensions
            assert ".docx" not in extensions

    def test_local_supported_extensions(self):
        """Local mode should support all file types."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "local"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            extensions = DeploymentConfig.get_supported_extensions()
            assert ".pdf" in extensions
            assert ".docx" in extensions
            assert ".pptx" in extensions

    def test_needs_local_processing_cloud_mode(self):
        """Office docs should need local processing in cloud mode."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "cloud"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.needs_local_processing("report.docx") is True
            assert DeploymentConfig.needs_local_processing("report.pdf") is False

    def test_needs_local_processing_local_mode(self):
        """Nothing should need local processing in local mode."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "local"}):
            import importlib
            import config

            importlib.reload(config)

            from config import DeploymentConfig

            assert DeploymentConfig.needs_local_processing("report.docx") is False
            assert DeploymentConfig.needs_local_processing("report.pdf") is False

    def test_config_summary(self):
        """Config summary should return all expected fields."""
        from config import DeploymentConfig

        summary = DeploymentConfig.get_config_summary()

        assert "deployment_mode" in summary
        assert "docling_enabled" in summary
        assert "ocr_enabled" in summary
        assert "max_upload_size_mb" in summary
        assert "supported_extensions" in summary


class TestSyncConfig:
    """Test SyncConfig behavior."""

    def test_sync_disabled_by_default(self):
        """Sync should be disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import config

            importlib.reload(config)

            from config import SyncConfig

            assert SyncConfig.SYNC_ENABLED is False

    def test_sync_valid_when_disabled(self):
        """Disabled sync config should be valid."""
        with patch.dict(os.environ, {"SYNC_ENABLED": "false"}):
            import importlib
            import config

            importlib.reload(config)

            from config import SyncConfig

            assert SyncConfig.is_valid() is True

    def test_sync_invalid_when_enabled_without_url(self):
        """Enabled sync without URL should be invalid."""
        with patch.dict(
            os.environ, {"SYNC_ENABLED": "true", "SYNC_API_KEY": "test-key"}, clear=True
        ):
            import importlib
            import config

            importlib.reload(config)

            from config import SyncConfig

            assert SyncConfig.is_valid() is False
