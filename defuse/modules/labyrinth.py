"""Nine original perfect mazes. Coordinates in public text are 1-based (row, column)."""
from collections import deque
import random

SIZE = 6
DIRECTIONS = {'up':(-1,0), 'down':(1,0), 'left':(0,-1), 'right':(0,1)}


def edge(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


def generate_layout(index):
    rng = random.Random(0xD3F053 + index * 7919)
    start = (1, 1)
    visited, stack, passages = {start}, [start], set()
    while stack:
        cell = stack[-1]
        choices = []
        for dr, dc in DIRECTIONS.values():
            nxt = (cell[0]+dr, cell[1]+dc)
            if 1 <= nxt[0] <= SIZE and 1 <= nxt[1] <= SIZE and nxt not in visited:
                choices.append(nxt)
        if not choices:
            stack.pop()
        else:
            nxt = rng.choice(choices)
            passages.add(edge(cell, nxt))
            visited.add(nxt)
            stack.append(nxt)
    # Pairs are deliberately unique, independent of the generated wall geometry.
    markers = ((1 + index // 6, 1 + index % 6), (6, 1 + (index * 5) % 6))
    return {'id': index + 1, 'markers': markers, 'passages': frozenset(passages)}


LAYOUTS = tuple(generate_layout(i) for i in range(9))


def layout_for(markers):
    pair = {tuple(p) for p in markers}
    return next(layout for layout in LAYOUTS if set(layout['markers']) == pair)


def destination(cell, action):
    dr, dc = DIRECTIONS[action]
    return cell[0] + dr, cell[1] + dc


def legal(layout, cell, action):
    return edge(cell, destination(cell, action)) in layout['passages']


def distances(layout, exit_cell):
    result = {tuple(exit_cell): 0}
    queue = deque([tuple(exit_cell)])
    while queue:
        cell = queue.popleft()
        for action in DIRECTIONS:
            nxt = destination(cell, action)
            if legal(layout, cell, action) and nxt not in result:
                result[nxt] = result[cell] + 1
                queue.append(nxt)
    return result


def shortest_action(state):
    layout = layout_for(state['markers'])
    distance = distances(layout, state['exit'])
    cell = tuple(state['cell'])
    return next(action for action in DIRECTIONS
                if legal(layout, cell, action) and distance[destination(cell, action)] == distance[cell]-1)


def make_state(rng):
    layout = rng.choice(LAYOUTS)
    exit_cell = (rng.randint(1, SIZE), rng.randint(1, SIZE))
    distance = distances(layout, exit_cell)
    candidates = [p for p, d in distance.items() if 8 <= d <= 18]
    start = rng.choice(candidates)
    return {'markers':[list(p) for p in layout['markers']], 'cell':list(start),
            'exit':list(exit_cell), 'moves':[]}, distance[start]


def manual_section():
    paragraphs = [
        'Labyrinth — a 6×6 grid. Coordinates are (row,column), starting at (1,1) in the top left. '
        'Up reduces row; down increases row; left reduces column; right increases column. '
        'Identify the layout by its unordered pair of marker circles. Outer boundaries are walls. '
        'Each listed pair of adjacent cells has a wall between them; all other adjacent pairs are open. '
        'Move to the exit. Any open move is legal, including a detour; a wall bump adds a strike and leaves the dot in place. '
        'Shortest-path choices are measured separately from legality. The move history shows your prior attempts.'
    ]
    for layout in LAYOUTS:
        walls = []
        for row in range(1, 7):
            for col in range(1, 7):
                cell = (row, col)
                for action in ['down','right']:
                    nxt = destination(cell, action)
                    if nxt[0] <= 6 and nxt[1] <= 6 and edge(cell, nxt) not in layout['passages']:
                        walls.append(f'({row},{col})–({nxt[0]},{nxt[1]})')
        a,b = layout['markers']
        paragraphs.append(f'Layout {layout["id"]}: circles ({a[0]},{a[1]}) and ({b[0]},{b[1]}). Walls: ' + '; '.join(walls) + '.')
    return '\n\n'.join(paragraphs)
