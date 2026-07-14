
# Project Description
My personal portfolio website. I am making a graph visualizer with NetworkX for the graph logic and
Matplotlib for the animation.

## Context
Context: fixed-topology graph animation with NetworkX + Matplotlib

Building a matplotlib animation of a graph. Topology never changes at runtime; only node positions
move (tweening, and later force-directed layout). This split drives every decision below.

Architecture
Topology lives in an nx.DiGraph. Geometry lives in a separate (N, 2) float array. Don't store positions as node attributes for the animation path; rebuilding an array from a dict every frame kills vectorization.
Relabel nodes to integers 0..N-1 at construction with nx.convert_node_labels_to_integers(graph, label_attribute="name"). Node id then equals its row in the position array, so geometry and topology stay aligned with no separate index map. The original label is preserved on each node under "name".
Because topology is frozen, compile edge_idx = np.array(list(graph.edges), dtype=np.int32).reshape(-1, 2) once. This (E, 2) int array is the workhorse for both edge rendering (pos[edge_idx] gives (E, 2, 2) segments) and any force-directed physics (pos[edge_idx[:,1]] - pos[edge_idx[:,0]] is every edge vector, vectorized).
Reuse two artists for the whole run: one PathCollection (nodes) from ax.scatter([], []), one LineCollection (edges). Update in place, never recreate.
NetworkX facts that matter here
Storage is dict-of-dicts. DiGraph has _node, _succ (aliased _adj), _pred. Node/edge/attr lookups are average O(1). Iteration order is insertion order on CPython 3.7+.
nx.convert_node_labels_to_integers(G, label_attribute="name") numbers nodes in iteration order; node 0 is the first YAML entry. Find a root structurally instead of assuming id 0: next(n for n in G if G.in_degree(n) == 0).
Hierarchy layout: nx.bfs_layers(G, root) yields [[root], [children], [grandchildren], ...]. For a tree this matches a recursive "put each child below its parent" pass. For a reconvergent DAG where a node has parents at different depths, use nx.topological_generations(G) (no root arg); it places each node below all its predecessors.
Write an array back to node attributes only deliberately (to persist or hand to nx.draw), never per frame: nx.set_node_attributes(G, {n: pos[n] for n in G}, "pos").
Build a name→id map from {d["name"]: n for n, d in G.nodes(data=True)} if you want name-based access alongside index access.
Matplotlib collections facts that matter here
A Collection is one artist drawing many primitives in a single renderer call. That batching is the performance win over per-node Circle/Line2D artists; use collections above ~a few hundred elements.
PathCollection.set_offsets(offsets) takes an (N, 2) array and swaps node positions without rebuilding markers. This is what scatter uses internally and the standard idiom for animated scatter.
LineCollection.set_segments(segs) takes a list (or array) of (N_i, 2) polylines; for straight edges each is a (2, 2) pair. Mirrors the constructor input.
Collections don't autoscale. After adding one, call ax.set_xlim/ylim or ax.relim(); ax.autoscale_view() yourself. Here axis limits are fixed, so no relim in the animation loop.
Per-element props (facecolors, linewidths, set_array + cmap for colormapped values) accept scalar or per-element sequences, applied cyclically. Only needed if you later map degree/weight to color or width.
Minimal working shape
class GraphView:
    def __init__(self, fig, ax, graph, *, axis_lim=(0, 100), spawn_margin=20, rng=None):
        self.graph = nx.convert_node_labels_to_integers(graph, label_attribute="name")
        self._edge_idx = np.array(list(self.graph.edges), dtype=np.int32).reshape(-1, 2)
        rng = rng or np.random.default_rng(3)
        low, high = axis_lim[0] + spawn_margin, axis_lim[1] - spawn_margin
        self._pos = rng.uniform(low, high, size=(self.graph.number_of_nodes(), 2))
        self._scatter = ax.scatter(self._pos[:, 0], self._pos[:, 1], zorder=2)
        self._edge_lines = LineCollection(self._pos[self._edge_idx], zorder=1)
        ax.add_collection(self._edge_lines)

    @property def pos(self): return self._pos

    @pos.setter def pos(self, new): self._pos = new; self.refresh()

    def refresh(self): self._scatter.set_offsets(self._pos)
    self._edge_lines.set_segments(self._pos[self._edge_idx])


Animation: precompute history of shape (frames, N, 2) by tweening start to target; each frame does
G.pos = history[frame] (setter calls refresh()) and returns the two artists.

Gotchas that cost time Passing a string-labeled graph straight in makes np.array(list(edges),
dtype=np.int32) throw ValueError: invalid literal for int(). The integer relabel is mandatory, not
cosmetic. set_offsets and set_segments are the supported update path. Removing and re-adding
collections to refresh them is a common but wasteful anti-pattern. cached_property can't back pos
because it has no setter; a plain @property + setter over self._pos is the same "compute once" with
assignment support. Layout writes to a whole BFS layer at once with fancy indexing:
pos[list(layer), 1] = y.

## Code Standards
ALWAYS:
- Type hint all function parameters and return types. Prefer builtin types (`list`, `dict`) over
  `typing` module types (`List`, `Dict`).
- Use Google docstring style.
- Raise specific exceptions with context.
- Put regex patterns in constants with the `_RE` suffix (e.g. `DATE_RE`).
- When adding imports in `__init__.py`, add to `__all__` as well.
- Use relative imports within the same module.
- Use `pathlib` over `os` for file paths.

ASK FIRST:
- Adding dependencies beyond core stack
- Changing the SQLite schema
- Modifying URL processing rules or rewriters
- Changing scraping/conversion pipeline flow

NEVER:
- Skip type hints on functions
- Hardcode file paths
- Use lazy imports inside functions
- Add `*args` / `**kwargs` without a specific need
- Use premature abstraction, design patterns for their own sake, or metaprogramming where a simple
  function would do

## Formatting requirements
Avoid the stylistic tics common to LLM output. Don't inflate importance: skip phrases like "stands
as a testament to", "plays a vital/pivotal/crucial role", "rich tapestry", "vibrant", "underscores
its significance", or claims that some mundane detail "reflects a broader" trend. Don't tack
present-participle commentary onto sentence ends ("..., highlighting its impact", "..., cementing
its legacy"). Cut the recurring vocabulary: delve, boasts (meaning has), showcase, foster, robust,
meticulous, landscape (figurative), realm, nestled, leverage. Don't overuse the rule of three or
"not only X but Y" / "it's not just X, it's Y" parallelism. Prefer plain verbs (wrote, not authored;
used, not utilized; has, not features). Use straight quotes and apostrophes, no em-dashes, no curly
quotes. Don't end with a "Conclusion" or "In summary" restatement, and don't add a "Despite its
challenges..." wrap-up. Don't pad with hedges ("it's important to note", "it's worth mentioning").
Don't add knowledge-cutoff or "based on available information" disclaimers. Don't over-bold, don't
turn every list item into "**Bolded label**: explanation", and don't put every section in Title
Case. Match length and formality to the task; default to fewer words, concrete specifics over
generic praise, and a real voice over a neutral encyclopedic hum.

Don't restate the takeaway after demonstrating it: if a section, example, or code sample already
makes the point, don't add a sentence explaining what it shows or why it matters. In documentation,
describe what something does once; skip the closing "this ensures/enables..." interpretation. State
things plainly instead of through stock indirect formulas: write "this is slow" not "performance
leaves something to be desired". Plain statements are shorter and easier to follow. Don't resolve
everything in one pass. It's fine, often better, to deliver the core change, name what's left open,
and stop. Prefer "X works now; Y and Z are untouched" over silently expanding scope to tie up every
loose end. Open questions and known limitations are allowed to stay open.

For generated code: don't docstring or comment trivial functions; comment only where logic is
non-obvious. Use specific, contextual names, not generic data/result/temp/process_data. Add error
handling only where a failure can actually occur; never wrap everything in broad try/except that
swallows exceptions. Don't over-engineer: no repository patterns, abstract base classes, factories,
or dependency injection for problems that don't need them. Prefer stdlib over pulling a library per
sub-problem; don't grow the dependency list unnecessarily. Clean up after iteration: remove dead
code, unused functions, and orphaned imports rather than leaving them. Calibrate structure to the
actual requirement instead of applying "best practice" boilerplate by default. Stay within the asked
scope: don't opportunistically refactor, rename, or add tests or features that weren't requested;
mention them as follow-ups instead.