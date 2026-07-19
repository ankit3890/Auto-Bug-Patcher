"""
AutoBug AI — LangGraph Master Graph
======================================
Wires all 17 agents into a directed StateGraph with conditional branching.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.build_agent import build_agent
from app.agents.environment_agent import environment_agent
from app.agents.git_agent import git_agent
from app.agents.issue_agent import issue_agent
from app.agents.localization_agent import localization_agent
from app.agents.patch_agent import patch_agent
from app.agents.planner_agent import planner_agent
from app.agents.pr_agent import pr_agent
from app.agents.report_agent import report_agent
from app.agents.repository_agent import repository_agent
from app.agents.reproduction_agent import reproduction_agent
from app.agents.retrieval_agent import retrieval_agent
from app.agents.reviewer_agent import reviewer_agent
from app.agents.root_cause_agent import root_cause_agent
from app.agents.risk_agent import risk_agent
from app.agents.consistency_checker import consistency_checker
from app.agents.state import AutoBugState
from app.agents.static_analysis_agent import static_analysis_agent
from app.agents.test_generator_agent import test_generator_agent
from app.agents.test_runner_agent import test_runner_agent
from app.agents.test_validator_agent import test_validator_agent

logger = logging.getLogger(__name__)

from app.agents.environment_validator_agent import environment_validator_agent
from app.agents.performance_agent import performance_agent
from app.agents.decision_engine import decision_engine

AGENT_SEQUENCE = [
    ("repository_agent",             repository_agent),
    ("environment_agent",            environment_agent),
    ("environment_validator_agent",  environment_validator_agent),   # Sprint 3
    ("issue_agent",                  issue_agent),
    ("planner_agent",                planner_agent),
    ("retrieval_agent",              retrieval_agent),
    ("build_agent",                  build_agent),
    ("reproduction_agent",           reproduction_agent),
    ("localization_agent",           localization_agent),
    ("root_cause_agent",             root_cause_agent),
    ("patch_agent",                  patch_agent),
    ("static_analysis_agent",        static_analysis_agent),
    ("test_generator_agent",         test_generator_agent),
    ("test_validator_agent",         test_validator_agent),
    ("test_runner_agent",            test_runner_agent),
    ("reviewer_agent",               reviewer_agent),
    ("risk_agent",                   risk_agent),
    ("performance_agent",            performance_agent),             # Sprint 7
    ("decision_engine",              decision_engine),               # Sprint 5
    ("git_agent",                    git_agent),
    ("pr_agent",                     pr_agent),
    ("consistency_checker",          consistency_checker),
    ("report_agent",                 report_agent),
]

# Agents that are "critical" — pipeline aborts if these fail
CRITICAL_AGENTS = {"repository_agent", "issue_agent"}

# The environment gate — if not ready, skip to report immediately
ENV_GATE_AGENT = "environment_validator_agent"


def _should_continue_repository(state: AutoBugState) -> str:
    """Conditional edge after repository_agent."""
    failed = state.get("failed_agent")
    if failed == "repository_agent":
        logger.warning("Repository agent failed — aborting pipeline")
        return "abort"
    return "continue"


def _should_continue_issue(state: AutoBugState) -> str:
    """Conditional edge after issue_agent."""
    failed = state.get("failed_agent")
    if failed == "issue_agent":
        logger.warning("Issue agent failed — aborting pipeline")
        return "abort"
    return "continue"


def _check_environment_ready(state: AutoBugState) -> str:
    """
    Fix 2: Conditional edge after environment_validator_agent.
    If environment is not ready, skip ALL downstream agents and jump
    directly to report_agent — no patch, no LLM, no wasted API calls.
    """
    env = state.get("environment_result") or {}
    ready = env.get("ready", True)  # default True: no env check = proceed
    if not ready:
        reason = env.get("blocking_reason", "unknown")
        logger.warning("[Graph] Environment NOT ready — short-circuiting to report_agent. Reason: %s", reason)
        return "blocked"
    return "ready"


def _check_validation_passed(state: AutoBugState) -> str:
    """
    Pipeline v2: Check if static analysis & tests passed.
    If yes, proceed to Reviewer -> Risk -> Decision.
    If no, proceed directly to Decision (to evaluate Changes Required decision) and skip review/risk.
    """
    test_result = state.get("test_result") or {}
    tests_passed = test_result.get("success") or test_result.get("passed", False)
    
    static = state.get("static_analysis_result") or {}
    static_passed = static.get("passed", True)

    if tests_passed and static_passed:
        logger.info("[Graph] Validation passed — routing to Reviewer/Risk agents")
        return "passed"
    logger.warning("[Graph] Validation failed — routing straight to Decision Engine")
    return "failed"


def _check_merge_decision(state: AutoBugState) -> str:
    """
    Pipeline v2: Decision Gate.
    Check if the programmatic decision allows commit & PR.
    """
    decision_data = state.get("decision") or {}
    allow_commit = decision_data.get("allow_commit", False)
    if allow_commit:
        logger.info("[Graph] Decision allows merge — routing to Git Commit & PR agents")
        return "merge"
    logger.warning("[Graph] Decision does not allow merge — routing straight to Report Agent")
    return "skip"


def _check_test_validity(state: AutoBugState) -> str:
    """Check if the generated test passed import and syntax validation."""
    val = state.get("test_validation_result") or {}
    if val.get("valid", True):
        logger.info("[Graph] Test is valid — proceeding to Test Runner")
        return "valid"
    
    # Loop/Retry up to 2 times
    retries = state.get("test_gen_retries") or 0
    if retries < 2:
        logger.warning("[Graph] Test is invalid. Retrying generation (Attempt %d/2)", retries + 1)
        return "retry"
    
    logger.error("[Graph] Test validation failed and retries exhausted — aborting to Decision Engine")
    return "abort"


def _check_consistency_passed(state: AutoBugState) -> str:
    """
    Pipeline v2: Consistency Gate (with teeth).
    If consistency checker failed, skip PR agent and jump to report.
    """
    failed = state.get("failed_agent")
    decision = state.get("decision") or {}
    if failed == "consistency_checker" or not decision.get("allow_commit", False):
        logger.error("[Graph] Consistency or decision gate blocked commit/PR")
        return "failed"
    return "passed"


import time

def make_metric_wrapper(node_name: str, agent_func):
    async def wrapper(state: AutoBugState) -> AutoBugState:
        logger.info("[MetricsWrapper] Starting agent %s", node_name)
        start_time = time.perf_counter()
        
        result_state = await agent_func(state)
        
        duration = time.perf_counter() - start_time
        logger.info("[MetricsWrapper] Completed agent %s in %.2f seconds", node_name, duration)
        
        metrics = result_state.get("metrics") or {
            "node_durations": {},
            "token_counts": {},
            "costs": {},
            "total_duration_seconds": 0.0,
            "total_cost": 0.0
        }
        
        metrics["node_durations"][node_name] = round(duration, 2)
        metrics["total_duration_seconds"] = round(sum(metrics["node_durations"].values()), 2)
        
        llm_nodes = {
            "issue_agent":           0.00020,
            "planner_agent":         0.00010,
            "root_cause_agent":      0.00030,
            "patch_agent":           0.00040,
            "performance_agent":     0.00030,
            "reproduction_agent":    0.00020,
            "test_generator_agent":  0.00030,
            "reviewer_agent":        0.00040,
            "risk_agent":            0.00020,
        }
        if node_name in llm_nodes:
            cost = llm_nodes[node_name]
            metrics["costs"][node_name] = cost
            metrics["total_cost"] = round(sum(metrics["costs"].values()), 5)
            
        result_state["metrics"] = metrics
        return result_state
    return wrapper


def build_graph() -> Any:
    """Build and compile the AutoBug LangGraph pipeline."""
    graph = StateGraph(AutoBugState)  # type: ignore[bad-specialization]  # Pyrefly FP: TypedDict satisfies StateT at runtime

    # Add all agent nodes
    for name, func in AGENT_SEQUENCE:
        graph.add_node(name, make_metric_wrapper(name, func))

    # Set entry point
    graph.set_entry_point("repository_agent")

    # 1. Repository Gate
    graph.add_conditional_edges(
        "repository_agent",
        _should_continue_repository,
        {"continue": "environment_validator_agent", "abort": "report_agent"},
    )

    # 2. Environment Setup & Validation Gate

    graph.add_conditional_edges(
        "environment_validator_agent",
        _check_environment_ready,
        {"ready": "environment_agent", "blocked": "report_agent"},
    )

    graph.add_edge("environment_agent", "issue_agent")

    # 3. Issue & Planner Gate
    graph.add_conditional_edges(
        "issue_agent",
        _should_continue_issue,
        {"continue": "planner_agent", "abort": "report_agent"},
    )

    # 4. Sequential analysis & generation up to Test Runner
    graph.add_edge("planner_agent", "retrieval_agent")
    graph.add_edge("retrieval_agent", "build_agent")
    graph.add_edge("build_agent", "reproduction_agent")
    graph.add_edge("reproduction_agent", "localization_agent")
    graph.add_edge("localization_agent", "root_cause_agent")
    graph.add_edge("root_cause_agent", "patch_agent")
    graph.add_edge("patch_agent", "static_analysis_agent")
    graph.add_edge("static_analysis_agent", "test_generator_agent")
    graph.add_edge("test_generator_agent", "test_validator_agent")

    # 4b. Test Validation Gate
    graph.add_conditional_edges(
        "test_validator_agent",
        _check_test_validity,
        {"valid": "test_runner_agent", "retry": "test_generator_agent", "abort": "decision_engine"},
    )

    # 5. Validation Passed Gate
    graph.add_conditional_edges(
        "test_runner_agent",
        _check_validation_passed,
        {"passed": "reviewer_agent", "failed": "decision_engine"},
    )

    # 6. Review, Risk & Performance (Only run if validation passed)
    graph.add_edge("reviewer_agent", "risk_agent")
    graph.add_edge("risk_agent", "performance_agent")
    graph.add_edge("performance_agent", "decision_engine")

    # 7. Merge Decision Gate
    graph.add_conditional_edges(
        "decision_engine",
        _check_merge_decision,
        {"merge": "git_agent", "skip": "report_agent"},
    )

    # 8. Git Commit & Consistency Gate
    graph.add_edge("git_agent", "consistency_checker")
    graph.add_conditional_edges(
        "consistency_checker",
        _check_consistency_passed,
        {"passed": "pr_agent", "failed": "report_agent"},
    )

    # 9. PR creation to Report Agent
    graph.add_edge("pr_agent", "report_agent")

    # 10. End point
    graph.add_edge("report_agent", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_compiled_graph():
    """Return (lazily compiled) singleton graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
