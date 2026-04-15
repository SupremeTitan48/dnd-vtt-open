from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from content.tutorial_loader import TutorialScenario
from desktop.app.session_controller import SessionController


class TabletopApp:
    def __init__(self, controller: SessionController, tutorial: TutorialScenario) -> None:
        if not controller.engine:
            raise ValueError("SessionController must have an active engine")

        self.controller = controller
        self.engine = controller.engine
        self.tutorial = tutorial

        self.cell_size = 24
        self.selected_token = "hero"

        self.root = tk.Tk()
        self.root.title("DND VTT - Tutorial Session")
        self.root.geometry("1150x700")

        self._build_layout()
        self._bind_events()
        self.refresh_view()

    def _build_layout(self) -> None:
        wrapper = ttk.Frame(self.root, padding=10)
        wrapper.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(wrapper)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.Frame(wrapper, width=340)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(
            left,
            width=self.engine.map_state.width * self.cell_size,
            height=self.engine.map_state.height * self.cell_size,
            bg="#1f1f1f",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        control_row = ttk.Frame(left)
        control_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(control_row, text="Up", command=lambda: self._move_selected(0, -1)).pack(side=tk.LEFT)
        ttk.Button(control_row, text="Down", command=lambda: self._move_selected(0, 1)).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_row, text="Left", command=lambda: self._move_selected(-1, 0)).pack(side=tk.LEFT)
        ttk.Button(control_row, text="Right", command=lambda: self._move_selected(1, 0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_row, text="Next Turn", command=self._next_turn).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(control_row, text="Save Session", command=self._save_session).pack(side=tk.LEFT, padx=(12, 0))

        # Right-side info panels
        session_box = ttk.LabelFrame(right, text="Session", padding=8)
        session_box.pack(fill=tk.X, pady=(0, 8))
        self.session_label = ttk.Label(session_box, text="")
        self.session_label.pack(anchor="w")

        token_box = ttk.LabelFrame(right, text="Selected Token", padding=8)
        token_box.pack(fill=tk.X, pady=(0, 8))
        self.token_var = tk.StringVar(value=self.selected_token)
        token_picker = ttk.Combobox(token_box, textvariable=self.token_var, state="readonly")
        token_picker.bind("<<ComboboxSelected>>", self._on_token_changed)
        token_picker.pack(fill=tk.X)
        self.token_picker = token_picker

        combat_box = ttk.LabelFrame(right, text="Combat", padding=8)
        combat_box.pack(fill=tk.X, pady=(0, 8))
        self.round_label = ttk.Label(combat_box, text="")
        self.round_label.pack(anchor="w")
        self.active_actor_label = ttk.Label(combat_box, text="")
        self.active_actor_label.pack(anchor="w")
        self.initiative_list = tk.Listbox(combat_box, height=5)
        self.initiative_list.pack(fill=tk.X, pady=(6, 0))

        actor_box = ttk.LabelFrame(right, text="Actor States", padding=8)
        actor_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.actor_state_text = tk.Text(actor_box, height=10, wrap=tk.WORD)
        self.actor_state_text.pack(fill=tk.BOTH, expand=True)

        tutorial_box = ttk.LabelFrame(right, text="DM Tutorial Steps", padding=8)
        tutorial_box.pack(fill=tk.BOTH, expand=True)
        self.tutorial_list = tk.Listbox(tutorial_box, height=8)
        self.tutorial_list.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self) -> None:
        self.root.bind("<Up>", lambda _e: self._move_selected(0, -1))
        self.root.bind("<Down>", lambda _e: self._move_selected(0, 1))
        self.root.bind("<Left>", lambda _e: self._move_selected(-1, 0))
        self.root.bind("<Right>", lambda _e: self._move_selected(1, 0))

    def _on_token_changed(self, _event: object) -> None:
        self.selected_token = self.token_var.get()
        self.refresh_view()

    def _save_session(self) -> None:
        save_path = self.controller.save_active_session()
        self.session_label.config(text=f"Saved: {save_path}")

    def _next_turn(self) -> None:
        if self.engine.combat_tracker.initiative_order:
            self.engine.advance_turn()
        self.refresh_view()

    def _move_selected(self, dx: int, dy: int) -> None:
        token_id = self.selected_token
        current_x, current_y = self.engine.map_state.token_positions.get(token_id, (0, 0))
        next_x = max(0, min(self.engine.map_state.width - 1, current_x + dx))
        next_y = max(0, min(self.engine.map_state.height - 1, current_y + dy))
        self.engine.move_token(token_id, next_x, next_y)
        self.refresh_view()

    def _draw_grid(self) -> None:
        self.canvas.delete("grid")
        width_px = self.engine.map_state.width * self.cell_size
        height_px = self.engine.map_state.height * self.cell_size

        for x in range(0, width_px + 1, self.cell_size):
            self.canvas.create_line(x, 0, x, height_px, fill="#343434", tags="grid")
        for y in range(0, height_px + 1, self.cell_size):
            self.canvas.create_line(0, y, width_px, y, fill="#343434", tags="grid")

    def _draw_tokens(self) -> None:
        self.canvas.delete("token")
        for token_id, (x, y) in self.engine.map_state.token_positions.items():
            x1 = x * self.cell_size + 3
            y1 = y * self.cell_size + 3
            x2 = (x + 1) * self.cell_size - 3
            y2 = (y + 1) * self.cell_size - 3
            is_selected = token_id == self.selected_token
            fill = "#5dc1ff" if is_selected else "#82e082"
            self.canvas.create_oval(x1, y1, x2, y2, fill=fill, outline="#101010", width=2, tags="token")
            self.canvas.create_text(
                x * self.cell_size + self.cell_size / 2,
                y * self.cell_size + self.cell_size / 2,
                text=token_id[:1].upper(),
                fill="#111111",
                font=("Helvetica", 11, "bold"),
                tags="token",
            )

    def refresh_view(self) -> None:
        self._draw_grid()
        self._draw_tokens()

        session_name = self.controller.active_session_name or "Unknown"
        self.session_label.config(text=f"Session: {session_name}")

        token_ids = sorted(self.engine.map_state.token_positions.keys())
        if not token_ids:
            token_ids = [self.selected_token]
        if self.selected_token not in token_ids:
            self.selected_token = token_ids[0]
        self.token_picker["values"] = token_ids
        self.token_var.set(self.selected_token)

        self.round_label.config(text=f"Round: {self.engine.combat_tracker.round_number}")
        active_actor = (
            self.engine.combat_tracker.current_actor()
            if self.engine.combat_tracker.initiative_order
            else "Not started"
        )
        self.active_actor_label.config(text=f"Active: {active_actor}")

        self.initiative_list.delete(0, tk.END)
        for actor in self.engine.combat_tracker.initiative_order:
            prefix = "-> " if actor == active_actor else "   "
            self.initiative_list.insert(tk.END, f"{prefix}{actor}")

        self.actor_state_text.delete("1.0", tk.END)
        states = self.engine.snapshot().get("actors", {})
        if not states:
            self.actor_state_text.insert(tk.END, "No actor state yet.")
        else:
            for actor_id, state in states.items():
                self.actor_state_text.insert(tk.END, f"{actor_id}\n")
                self.actor_state_text.insert(tk.END, f"  HP: {state['hit_points']}\n")
                self.actor_state_text.insert(
                    tk.END, f"  Items: {', '.join(state['held_items']) or 'None'}\n"
                )
                self.actor_state_text.insert(
                    tk.END, f"  Conditions: {', '.join(state['conditions']) or 'None'}\n\n"
                )

        self.tutorial_list.delete(0, tk.END)
        for idx, step in enumerate(self.tutorial.steps, start=1):
            self.tutorial_list.insert(tk.END, f"{idx}. {step}")

    def run(self) -> None:
        self.root.mainloop()
