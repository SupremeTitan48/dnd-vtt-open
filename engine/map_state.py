from dataclasses import dataclass, field


@dataclass
class MapState:
    width: int
    height: int
    token_positions: dict[str, tuple[int, int]] = field(default_factory=dict)

    def move_token(self, token_id: str, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError("Token move outside map bounds")
        self.token_positions[token_id] = (x, y)
