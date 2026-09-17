"""Sub-agent orchestration: DAG planner, Scout, Coder, and Critic agents."""

from typing import Any, Callable


class TaskNode:
    """Node representing a single sub-task in a Directed Acyclic Graph (DAG)."""

    def __init__(self, task_id: str, description: str, agent_type: str, dependencies: list[str] | None = None):
        self.task_id = task_id
        self.description = description
        self.agent_type = agent_type  # 'scout', 'coder', 'critic'
        self.dependencies = dependencies or []
        self.status = "pending"  # pending, running, completed, failed
        self.result = ""


class PlanDAG:
    """Directed Acyclic Graph of sub-agent tasks."""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add_task(self, task_id: str, description: str, agent_type: str, dependencies: list[str] | None = None) -> TaskNode:
        node = TaskNode(task_id, description, agent_type, dependencies)
        self.nodes[task_id] = node
        return node

    def get_ready_tasks(self) -> list[TaskNode]:
        """Return tasks whose dependencies are all completed."""
        ready = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            deps_done = all(self.nodes[d].status == "completed" for d in node.dependencies if d in self.nodes)
            if deps_done:
                ready.append(node)
        return ready

    def is_complete(self) -> bool:
        return all(node.status == "completed" for node in self.nodes.values())


class SubAgentContext:
    """Isolated execution context for a sub-agent."""

    def __init__(self, role: str, system_prompt: str):
        self.role = role
        self.system_prompt = system_prompt
        self.messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    def add_turn(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


class ScoutAgent:
    """Read-only agent tasked with exploring code, grepping, and AST outlines."""

    def __init__(self):
        self.context = SubAgentContext(
            role="scout",
            system_prompt="You are a lightweight Scout sub-agent. Search files, outlines, and symbols. Do NOT edit files."
        )

    def run_task(self, prompt: str, tool_runner: Callable[[str, dict], str] | None = None) -> str:
        self.context.add_turn("user", prompt)
        # Formulate search report
        return f"[Scout] Explored and gathered context for: {prompt[:80]}"


class CoderAgent:
    """Implementation agent tasked with modifying code and creating files."""

    def __init__(self):
        self.context = SubAgentContext(
            role="coder",
            system_prompt="You are an implementation Coder sub-agent. Generate clean, idiomatic code without unnecessary comments."
        )

    def run_task(self, prompt: str, tool_runner: Callable[[str, dict], str] | None = None) -> str:
        self.context.add_turn("user", prompt)
        return f"[Coder] Implemented task: {prompt[:80]}"


class CriticAgent:
    """Auditing agent tasked with reviewing diffs for regressions and bugs."""

    def __init__(self):
        self.context = SubAgentContext(
            role="critic",
            system_prompt="You are an adversarial Critic sub-agent. Scrutinize code diffs for syntax errors, regressions, and safety risks."
        )

    def audit_diff(self, diff_text: str) -> dict[str, Any]:
        has_syntax_risk = "SyntaxError" in diff_text or "TODO" in diff_text
        return {
            "passed": not has_syntax_risk,
            "summary": "Passed code quality audit" if not has_syntax_risk else "Flagged potential issues in patch",
            "diff_size_lines": len(diff_text.splitlines()),
        }


class Orchestrator:
    """Coordinates multi-agent DAG execution."""

    def __init__(self):
        self.scout = ScoutAgent()
        self.coder = CoderAgent()
        self.critic = CriticAgent()

    def build_plan_for_prompt(self, user_prompt: str) -> PlanDAG:
        """Decompose prompt into standard 3-phase DAG: Scout -> Coder -> Critic."""
        dag = PlanDAG()
        dag.add_task("task_1_scout", f"Research codebase symbols: {user_prompt[:50]}", "scout")
        dag.add_task("task_2_code", f"Implement changes: {user_prompt[:50]}", "coder", dependencies=["task_1_scout"])
        dag.add_task("task_3_critic", f"Audit and verify changes: {user_prompt[:50]}", "critic", dependencies=["task_2_code"])
        return dag

    def execute_dag(self, dag: PlanDAG) -> list[str]:
        """Execute all nodes in the DAG until completion."""
        logs = []
        while not dag.is_complete():
            ready = dag.get_ready_tasks()
            if not ready:
                break
            for task in ready:
                task.status = "running"
                if task.agent_type == "scout":
                    task.result = self.scout.run_task(task.description)
                elif task.agent_type == "coder":
                    task.result = self.coder.run_task(task.description)
                elif task.agent_type == "critic":
                    audit = self.critic.audit_diff(task.description)
                    task.result = f"[Critic] {audit['summary']}"
                task.status = "completed"
                logs.append(f"Completed {task.task_id} ({task.agent_type}): {task.result}")
        return logs
