"""
Contract System - JSON Schema Validation for LLM I/O.

Provides:
- JSON schema definitions for LLM inputs/outputs
- Validation of requests and responses
- Contract versioning
- Schema registry
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = Exception


@dataclass
class Contract:
    """Represents a contract (JSON schema) for validation."""
    name: str
    version: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: str
    created_at: datetime

    def validate_input(self, data: Any) -> tuple[bool, Optional[str]]:
        """
        Validate input data against schema.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not HAS_JSONSCHEMA:
            return True, "jsonschema not installed, skipping validation"

        try:
            validate(instance=data, schema=self.input_schema)
            return True, None
        except ValidationError as e:
            return False, str(e)

    def validate_output(self, data: Any) -> tuple[bool, Optional[str]]:
        """
        Validate output data against schema.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not HAS_JSONSCHEMA:
            return True, "jsonschema not installed, skipping validation"

        try:
            validate(instance=data, schema=self.output_schema)
            return True, None
        except ValidationError as e:
            return False, str(e)


class ContractRegistry:
    """
    Registry for managing contracts.

    Provides:
    - Loading contracts from files
    - Contract versioning
    - Schema validation
    """

    def __init__(self, contracts_dir: Optional[str] = None):
        """
        Initialize contract registry.

        Args:
            contracts_dir: Directory containing contract files
        """
        if contracts_dir is None:
            contracts_dir = Path(__file__).parent.parent.parent / "contracts"

        self.contracts_dir = Path(contracts_dir)
        self.contracts_dir.mkdir(exist_ok=True)

        # Cache for loaded contracts
        self._cache: Dict[str, Contract] = {}

        # Load all contracts
        self._load_all_contracts()

    def register_contract(
        self,
        name: str,
        version: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        description: str = ""
    ) -> Contract:
        """
        Register a new contract.

        Args:
            name: Contract name
            version: Version string
            input_schema: JSON schema for input validation
            output_schema: JSON schema for output validation
            description: Contract description

        Returns:
            Contract object
        """
        contract = Contract(
            name=name,
            version=version,
            input_schema=input_schema,
            output_schema=output_schema,
            description=description,
            created_at=datetime.utcnow()
        )

        # Save to file
        self._save_contract(contract)

        # Update cache
        cache_key = f"{name}:{version}"
        self._cache[cache_key] = contract

        return contract

    def get_contract(self, name: str, version: Optional[str] = None) -> Contract:
        """
        Get a contract by name and version.

        Args:
            name: Contract name
            version: Version string (uses latest if None)

        Returns:
            Contract object

        Raises:
            KeyError: If contract not found
        """
        if version:
            cache_key = f"{name}:{version}"
            if cache_key in self._cache:
                return self._cache[cache_key]
        else:
            # Find latest version
            versions = [
                k for k in self._cache.keys() if k.startswith(f"{name}:")
            ]
            if versions:
                versions.sort(reverse=True)
                return self._cache[versions[0]]

        raise KeyError(f"Contract '{name}' (version: {version}) not found")

    def validate_input(
        self,
        contract_name: str,
        data: Any,
        version: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate input data against contract.

        Args:
            contract_name: Contract name
            data: Data to validate
            version: Contract version (uses latest if None)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            contract = self.get_contract(contract_name, version)
            return contract.validate_input(data)
        except KeyError as e:
            return False, str(e)

    def validate_output(
        self,
        contract_name: str,
        data: Any,
        version: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate output data against contract.

        Args:
            contract_name: Contract name
            data: Data to validate
            version: Contract version (uses latest if None)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            contract = self.get_contract(contract_name, version)
            return contract.validate_output(data)
        except KeyError as e:
            return False, str(e)

    def list_contracts(self) -> List[str]:
        """List all registered contracts."""
        return list(set(k.split(':')[0] for k in self._cache.keys()))

    def _save_contract(self, contract: Contract) -> None:
        """Save contract to file."""
        contract_file = self.contracts_dir / f"{contract.name}_{contract.version}.json"

        data = {
            "name": contract.name,
            "version": contract.version,
            "input_schema": contract.input_schema,
            "output_schema": contract.output_schema,
            "description": contract.description,
            "created_at": contract.created_at.isoformat()
        }

        with open(contract_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _load_all_contracts(self) -> None:
        """Load all contracts from directory."""
        if not self.contracts_dir.exists():
            return

        for contract_file in self.contracts_dir.glob("*.json"):
            try:
                with open(contract_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse datetime
                if isinstance(data['created_at'], str):
                    data['created_at'] = datetime.fromisoformat(data['created_at'])

                contract = Contract(**data)

                cache_key = f"{contract.name}:{contract.version}"
                self._cache[cache_key] = contract

            except Exception as e:
                print(f"Failed to load contract from {contract_file}: {e}")


# Define standard contracts for the ASA system

# Fix Agent Patch Contract
FIX_AGENT_PATCH_SCHEMA = {
    "name": "fix_agent_patch",
    "version": "1.0",
    "description": "Contract for FixAgent patch generation",
    "input_schema": {
        "type": "object",
        "properties": {
            "bug_description": {"type": "string", "minLength": 10},
            "failing_output": {"type": "string"},
            "code_context": {"type": "string"}
        },
        "required": ["bug_description", "failing_output", "code_context"]
    },
    "output_schema": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_snippet": {"type": "string"},
                "new_snippet": {"type": "string"}
            },
            "required": ["file_path", "old_snippet", "new_snippet"]
        },
        "minItems": 1
    }
}

# Code Agent Patch Contract
CODE_AGENT_PATCH_SCHEMA = {
    "name": "code_agent_patch",
    "version": "1.0",
    "description": "Contract for CodeAgent structured patch generation",
    "input_schema": {
        "type": "object",
        "properties": {
            "bug_description": {"type": "string", "minLength": 10},
            "test_failure_log": {"type": "string"},
            "code_context": {"type": "string"}
        },
        "required": ["bug_description", "test_failure_log", "code_context"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "patches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "patch_type": {"type": "string", "enum": ["replace", "insert", "delete"]},
                        "start_line": {"type": "integer", "minimum": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                        "new_code": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["file_path", "patch_type", "start_line", "end_line", "description"]
                }
            },
            "bug_description": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"}
        },
        "required": ["patches", "bug_description", "confidence", "rationale"]
    }
}

# Test Generator Contract
TEST_GENERATOR_SCHEMA = {
    "name": "test_generator",
    "version": "1.0",
    "description": "Contract for TestGenerator E2E test generation",
    "input_schema": {
        "type": "object",
        "properties": {
            "bug_description": {"type": "string", "minLength": 10},
            "app_context": {"type": "string"}
        },
        "required": ["bug_description"]
    },
    "output_schema": {
        "type": "string",
        "minLength": 50  # Test code should be at least 50 characters
    }
}

# LLM Chat Completion Contract
LLM_CHAT_COMPLETION_SCHEMA = {
    "name": "llm_chat_completion",
    "version": "1.0",
    "description": "Contract for LLM chat completion requests",
    "input_schema": {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                        "content": {"type": "string", "minLength": 1}
                    },
                    "required": ["role", "content"]
                },
                "minItems": 1
            },
            "model": {"type": "string", "minLength": 1},
            "temperature": {"type": "number", "minimum": 0, "maximum": 2},
            "max_tokens": {"type": "integer", "minimum": 1}
        },
        "required": ["messages", "model"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "choices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["content"]
                        }
                    },
                    "required": ["message"]
                },
                "minItems": 1
            },
            "usage": {
                "type": "object",
                "properties": {
                    "prompt_tokens": {"type": "integer", "minimum": 0},
                    "completion_tokens": {"type": "integer", "minimum": 0},
                    "total_tokens": {"type": "integer", "minimum": 0}
                }
            }
        },
        "required": ["choices"]
    }
}


# Global contract registry instance
_contract_registry: Optional[ContractRegistry] = None


def get_contract_registry() -> ContractRegistry:
    """Get global contract registry instance."""
    global _contract_registry
    if _contract_registry is None:
        _contract_registry = ContractRegistry()

        # Register standard contracts
        _contract_registry.register_contract(**FIX_AGENT_PATCH_SCHEMA)
        _contract_registry.register_contract(**CODE_AGENT_PATCH_SCHEMA)
        _contract_registry.register_contract(**TEST_GENERATOR_SCHEMA)
        _contract_registry.register_contract(**LLM_CHAT_COMPLETION_SCHEMA)

    return _contract_registry
