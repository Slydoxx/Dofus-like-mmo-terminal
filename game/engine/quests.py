from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from .inventory import Item


class QuestStatus(Enum):
	NOT_STARTED = "not_started"
	IN_PROGRESS = "in_progress"
	COMPLETED = "completed"
	FAILED = "failed"


class ObjectiveType(Enum):
	KILL_MONSTERS = "kill_monsters"
	COLLECT_ITEMS = "collect_items"
	REACH_LOCATION = "reach_location"
	TALK_TO_NPC = "talk_to_npc"


@dataclass
class QuestObjective:
	id: str
	description: str
	objective_type: ObjectiveType
	target: str
	required_amount: int
	current_amount: int = 0
	completed: bool = False
	
	def update_progress(self, amount: int = 1) -> bool:
		if self.completed:
			return False
		
		self.current_amount += amount
		if self.current_amount >= self.required_amount:
			self.current_amount = self.required_amount
			self.completed = True
			return True
		return False


@dataclass
class QuestReward:
	xp: int = 0
	gold: int = 0
	items: List[Dict[str, Any]] = field(default_factory=list)
	skill_points: int = 0


@dataclass
class Quest:
	id: str
	name: str
	description: str
	objectives: List[QuestObjective]
	rewards: QuestReward
	level_requirement: int = 1
	prerequisites: List[str] = field(default_factory=list)
	repeatable: bool = False
	time_limit: Optional[int] = None


@dataclass
class QuestLog:
	active_quests: Dict[str, Quest] = field(default_factory=dict)
	completed_quests: List[str] = field(default_factory=list)
	failed_quests: List[str] = field(default_factory=list)
	
	def add_quest(self, quest: Quest) -> bool:
		if quest.id in self.active_quests or quest.id in self.completed_quests:
			return False
		self.active_quests[quest.id] = quest
		return True
	
	def complete_quest(self, quest_id: str) -> Optional[QuestReward]:
		if quest_id not in self.active_quests:
			return None
		
		quest = self.active_quests[quest_id]
		if not all(obj.completed for obj in quest.objectives):
			return None
		
		self.completed_quests.append(quest_id)
		del self.active_quests[quest_id]
		return quest.rewards
	
	def update_objective(self, quest_id: str, objective_id: str, amount: int = 1) -> bool:
		if quest_id not in self.active_quests:
			return False
		
		quest = self.active_quests[quest_id]
		for objective in quest.objectives:
			if objective.id == objective_id:
				return objective.update_progress(amount)
		return False
	
	def get_quest_progress(self, quest_id: str) -> Optional[Dict[str, Any]]:
		if quest_id not in self.active_quests:
			return None
		
		quest = self.active_quests[quest_id]
		completed = sum(1 for obj in quest.objectives if obj.completed)
		total = len(quest.objectives)
		
		return {
			"name": quest.name,
			"description": quest.description,
			"progress": f"{completed}/{total}",
			"objectives": quest.objectives
		}


QUESTS = {
	"first_blood": Quest(
		id="first_blood",
		name="First Blood",
		description="Defeat your first monster to prove your worth",
		objectives=[
			QuestObjective(
				id="kill_slime",
				description="Kill 1 Slime",
				objective_type=ObjectiveType.KILL_MONSTERS,
				target="slime",
				required_amount=1
			)
		],
		rewards=QuestReward(xp=100, gold=50, items=[{"id": "health_potion", "quantity": 2}]),
		level_requirement=1
	),
	"monster_hunter": Quest(
		id="monster_hunter",
		name="Monster Hunter",
		description="Defeat multiple monsters to gain experience",
		objectives=[
			QuestObjective(
				id="kill_monsters",
				description="Kill 3 monsters",
				objective_type=ObjectiveType.KILL_MONSTERS,
				target="any",
				required_amount=3
			)
		],
		rewards=QuestReward(xp=300, gold=150, skill_points=1),
		level_requirement=2,
		prerequisites=["first_blood"]
	),
	"collector": Quest(
		id="collector",
		name="Item Collector",
		description="Collect various items to improve your equipment",
		objectives=[
			QuestObjective(
				id="collect_potions",
				description="Collect 5 health potions",
				objective_type=ObjectiveType.COLLECT_ITEMS,
				target="health_potion",
				required_amount=5
			)
		],
		rewards=QuestReward(xp=200, gold=100, items=[{"id": "iron_sword", "quantity": 1}]),
		level_requirement=1
	)
}


def get_quest_by_id(quest_id: str) -> Optional[Quest]:
	return QUESTS.get(quest_id)


def check_quest_requirements(quest: Quest, player_level: int, completed_quests: List[str]) -> bool:
	if player_level < quest.level_requirement:
		return False
	
	for prereq in quest.prerequisites:
		if prereq not in completed_quests:
			return False
	
	return True
