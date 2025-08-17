from game.engine.grid import Grid


def make_grid() -> Grid:
	blocked = {(1, 1)}
	return Grid(width=4, height=3, blocked=set(blocked))


def test_in_bounds_edges():
	g = make_grid()
	assert g.in_bounds(0, 0)
	assert g.in_bounds(3, 2)
	assert not g.in_bounds(-1, 0)
	assert not g.in_bounds(4, 2)
	assert not g.in_bounds(0, 3)


def test_walkable_blocked_and_border():
	g = make_grid()
	assert not g.walkable(1, 1)
	assert g.walkable(0, 0)
	assert not g.walkable(-1, 0)
	assert not g.walkable(0, 3)


