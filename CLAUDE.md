# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the game**: `python -m game.app.cli`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run tests**: `pytest -q`
- **Run specific test**: `pytest game/tests/test_grid.py -q`

## Project Architecture

This is a terminal-based Dofus-like tactical RPG built with strict separation of concerns:

### Core Architecture Principles
- **Engine module**: Pure logic with no I/O operations (no prints or inputs)
- **App module**: Handles all terminal input/output and user interface
- **Content module**: JSON-based data definitions validated with Pydantic

### Module Structure
- `game/engine/`: Pure game logic
  - `entities.py`: Player, Monster, Merchant, NPC, Portal classes
  - `combat.py`: Turn-based combat system with CombatState and CombatArena
  - `ability.py`: Ability system with effect resolution
  - `grid.py`: Map grid and movement validation
  - `inventory.py`: Item management and equipment slots
  - `progression.py`: Player leveling and weapon skills
  - `stats.py`: Character statistics and damage calculations
  - `quests.py`: Quest system with objectives and rewards
- `game/app/`: Terminal interface
  - `cli.py`: Main entry point and input handling
  - `game_loop.py`: Game state management and rendering
  - `iso.py`: Isometric rendering (in development)
  - `ui/`: UI components and themes
- `game/content/`: JSON data files
  - `maps/`: Map definitions with blocked tiles
  - `monsters/`: Monster stats and abilities
  - `spells/`: Spell definitions with effects
  - `abilities/`: Weapon abilities and effects
  - `shops/`: Merchant inventories

### Key Design Patterns
- **Ability Registry**: Abilities are registered by ID and referenced throughout the system
- **Effect System**: Abilities have composable effects (Damage, Push, BuffAp, Charge)
- **Combat Arena**: Separate combat grid (7x5) from world map during fights
- **Tag System**: Entities use tags for flexible categorization and targeting
- **Quest System**: Objective-based quests with progress tracking

### Game State Management
The main `GameState` class tracks:
- World grid and player position
- Monsters, merchants, NPCs, and portals
- Combat state (separate from world state)
- Player inventory, equipment, and progression
- Quest log and completion tracking

### Combat System
- Turn-based with AP (Action Points) and MP (Movement Points)
- Line-of-sight validation for ranged abilities
- Melee abilities require adjacency (range_max <= 1)
- Combat uses a separate 7x5 arena grid
- Monster AI with basic movement and attack patterns

### Dependencies
- **Pydantic**: Data validation for JSON content
- **Pygame**: Graphics support (for future isometric rendering)
- **Pytest**: Unit testing framework

## Development Iteration Plan

Current iteration focuses on terminal gameplay with ASCII rendering. Future iterations will add:
1. Targeting mode improvements
2. Isometric renderer with Raylib/Pygame
3. Enhanced combat effects and animations
4. Expanded quest and dialogue systems

## Important Notes

- Always maintain the engine/app boundary - engine code must not contain I/O operations
- JSON content files are validated by Pydantic models on load
- Combat uses a separate grid system from the world map
- The ability registry must be populated before creating players with weapons
- Quest progress updates automatically when certain game events occur