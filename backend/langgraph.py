"""
A tiny local shim for the `langgraph` API surface the app expects.

This provides minimal `Graph` and `Node` classes so the backend can run
without depending on the external package API surface. It's intentionally
small and only implements the features the app uses:
- Node(name, process)
- Graph(name) with add_node, add_edge, get_node

If you later want the real `langgraph` behavior, remove this file so Python
will import the installed package instead.
"""
from typing import Callable, Dict, List, Tuple, Optional


class Node:
    def __init__(self, name: str, process: Callable[[str, dict], str]):
        self.name = name
        # store the callable that processes input
        self._process = process

    def process(self, input_text: str, state: dict) -> str:
        return self._process(input_text, state)


class Graph:
    def __init__(self, name: str):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Tuple[str, str]] = []

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node

    def add_edge(self, src: Node, dst: Node) -> None:
        self._edges.append((src.name, dst.name))

    def get_node(self, name_or_node) -> Optional[Node]:
        # Accept either the node object or the node's name
        if isinstance(name_or_node, str):
            return self._nodes.get(name_or_node)
        if hasattr(name_or_node, "name"):
            return self._nodes.get(name_or_node.name)
        return None
