# Autonomous Bug Fix

## 🤖 ASA Run Report

**Task ID:** `{{TASK_ID}}`
**Sandbox Run ID:** `{{SANDBOX_RUN_ID}}`
**Status:** {{STATUS}}

---

## 📊 Execution Summary

### Timing
- **Total Time:** {{TOTAL_TIME}}
- **P50 Stage Duration:** {{P50_STAGE_DURATION}}
- **P95 Stage Duration:** {{P95_STAGE_DURATION}}

### Token Usage
- **Total Tokens:** {{TOTAL_TOKENS}} / {{TOKEN_BUDGET}}
- **Prompt Tokens:** {{PROMPT_TOKENS}}
- **Completion Tokens:** {{COMPLETION_TOKENS}}
- **Cost:** ${{TOTAL_COST}} / ${{COST_BUDGET}}

### Model Usage
{{MODEL_BREAKDOWN}}

---

## 🐛 Bug Description

{{BUG_DESCRIPTION}}

---

## 🧪 Test Results

### Pre-Fix Tests
```
{{PRE_FIX_TEST_OUTPUT}}
```

**Status:** {{PRE_FIX_STATUS}}

### Post-Fix Tests
```
{{POST_FIX_TEST_OUTPUT}}
```

**Status:** {{POST_FIX_STATUS}}

### E2E Behavioral Tests
{{E2E_TEST_SUMMARY}}

---

## 🔧 Changes Made

{{CHANGES_SUMMARY}}

### Files Modified
{{FILES_MODIFIED_LIST}}

---

## 📈 Stage Breakdown

| Stage | Duration | Tokens Used | Cost | Status |
|-------|----------|-------------|------|--------|
{{STAGE_TABLE_ROWS}}

---

## 🔗 Links

- [Task Details]({{TASK_URL}})
- [Execution Logs]({{LOGS_URL}})
- [Sandbox Container]({{SANDBOX_URL}})

---

## ⚠️ Budget Status

- **Token Budget:** {{TOKEN_USAGE_PERCENTAGE}}% used ({{TOTAL_TOKENS}}/{{TOKEN_BUDGET}})
- **Cost Budget:** {{COST_USAGE_PERCENTAGE}}% used (${{TOTAL_COST}}/${{COST_BUDGET}})
- **Time Budget:** {{TIME_USAGE_PERCENTAGE}}% used ({{TOTAL_TIME}}/{{TIME_BUDGET}})

{{BUDGET_WARNING}}

---

## 🤝 Review Checklist

- [ ] Tests pass after fix
- [ ] No new security vulnerabilities introduced
- [ ] Code follows project style guidelines
- [ ] No hardcoded secrets or sensitive data
- [ ] Changes are minimal and focused on the bug
- [ ] E2E behavioral tests validate the fix

---

## 📝 Notes

{{ADDITIONAL_NOTES}}

---

<details>
<summary>📋 Full Execution Trace</summary>

```
{{FULL_EXECUTION_TRACE}}
```

</details>

---

*Generated automatically by ASA v{{ASA_VERSION}}*
*Review the [execution logs]({{LOGS_URL}}) for full details*
