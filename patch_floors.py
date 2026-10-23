with open("src/core/game_state.py", "r") as f:
    gs = f.read()

# Add Act tracking to GameState
gs = gs.replace(
    "self.floor: int = 1",
    "self.floor: int = 1\n        self.act: int = 1"
)

# In update_combat, when defeating a BOSS, move to next Act or Victory
old_boss_logic = """            current_node = self.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                self.switch_mode(GameMode.VICTORY)
            else:
                self.switch_mode(GameMode.MAP)"""

new_boss_logic = """            current_node = self.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                if self.act < 3:
                    self.act += 1
                    self.floor = 1
                    self.map_graph = generate_spire_map(num_floors=8, width_lanes=4)
                    self.player.heal(9999) # Full heal between acts
                    self.switch_mode(GameMode.MAP)
                else:
                    self.switch_mode(GameMode.VICTORY)
            else:
                self.switch_mode(GameMode.MAP)"""
gs = gs.replace(old_boss_logic, new_boss_logic)

with open("src/core/game_state.py", "w") as f:
    f.write(gs)
