"""Tests for repository list parser functionality."""
import pytest
import tempfile
import os
from src.utils.repo_list_parser import parse_repo_list_file


class TestRepoListParser:
    """Test suite for repository list parser."""

    def test_parse_repo_list_none(self):
        """Test parsing when file path is None."""
        result = parse_repo_list_file(None)
        assert result is None

    def test_parse_repo_list_simple(self):
        """Test parsing a simple list of repositories."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("repo1\n")
            f.write("repo2\n")
            f.write("repo3\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == ['repo1', 'repo2', 'repo3']
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_with_comments(self):
        """Test parsing with comment lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("# This is a comment\n")
            f.write("repo1\n")
            f.write("# Another comment\n")
            f.write("repo2\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == ['repo1', 'repo2']
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_with_empty_lines(self):
        """Test parsing with empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("repo1\n")
            f.write("\n")
            f.write("repo2\n")
            f.write("  \n")  # Line with spaces
            f.write("repo3\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == ['repo1', 'repo2', 'repo3']
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("  repo1  \n")
            f.write("\trepo2\t\n")
            f.write(" repo3\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == ['repo1', 'repo2', 'repo3']
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_remove_duplicates(self):
        """Test that duplicates are removed while preserving order."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("repo1\n")
            f.write("repo2\n")
            f.write("repo1\n")  # Duplicate
            f.write("repo3\n")
            f.write("repo2\n")  # Duplicate
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == ['repo1', 'repo2', 'repo3']
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_file_not_found(self):
        """Test error handling when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_repo_list_file('/non/existent/file.txt')

    def test_parse_repo_list_empty_file(self):
        """Test error handling for empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("")
            f.flush()
            temp_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match="No valid repository names found"):
                parse_repo_list_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_only_comments(self):
        """Test error handling when file contains only comments."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("# Comment 1\n")
            f.write("# Comment 2\n")
            f.flush()
            temp_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match="No valid repository names found"):
                parse_repo_list_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_invalid_with_slash(self):
        """Test error handling for repository names with slash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("repo1\n")
            f.write("org/repo2\n")  # Invalid: contains slash
            f.flush()
            temp_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match=r"Invalid repository name"):
                parse_repo_list_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_invalid_with_space(self):
        """Test error handling for repository names with spaces."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("repo1\n")
            f.write("repo name\n")  # Invalid: contains space
            f.flush()
            temp_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match=r"Invalid repository name"):
                parse_repo_list_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_repo_list_complex_scenario(self):
        """Test a complex realistic scenario."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("# Production repositories\n")
            f.write("api-service\n")
            f.write("web-frontend\n")
            f.write("\n")
            f.write("# Staging repositories\n")
            f.write("api-service-staging\n")
            f.write("\n")
            f.write("  web-frontend-staging  \n")
            f.write("# End of list\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = parse_repo_list_file(temp_path)
            assert result == [
                'api-service',
                'web-frontend',
                'api-service-staging',
                'web-frontend-staging'
            ]
        finally:
            os.unlink(temp_path)
