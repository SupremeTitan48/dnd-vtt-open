from dataclasses import dataclass, field


@dataclass
class MapState:
    width: int
    height: int
    token_positions: dict[str, tuple[int, int]] = field(default_factory=dict)
    fog_enabled: bool = False
    revealed_cells: set[tuple[int, int]] = field(default_factory=set)
    terrain_tiles: dict[tuple[int, int], str] = field(default_factory=dict)
    blocked_cells: set[tuple[int, int]] = field(default_factory=set)
    asset_stamps: dict[tuple[int, int], str] = field(default_factory=dict)

    def _validate_cell(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError("Cell outside map bounds")

    def move_token(self, token_id: str, x: int, y: int) -> None:
        self._validate_cell(x, y)
        self.token_positions[token_id] = (x, y)
        if self.fog_enabled:
            self.revealed_cells.add((x, y))

    def toggle_fog(self, enabled: bool) -> None:
        self.fog_enabled = enabled
        if not enabled:
            self.revealed_cells.clear()

    def reveal_cell(self, x: int, y: int) -> None:
        self._validate_cell(x, y)
        self.revealed_cells.add((x, y))

    def paint_terrain(self, x: int, y: int, terrain_type: str) -> None:
        self._validate_cell(x, y)
        if terrain_type == "clear":
            self.terrain_tiles.pop((x, y), None)
            return
        self.terrain_tiles[(x, y)] = terrain_type

    def toggle_blocked(self, x: int, y: int) -> None:
        self._validate_cell(x, y)
        cell = (x, y)
        if cell in self.blocked_cells:
            self.blocked_cells.remove(cell)
        else:
            self.blocked_cells.add(cell)

    def stamp_asset(self, x: int, y: int, asset_id: str) -> None:
        self._validate_cell(x, y)
        if asset_id == "clear":
            self.asset_stamps.pop((x, y), None)
            return
        self.asset_stamps[(x, y)] = asset_id
