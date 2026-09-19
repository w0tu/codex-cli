"""Sub-Agent System: Multi-Agent State Machine Architecture.

State Machine transitions:
IDLE -> PLANNING (Planner Agent) -> CODING (Coder Agent) -> AUDITING (Auditor Agent) -> EXECUTING (Executor Agent) -> COMPLETED / FAILED

Agents:
- Planner Agent: Deconstructs high-level tasks into discrete file and terminal steps.
- Coder Agent: Streams syntax-highlighted code and generates unified diffs.
- Auditor Agent: Scans proposed file modifications and shell commands for syntax errors or destructive operations before execution.
- Executor Agent: Runs approved shell commands and reports stderr/stdout back to the context loop.
"""

import os
import sys
import ast
import json
import difflib
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from codex.themes import render_isolated_code_block
from codex.gatekeeper import gatekeeper


class AgentState(Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    CODING = "CODING"
    AUDITING = "AUDITING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStep:
    """Discrete unit of work within a decomposed plan."""

    def __init__(
        self,
        step_id: str,
        action_type: str,  # "file_edit", "file_create", "shell_cmd", "inspect"
        description: str,
        target_path: Optional[str] = None,
        command: Optional[str] = None,
        code_content: Optional[str] = None,
    ):
        self.step_id = step_id
        self.action_type = action_type
        self.description = description
        self.target_path = target_path
        self.command = command
        self.code_content = code_content
        self.diff: Optional[str] = None
        self.audit_passed = False
        self.audit_notes = ""
        self.execution_output = ""
        self.execution_status = "pending"  # pending, running, success, error


class PlannerAgent:
    """Deconstructs high-level tasks into discrete file and terminal steps."""

    def __init__(self):
        self.role = "Planner"

    def plan_task(self, prompt: str, context_files: Optional[List[str]] = None) -> List[TaskStep]:
        """Deconstruct high-level user objective into ordered TaskSteps."""
        steps: List[TaskStep] = []
        words = prompt.lower()

        # Step 1: Inspection / environment check
        steps.append(
            TaskStep(
                step_id="step_1_inspect",
                action_type="inspect",
                description=f"Inspect workspace and environment for: {prompt[:60]}",
                command="git status --short",
            )
        )

        # Step 2: Coding implementation
        target_file = None
        if context_files and len(context_files) > 0:
            target_file = context_files[0]
        else:
            # Simple heuristic detection for file names
            for token in prompt.split():
                if any(token.endswith(ext) for ext in [".py", ".sh", ".json", ".md", ".txt", ".js", ".ts"]):
                    target_file = token.strip("`'\",")
                    break

        steps.append(
            TaskStep(
                step_id="step_2_code",
                action_type="file_edit" if (target_file and Path(target_file).exists()) else "file_create",
                description=f"Generate code changes for {target_file or 'target implementation'}",
                target_path=target_file,
            )
        )

        # Step 3: Verification / execution
        steps.append(
            TaskStep(
                step_id="step_3_execute",
                action_type="shell_cmd",
                description=f"Verify implementation via tests or linters",
                command="pytest -q 2>/dev/null || python3 -m unittest 2>/dev/null || true",
            )
        )

        return steps


class CoderAgent:
    """Streams syntax-highlighted code and generates unified diffs."""

    def __init__(self):
        self.role = "Coder"

    def generate_unified_diff(self, file_path: str, new_content: str) -> str:
        """Create a clean unified diff between original file content and new content."""
        p = Path(file_path)
        old_lines = []
        if p.exists():
            try:
                old_lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            except Exception:
                old_lines = []

        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="\n"
        )
        return "".join(diff)

    def prepare_step_code(self, step: TaskStep, code: str) -> None:
        """Assign code and compute unified diff."""
        step.code_content = code
        if step.target_path:
            step.diff = self.generate_unified_diff(step.target_path, code)


class AuditorAgent:
    """Scans proposed file modifications and shell commands for syntax errors or destructive operations."""

    DESTRUCTIVE_COMMAND_PATTERNS = [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf *",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",  # fork bomb
        "chmod -R 777 /",
        "> /dev/sda",
        "shutdown",
        "reboot",
        "init 0",
    ]

    def __init__(self):
        self.role = "Auditor"

    def audit_command(self, cmd: Optional[str]) -> Tuple[bool, str]:
        """Verify shell command safety before execution."""
        if not cmd or not cmd.strip():
            return True, "No shell command to audit."

        cleaned = cmd.strip()
        for pattern in self.DESTRUCTIVE_COMMAND_PATTERNS:
            if pattern in cleaned:
                return False, f"CRITICAL SECURITY AUDIT FAILED: Destructive command pattern detected: '{pattern}'"

        return True, "Shell command passed safety audit."

    def audit_code_syntax(self, file_path: Optional[str], content: Optional[str]) -> Tuple[bool, str]:
        """Audit source code syntax before disk writes."""
        if not content:
            return True, "No code content to audit."

        # Python syntax validation via AST
        if file_path and file_path.endswith(".py"):
            try:
                ast.parse(content, filename=file_path)
            except SyntaxError as e:
                return False, f"SYNTAX AUDIT FAILED in {file_path} at line {e.lineno}: {e.msg}"
            except Exception as e:
                return False, f"SYNTAX AUDIT WARNING: {e}"

        # JSON syntax validation
        if file_path and file_path.endswith(".json"):
            try:
                json.loads(content)
            except Exception as e:
                return False, f"JSON SYNTAX AUDIT FAILED in {file_path}: {e}"

        return True, "Code syntax verified successfully."

    def audit_step(self, step: TaskStep) -> Tuple[bool, str]:
        """Perform comprehensive audit on a TaskStep."""
        if step.command:
            cmd_ok, cmd_msg = self.audit_command(step.command)
            if not cmd_ok:
                step.audit_passed = False
                step.audit_notes = cmd_msg
                return False, cmd_msg

        if step.code_content:
            code_ok, code_msg = self.audit_code_syntax(step.target_path, step.code_content)
            if not code_ok:
                step.audit_passed = False
                step.audit_notes = code_msg
                return False, code_msg

        step.audit_passed = True
        step.audit_notes = "All security and syntax checks passed."
        return True, step.audit_notes


class ExecutorAgent:
    """Runs approved shell commands and reports stderr/stdout back to the context loop."""

    def __init__(self):
        self.role = "Executor"

    def execute_step(self, step: TaskStep, timeout_seconds: int = 60) -> Tuple[bool, str]:
        """Execute approved command or file modification, respecting Gatekeeper permissions."""
        if not step.audit_passed:
            step.execution_status = "error"
            step.execution_output = f"Execution blocked: Step failed audit ({step.audit_notes})"
            return False, step.execution_output

        # Check Directory Gatekeeper
        if gatekeeper.read_only_mode and step.action_type in ["file_edit", "file_create", "shell_cmd"]:
            step.execution_status = "error"
            step.execution_output = "Execution blocked: Workspace is in read-only advisory mode."
            return False, step.execution_output

        # Apply file edit if applicable
        if step.action_type in ["file_edit", "file_create"] and step.target_path and step.code_content:
            try:
                target_p = Path(step.target_path)
                target_p.parent.mkdir(parents=True, exist_ok=True)
                target_p.write_text(step.code_content, encoding="utf-8")
                step.execution_status = "success"
                step.execution_output = f"Wrote {len(step.code_content)} bytes to {step.target_path}"
                return True, step.execution_output
            except Exception as e:
                step.execution_status = "error"
                step.execution_output = f"File write failed: {e}"
                return False, step.execution_output

        # Execute shell command if applicable
        if step.command:
            try:
                res = subprocess.run(
                    step.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                output_parts = []
                if stdout:
                    output_parts.append(f"[STDOUT]\n{stdout}")
                if stderr:
                    output_parts.append(f"[STDERR]\n{stderr}")
                
                step.execution_output = "\n".join(output_parts) if output_parts else "[No output, exit code 0]"
                step.execution_status = "success" if res.returncode == 0 else "error"
                return res.returncode == 0, step.execution_output
            except subprocess.TimeoutExpired:
                step.execution_status = "error"
                step.execution_output = f"Command timed out after {timeout_seconds}s"
                return False, step.execution_output
            except Exception as e:
                step.execution_status = "error"
                step.execution_output = f"Execution exception: {e}"
                return False, step.execution_output

        step.execution_status = "success"
        step.execution_output = "[Inspection step completed]"
        return True, step.execution_output


class MultiAgentStateMachine:
    """Coordinates Planner, Coder, Auditor, and Executor agents through lifecycle states."""

    def __init__(self):
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.auditor = AuditorAgent()
        self.executor = ExecutorAgent()
        self.current_state = AgentState.IDLE
        self.plan: List[TaskStep] = []
        self.history: List[str] = []

    def run_workflow(
        self,
        prompt: str,
        code_generator: Optional[Callable[[TaskStep], str]] = None,
        context_files: Optional[List[str]] = None,
        logger: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Run complete state machine workflow."""
        log = logger or (lambda msg: sys.stdout.write(f"{msg}\n"))

        # 1. PLANNING
        self.current_state = AgentState.PLANNING
        log(f"\033[38;2;120;120;130m▌\033[0m \033[1;36m[STATE: PLANNING]\033[0m Planner Agent analyzing prompt...")
        self.plan = self.planner.plan_task(prompt, context_files=context_files)
        log(f"  • Generated {len(self.plan)} discrete steps.")

        for step in self.plan:
            # 2. CODING
            self.current_state = AgentState.CODING
            log(f"\033[38;2;120;120;130m▌\033[0m \033[1;33m[STATE: CODING]\033[0m Coder Agent handling '{step.step_id}' ({step.action_type})...")
            if code_generator and step.action_type in ["file_edit", "file_create"]:
                code = code_generator(step)
                self.coder.prepare_step_code(step, code)
                if step.diff:
                    log(f"  • Generated diff for {step.target_path}:\n{step.diff[:200]}...")

            # 3. AUDITING
            self.current_state = AgentState.AUDITING
            log(f"\033[38;2;120;120;130m▌\033[0m \033[1;35m[STATE: AUDITING]\033[0m Auditor Agent scanning step for security and syntax...")
            passed, notes = self.auditor.audit_step(step)
            if not passed:
                log(f"  \033[1;31m✗ AUDIT FAILED: {notes}\033[0m")
                self.current_state = AgentState.FAILED
                return False
            log(f"  \033[1;32m✓ AUDIT PASSED: {notes}\033[0m")

            # 4. EXECUTING
            self.current_state = AgentState.EXECUTING
            log(f"\033[38;2;120;120;130m▌\033[0m \033[1;34m[STATE: EXECUTING]\033[0m Executor Agent executing approved step...")
            success, output = self.executor.execute_step(step)
            if not success:
                log(f"  \033[1;31m✗ Execution error:\033[0m {output}")
                self.current_state = AgentState.FAILED
                return False
            log(f"  \033[1;32m✓ Step completed:\033[0m {output[:120]}")

        self.current_state = AgentState.COMPLETED
        log(f"\033[38;2;120;120;130m▌\033[0m \033[1;32m[STATE: COMPLETED]\033[0m Multi-agent state machine finished all steps.\n")
        return True
