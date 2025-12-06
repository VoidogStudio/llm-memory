"""Namespace resolution and validation service."""

import re
from pathlib import Path

from llm_memory.config.settings import Settings


class NamespaceService:
    """Service for namespace resolution, validation, and auto-detection."""

    NAMESPACE_PATTERN = r"^[a-z0-9_/-]{1,128}$"

    def __init__(self, settings: Settings) -> None:
        """Initialize namespace service.

        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self._cache: dict[str, str] = {}

    async def resolve_namespace(
        self,
        explicit: str | None,
        current_dir: Path | None = None,
    ) -> str:
        """Resolve namespace using priority order.

        Priority:
        1. Explicit parameter
        2. Settings default_namespace
        3. Auto-detection (if enabled)
        4. Fallback to 'default'

        Args:
            explicit: Explicitly specified namespace
            current_dir: Directory for auto-detection

        Returns:
            Resolved namespace value

        Raises:
            ValueError: If namespace format is invalid
        """
        # Priority 1: Explicit parameter
        if explicit:
            return self.validate_namespace(explicit)

        # Priority 2: Settings default_namespace
        if self.settings.default_namespace:
            return self.validate_namespace(self.settings.default_namespace)

        # Priority 3: Auto-detection
        if self.settings.namespace_auto_detect:
            detected = await self._auto_detect(current_dir)
            if detected:
                return detected

        # Priority 4: Fallback
        return "default"

    def validate_namespace(self, namespace: str) -> str:
        """Validate and normalize namespace format.

        Args:
            namespace: Namespace value to validate

        Returns:
            Normalized namespace (lowercase)

        Raises:
            ValueError: If format is invalid
        """
        normalized = namespace.lower().strip()
        if not re.match(self.NAMESPACE_PATTERN, normalized):
            raise ValueError(
                f"Invalid namespace format: {namespace}. "
                "Must be 1-128 characters, alphanumeric, hyphens, "
                "underscores, and slashes only."
            )
        return normalized

    def validate_shared_write(self, namespace: str, explicit: bool) -> None:
        """Prevent accidental writes to 'shared' namespace.

        Args:
            namespace: Target namespace
            explicit: Whether namespace was explicitly specified

        Raises:
            ValueError: If attempting implicit write to 'shared'
        """
        if namespace == "shared" and not explicit:
            raise ValueError(
                "Writing to 'shared' namespace requires explicit "
                "namespace='shared' parameter. Auto-detected namespaces "
                "cannot write to shared."
            )

    async def _auto_detect(self, current_dir: Path | None) -> str:
        """Auto-detect namespace from Git config or directory name.

        Args:
            current_dir: Directory to search (defaults to cwd)

        Returns:
            Detected namespace value
        """
        if current_dir is None:
            current_dir = Path.cwd()

        # Check cache
        cache_key = str(current_dir)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try Git config
        git_config = current_dir / ".git" / "config"
        if git_config.exists():
            remote_url = self._parse_git_config(git_config)
            if remote_url:
                namespace = self._normalize_git_url(remote_url)
                if namespace:
                    self._cache[cache_key] = namespace
                    return namespace

        # Fallback to directory name
        dir_name = current_dir.name.lower()
        # Normalize directory name to match namespace pattern
        dir_name = re.sub(r"[^a-z0-9_/-]", "-", dir_name)
        if dir_name and re.match(self.NAMESPACE_PATTERN, dir_name):
            self._cache[cache_key] = dir_name
            return dir_name

        # Last resort
        return "default"

    def _parse_git_config(self, config_path: Path) -> str | None:
        """Parse .git/config to extract remote.origin.url.

        Args:
            config_path: Path to .git/config file

        Returns:
            Remote URL or None if not found
        """
        try:
            content = config_path.read_text(encoding="utf-8")
            in_remote_origin = False

            for line in content.splitlines():
                line = line.strip()

                # Check for [remote "origin"] section
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue

                # Exit section
                if line.startswith("[") and in_remote_origin:
                    break

                # Extract URL
                if in_remote_origin and line.startswith("url = "):
                    return line.split("url = ", 1)[1].strip()

            return None
        except (OSError, UnicodeDecodeError):
            return None

    def _normalize_git_url(self, url: str) -> str | None:
        """Normalize Git URL to owner/repo format.

        Supports GitHub, GitLab, and Bitbucket URLs in both HTTPS and SSH formats.

        Args:
            url: Git remote URL

        Returns:
            Normalized namespace (owner/repo) or None if parsing fails
        """
        # Patterns for common Git hosting services
        patterns = [
            # GitHub: https://github.com/owner/repo.git or git@github.com:owner/repo.git
            r"github\.com[:/]([^/]+)/([^/.]+)",
            # GitLab: https://gitlab.com/owner/repo.git or git@gitlab.com:owner/repo.git
            r"gitlab\.com[:/]([^/]+)/([^/.]+)",
            # Bitbucket: https://bitbucket.org/owner/repo.git or git@bitbucket.org:owner/repo.git
            r"bitbucket\.org[:/]([^/]+)/([^/.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner, repo = match.groups()
                # Remove .git suffix if present
                repo = re.sub(r"\.git$", "", repo)
                namespace = f"{owner}/{repo}".lower()
                return namespace

        return None
