Fruchterman-Reingold is a force-directed layout, and after Sugiyama it's going to feel like a vacation. There's no layering, no orderings, no combinatorics. You simulate a physical system and let it settle.

**The physical metaphor**

Treat the graph as a physical system with two forces:

1. Every pair of nodes repels each other, like charged particles. This spreads the graph out and stops nodes from overlapping.
2. Every edge pulls its two endpoints together, like a spring. This keeps connected nodes near each other.

Run the simulation until the forces balance. At equilibrium, connected nodes sit close, unconnected nodes sit far, and dense clusters emerge as visual clusters. Nobody told the layout what the structure is; it falls out of the force balance.

**The forces**

Both forces are scaled by a single constant k, the "ideal edge length":

```
k = C * sqrt(area / N)
```

The intuition: if you divided the canvas into N equal cells, one per node, k is roughly the cell width. C is a fudge factor, usually near 1.

For a pair of nodes at distance d:

```
repulsion  f_r(d) = k^2 / d     (applies to ALL pairs, pushes apart)
attraction f_a(d) = d^2 / k     (applies to EDGES only, pulls together)
```

Look at the asymmetry, because it's the whole design. At short distance, repulsion (1/d) blows up and attraction (d^2) vanishes, so nodes never collapse into each other. At long distance, attraction dominates and repulsion fades, so edges can't stretch forever. For two connected nodes, the forces cancel exactly at d = k: set k^2/d = d^2/k and solve, you get d = k. Hence "ideal edge length": every edge *wants* to be length k, and the layout is the compromise when they can't all get it.

**The algorithm**

```
for each iteration:
    # accumulate displacement per node
    for each node v:
        disp[v] = 0

    # repulsion: all pairs
    for each pair (v, u):
        delta = pos[v] - pos[u]
        d = |delta|
        disp[v] += (delta / d) * (k^2 / d)
        disp[u] -= (delta / d) * (k^2 / d)

    # attraction: edges
    for each edge (v, u):
        delta = pos[v] - pos[u]
        d = |delta|
        disp[v] -= (delta / d) * (d^2 / k)
        disp[u] += (delta / d) * (d^2 / k)

    # move, but no further than the temperature allows
    for each node v:
        pos[v] += (disp[v] / |disp[v]|) * min(|disp[v]|, t)

    t = cool(t)
```

Note the structure: forces are *accumulated* into a displacement buffer first, then applied all at once. Nodes don't move mid-iteration.

**Temperature is the part that matters**

That `min(|disp[v]|, t)` is doing more work than it looks like. The raw forces can be huge (two nodes spawned close together produce a massive repulsion), and without a cap the system explodes or oscillates: a node overshoots its equilibrium, gets yanked back, overshoots again, forever.

The temperature t caps the maximum move per iteration, and `cool()` shrinks it over time, typically linearly toward zero or by multiplying with ~0.95 each step. Early on, big moves are allowed and the global structure sorts itself out; later, only small refinements are possible and the layout crystallizes. It's simulated annealing in spirit: coarse first, fine later. If your final layout jitters instead of settling, temperature is the knob. Start around 1/10th of the canvas width.

**What this means for your code**

This maps almost verbatim onto what you already built, which I suspect you noticed:

- One FR iteration = a function `(N, 2) positions -> (N, 2) displacement`. That is exactly the `step_fn` signature of your `step_history`. Sugiyama was a one-shot tween; FR is the algorithm `step_history` was waiting for.
- The all-pairs repulsion is a nested loop in the pseudocode, but with your `_pos` array it's a vectorized pairwise-difference computation, no Python loops. Same for attraction via `_edge_idx`.
- Temperature lives naturally as state across frames, so the animation *is* the algorithm converging, in contrast to the tween where you animated toward a precomputed answer.

Complexity: O(N^2) per iteration from the all-pairs repulsion, which at 50 nodes is nothing (the classic optimizations, grid buckets and Barnes-Hut, exist for thousands of nodes; ignore them).

Two things to think through before implementing, since they're the traps everyone hits: what happens when two nodes are at (nearly) the same position and d approaches 0, and whether/how you keep nodes inside your axis limits. The paper clamps to the frame; a softer option is letting repulsion from the walls do it. Have an answer for the first one before you run anything, or your first frame will fling nodes to infinity.