# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import itertools


class CycleError(Exception):
    pass


class DependencyDoesNotExistError(Exception):
    pass


class TaskGraph(object):
    def __init__(self, taskconfigs):
        self._nodes = {}
        for task in taskconfigs:
            self._nodes[task.name] = task

        self._refresh()

        missing = self._missing_tasks()
        if missing:
            raise DependencyDoesNotExistError("The following are depended on "
                                              "but do not exist: "
                                              + ", ".join(missing))

    def _refresh(self):
        """Refreshes the pointers between graph nodes"""
        for node in self._nodes.values():
            for sd in node.stated_dependencies:
                if sd in self._nodes and sd not in node.dependencies:
                    node.dependencies.add(self._nodes[sd])

    def _missing_tasks(self):
        """List of missing tasks (ie. unfulfilled dependencies)"""
        lst = [node._missing_dependencies() for node in self._nodes.values()]
        return set(itertools.chain.from_iterable(lst))

    def sequential_ordering(self):
        """Topological sort, ignores parallelisation possibilities
        Algorithm is Kahn (1962),
        http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
        """

        to_ret = []
        graph = copy.deepcopy(self._nodes.values())
        no_inc_edges = self._start_nodes(graph)

        while no_inc_edges:
            n = no_inc_edges.pop()
            to_ret.append(n.name)
            for m in self._nodes_with_edges_from(graph, n):
                self._remove_edge(graph, n, m)
                if not set(self._nodes_with_edges_to(graph, m)) - set([n]):
                    no_inc_edges.add(m)

        if self._has_edges(graph):
            # we've got a cycle in our graph!
            raise CycleError("Graph of task dependencies has cycles")

        to_ret.reverse()  # because we point TO our dependents
        return to_ret

    @classmethod
    def _start_nodes(cls, graph):
        """Returns the nodes in the graph with no dependencies"""
        return {n for n in graph
                if not cls._nodes_with_edges_to(graph, n)}

    @staticmethod
    def _has_edges(graph):
        """Returns True if there are any edges remaining in the graph,
        False otherwise"""

        for node in graph:
            if node.dependencies:
                return True
        return False

    @staticmethod
    def _nodes_with_edges_to(graph, n):
        """Returns the list of task nodes which depend on n.

        More generally this means it returns the list of nodes which have
        directed edges pointed to n.
        """
        return {m for m in graph if m is not n and n in m.dependencies}

    @staticmethod
    def _nodes_with_edges_from(graph, n):
        """Returns the list of task nodes which n depends on

        More generally this means it returns the list of nodes which n points
        to
        """
        return copy.copy(n.dependencies)

    @staticmethod
    def _remove_edge(graph, n, m):
        """Remove the edge from n to m"""
        if m not in n.dependencies:
            return

        n.dependencies.remove(m)

    def __str__(self):
        return ", ".join(map(str, self._nodes.values()))
