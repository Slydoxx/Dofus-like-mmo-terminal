from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from pydantic import BaseModel, Field, ValidationError, field_validator


class BlockedCellModel(BaseModel):
	x: int
	y: int


class MapModel(BaseModel):
	name: str
	width: int
	height: int
	blocked: List[BlockedCellModel] = Field(default_factory=list)

	@field_validator("width", "height")
	def positive(cls, v: int) -> int:
		if v <= 0:
			raise ValueError("must be positive")
		return v


class StatsModel(BaseModel):
	hp: int
	ap: int
	mp: int
	atk: int
	res: int


class MonsterModel(BaseModel):
	id: str
	name: str
	tags: List[str]
	stats: StatsModel
	abilities: List[str]


class EffectModel(BaseModel):
	type: str
	amount: int | None = None
	distance: int | None = None
	duration: int | None = None


class SpellModel(BaseModel):
	id: str
	name: str
	tags: List[str]
	cost_ap: int
	range_min: int = 0
	range_max: int
	effects: List[EffectModel]


class AbilityModel(BaseModel):
	id: str
	name: str
	tags: List[str]
	cost_ap: int
	range_min: int = 0
	range_max: int
	effects: List[EffectModel]
	weapon_type: str


class ShopItemModel(BaseModel):
	item_id: str
	price: int
	stock: int | None = None


class ShopModel(BaseModel):
	id: str
	name: str
	items: List[ShopItemModel]


def load_json(path: Path) -> dict:
	with path.open("r", encoding="utf-8") as f:
		return json.load(f)


def load_map(path: Path) -> MapModel:
	try:
		data = load_json(path)
		return MapModel(**data)
	except ValidationError as e:
		raise ValueError(f"Invalid map at {path}: {e}")


def load_monster(path: Path) -> MonsterModel:
	try:
		data = load_json(path)
		return MonsterModel(**data)
	except ValidationError as e:
		raise ValueError(f"Invalid monster at {path}: {e}")


def load_spells(path: Path) -> List[SpellModel]:
	try:
		data = load_json(path)
		return [SpellModel(**s) for s in data]
	except ValidationError as e:
		raise ValueError(f"Invalid spells at {path}: {e}")


def load_abilities(path: Path) -> List[AbilityModel]:
	try:
		data = load_json(path)
		return [AbilityModel(**s) for s in data]
	except ValidationError as e:
		raise ValueError(f"Invalid abilities at {path}: {e}")


def load_shop(path: Path) -> ShopModel:
	try:
		data = load_json(path)
		return ShopModel(**data)
	except ValidationError as e:
		raise ValueError(f"Invalid shop at {path}: {e}")


