#!/usr/bin/env python3
"""
Check git status across all active repositories.

This script checks the git status of REPLAYER and related repositories
to identify:
- Uncommitted changes
- Unpushed commits
- Branches ahead/behind remote
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Color:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class RepoStatus:
    """Check git repository status."""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.exists = path.exists() and (path / ".git").exists()

    def run_git(self, *args) -> Tuple[bool, str]:
        """Run a git command and return success status and output."""
        if not self.exists:
            return False, "Repository not found"
        
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path)] + list(args),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Error: {e}"

    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        success, output = self.run_git("rev-parse", "--abbrev-ref", "HEAD")
        return output if success else None

    def get_remote_branch(self) -> Optional[str]:
        """Get the remote tracking branch."""
        branch = self.get_current_branch()
        if not branch:
            return None
        success, output = self.run_git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
        return output if success else None

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        success, output = self.run_git("status", "--porcelain")
        return success and bool(output)

    def get_unpushed_commits(self) -> int:
        """Get number of unpushed commits."""
        remote_branch = self.get_remote_branch()
        if not remote_branch:
            return 0
        
        success, output = self.run_git("rev-list", "--count", f"{remote_branch}..HEAD")
        if success and output.isdigit():
            return int(output)
        return 0

    def get_unpulled_commits(self) -> int:
        """Get number of unpulled commits from remote."""
        remote_branch = self.get_remote_branch()
        if not remote_branch:
            return 0
        
        # Fetch remote updates first
        self.run_git("fetch", "--quiet")
        
        success, output = self.run_git("rev-list", "--count", f"HEAD..{remote_branch}")
        if success and output.isdigit():
            return int(output)
        return 0

    def get_status_summary(self) -> Dict[str, any]:
        """Get comprehensive status summary."""
        if not self.exists:
            return {
                "exists": False,
                "name": self.name,
                "path": str(self.path),
                "error": "Repository not found"
            }

        branch = self.get_current_branch()
        remote_branch = self.get_remote_branch()
        uncommitted = self.has_uncommitted_changes()
        unpushed = self.get_unpushed_commits()
        unpulled = self.get_unpulled_commits()

        return {
            "exists": True,
            "name": self.name,
            "path": str(self.path),
            "branch": branch,
            "remote_branch": remote_branch,
            "uncommitted_changes": uncommitted,
            "unpushed_commits": unpushed,
            "unpulled_commits": unpulled,
            "needs_attention": uncommitted or unpushed > 0 or unpulled > 0
        }


def print_repo_status(status: Dict[str, any]):
    """Print repository status in a formatted way."""
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*80}{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}Repository: {status['name']}{Color.RESET}")
    print(f"{Color.WHITE}Path: {status['path']}{Color.RESET}")
    
    if not status["exists"]:
        print(f"{Color.RED}✗ {status.get('error', 'Not found')}{Color.RESET}")
        return

    print(f"{Color.WHITE}Branch: {status['branch']}{Color.RESET}")
    
    if status['remote_branch']:
        print(f"{Color.WHITE}Remote: {status['remote_branch']}{Color.RESET}")
    else:
        print(f"{Color.YELLOW}⚠ No remote tracking branch configured{Color.RESET}")

    # Status indicators
    issues = []
    
    if status['uncommitted_changes']:
        issues.append(f"{Color.YELLOW}⚠ Uncommitted changes present{Color.RESET}")
    
    if status['unpushed_commits'] > 0:
        issues.append(f"{Color.YELLOW}⚠ {status['unpushed_commits']} unpushed commit(s){Color.RESET}")
    
    if status['unpulled_commits'] > 0:
        issues.append(f"{Color.MAGENTA}⚠ {status['unpulled_commits']} unpulled commit(s) from remote{Color.RESET}")

    if issues:
        print(f"\n{Color.BOLD}Status:{Color.RESET}")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n{Color.GREEN}✓ Up to date - no pending changes{Color.RESET}")


def main():
    """Check status of all active repositories."""
    print(f"{Color.BOLD}{Color.CYAN}")
    print("=" * 80)
    print("  Multi-Repository Status Checker")
    print("=" * 80)
    print(f"{Color.RESET}")

    # Define repositories to check
    # In CI/CD environment, we only check the current REPLAYER repo
    # In local environment, these paths would be checked
    repos_to_check = [
        Path("/home/runner/work/REPLAYER/REPLAYER"),  # Current repo in CI
    ]
    
    # Add local paths if they exist (for local development)
    local_repos = [
        Path.home() / "Desktop" / "REPLAYER",
        Path.home() / "Desktop" / "rugs-rl-bot",
        Path.home() / "Desktop" / "CV-BOILER-PLATE-FORK",
    ]
    
    for repo_path in local_repos:
        if repo_path.exists() and repo_path not in repos_to_check:
            repos_to_check.append(repo_path)

    # Check each repository
    all_statuses = []
    repos_needing_attention = []
    
    for repo_path in repos_to_check:
        repo = RepoStatus(repo_path)
        status = repo.get_status_summary()
        all_statuses.append(status)
        
        print_repo_status(status)
        
        if status.get("needs_attention"):
            repos_needing_attention.append(status["name"])

    # Summary
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*80}{Color.RESET}")
    print(f"{Color.BOLD}Summary{Color.RESET}")
    print(f"{Color.CYAN}{'='*80}{Color.RESET}")
    
    checked_count = sum(1 for s in all_statuses if s["exists"])
    print(f"Repositories checked: {checked_count}")
    
    if repos_needing_attention:
        print(f"\n{Color.YELLOW}Repositories needing attention:{Color.RESET}")
        for name in repos_needing_attention:
            print(f"  • {name}")
    else:
        print(f"\n{Color.GREEN}✓ All repositories are up to date!{Color.RESET}")

    print(f"{Color.CYAN}{'='*80}{Color.RESET}\n")

    # Exit with error code if any repos need attention
    return 1 if repos_needing_attention else 0


if __name__ == "__main__":
    sys.exit(main())
