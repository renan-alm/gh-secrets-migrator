// Package github provides GitHub API client functionality.
package github

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"

	"github.com/google/go-github/v57/github"
	"golang.org/x/crypto/nacl/box"
	"golang.org/x/oauth2"

	"github.com/renan-alm/gh-secrets-migrator/internal/logger"
)

// Client provides methods to interact with the GitHub API.
type Client struct {
	client *github.Client
	log    *logger.Logger
}

// New creates a new GitHub API client.
func New(ctx context.Context, pat string, log *logger.Logger) *Client {
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: pat},
	)
	tc := oauth2.NewClient(ctx, ts)
	ghClient := github.NewClient(tc)

	return &Client{
		client: ghClient,
		log:    log,
	}
}

// GetDefaultBranch retrieves the default branch of a repository.
func (c *Client) GetDefaultBranch(ctx context.Context, org, repo string) (string, error) {
	r, _, err := c.client.Repositories.Get(ctx, org, repo)
	if err != nil {
		return "", fmt.Errorf("failed to get repository: %w", err)
	}
	return r.GetDefaultBranch(), nil
}

// GetCommitSha retrieves the commit SHA for a given branch.
func (c *Client) GetCommitSha(ctx context.Context, org, repo, branch string) (string, error) {
	ref, _, err := c.client.Git.GetRef(ctx, org, repo, fmt.Sprintf("heads/%s", branch))
	if err != nil {
		return "", fmt.Errorf("failed to get ref: %w", err)
	}
	return ref.Object.GetSHA(), nil
}

// CreateBranch creates a new branch in the repository.
func (c *Client) CreateBranch(ctx context.Context, org, repo, branchName, sha string) error {
	_, _, err := c.client.Git.CreateRef(ctx, org, repo, &github.Reference{
		Ref:    github.String(fmt.Sprintf("refs/heads/%s", branchName)),
		Object: &github.GitObject{SHA: github.String(sha)},
	})
	if err != nil {
		return fmt.Errorf("failed to create branch: %w", err)
	}
	return nil
}

// GetRepoPublicKey retrieves the public key for a repository.
func (c *Client) GetRepoPublicKey(ctx context.Context, org, repo string) ([]byte, string, error) {
	key, _, err := c.client.Actions.GetRepoPublicKey(ctx, org, repo)
	if err != nil {
		return nil, "", fmt.Errorf("failed to get public key: %w", err)
	}

	publicKeyBytes, err := base64.StdEncoding.DecodeString(key.GetKey())
	if err != nil {
		return nil, "", fmt.Errorf("failed to decode public key: %w", err)
	}

	return publicKeyBytes, key.GetKeyID(), nil
}

// CreateRepoSecret creates a secret in the repository using the public key.
func (c *Client) CreateRepoSecret(ctx context.Context, org, repo string, publicKey []byte, publicKeyID, secretName, secretValue string) error {
	// Convert public key to array for encryption
	var publicKeyArray [32]byte
	copy(publicKeyArray[:], publicKey)

	// Encrypt the secret using libsodium's sealed box
	encryptedSecret, err := box.SealAnonymous(nil, []byte(secretValue), &publicKeyArray, nil)
	if err != nil {
		return fmt.Errorf("failed to encrypt secret: %w", err)
	}

	encryptedValue := base64.StdEncoding.EncodeToString(encryptedSecret)

	secret := &github.EncryptedSecret{
		Name:           secretName,
		EncryptedValue: encryptedValue,
		KeyID:          publicKeyID,
	}

	_, err = c.client.Actions.CreateOrUpdateRepoSecret(ctx, org, repo, secret)
	if err != nil {
		return fmt.Errorf("failed to create secret: %w", err)
	}
	return nil
}

// ListRepoSecrets retrieves all secrets in the repository.
func (c *Client) ListRepoSecrets(ctx context.Context, org, repo string) ([]string, error) {
	opts := &github.ListOptions{PerPage: 100}
	var secretNames []string

	for {
		secrets, resp, err := c.client.Actions.ListRepoSecrets(ctx, org, repo, opts)
		if err != nil {
			return nil, fmt.Errorf("failed to list secrets: %w", err)
		}

		for _, secret := range secrets.Secrets {
			secretNames = append(secretNames, secret.Name)
		}

		if resp.NextPage == 0 {
			break
		}
		opts.Page = resp.NextPage
	}

	return secretNames, nil
}

// CreateBlob creates a blob and returns its SHA.
func (c *Client) CreateBlob(ctx context.Context, org, repo, contents string) (string, error) {
	blob, _, err := c.client.Git.CreateBlob(ctx, org, repo, &github.Blob{
		Content:  github.String(base64.StdEncoding.EncodeToString([]byte(contents))),
		Encoding: github.String("base64"),
	})
	if err != nil {
		return "", fmt.Errorf("failed to create blob: %w", err)
	}
	return blob.GetSHA(), nil
}

// GetTreeSha retrieves the tree SHA for a commit.
func (c *Client) GetTreeSha(ctx context.Context, org, repo, commitSha string) (string, error) {
	commit, _, err := c.client.Git.GetCommit(ctx, org, repo, commitSha)
	if err != nil {
		return "", fmt.Errorf("failed to get commit: %w", err)
	}
	return commit.Tree.GetSHA(), nil
}

// CreateTree creates a tree with the given entries.
func (c *Client) CreateTree(ctx context.Context, org, repo, baseTreeSha string, entries []*github.TreeEntry) (string, error) {
	tree, _, err := c.client.Git.CreateTree(ctx, org, repo, baseTreeSha, entries)
	if err != nil {
		return "", fmt.Errorf("failed to create tree: %w", err)
	}
	return tree.GetSHA(), nil
}

// CreateCommit creates a commit with the given tree and parent.
func (c *Client) CreateCommit(ctx context.Context, org, repo, message, treeSha, parentSha string) (string, error) {
	commit, _, err := c.client.Git.CreateCommit(ctx, org, repo, &github.Commit{
		Message: github.String(message),
		Tree:    &github.Tree{SHA: github.String(treeSha)},
		Parents: []*github.Commit{
			{SHA: github.String(parentSha)},
		},
	}, &github.CreateCommitOptions{})
	if err != nil {
		return "", fmt.Errorf("failed to create commit: %w", err)
	}
	return commit.GetSHA(), nil
}

// UpdateRef updates a reference to point to a new commit.
func (c *Client) UpdateRef(ctx context.Context, org, repo, ref, sha string) error {
	_, _, err := c.client.Git.UpdateRef(ctx, org, repo, &github.Reference{
		Ref:    github.String(ref),
		Object: &github.GitObject{SHA: github.String(sha)},
	}, false)
	if err != nil {
		return fmt.Errorf("failed to update ref: %w", err)
	}
	return nil
}

// CreateFile creates or updates a file in the repository.
func (c *Client) CreateFile(ctx context.Context, org, repo, branch, path, contents string) error {
	opts := &github.RepositoryContentFileOptions{
		Message: github.String(fmt.Sprintf("Add %s", path)),
		Content: []byte(contents),
		Branch:  github.String(branch),
	}

	_, _, err := c.client.Repositories.CreateFile(ctx, org, repo, path, opts)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	return nil
}

// DeleteRef deletes a reference.
func (c *Client) DeleteRef(ctx context.Context, org, repo, ref string) error {
	_, err := c.client.Git.DeleteRef(ctx, org, repo, ref)
	if err != nil {
		return fmt.Errorf("failed to delete ref: %w", err)
	}
	return nil
}

// DeleteSecret deletes a secret from the repository.
func (c *Client) DeleteSecret(ctx context.Context, org, repo, secretName string) error {
	_, err := c.client.Actions.DeleteRepoSecret(ctx, org, repo, secretName)
	if err != nil {
		return fmt.Errorf("failed to delete secret: %w", err)
	}
	return nil
}

// MarshalSecretsJSON marshals secrets to JSON for the workflow.
func MarshalSecretsJSON(secrets map[string]string) (string, error) {
	data, err := json.Marshal(secrets)
	if err != nil {
		return "", fmt.Errorf("failed to marshal secrets: %w", err)
	}
	return string(data), nil
}
