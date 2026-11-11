"""The kitchen: a 1990s fitted kitchen at the back of the ground floor."""

from __future__ import annotations

import plan
from . import dressing as dr
from . import models

GF = 0.0


def build():
    models.place("wooden_table_02", "kitchen_table", (4.45, 6.00, GF), facing=0, scale=1.2)
    models.place("painted_wooden_chair_01", "kitchen_chair_1", (4.42, 5.22, GF), facing=85)
    models.place("painted_wooden_chair_01", "kitchen_chair_2", (4.55, 6.80, GF), facing=-98)
    dr.pendant("kitchen", 4.5, 6.0, plan.CEILING, drop=0.75, kind="off")
