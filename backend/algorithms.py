"""Hand-written data structures for the taxi dashboard.

Nothing in this file uses heapq, sorted(), list.sort(), Counter or pandas
sorting. The only Python features used are lists, loops and comparisons.

Problem solved: "which K zones have the most pickups (or dropoffs, or the
highest average fare)?" A full sort of n rows costs O(n log n) and builds a
sorted copy of everything. A bounded min-heap of size K answers it in
O(n log K) time and O(K) extra space.
"""


class MinHeap:
    """Binary min-heap stored in a flat list.

    For the node at index i:  parent = (i - 1) // 2,
                              left   = 2i + 1,
                              right  = 2i + 2.
    Each item is a (score, tie_break, payload) tuple compared by hand so the
    ordering rules are explicit: lower score is "smaller"; on equal scores the
    larger tie_break is "smaller" (so lower ids win ties and results are stable).
    """

    def __init__(self):
        self.items = []

    def __len__(self):
        return len(self.items)

    @staticmethod
    def _smaller(a, b):
        """True if item a should sit above item b in the min-heap."""
        if a[0] != b[0]:
            return a[0] < b[0]
        return a[1] > b[1]

    def peek(self):
        """Return the smallest item without removing it. O(1)."""
        if not self.items:
            raise IndexError("peek from an empty heap")
        return self.items[0]

    def push(self, item):
        """Add an item and restore the heap order. O(log n)."""
        self.items.append(item)
        self._sift_up(len(self.items) - 1)

    def pop(self):
        """Remove and return the smallest item. O(log n)."""
        if not self.items:
            raise IndexError("pop from an empty heap")
        smallest = self.items[0]
        last = self.items.pop()
        if self.items:
            self.items[0] = last
            self._sift_down(0)
        return smallest

    def replace_root(self, item):
        """Swap the smallest item for a new one and fix the order. O(log n)."""
        if not self.items:
            raise IndexError("replace_root on an empty heap")
        self.items[0] = item
        self._sift_down(0)

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self._smaller(self.items[i], self.items[parent]):
                self.items[i], self.items[parent] = self.items[parent], self.items[i]
                i = parent
            else:
                break

    def _sift_down(self, i):
        size = len(self.items)
        while True:
            smallest = i
            left = 2 * i + 1
            right = 2 * i + 2
            if left < size and self._smaller(self.items[left], self.items[smallest]):
                smallest = left
            if right < size and self._smaller(self.items[right], self.items[smallest]):
                smallest = right
            if smallest == i:
                break
            self.items[i], self.items[smallest] = self.items[smallest], self.items[i]
            i = smallest


def top_k(rows, k, key, tie_key=None):
    """Return the k rows with the largest row[key], largest first.

    rows     any iterable of dicts
    k        how many rows to return (k <= 0 returns [])
    key      name of the numeric field to rank by
    tie_key  optional field used to break ties (lower value wins); keeps the
             output deterministic when two zones have the same count

    Rows whose key is missing or None are skipped.

    Time:  O(n log k)  - one comparison per row, and at most one O(log k)
                         replace per row; final extraction is O(k log k).
    Space: O(k) beyond the input.
    """
    if k <= 0:
        return []

    heap = MinHeap()
    for row in rows:
        score = row.get(key)
        if score is None:
            continue
        tie = row.get(tie_key) if tie_key else 0
        if tie is None:
            tie = 0
        item = (score, tie, row)
        if len(heap) < k:
            heap.push(item)
        elif MinHeap._smaller(heap.peek(), item):
            # The new row beats the weakest of the current best k.
            heap.replace_root(item)

    # Popping gives smallest first; fill the result from the back so the
    # final list is largest first without calling reverse() or sorted().
    result = [None] * len(heap)
    position = len(heap) - 1
    while len(heap) > 0:
        result[position] = heap.pop()[2]
        position -= 1
    return result
