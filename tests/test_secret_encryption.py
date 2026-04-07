"""Tests for secret encryption and creation per GitHub REST API docs.

Covers:
- LibSodium sealed-box encryption (_encrypt_secret)
- Repository secret creation (create_repo_secret) with public-key fetch + encryption
- Organization secret creation (create_org_secret) with public-key fetch + encryption
- File create/update handling (create_file) including the SHA-required update case
"""
import pytest
from base64 import b64encode
from unittest.mock import Mock, patch, call

from github import UnknownObjectException
from nacl import encoding, public

from src.clients.github import GitHubClient
from src.utils.logger import Logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_nacl_keypair():
    """Generate a real NaCl keypair for testing encryption round-trips."""
    private_key = public.PrivateKey.generate()
    public_key = private_key.public_key
    # Base64-encode the public key (same format the GitHub API returns)
    b64_public = public_key.encode(encoder=encoding.Base64Encoder).decode("utf-8")
    return private_key, b64_public


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_logger():
    logger = Mock(spec=Logger)
    logger.debug = Mock()
    logger.error = Mock()
    logger.warn = Mock()
    logger.info = Mock()
    return logger


@pytest.fixture
def github_client(mock_logger):
    with patch('src.clients.github.Github'):
        client = GitHubClient(pat="test-token", logger=mock_logger)
        client.client = Mock()
        # Stub out rate-limit logging so tests don't need to mock it
        client.client.get_rate_limit.side_effect = AttributeError("stubbed")
        return client


# ---------------------------------------------------------------------------
# _encrypt_secret
# ---------------------------------------------------------------------------

class TestEncryptSecret:
    """Tests for GitHubClient._encrypt_secret static method."""

    def test_encrypt_produces_base64_string(self):
        """Encrypted output must be a valid base64-encoded string."""
        _, b64_pub = _generate_nacl_keypair()

        result = GitHubClient._encrypt_secret(b64_pub, "my-secret-value")

        # Should be a non-empty base64 string
        assert isinstance(result, str)
        assert len(result) > 0
        # Should decode without error
        import base64
        base64.b64decode(result)

    def test_encrypt_can_be_decrypted_with_private_key(self):
        """Round-trip: encrypt with public key, decrypt with private key."""
        private_key, b64_pub = _generate_nacl_keypair()
        plaintext = "super-secret-token-123"

        encrypted_b64 = GitHubClient._encrypt_secret(b64_pub, plaintext)

        # Decrypt
        import base64
        encrypted_bytes = base64.b64decode(encrypted_b64)
        unseal_box = public.SealedBox(private_key)
        decrypted = unseal_box.decrypt(encrypted_bytes).decode("utf-8")

        assert decrypted == plaintext

    def test_encrypt_different_inputs_produce_different_outputs(self):
        """Different secret values should produce different ciphertexts."""
        _, b64_pub = _generate_nacl_keypair()

        enc1 = GitHubClient._encrypt_secret(b64_pub, "value-a")
        enc2 = GitHubClient._encrypt_secret(b64_pub, "value-b")

        assert enc1 != enc2

    def test_encrypt_with_empty_string(self):
        """Encrypting an empty string should still work."""
        _, b64_pub = _generate_nacl_keypair()
        result = GitHubClient._encrypt_secret(b64_pub, "")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# create_repo_secret
# ---------------------------------------------------------------------------

class TestCreateRepoSecret:
    """Tests for GitHubClient.create_repo_secret (repo-level secrets)."""

    def test_fetches_public_key_encrypts_and_puts(self, github_client, mock_logger):
        """Verify the 3-step flow: GET public-key, encrypt, PUT secret."""
        private_key, b64_pub = _generate_nacl_keypair()

        mock_repo = Mock()
        mock_requester = Mock()

        # First call: GET public-key; Second call: PUT secret
        mock_requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "key-id-123"}),
            ({}, {}),
        ]
        mock_repo._requester = mock_requester
        github_client.client.get_repo.return_value = mock_repo

        github_client.create_repo_secret("org", "repo", "MY_SECRET", "s3cret")

        # Verify GET public-key call
        first_call = mock_requester.requestJsonAndCheck.call_args_list[0]
        assert first_call[0][0] == "GET"
        assert "/repos/org/repo/actions/secrets/public-key" in first_call[0][1]

        # Verify PUT secret call
        second_call = mock_requester.requestJsonAndCheck.call_args_list[1]
        assert second_call[0][0] == "PUT"
        assert "/repos/org/repo/actions/secrets/MY_SECRET" in second_call[0][1]

        put_body = second_call[1]["input"]
        assert put_body["key_id"] == "key-id-123"
        assert "encrypted_value" in put_body
        assert len(put_body["encrypted_value"]) > 0

    def test_encrypted_value_is_decryptable(self, github_client):
        """Verify the encrypted_value sent to the API is correctly encrypted."""
        private_key, b64_pub = _generate_nacl_keypair()

        mock_repo = Mock()
        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "key-42"}),
            ({}, {}),
        ]
        mock_repo._requester = mock_requester
        github_client.client.get_repo.return_value = mock_repo

        github_client.create_repo_secret("org", "repo", "TOKEN", "my-pat-value")

        put_body = mock_requester.requestJsonAndCheck.call_args_list[1][1]["input"]

        import base64
        encrypted_bytes = base64.b64decode(put_body["encrypted_value"])
        unseal_box = public.SealedBox(private_key)
        decrypted = unseal_box.decrypt(encrypted_bytes).decode("utf-8")

        assert decrypted == "my-pat-value"

    def test_raises_runtime_error_on_failure(self, github_client):
        """Should wrap API errors in RuntimeError."""
        github_client.client.get_repo.side_effect = Exception("network failure")

        with pytest.raises(RuntimeError, match="Failed to create/update secret"):
            github_client.create_repo_secret("org", "repo", "SECRET", "value")

    def test_raises_runtime_error_when_public_key_fetch_fails(self, github_client):
        """Should raise RuntimeError when the public-key endpoint fails."""
        mock_repo = Mock()
        mock_repo._requester.requestJsonAndCheck.side_effect = Exception("403 Forbidden")
        github_client.client.get_repo.return_value = mock_repo

        with pytest.raises(RuntimeError, match="Failed to create/update secret"):
            github_client.create_repo_secret("org", "repo", "SECRET", "value")


# ---------------------------------------------------------------------------
# create_org_secret
# ---------------------------------------------------------------------------

class TestCreateOrgSecret:
    """Tests for GitHubClient.create_org_secret (org-level secrets)."""

    def test_fetches_org_public_key_encrypts_and_puts(self, github_client, mock_logger):
        """Verify the 3-step flow for org secrets."""
        private_key, b64_pub = _generate_nacl_keypair()

        mock_org = Mock()
        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "org-key-99"}),
            ({}, {}),
        ]
        mock_org._requester = mock_requester
        github_client.client.get_organization.return_value = mock_org

        github_client.create_org_secret("my-org", "ORG_TOKEN", "org-secret-val")

        # Verify GET public-key
        first_call = mock_requester.requestJsonAndCheck.call_args_list[0]
        assert first_call[0][0] == "GET"
        assert "/orgs/my-org/actions/secrets/public-key" in first_call[0][1]

        # Verify PUT secret
        second_call = mock_requester.requestJsonAndCheck.call_args_list[1]
        assert second_call[0][0] == "PUT"
        assert "/orgs/my-org/actions/secrets/ORG_TOKEN" in second_call[0][1]

        put_body = second_call[1]["input"]
        assert put_body["key_id"] == "org-key-99"
        assert put_body["visibility"] == "all"
        assert len(put_body["encrypted_value"]) > 0

    def test_passes_visibility_parameter(self, github_client):
        """Verify visibility is forwarded to the API payload."""
        _, b64_pub = _generate_nacl_keypair()

        mock_org = Mock()
        mock_org._requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "k"}),
            ({}, {}),
        ]
        github_client.client.get_organization.return_value = mock_org

        github_client.create_org_secret("org", "S", "v", visibility="selected")

        put_body = mock_org._requester.requestJsonAndCheck.call_args_list[1][1]["input"]
        assert put_body["visibility"] == "selected"

    def test_default_visibility_is_all(self, github_client):
        """When visibility is not specified, it defaults to 'all'."""
        _, b64_pub = _generate_nacl_keypair()

        mock_org = Mock()
        mock_org._requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "k"}),
            ({}, {}),
        ]
        github_client.client.get_organization.return_value = mock_org

        github_client.create_org_secret("org", "SEC", "val")

        put_body = mock_org._requester.requestJsonAndCheck.call_args_list[1][1]["input"]
        assert put_body["visibility"] == "all"

    def test_encrypted_value_is_decryptable(self, github_client):
        """Verify the encrypted_value for org secrets is correctly encrypted."""
        private_key, b64_pub = _generate_nacl_keypair()

        mock_org = Mock()
        mock_org._requester.requestJsonAndCheck.side_effect = [
            ({}, {"key": b64_pub, "key_id": "k"}),
            ({}, {}),
        ]
        github_client.client.get_organization.return_value = mock_org

        github_client.create_org_secret("org", "SEC", "org-plaintext")

        put_body = mock_org._requester.requestJsonAndCheck.call_args_list[1][1]["input"]

        import base64
        encrypted_bytes = base64.b64decode(put_body["encrypted_value"])
        unseal_box = public.SealedBox(private_key)
        decrypted = unseal_box.decrypt(encrypted_bytes).decode("utf-8")

        assert decrypted == "org-plaintext"

    def test_raises_runtime_error_on_failure(self, github_client):
        """Should wrap errors in RuntimeError."""
        github_client.client.get_organization.side_effect = Exception("boom")

        with pytest.raises(RuntimeError, match="Failed to create/update organization secret"):
            github_client.create_org_secret("org", "S", "v")


# ---------------------------------------------------------------------------
# create_file (create vs update)
# ---------------------------------------------------------------------------

class TestCreateFile:
    """Tests for GitHubClient.create_file handling create and update cases."""

    def test_creates_new_file_when_not_exists(self, github_client, mock_logger):
        """When file does not exist, call create_file on the repo."""
        mock_repo = Mock()
        mock_repo.get_contents.side_effect = UnknownObjectException(404, "Not Found", None)
        github_client.client.get_repo.return_value = mock_repo

        github_client.create_file("org", "repo", "feature-branch", ".github/workflows/ci.yml", "content: true")

        mock_repo.create_file.assert_called_once_with(
            path=".github/workflows/ci.yml",
            message="Add .github/workflows/ci.yml",
            content="content: true",
            branch="feature-branch",
        )
        mock_repo.update_file.assert_not_called()

    def test_updates_existing_file_with_sha(self, github_client, mock_logger):
        """When file already exists, call update_file with its SHA (fixes 422 error)."""
        mock_repo = Mock()
        mock_existing = Mock()
        mock_existing.sha = "abc123deadbeef"
        mock_repo.get_contents.return_value = mock_existing
        github_client.client.get_repo.return_value = mock_repo

        github_client.create_file("org", "repo", "migrate-secrets", ".github/workflows/migrate.yml", "new-content")

        mock_repo.update_file.assert_called_once_with(
            path=".github/workflows/migrate.yml",
            message="Update .github/workflows/migrate.yml",
            content="new-content",
            sha="abc123deadbeef",
            branch="migrate-secrets",
        )
        mock_repo.create_file.assert_not_called()

    def test_raises_runtime_error_on_repo_failure(self, github_client):
        """Should raise RuntimeError when repo can't be fetched."""
        github_client.client.get_repo.side_effect = Exception("network")

        with pytest.raises(RuntimeError, match="Failed to create file"):
            github_client.create_file("org", "repo", "branch", "path.yml", "content")

    def test_raises_runtime_error_on_update_failure(self, github_client):
        """Should raise RuntimeError when update_file itself fails."""
        mock_repo = Mock()
        mock_existing = Mock()
        mock_existing.sha = "sha123"
        mock_repo.get_contents.return_value = mock_existing
        mock_repo.update_file.side_effect = Exception("permission denied")
        github_client.client.get_repo.return_value = mock_repo

        with pytest.raises(RuntimeError, match="Failed to create file"):
            github_client.create_file("org", "repo", "branch", "f.yml", "c")
