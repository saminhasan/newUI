# ────────original states/transitions, untouched ───────────────────────────────
states = [
    "IDLE",
    "DISCONNECTED",
    "CONNECTED",
    "STOPPED",
    "PLAYING",
    "PAUSED",
    "ERROR",
]

transitions = [
    {"transition": "portSelect", "source": "IDLE", "dest": "DISCONNECTED"},
    {"transition": "portSelect", "source": "DISCONNECTED", "dest": "DISCONNECTED"},
    {"transition": "connect", "source": "DISCONNECTED", "dest": "CONNECTED"},
    {"transition": "disconnect", "source": "CONNECTED", "dest": "DISCONNECTED"},
    {"transition": "enable", "source": "CONNECTED", "dest": "STOPPED"},
    {"transition": "upload", "source": "STOPPED", "dest": "PAUSED"},
    {"transition": "pause", "source": "PLAYING", "dest": "PAUSED"},
    {"transition": "play", "source": "PAUSED", "dest": "PLAYING"},
    {"transition": "stop", "source": "PLAYING", "dest": "STOPPED"},
    {"transition": "stop", "source": "PAUSED", "dest": "STOPPED"},
    {"transition": "reset", "source": states[1:], "dest": "DISCONNECTED"},
    {"transition": "disable", "source": states[2:], "dest": "ERROR"},
    {"transition": "quit", "source": states, "dest": "IDLE"},
]
# ─────────────────────────────────────────────────────────────────────────
import networkx as nx


class FSM:
    def __init__(self, states=states, transitions=transitions, initial=None):
        # build the graph
        self._G = nx.MultiDiGraph()
        self._G.add_nodes_from(states)
        # flatten each transition’s source(s) into edges
        edges = [
            (src, t["dest"], t["transition"])
            for t in transitions
            for src in (t["source"] if isinstance(t["source"], list) else [t["source"]])
        ]
        for u, v, trig in edges:
            self._G.add_edge(u, v, transition=trig)
        # set initial state
        self.state = initial if initial is not None else states[0]

    def trigger(self, name):
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

    def available_transitions(self):
        """List all valid transitions from the current state."""
        return list({data["transition"] for _, _, _, data in self._G.out_edges(self.state, keys=True, data=True)})

    def __repr__(self):
        return f"<Current State={self.state!r}>"


def test():
    import random

    fsm = FSM(states, transitions, initial="IDLE")
    States = set()
    while True:
        previous_state = fsm.state
        options = fsm.available_transitions()
        random_event = random.choice(options)
        fsm.trigger(random_event)
        print(f"{previous_state} -> {random_event} -> {fsm.state}")
        States.add(fsm.state)
        if States == set(states):
            print("All states reached!")
            print("----------------------TEST PASSED----------------------")
            break


if __name__ == "__main__":
    test()
