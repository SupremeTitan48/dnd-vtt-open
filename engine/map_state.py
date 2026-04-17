from dataclasses import dataclass, field

VISION_MODES = {"normal", "darkvision", "truesight"}
SCENE_LIGHTING_PRESETS = {"day", "dim", "night"}


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
    visibility_cells_by_token: dict[str, set[tuple[int, int]]] = field(default_factory=dict)
    vision_radius_by_token: dict[str, int] = field(default_factory=dict)
    vision_mode_by_token: dict[str, str] = field(default_factory=dict)
    token_light_by_token: dict[str, dict[str, int | str | bool]] = field(default_factory=dict)
    scene_lighting_preset: str = "day"
    blocker_revision: int = 0
    _visibility_cache: dict[tuple[int, int, int, int], frozenset[tuple[int, int]]] = field(
        default_factory=dict
    )
    visibility_cache_hits: int = 0
    visibility_cache_misses: int = 0

    def _line_cells(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        x0, y0 = start
        x1, y1 = end
        cells: list[tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return cells

    def compute_visible_cells(self, origin_x: int, origin_y: int, radius: int) -> set[tuple[int, int]]:
        self._validate_cell(origin_x, origin_y)
        if radius < 0:
            raise ValueError("radius must be >= 0")
        cache_key = (origin_x, origin_y, radius, self.blocker_revision)
        cached = self._visibility_cache.get(cache_key)
        if cached is not None:
            self.visibility_cache_hits += 1
            return set(cached)
        self.visibility_cache_misses += 1
        visible: set[tuple[int, int]] = set()
        min_x = max(0, origin_x - radius)
        max_x = min(self.width - 1, origin_x + radius)
        min_y = max(0, origin_y - radius)
        max_y = min(self.height - 1, origin_y + radius)
        radius_sq = radius * radius
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                dx = x - origin_x
                dy = y - origin_y
                if (dx * dx + dy * dy) > radius_sq:
                    continue
                ray = self._line_cells((origin_x, origin_y), (x, y))
                blocked = False
                for cell in ray[1:-1]:
                    if cell in self.blocked_cells:
                        blocked = True
                        break
                if blocked:
                    continue
                visible.add((x, y))
                if (x, y) in self.blocked_cells and (x, y) != (origin_x, origin_y):
                    continue
        self._visibility_cache[cache_key] = frozenset(visible)
        return visible

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

    def hide_cell(self, x: int, y: int) -> None:
        self._validate_cell(x, y)
        self.revealed_cells.discard((x, y))

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
        self.blocker_revision += 1
        self._visibility_cache.clear()

    def stamp_asset(self, x: int, y: int, asset_id: str) -> None:
        self._validate_cell(x, y)
        if asset_id == "clear":
            self.asset_stamps.pop((x, y), None)
            return
        self.asset_stamps[(x, y)] = asset_id

    def recompute_visibility(self, token_id: str, radius: int) -> set[tuple[int, int]]:
        position = self.token_positions.get(token_id)
        if position is None:
            raise ValueError("Token not found")
        x, y = position
        visible = self.compute_visible_cells(x, y, radius)
        self.visibility_cells_by_token[token_id] = visible
        return visible

    def set_token_vision_radius(self, token_id: str, radius: int) -> set[tuple[int, int]]:
        if radius < 0:
            raise ValueError("radius must be >= 0")
        self.vision_radius_by_token[token_id] = radius
        return self.recompute_visibility(token_id, radius)

    def set_token_vision_mode(self, token_id: str, vision_mode: str) -> None:
        normalized = vision_mode.strip().lower()
        if normalized not in VISION_MODES:
            raise ValueError(f"vision_mode must be one of {sorted(VISION_MODES)}")
        self.vision_mode_by_token[token_id] = normalized

    def set_token_light(
        self,
        token_id: str,
        *,
        bright_radius: int,
        dim_radius: int,
        color: str,
        enabled: bool,
    ) -> None:
        if bright_radius < 0 or dim_radius < 0:
            raise ValueError("light radii must be >= 0")
        if bright_radius > dim_radius:
            raise ValueError("bright_radius must be <= dim_radius")
        normalized_color = color.strip() or "#ffffff"
        self.token_light_by_token[token_id] = {
            "bright_radius": int(bright_radius),
            "dim_radius": int(dim_radius),
            "color": normalized_color,
            "enabled": bool(enabled),
        }

    def set_scene_lighting_preset(self, preset: str) -> None:
        normalized = preset.strip().lower()
        if normalized not in SCENE_LIGHTING_PRESETS:
            raise ValueError(f"scene lighting preset must be one of {sorted(SCENE_LIGHTING_PRESETS)}")
        self.scene_lighting_preset = normalized
