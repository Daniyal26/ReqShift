"""Synthetic restricted type goal models for scalability measurement."""

def make_spec(n_types=3, hi=2, depth=1, dep_mult='1..*', n_deps=None, lo_first=1):
    """depth=1 -> root + 2 leaves (3 goals); depth=2 -> 7 goals; depth=d -> 2^(d+1)-1.
    Internal nodes alternate AND (even depth) / XOR (odd depth) so XOR nodes
    create genuine choice (and therefore multiple satisfying assignments)."""
    actors, goals, decomp, roots = [], [], {}, {}
    leaves_by_type = {}
    for t in range(n_types):
        T = f'T{t}'
        actors.append({'type': T, 'lo': (lo_first if t == 0 else 0), 'hi': hi})
        # build binary tree
        root = f'{T}_n0'
        roots[T] = root
        frontier = [(root, 0)]
        nodes = [root]
        leaves = []
        counter = 1
        while frontier:
            node, d = frontier.pop(0)
            if d == depth:
                leaves.append(node)
                continue
            c1, c2 = f'{T}_n{counter}', f'{T}_n{counter+1}'
            counter += 2
            nodes += [c1, c2]
            op = 'AND' if d % 2 == 0 else 'XOR'
            decomp[node] = {'parent': node, 'op': op, 'children': [c1, c2]}
            frontier += [(c1, d + 1), (c2, d + 1)]
        for n in nodes:
            goals.append({'name': n, 'owner': T, 'kind': 'goal',
                          'root': n == root})
        leaves_by_type[T] = leaves

    deps = []
    chain = n_types - 1 if n_deps is None else n_deps
    for k in range(chain):
        src_t, dst_t = f'T{k % n_types}', f'T{(k + 1) % n_types}'
        src = leaves_by_type[src_t][k % len(leaves_by_type[src_t])]
        dst = leaves_by_type[dst_t][0]
        deps.append({'from': src, 'to': dst, 'mult': dep_mult})

    return {'actors': actors, 'roots': roots, 'goals': goals,
            'decomp': list(decomp.values()), 'deps': deps}
