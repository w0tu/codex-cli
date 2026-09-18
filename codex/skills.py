"""Skills management system for Codex — download, load, and run skills from GitHub."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

GLOBAL_SKILLS_DIR = Path.home() / ".codex" / "skills"
LOCAL_SKILLS_DIR = Path(".codex") / "skills"

# Starter skills definitions to pre-populate
BUILTIN_SKILLS = {
    "code-reviewer": (
        "# Code Reviewer Skill\n\n"
        "When reviewing code or analyzing diffs:\n"
        "1. Check for security vulnerabilities (injection, auth bypass, buffer safety).\n"
        "2. Inspect algorithmic complexity (O(N) vs O(N^2)) and memory efficiency.\n"
        "3. Ensure clean error handling and resource cleanup.\n"
        "4. Verify typing, test coverage, and documentation.\n"
    ),
    "git-workflow": (
        "# Git Workflow Skill\n\n"
        "When performing git operations:\n"
        "1. Follow Conventional Commits format (e.g. `feat:`, `fix:`, `refactor:`).\n"
        "2. Check `git status` and `git diff` before committing.\n"
        "3. Write concise, informative commit messages explaining the 'why'.\n"
    ),
    "test-synthesizer": (
        "# Test Synthesizer Skill\n\n"
        "When creating or updating tests:\n"
        "1. Write isolated, deterministic unit tests.\n"
        "2. Cover edge cases: empty inputs, boundary limits, None/null checks, and failure states.\n"
        "3. Verify all tests pass locally before declaring done.\n"
    ),
}


class SkillsManager:
    """Discovers, installs, and injects skills from GitHub or local directories."""

    def __init__(self):
        GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_builtins()

    def _ensure_builtins(self) -> None:
        """Seed default skills if not already present."""
        for name, content in BUILTIN_SKILLS.items():
            skill_dir = GLOBAL_SKILLS_DIR / name
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                skill_dir.mkdir(parents=True, exist_ok=True)
                skill_file.write_text(content, encoding="utf-8")

    def list_skills(self) -> list[dict[str, str]]:
        """List all installed skills from global and local directories."""
        skills = []
        seen = set()

        for base_dir in [LOCAL_SKILLS_DIR, GLOBAL_SKILLS_DIR]:
            if not base_dir.exists():
                continue
            for item in sorted(base_dir.iterdir()):
                if item.is_dir() and item.name not in seen:
                    skill_file = item / "SKILL.md"
                    readme = item / "README.md"
                    desc = "Custom community skill"
                    if skill_file.exists():
                        lines = skill_file.read_text(encoding="utf-8", errors="replace").splitlines()
                        desc_found = False
                        in_frontmatter = False
                        for i, line in enumerate(lines[:20]):
                            s = line.strip()
                            if s == "---":
                                in_frontmatter = not in_frontmatter
                                continue
                            if in_frontmatter and s.startswith("description:"):
                                val = s.replace("description:", "").strip().lstrip(">").strip()
                                if val:
                                    desc = val[:100]
                                    desc_found = True
                                    break
                                elif i + 1 < len(lines):
                                    desc = lines[i + 1].strip()[:100]
                                    desc_found = True
                                    break
                        if not desc_found:
                            for line in lines[:10]:
                                s = line.strip()
                                if s and not s.startswith("#") and s != "---":
                                    desc = s[:100]
                                    break
                    elif readme.exists():
                        desc = "GitHub skill package"

                    skills.append({
                        "name": item.name,
                        "path": str(item),
                        "description": desc,
                        "source": "workspace" if base_dir == LOCAL_SKILLS_DIR else "global",
                    })
                    seen.add(item.name)

        return skills

    def install_from_github(self, repo: str) -> str:
        """Clone or download a skill from a GitHub repository or URL."""
        repo = repo.strip()
        if not repo.startswith("http") and not repo.startswith("git@"):
            # Format: 'owner/repo'
            url = f"https://github.com/{repo}.git"
            skill_name = repo.split("/")[-1].replace(".git", "")
        else:
            url = repo
            skill_name = repo.rstrip("/").split("/")[-1].replace(".git", "")

        target_dir = GLOBAL_SKILLS_DIR / skill_name

        if target_dir.exists():
            # Update existing skill
            proc = subprocess.run(f"cd {target_dir} && git pull", shell=True, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                return f"Successfully updated skill '{skill_name}' from {repo}."
            return f"Skill '{skill_name}' already exists at {target_dir}."

        # Clone repository
        proc = subprocess.run(f"git clone --depth 1 {url} {target_dir}", shell=True, capture_output=True, text=True, timeout=45)
        if proc.returncode != 0:
            return f"Failed to install skill from GitHub: {proc.stderr.strip()}"

        # Ensure a SKILL.md exists
        skill_file = target_dir / "SKILL.md"
        if not skill_file.exists():
            readme = target_dir / "README.md"
            if readme.exists():
                skill_file.write_text(readme.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                skill_file.write_text(f"# Skill: {skill_name}\n\nInstructions imported from {url}\n", encoding="utf-8")

        return f"Successfully installed skill '{skill_name}' to {target_dir}."

    def remove_skill(self, name: str) -> str:
        """Remove an installed skill."""
        target_dir = GLOBAL_SKILLS_DIR / name.strip()
        if not target_dir.exists():
            return f"Skill '{name}' not found."
        try:
            shutil.rmtree(target_dir)
            return f"Successfully removed skill '{name}'."
        except Exception as e:
            return f"Error removing skill: {e}"

    def get_skills_prompt_context(self) -> str:
        """Gather all installed skill instructions to inject into system prompt."""
        sections = []
        for skill in self.list_skills():
            p = Path(skill["path"]) / "SKILL.md"
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8", errors="replace").strip()
                    if content:
                        sections.append(f"--- SKILL: {skill['name']} ---\n{content}")
                except Exception:
                    pass

        if not sections:
            return ""
        return "\n\nACTIVE COMMUNITY & GITHUB SKILLS:\n" + "\n\n".join(sections) + "\n"
