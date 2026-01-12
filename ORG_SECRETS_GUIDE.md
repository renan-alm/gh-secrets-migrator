# Organization Secrets Migration Guide

This guide explains how organization-level secrets are migrated and the important requirements for successful migration.

## How Organization Secrets Migration Works

When you use the `--org-to-org` flag, the tool:

1. **Lists** all organization secrets from the source organization
2. **Creates** a GitHub Actions workflow in the source repository
3. **Reads** secret values from the workflow's `secrets` context
4. **Creates** the secrets at the **organization level** in the target organization using `gh secret set --org`

## Critical Requirement: Secret Sharing

**⚠️ IMPORTANT**: Organization secrets **MUST be shared** with the source repository for the migration to work properly.

### Why This Requirement Exists

GitHub Actions workflows can only access organization secrets that have been explicitly shared with the repository running the workflow. This is a **security feature** built into GitHub to prevent unauthorized access to sensitive secrets.

When a secret is not shared:
- The workflow receives an **empty value** for that secret
- The migration will create a secret in the target organization, but with an **empty value**
- No error will be shown - the workflow completes successfully but the secret is empty

### How to Share Organization Secrets

Before running the migration, ensure all secrets are shared with your source repository:

#### Step 1: Navigate to Organization Settings
Go to: `https://github.com/organizations/YOUR_ORG/settings/secrets/actions` (replace `YOUR_ORG` with your organization name)

Or manually:
1. Go to your organization on GitHub
2. Click **Settings**
3. Click **Secrets and variables** → **Actions**

#### Step 2: Configure Each Secret
For each secret you want to migrate:

1. Click on the **secret name**
2. Look for the **Repository access** section
3. Choose one of these options:
   - **All repositories** (recommended for migration - easier to set up)
   - **Selected repositories** - click **Select repositories** and add your source repository

4. Click **Update secret**

#### Step 3: Verify Configuration
- Make sure every secret you want to migrate shows your source repository in the access list
- If using "Selected repositories", double-check the source repo is in the list

## Verifying Secrets Are Properly Migrated

After the migration workflow completes:

### Check Workflow Logs
1. Go to the source repository's **Actions** tab
2. Click on the latest workflow run (e.g., "migrate-org-secrets")
3. Review the logs for each secret:
   - ✓ Success: `✓ Successfully migrated 'SECRET_NAME' to organization 'target-org'`
   - ⚠️ Warning: Look for "secret value is empty" warnings

### Verify in Target Organization
1. Go to the target organization's secrets page
2. Check that all secrets were created
3. **Note**: You cannot view secret values through the UI (by design)

### Test the Secrets
The best way to verify secrets have actual values is to:
1. Create a test workflow in a repository in the target organization
2. Share the org secrets with that test repository
3. Use the secrets in the workflow and verify they work

## Common Issues and Solutions

### Issue: Empty Secrets in Target Organization

**Symptoms:**
- Secrets exist in target org but have empty/blank values
- Applications fail because secrets are missing values

**Cause:**
- Organization secrets were not shared with the source repository during migration

**Solution:**
1. Share the secrets with the source repository (see instructions above)
2. Delete the empty secrets from the target organization
3. Re-run the migration

### Issue: Some Secrets Migrated, Others Are Empty

**Symptoms:**
- Some secrets work fine, others are empty

**Cause:**
- Only some secrets were shared with the source repository

**Solution:**
1. Check which secrets are shared with the source repository in source org settings
2. Share the missing secrets
3. Re-migrate only the missing secrets (you can use a separate migration run)

### Issue: Cannot Verify Secret Values

**Symptom:**
- Cannot see secret values in GitHub UI

**Explanation:**
- This is **normal** and **expected**
- GitHub **never** displays secret values in the UI or API (security feature)
- The only way to verify is to use them in a workflow

**Solution:**
- Create a test workflow that uses the secrets
- Check if the workflow runs successfully

## Best Practices

### 1. Pre-Migration Checklist
Before starting migration:
- [ ] List all organization secrets to migrate
- [ ] Verify each secret is shared with the source repository
- [ ] Test with one or two secrets first
- [ ] Have admin access to both organizations

### 2. Use a Dedicated Migration Repository
Consider using a specific repository for migrations:
- Create a `.github` repository in your organization (common practice)
- Share all org secrets with this repository
- Use it as the source repository for migrations
- Keep it clean and dedicated for administrative tasks

### 3. Temporary "All Repositories" Access
For easier migration:
1. Before migration: Set all secrets to "All repositories" access
2. Run the migration
3. After migration: Restore specific repository access for security

### 4. Document Secret Purposes
Keep documentation about:
- What each secret is used for
- Which services/applications need it
- Which repositories should have access

### 5. Test After Migration
- Don't assume migration worked - always verify
- Test critical secrets in the target organization
- Have a rollback plan if issues are found

## Security Considerations

### Secret Values Are Never Exposed
- GitHub API does not allow reading secret values
- This is a security feature, not a limitation
- Migration works by having GitHub Actions access the values in the workflow context

### Temporary Secrets
During migration, temporary secrets are created in the source repository:
- `SECRETS_MIGRATOR_TARGET_PAT` - Target PAT for creating secrets
- `SECRETS_MIGRATOR_SOURCE_PAT` - Source PAT for cleanup

These are automatically deleted after the workflow completes.

### Audit Trail
- All migrations are recorded in GitHub Actions workflow logs
- You can review which secrets were migrated and when
- Keep these logs for compliance and auditing

## Example: Complete Migration Workflow

Here's a complete example of migrating org secrets from `old-org` to `new-org`:

### 1. Prepare Source Organization
```bash
# 1. Go to https://github.com/organizations/old-org/settings/secrets/actions
# 2. For each secret, set Repository access to "All repositories" (or add .github repo)
# 3. Click "Update secret" for each one
```

### 2. Run Migration
```bash
python main.py \
  --source-org old-org \
  --source-repo .github \
  --target-org new-org \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --org-to-org \
  --verbose
```

### 3. Monitor Progress
```bash
# Check the workflow at:
# https://github.com/old-org/.github/actions/workflows/migrate-org-secrets.yml
```

### 4. Verify in Target
```bash
# 1. Go to https://github.com/organizations/new-org/settings/secrets/actions
# 2. Verify all secrets are present
# 3. Set appropriate repository access for each secret
```

### 5. Test Secrets
```yaml
# Create a test workflow in new-org repository:
name: Test Secrets
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test Secret
        run: |
          if [ -z "${{ secrets.YOUR_SECRET_NAME }}" ]; then
            echo "❌ Secret is empty"
            exit 1
          else
            echo "✓ Secret has a value"
          fi
```

## FAQ

**Q: Can I migrate secrets without sharing them with the repository?**  
A: No. This is a GitHub security requirement. Workflows can only access org secrets that are shared.

**Q: Will the migration fail if secrets aren't shared?**  
A: No, it will succeed but create empty secrets. Always verify after migration.

**Q: Can I retrieve secret values via the API?**  
A: No. GitHub API never exposes secret values for security reasons.

**Q: Do I need admin access to both organizations?**  
A: Yes. You need permission to manage secrets in both organizations.

**Q: Can I migrate selected secrets only?**  
A: Currently, the tool migrates all org secrets. To migrate only specific secrets, consider temporarily removing access to others.

**Q: What happens to the original secrets?**  
A: They remain unchanged in the source organization. The tool only reads and copies them.

## Support

If you encounter issues:
1. Check the troubleshooting section in the main README
2. Review GitHub Actions workflow logs for detailed error messages
3. Verify PAT permissions and secret sharing configuration
4. Create an issue on GitHub with workflow logs and error details

## Summary

Organization secrets migration is **fully functional** and creates secrets at the **organization level** in the target organization. The key requirement is ensuring that organization secrets are **shared with the source repository** before running the migration. This is not a bug or limitation of the tool, but rather how GitHub's security model works to protect sensitive secrets.
