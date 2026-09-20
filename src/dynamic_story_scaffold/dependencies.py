from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from .core.identity import OperationId
from .core.proposals import ActionProposal


class DependencyError(ValueError):
    """Invalid proposal dependency declarations."""


@dataclass(frozen=True, slots=True)
class DependencyComponent:
    operations: tuple[OperationId, ...]
    cyclic: bool


@dataclass(frozen=True, slots=True)
class DependencyPlan:
    components: tuple[DependencyComponent, ...]


def build_dependency_graph(proposals: Iterable[ActionProposal]) -> nx.DiGraph:
    """Build a dependency->dependent graph from normalized proposals."""

    items = tuple(proposals)
    by_id = {proposal.operation_id: proposal for proposal in items}
    if len(by_id) != len(items):
        raise DependencyError("proposal operation ids must be unique")

    graph = nx.DiGraph()
    for operation_id in sorted(by_id):
        graph.add_node(operation_id)

    for proposal in items:
        for dependency in sorted(proposal.dependencies):
            if dependency not in by_id:
                raise DependencyError(
                    f"proposal {proposal.operation_id} depends on unknown operation {dependency}"
                )
            graph.add_edge(dependency, proposal.operation_id)

    return graph


def dependency_plan(proposals: Iterable[ActionProposal]) -> DependencyPlan:
    """Return SCCs in dependency order using NetworkX graph operations."""

    items = tuple(proposals)
    graph = build_dependency_graph(items)
    if not graph:
        return DependencyPlan(())

    condensation = nx.condensation(graph)
    members = {
        node: tuple(sorted(condensation.nodes[node]["members"]))
        for node in condensation.nodes
    }
    ordered_nodes = tuple(
        nx.lexicographical_topological_sort(
            condensation,
            key=lambda node: tuple(str(item) for item in members[node]),
        )
    )

    components: list[DependencyComponent] = []
    for node in ordered_nodes:
        operations = members[node]
        cyclic = len(operations) > 1 or any(
            graph.has_edge(operation, operation) for operation in operations
        )
        components.append(DependencyComponent(operations=operations, cyclic=cyclic))
    return DependencyPlan(tuple(components))
