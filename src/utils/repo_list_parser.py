"""Utility functions for parsing repository list files."""
from typing import List, Optional


def parse_repo_list_file(file_path: Optional[str]) -> Optional[List[str]]:
    """Parse a repository list file.
    
    The file should contain one repository name per line.
    Empty lines and lines starting with # are ignored (comments).
    
    Args:
        file_path: Path to the repository list file (optional)
        
    Returns:
        List of repository names, or None if file_path is None
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        RuntimeError: If the file is empty or has no valid entries
    """
    if file_path is None:
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"Repository list file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error reading repository list file: {e}")
    
    # Parse lines, ignoring comments and empty lines
    repo_names = []
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Validate repository name (basic validation)
        if '/' in line:
            raise RuntimeError(
                f"Invalid repository name on line {line_num}: '{line}'\n"
                f"Repository names should not contain '/' (only the name, not org/repo format)"
            )
        
        if ' ' in line:
            raise RuntimeError(
                f"Invalid repository name on line {line_num}: '{line}'\n"
                f"Repository names should not contain spaces"
            )
        
        repo_names.append(line)
    
    if not repo_names:
        raise RuntimeError(
            f"No valid repository names found in {file_path}\n"
            f"The file should contain one repository name per line"
        )
    
    # Remove duplicates while preserving order
    seen = set()
    unique_repos = []
    for repo in repo_names:
        if repo not in seen:
            seen.add(repo)
            unique_repos.append(repo)
    
    return unique_repos
