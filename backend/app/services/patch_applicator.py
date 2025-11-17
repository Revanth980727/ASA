"""
Patch Applicator - Safely applies code patches with line-level precision.

Features:
- Line-accurate patch application
- Automatic backups
- Dry-run mode
- Rollback support
"""

import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime

from app.services.patch_schema import CodePatch, PatchSet, PatchType, PatchValidator


class PatchApplicationError(Exception):
    """Raised when patch application fails."""
    pass


class PatchApplicator:
    """Applies code patches with safety checks and backups."""

    def __init__(self, workspace_path: str, create_backups: bool = True):
        """
        Initialize patch applicator.

        Args:
            workspace_path: Path to the workspace
            create_backups: Whether to create backup files before patching
        """
        self.workspace_path = Path(workspace_path)
        self.create_backups = create_backups
        self.backup_dir = self.workspace_path / ".asa_backups"
        self.applied_patches: List[Tuple[CodePatch, str]] = []  # (patch, backup_path)

    def apply_patch_set(
        self,
        patch_set: PatchSet,
        dry_run: bool = False,
        fail_fast: bool = True
    ) -> Dict[str, any]:
        """
        Apply a set of patches.

        Args:
            patch_set: PatchSet to apply
            dry_run: If True, validate but don't apply
            fail_fast: If True, stop on first error

        Returns:
            Dictionary with results:
            {
                "success": bool,
                "applied": int,
                "failed": int,
                "errors": List[str],
                "dry_run": bool
            }
        """
        results = {
            "success": True,
            "applied": 0,
            "failed": 0,
            "errors": [],
            "dry_run": dry_run
        }

        # Validate all patches first
        validation_errors = patch_set.validate(str(self.workspace_path))
        if validation_errors:
            results["success"] = False
            results["errors"].extend(validation_errors)
            if fail_fast:
                return results

        # Apply each patch
        for i, patch in enumerate(patch_set.patches):
            try:
                if dry_run:
                    # Just validate
                    errors = self._validate_patch(patch)
                    if errors:
                        results["failed"] += 1
                        results["errors"].extend([f"Patch {i+1}: {e}" for e in errors])
                        if fail_fast:
                            results["success"] = False
                            break
                    else:
                        results["applied"] += 1
                else:
                    # Actually apply
                    self.apply_patch(patch)
                    results["applied"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Patch {i+1} ({patch.file_path}): {str(e)}")
                results["success"] = False

                if fail_fast:
                    break

        return results

    def apply_patch(self, patch: CodePatch) -> None:
        """
        Apply a single patch.

        Args:
            patch: CodePatch to apply

        Raises:
            PatchApplicationError: If patch cannot be applied
        """
        # Validate patch
        errors = self._validate_patch(patch)
        if errors:
            raise PatchApplicationError(f"Validation failed: {'; '.join(errors)}")

        # Get file path
        file_path = self.workspace_path / patch.file_path
        if not file_path.exists():
            raise PatchApplicationError(f"File does not exist: {patch.file_path}")

        # Create backup
        backup_path = None
        if self.create_backups:
            backup_path = self._create_backup(file_path)

        try:
            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Apply patch based on type
            if patch.patch_type == PatchType.REPLACE:
                new_lines = self._apply_replace(lines, patch)
            elif patch.patch_type == PatchType.INSERT:
                new_lines = self._apply_insert(lines, patch)
            elif patch.patch_type == PatchType.DELETE:
                new_lines = self._apply_delete(lines, patch)
            else:
                raise PatchApplicationError(f"Unknown patch type: {patch.patch_type}")

            # Write patched file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # Track applied patch for potential rollback
            if backup_path:
                self.applied_patches.append((patch, backup_path))

            print(f"✓ Applied {patch.patch_type.value} patch to {patch.file_path} "
                  f"(lines {patch.start_line}-{patch.end_line})")

        except Exception as e:
            # Restore from backup if something went wrong
            if backup_path and backup_path.exists():
                shutil.copy(backup_path, file_path)
                print(f"Restored {file_path} from backup")

            raise PatchApplicationError(f"Failed to apply patch: {str(e)}")

    def _apply_replace(self, lines: List[str], patch: CodePatch) -> List[str]:
        """Apply REPLACE patch: replace lines start_line to end_line with new_code."""
        # Convert to 0-indexed
        start_idx = patch.start_line - 1
        end_idx = patch.end_line  # end_line is inclusive, so this is the line after the last one to replace

        # Ensure new_code ends with newline
        new_code = patch.new_code
        if not new_code.endswith('\n'):
            new_code += '\n'

        # Build new content
        new_lines = (
            lines[:start_idx] +  # Lines before replacement
            [new_code] +         # New code
            lines[end_idx:]      # Lines after replacement
        )

        return new_lines

    def _apply_insert(self, lines: List[str], patch: CodePatch) -> List[str]:
        """Apply INSERT patch: insert new_code before start_line."""
        # Convert to 0-indexed
        insert_idx = patch.start_line - 1

        # Ensure new_code ends with newline
        new_code = patch.new_code
        if not new_code.endswith('\n'):
            new_code += '\n'

        # Build new content
        new_lines = (
            lines[:insert_idx] +  # Lines before insertion
            [new_code] +          # New code
            lines[insert_idx:]    # Lines from insertion point onward
        )

        return new_lines

    def _apply_delete(self, lines: List[str], patch: CodePatch) -> List[str]:
        """Apply DELETE patch: delete lines start_line to end_line."""
        # Convert to 0-indexed
        start_idx = patch.start_line - 1
        end_idx = patch.end_line  # end_line is inclusive

        # Build new content (skip deleted lines)
        new_lines = lines[:start_idx] + lines[end_idx:]

        return new_lines

    def _validate_patch(self, patch: CodePatch) -> List[str]:
        """Validate a patch before application."""
        errors = []

        # Syntax validation
        errors.extend(PatchValidator.validate_syntax(patch))

        # File validation
        errors.extend(PatchValidator.validate_file(patch, str(self.workspace_path)))

        return errors

    def _create_backup(self, file_path: Path) -> str:
        """Create a backup of a file."""
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        relative_path = file_path.relative_to(self.workspace_path)
        backup_name = f"{relative_path.name}.{timestamp}.bak"

        # Create subdirectory structure in backup
        backup_subdir = self.backup_dir / relative_path.parent
        backup_subdir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_subdir / backup_name

        # Copy file
        shutil.copy(file_path, backup_path)
        print(f"Created backup: {backup_path}")

        return str(backup_path)

    def rollback(self) -> int:
        """
        Rollback all applied patches by restoring from backups.

        Returns:
            Number of files restored
        """
        restored = 0

        for patch, backup_path in reversed(self.applied_patches):
            try:
                file_path = self.workspace_path / patch.file_path
                backup = Path(backup_path)

                if backup.exists():
                    shutil.copy(backup, file_path)
                    print(f"Restored {file_path} from {backup_path}")
                    restored += 1
                else:
                    print(f"Warning: Backup not found: {backup_path}")

            except Exception as e:
                print(f"Error restoring {patch.file_path}: {e}")

        self.applied_patches.clear()
        return restored

    def get_patch_preview(self, patch: CodePatch) -> str:
        """
        Get a preview of what the patch will do.

        Returns:
            Human-readable preview string
        """
        try:
            file_path = self.workspace_path / patch.file_path

            if not file_path.exists():
                return f"File does not exist: {patch.file_path}"

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            preview = []
            preview.append(f"File: {patch.file_path}")
            preview.append(f"Operation: {patch.patch_type.value}")
            preview.append(f"Lines: {patch.start_line}-{patch.end_line}")

            if patch.description:
                preview.append(f"Description: {patch.description}")

            preview.append("\nBefore:")
            preview.append("-------")

            # Show affected lines (with context)
            context_before = 2
            context_after = 2
            start_idx = max(0, patch.start_line - 1 - context_before)
            end_idx = min(len(lines), patch.end_line + context_after)

            for i in range(start_idx, end_idx):
                line_num = i + 1
                prefix = ">" if patch.start_line <= line_num <= patch.end_line else " "
                preview.append(f"{prefix} {line_num:4d} | {lines[i].rstrip()}")

            preview.append("\nAfter:")
            preview.append("------")

            # Show new code
            if patch.patch_type in (PatchType.REPLACE, PatchType.INSERT):
                for i, line in enumerate(patch.new_code.split('\n')):
                    preview.append(f"+ {patch.start_line + i:4d} | {line}")

            return "\n".join(preview)

        except Exception as e:
            return f"Error generating preview: {e}"
