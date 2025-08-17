from game.engine.tags import TaggableMixin, damage_multiplier_for_target


class T(TaggableMixin):
	def __init__(self, tags: set[str]):
		self.tags = tags


def test_has_tag_and_has_any():
	t = T({"a", "b"})
	assert t.has_tag("a")
	assert not t.has_tag("c")
	assert t.has_any(["x", "b"]) 
	assert not t.has_any(["x", "y"]) 


def test_damage_multiplier_boss():
	assert damage_multiplier_for_target({"boss"}) == 1.1
	assert damage_multiplier_for_target({"monster"}) == 1.0


