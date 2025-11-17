"""
Prompt Versioning and Management System.

Provides:
- Versioned prompt storage
- Checksum-based change detection
- Prompt template rendering
- Prompt history tracking
- A/B testing support
"""

import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PromptVersion


@dataclass
class PromptTemplate:
    """Represents a versioned prompt template."""
    name: str
    version: str
    template: str
    variables: List[str]
    checksum: str
    metadata: Dict[str, Any]
    created_at: datetime

    def render(self, **kwargs) -> str:
        """
        Render the prompt template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If required variables are missing
        """
        # Check all required variables are provided
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # Render template
        return self.template.format(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PromptManager:
    """
    Manages versioned prompts with checksum validation.

    Features:
    - Load prompts from files or database
    - Calculate and verify checksums
    - Track prompt versions
    - Render templates with variables
    - A/B testing support
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt files (default: backend/prompts/)
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)

        # Cache for loaded prompts
        self._cache: Dict[str, PromptTemplate] = {}

    def save_prompt(
        self,
        name: str,
        template: str,
        variables: List[str],
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        persist_to_db: bool = True
    ) -> PromptTemplate:
        """
        Save a new prompt version.

        Args:
            name: Prompt name (e.g., "fix_agent_system")
            template: Prompt template string
            variables: List of variable names used in template
            version: Version string (auto-generated if None)
            metadata: Additional metadata
            persist_to_db: Save to database

        Returns:
            PromptTemplate object
        """
        # Auto-generate version if not provided
        if version is None:
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Calculate checksum
        checksum = self._calculate_checksum(template)

        # Create prompt template
        prompt = PromptTemplate(
            name=name,
            version=version,
            template=template,
            variables=variables,
            checksum=checksum,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )

        # Save to file
        self._save_to_file(prompt)

        # Save to database
        if persist_to_db:
            self._save_to_db(prompt)

        # Update cache
        cache_key = f"{name}:{version}"
        self._cache[cache_key] = prompt

        return prompt

    def load_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        use_cache: bool = True
    ) -> PromptTemplate:
        """
        Load a prompt template.

        Args:
            name: Prompt name
            version: Version string (loads latest if None)
            use_cache: Use cached version if available

        Returns:
            PromptTemplate object

        Raises:
            FileNotFoundError: If prompt not found
        """
        # Check cache first
        if use_cache and version:
            cache_key = f"{name}:{version}"
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Try loading from database first
        try:
            prompt = self._load_from_db(name, version)
            if prompt:
                # Update cache
                cache_key = f"{name}:{prompt.version}"
                self._cache[cache_key] = prompt
                return prompt
        except Exception as e:
            print(f"Failed to load from DB: {e}")

        # Fallback to file system
        prompt = self._load_from_file(name, version)

        # Update cache
        cache_key = f"{name}:{prompt.version}"
        self._cache[cache_key] = prompt

        return prompt

    def get_prompt_history(self, name: str) -> List[PromptTemplate]:
        """
        Get all versions of a prompt.

        Args:
            name: Prompt name

        Returns:
            List of PromptTemplate objects, sorted by version (newest first)
        """
        db = SessionLocal()
        try:
            records = db.query(PromptVersion).filter(
                PromptVersion.name == name
            ).order_by(PromptVersion.created_at.desc()).all()

            return [
                PromptTemplate(
                    name=r.name,
                    version=r.version,
                    template=r.template,
                    variables=json.loads(r.variables),
                    checksum=r.checksum,
                    metadata=json.loads(r.metadata) if r.metadata else {},
                    created_at=r.created_at
                )
                for r in records
            ]
        finally:
            db.close()

    def verify_checksum(self, prompt: PromptTemplate) -> bool:
        """
        Verify prompt checksum.

        Args:
            prompt: PromptTemplate to verify

        Returns:
            True if checksum matches, False otherwise
        """
        calculated = self._calculate_checksum(prompt.template)
        return calculated == prompt.checksum

    def render_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Load and render a prompt template.

        Args:
            name: Prompt name
            version: Version string (uses latest if None)
            **kwargs: Variables to substitute

        Returns:
            Rendered prompt string
        """
        prompt = self.load_prompt(name, version)
        return prompt.render(**kwargs)

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _save_to_file(self, prompt: PromptTemplate) -> None:
        """Save prompt to file system."""
        # Create directory for this prompt name
        prompt_dir = self.prompts_dir / prompt.name
        prompt_dir.mkdir(exist_ok=True)

        # Save as JSON file
        file_path = prompt_dir / f"{prompt.version}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(prompt.to_dict(), f, indent=2, default=str)

    def _save_to_db(self, prompt: PromptTemplate) -> None:
        """Save prompt to database."""
        db = SessionLocal()
        try:
            # Check if version already exists
            existing = db.query(PromptVersion).filter(
                PromptVersion.name == prompt.name,
                PromptVersion.version == prompt.version
            ).first()

            if existing:
                # Update existing
                existing.template = prompt.template
                existing.variables = json.dumps(prompt.variables)
                existing.checksum = prompt.checksum
                existing.metadata = json.dumps(prompt.metadata)
            else:
                # Create new
                record = PromptVersion(
                    name=prompt.name,
                    version=prompt.version,
                    template=prompt.template,
                    variables=json.dumps(prompt.variables),
                    checksum=prompt.checksum,
                    metadata=json.dumps(prompt.metadata),
                    created_at=prompt.created_at
                )
                db.add(record)

            db.commit()
        finally:
            db.close()

    def _load_from_file(self, name: str, version: Optional[str]) -> PromptTemplate:
        """Load prompt from file system."""
        prompt_dir = self.prompts_dir / name

        if not prompt_dir.exists():
            raise FileNotFoundError(f"Prompt '{name}' not found")

        # Get all version files
        version_files = list(prompt_dir.glob("*.json"))

        if not version_files:
            raise FileNotFoundError(f"No versions found for prompt '{name}'")

        # Find specific version or latest
        if version:
            file_path = prompt_dir / f"{version}.json"
            if not file_path.exists():
                raise FileNotFoundError(f"Version '{version}' not found for prompt '{name}'")
        else:
            # Get latest version (sort by filename)
            version_files.sort(reverse=True)
            file_path = version_files[0]

        # Load from file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse datetime
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        return PromptTemplate(**data)

    def _load_from_db(self, name: str, version: Optional[str]) -> Optional[PromptTemplate]:
        """Load prompt from database."""
        db = SessionLocal()
        try:
            query = db.query(PromptVersion).filter(PromptVersion.name == name)

            if version:
                query = query.filter(PromptVersion.version == version)
            else:
                # Get latest version
                query = query.order_by(PromptVersion.created_at.desc())

            record = query.first()

            if not record:
                return None

            return PromptTemplate(
                name=record.name,
                version=record.version,
                template=record.template,
                variables=json.loads(record.variables),
                checksum=record.checksum,
                metadata=json.loads(record.metadata) if record.metadata else {},
                created_at=record.created_at
            )
        finally:
            db.close()


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
