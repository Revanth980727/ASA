"""
Test Generator - LLM-based Playwright test generation.

Generates E2E tests from bug descriptions for behavioral verification.
"""

import os
import json
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.core.limits import LLMPurpose


class TestGenerator:
    """Generate Playwright E2E tests from bug descriptions."""

    def __init__(self, task_id: Optional[str] = None, user_id: Optional[str] = None, db: Optional[Session] = None):
        """
        Initialize test generator with LLMGateway.

        Args:
            task_id: Optional task ID for usage tracking and budgets
            user_id: Optional user ID for usage tracking
            db: Optional database session (creates one if not provided)
        """
        self.task_id = task_id
        self.user_id = user_id

        # Use LLMGateway for all LLM calls (with model pinning and budgets)
        self.llm_gateway = LLMGateway(task_id=task_id, user_id=user_id, db=db)

    def generate_test(self, bug_description: str, app_context: str = "") -> str:
        """
        Generate a Playwright test script from a bug description.

        Args:
            bug_description: Description of the bug to test
            app_context: Optional context about the application (URLs, components, etc.)

        Returns:
            Playwright test script as a string
        """
        prompt = self._create_test_prompt(bug_description, app_context)

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert QA engineer specializing in Playwright E2E testing. "
                               "You write clear, concise, and reliable Playwright tests that verify specific behaviors."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Use LLMGateway with TEST_GENERATION purpose
            # This automatically uses the correct model and enforces budgets
            response_text = self.llm_gateway.chat_completion(
                purpose=LLMPurpose.TEST_GENERATION,
                messages=messages,
                metadata={"bug_description": bug_description[:100]}
            )

            test_code = response_text.strip()

            # Extract code from markdown if present
            if "```javascript" in test_code or "```typescript" in test_code:
                # Find code block
                lines = test_code.split('\n')
                in_code_block = False
                code_lines = []

                for line in lines:
                    if line.strip().startswith('```'):
                        if in_code_block:
                            break
                        in_code_block = True
                        continue
                    if in_code_block:
                        code_lines.append(line)

                test_code = '\n'.join(code_lines)

            return test_code

        except Exception as e:
            print(f"Error generating test: {e}")
            raise Exception(f"Failed to generate test: {str(e)}")

    def _create_test_prompt(self, bug_description: str, app_context: str) -> str:
        """Create the prompt for test generation."""
        context_section = ""
        if app_context:
            context_section = f"\n**Application Context:**\n{app_context}\n"

        return f"""Generate a Playwright E2E test that verifies the following bug exists.

**Bug Description:**
{bug_description}
{context_section}
**Requirements:**
1. Write a complete, runnable Playwright test in JavaScript/TypeScript
2. Use Playwright's `test` and `expect` syntax
3. The test should FAIL when the bug exists and PASS when it's fixed
4. Include clear test descriptions and assertions
5. Add comments explaining what you're testing
6. Handle common edge cases (page load, timeouts, etc.)
7. Use descriptive locators (prefer data-testid or role-based selectors)
8. Keep the test focused on verifying the specific bug

**Output Format:**
Provide ONLY the Playwright test code, no explanations before or after.

**Example Structure:**
```javascript
const {{ test, expect }} = require('@playwright/test');

test('bug description - specific behavior', async ({{ page }}) => {{
  // Setup
  await page.goto('http://localhost:3000');

  // Action that triggers the bug
  await page.click('[data-testid="some-button"]');

  // Assertion that fails when bug exists
  await expect(page.locator('[data-testid="result"]')).toHaveText('expected value');
}});
```

Generate the test now:"""

    def save_test(self, test_code: str, output_path: str) -> str:
        """
        Save generated test to a file.

        Args:
            test_code: The test code to save
            output_path: Path to save the test file

        Returns:
            Path to the saved test file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(test_code)

        print(f"Test saved to: {output_file}")
        return str(output_file)

    def generate_and_save(
        self,
        bug_description: str,
        output_path: str,
        app_context: str = ""
    ) -> str:
        """
        Generate a test and save it to a file.

        Args:
            bug_description: Description of the bug
            output_path: Where to save the test
            app_context: Optional application context

        Returns:
            Path to the saved test file
        """
        test_code = self.generate_test(bug_description, app_context)
        return self.save_test(test_code, output_path)
