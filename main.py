import threading, time, tkinter as tk

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Root-is-self example")

        self.label = tk.Label(self, text="Idle")
        self.label.pack(padx=10, pady=10)

        btn = tk.Button(self, text="Start", command=self.start_work)
        btn.pack(padx=10, pady=5)

        # Bind the custom event on self
        self.bind("<<WorkerDone>>", self.on_done)

    def start_work(self):
        self.label.config(text="Working…")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        time.sleep(3)
        # Here, self is the root Tk widget
        self.event_generate("<<WorkerDone>>", when="tail")

    def on_done(self, event):
        self.label.config(text="Done")

if __name__ == "__main__":
    App().mainloop()

# from dataclasses import dataclass
# from typing import List, Union, Optional, Tuple

# # ────────original states/transitions, untouched ───────────────────────────────
# states = [
#     "IDLE",
#     "DISCONNECTED",
#     "CONNECTED",
#     "STOPPED",
#     "READY",
#     "PLAYING",
#     "PAUSED",
#     "ERROR",
# ]

# transitions = [
#     {"trigger": "portSelect",  "source": "IDLE",          "dest": "DISCONNECTED"},
#     {"trigger": "portSelect",  "source": "DISCONNECTED",  "dest": "DISCONNECTED"},
#     {"trigger": "connect",     "source": "DISCONNECTED",  "dest": "CONNECTED"},
#     {"trigger": "disconnect",  "source": "CONNECTED",     "dest": "DISCONNECTED"},
#     {"trigger": "enable",      "source": "CONNECTED",     "dest": "STOPPED"},
#     {"trigger": "upload",      "source": "STOPPED",       "dest": "READY"},
#     {"trigger": "play",        "source": "READY",         "dest": "PLAYING"},
#     {"trigger": "pause",       "source": "PLAYING",       "dest": "PAUSED"},
#     {"trigger": "play",        "source": "PAUSED",        "dest": "PLAYING"},
#     {"trigger": "stop",        "source": "PLAYING",       "dest": "STOPPED"},
#     {"trigger": "stop",        "source": "PAUSED",        "dest": "STOPPED"},
#     {"trigger": "reset",     "source": states,         "dest": "DISCONNECTED"},
#     {"trigger": "disable",     "source": states[2:],      "dest": "ERROR"},
#     {"trigger": "quit",        "source": states,          "dest": "IDLE"},
# ]
# # ─────────────────────────────────────────────────────────────────────────

# @dataclass(frozen=True)
# class Transition:
#     trigger: str
#     source: Union[str, List[str]]
#     dest: str

# class StateMachine:
#     states: List[str] = states
#     transitions: List[Transition]  
#     current_state: str

#     def __init__(
#         self,
#         states: List[str] = states,
#         transitions: List[Union[Transition, dict]]  = transitions,
#         initial_state: Optional[str] = None
#     ) -> None:
#         # allow passing either Transition instances or raw dicts
#         self.states = states
#         self.transitions = [
#             t if isinstance(t, Transition) else Transition(**t)
#             for t in transitions
#         ]
#         self.current_state = initial_state or states[0]

#     def get_valid_triggers(self) -> List[Tuple[str, str]]:
#         """All (trigger, destination) pairs valid from the current state."""
#         return [
#             (t.trigger, t.dest)
#             for t in self.transitions
#             if self.current_state in (t.source if isinstance(t.source, list) else [t.source])
#         ]

#     def trigger(self, trigger_name: str) -> bool:
#         """
#         Fire a trigger by name. 
#         Returns True and updates state if valid; otherwise returns False.
#         """
#         match = next(
#             (
#                 t for t in self.transitions
#                 if t.trigger == trigger_name
#                 and self.current_state in (t.source if isinstance(t.source, list) else [t.source])
#             ),
#             None
#         )
#         if not match:
#             return False

#         self.current_state = match.dest
#         return True
    

# if __name__ == "__main__":
#     import random
#     import networkx as nx
#     import matplotlib.pyplot as plt
#     fsm = StateMachine(states, transitions, initial_state="IDLE")
#     G = nx.DiGraph()
#     G.add_nodes_from(fsm.states)
#     for t in fsm.transitions:
#         srcs = t.source if isinstance(t.source, list) else [t.source]
#         for src in srcs:
#             G.add_edge(src, t.dest, label=t.trigger)
#     edge_labels = {(u, v): d["label"] for u, v, d in G.edges(data=True)}
#     pos = nx.spring_layout(G, k=1.0, iterations=1000, seed=42)

#     try:
#         plt.ion()
#         fig, ax = plt.subplots(figsize=(8, 6))
#         fig.canvas.mpl_connect("close_event", lambda event: quit())
#         while True:
#             ax.clear()
#             ax.set_title(f"State Machine — Current: {fsm.current_state}", fontsize=14)
#             ax.set_axis_off()

#             # draw nodes (active state in red)
#             nx.draw_networkx_nodes(G, pos,node_color=[("red" if n == fsm.current_state else "lightblue") for n in G.nodes()],
#                                     edgecolors="k", linewidths=1.0, node_size=2500,ax=ax, node_shape='s')
#             nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)
#             nx.draw_networkx_edges(G, pos, arrowstyle="-|>", arrowsize=20, connectionstyle="arc3,rad=0.1", edge_color="gray", width=1.2, ax=ax)
#             nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5, rotate=False, ax=ax)

#             options = fsm.get_valid_triggers()
#             print(f"STATE: {fsm.current_state} | Options: {[t for t, _ in options]}")
#             if options:
#                 trigger, dest = random.choice(options)
#                 fsm.trigger(trigger)
#                 print(f"   {trigger} -> {dest}")
#             else:
#                 print("No valid transitions available. Stopping visualization.")
#                 break
#             plt.pause(0.1)  # allow the figure to update

#     except KeyboardInterrupt:
#         print("\nVisualization stopped by user.")
#     finally:
#         plt.ioff()
#         plt.show()
