"""Lines laid on display cells, so checks work on columns, never string indexes."""
from __future__ import annotations

from .width import cell_width, clusters


class Grid:
    """Rows of cells. A cluster takes cells equal to its width: the first
    cell holds the cluster text, each further cell is "" (continuation).
    A zero-width cluster takes no cell.

    Rows are not padded: at() is None past the end of a row, so "a space"
    and "no more line" stay distinct. Tabs are not expanded.
    """

    def __init__(self, lines, ambiguous_wide: bool = False):
        self.ambiguous_wide = ambiguous_wide
        self.lines = list(lines)
        self._cells = []   # type: list[list[str]]
        self._starts = []  # type: list[list[int]]
        self._clusters = []  # type: list[list[tuple[int, str, int]]]
        for line in self.lines:
            cells = []  # type: list[str]
            starts = []  # type: list[int]
            cl = []  # type: list[tuple[int, str, int]]
            for text, _ in clusters(line):
                w = cell_width(text, ambiguous_wide)
                col = len(cells)
                starts.extend([col] * len(text))
                if w > 0:
                    cells.append(text)
                    cells.extend([""] * (w - 1))
                    cl.append((col, text, w))
            starts.append(len(cells))
            self._cells.append(cells)
            self._starts.append(starts)
            self._clusters.append(cl)

    @property
    def height(self) -> int:
        return len(self._cells)

    def width(self, row: int) -> int:
        """Display width of a row in cells."""
        return len(self._cells[row])

    @property
    def max_width(self) -> int:
        return max((len(c) for c in self._cells), default=0)

    def at(self, row: int, col: int):
        """The cell at (row, col): the cluster text, "" for the continuation
        of a wide cluster, None outside the row or the grid."""
        if row < 0 or row >= len(self._cells) or col < 0:
            return None
        cells = self._cells[row]
        if col >= len(cells):
            return None
        return cells[col]

    def col_of(self, row: int, index: int) -> int:
        """Display column of the string index `index` in lines[row]
        (index == len(line) gives the row width)."""
        return self._starts[row][index]

    def row_clusters(self, row: int) -> "list[tuple[int, str, int]]":
        """(column, cluster text, cells) for every cell-taking cluster."""
        return list(self._clusters[row])

    def index_of(self, row: int, col: int) -> int:
        """String index in lines[row] of the cluster that covers column col."""
        line = self.lines[row]
        best = 0
        for i, c in enumerate(self._starts[row][:len(line)]):
            if c <= col:
                best = i
            else:
                break
        return best
