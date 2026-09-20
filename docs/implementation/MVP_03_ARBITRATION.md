# MVP-03 dependency and arbitration contracts

MVP-03 adds finite dependency and conflict scheduling to the round coordinator.

ActionProposal carries a stable OperationId, typed StateRef read and write metadata, exclusive claims, dependency operation IDs, causal parent, and causal depth. StateRef uses EntityRef or ComponentRef plus an optional structured SubresourceKey, avoiding ambiguous dotted strings at subsystem boundaries.

Writes have three classes: aggregatable, exclusive, and rule-governed. Aggregatable writes remain eligible together. Exclusive writes are arbitrated. Rule-governed writes name the policy that will govern later combination or stacking behavior.

The dependency module uses NetworkX to build the directed dependency graph, find strongly connected components, and topologically order the condensation graph. Cyclic components are data for arbitration rather than errors or waits.

Stochastic arbitration uses stable OperationId ordering and semantic streams keyed by arbitration, round identity, and conflict identity. Audit data records the conflict rule, candidates, terminal outcomes, effective weights and modifiers, semantic stream key, sampled value, and chosen result.

The coordinator normalizes plain ActionIntent values into ActionProposal records, also accepts already-normalized ActionProposal values, arbitrates them before resolution, and resolves only proposals with accepted terminal status. Proposal, causal-depth, and resolution budgets remain enforced by the coordinator.
