# Hand-written algorithm: top-K zones with a binary min-heap

Code: `backend/algorithms.py` (`MinHeap`, `top_k`)
Used by: `GET /api/zones/top` and the "Top zones" ranking panel on the dashboard
Tests: `tests/test_algorithms.py` (run `python -m unittest tests.test_algorithms`)

## 1. Problem

The dashboard must show the K busiest taxi zones by pickups, drop-offs or average fare. It will later need the K busiest origin-destination routes, which can be up to 265 x 265 = 70,225 pairs.

Sorting every row costs O(n log n) and builds a full sorted copy, even though only K rows are needed.

## 2. Approach

Keep a **min-heap of size K** that holds the K best rows seen so far. The root of a min-heap is its smallest item, so the root is always the weakest of the current best K.

For each new row:
- If the heap has fewer than K rows, push the row.
- Otherwise compare the row with the root. If the row is better, replace the root with it and restore the heap order. If not, ignore the row.

When all rows have been seen, the heap holds exactly the K best rows. They are popped smallest first and written into the result list from the back, so the final list is largest first without calling `reverse()` or `sorted()`.

The heap is a flat list. For the node at index `i`: parent `(i - 1) // 2`, left child `2i + 1`, right child `2i + 2`. Order is restored by `sift_up` after a push and `sift_down` after a pop or replace.

Ties are broken explicitly: on equal scores the lower `location_id` wins, so results are deterministic.

No `heapq`, `sorted()`, `list.sort()`, `Counter` or pandas sorting is used.

## 3. Pseudocode

```
top_k(rows, K, key, tie_key):
    if K <= 0: return []
    heap = empty min-heap
    for row in rows:
        if row[key] is missing: continue
        item = (row[key], row[tie_key], row)
        if size(heap) < K:
            push(heap, item)
        else if item is better than root(heap):
            replace_root(heap, item)
    result = list of size(heap) empty slots
    position = size(heap) - 1
    while heap is not empty:
        result[position] = pop(heap).row
        position = position - 1
    return result

push(heap, item):
    append item to the end
    sift_up(last index)

pop(heap):
    smallest = heap[0]
    move the last item to index 0
    sift_down(0)
    return smallest

sift_up(i):
    while i > 0 and heap[i] is smaller than heap[parent(i)]:
        swap heap[i] and heap[parent(i)]
        i = parent(i)

sift_down(i):
    loop:
        m = i
        if left(i)  exists and heap[left(i)]  is smaller than heap[m]: m = left(i)
        if right(i) exists and heap[right(i)] is smaller than heap[m]: m = right(i)
        if m == i: stop
        swap heap[i] and heap[m]
        i = m
```

## 4. Complexity

n = number of rows, K = result size.

| Step | Time | Space |
|---|---|---|
| Scan all rows (one comparison with the root each) | O(n) | |
| Replace the root for a better row (at most once per row) | O(log K) each, O(n log K) worst case | |
| Extract K items at the end | O(K log K) | |
| **Total** | **O(n log K + K log K) = O(n log K)** | **O(K)** beyond the input |

A full sort is O(n log n) time and O(n) space. For K = 10 and n = 70,000 routes, the heap needs about 70,000 comparisons plus a few swaps, while a full sort needs roughly 1.1 million comparisons.

Worst case for the heap is input already in ascending order (every row beats the root). Typical zone data replaces the root rarely.

## 5. Testing

`tests/test_algorithms.py` checks:
- heap operations (push, pop order, peek, replace_root, empty-heap errors)
- `top_k` against Python's built-in `sorted()` on 200 random inputs (the built-in is used only inside the test as an independent reference)
- edge cases: K larger than the input, K of 0 or negative, empty input, missing scores, ties, and that the input list is not modified

A separate check compared the API ranking with `ORDER BY ... LIMIT 10` in SQL and the results matched.