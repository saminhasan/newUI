# ────────original states/transitions, untouched ───────────────────────────────
states: list[str] = [
    "IDLE",
    "DISCONNECTED",
    "CONNECTED",
    "STOPPED",
    "PLAYING",
    "PAUSED",
    "ERROR",
]

transitions: list[dict[str, str | list[str]]] = [
    {"transition": "PORTSELECT", "source": "IDLE", "dest": "DISCONNECTED"},
    {"transition": "PORTSELECT", "source": "DISCONNECTED", "dest": "DISCONNECTED"},
    {"transition": "CONNECT", "source": "DISCONNECTED", "dest": "CONNECTED"},
    {"transition": "DISCONNECT", "source": "CONNECTED", "dest": "DISCONNECTED"},
    {"transition": "ENABLE", "source": "CONNECTED", "dest": "STOPPED"},
    {"transition": "UPLOAD", "source": "STOPPED", "dest": "READY"},
    {"transition": "PLAY", "source": "READY", "dest": "PLAYING"},
    {"transition": "PAUSE", "source": "PLAYING", "dest": "PAUSED"},
    {"transition": "PLAY", "source": "PAUSED", "dest": "PLAYING"},
    {"transition": "STOP", "source": "PLAYING", "dest": "STOPPED"},
    {"transition": "STOP", "source": "PAUSED", "dest": "STOPPED"},
    {"transition": "RESET", "source": states[1:], "dest": "DISCONNECTED"},
    {"transition": "DISABLE", "source": states[2:], "dest": "ERROR"},
    {"transition": "QUIT", "source": states, "dest": "IDLE"},
]
# ─────────────────────────────────────────────────────────────────────────
import networkx as nx


class FSM:
    def __init__(
        self, states: list[str] = states, transitions: list[dict[str, str | list[str]]] = transitions, initial: str = ""
    ) -> None:
        # build the graph
        self._G: nx.MultiDiGraph = nx.MultiDiGraph()
        self._G.add_nodes_from(states)
        # flatten each transition’s source(s) into edges
        edges: list[tuple[str, str, str]] = [
            (src, t["dest"], t["transition"])
            for t in transitions
            for src in (t["source"] if isinstance(t["source"], list) else [t["source"]])
        ]
        for u, v, trig in edges:
            self._G.add_edge(u, v, transition=trig)
        # set initial state
        self.state: str = initial if initial else states[0]

    def trigger(self, name: str) -> str:
        """
        Fire a transition by trigger name.
        On success: updates self.state and returns the new state.
        On failure: raises ValueError.
        """
        # search outgoing edges for this transition
        for _, dest, key, data in self._G.out_edges(self.state, keys=True, data=True):
            if data["transition"] == name:
                self.state = dest
                return dest
        raise ValueError(f"No transition '{name}' from state '{self.state}'")

    def available_transitions(self) -> list[str]:
        """List all valid transitions from the current state."""
        return list({data["transition"] for _, _, _, data in self._G.out_edges(self.state, keys=True, data=True)})

    def __repr__(self) -> str:
        return f"<Current State={self.state!r}>"


def test() -> None:
    import random

    fsm: FSM = FSM(states, transitions, initial="IDLE")
    States: set[str] = set()
    while True:
        previous_state: str = fsm.state
        options: list[str] = fsm.available_transitions()
        random_event: str = random.choice(options)
        fsm.trigger(random_event)
        print(f"{previous_state} -> {random_event} -> {fsm.state}")
        States.add(fsm.state)
        if States == set(states):
            print("All states reached!")
            print("----------------------TEST PASSED----------------------")
            break


if __name__ == "__main__":
    test()
