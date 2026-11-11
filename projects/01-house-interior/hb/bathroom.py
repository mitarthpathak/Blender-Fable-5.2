"""The bathroom: upstairs at the back, where the box room was."""

from __future__ import annotations

import plan
from . import dressing as dr


def build():
    dr.pendant("bathroom", 4.9, 6.2, plan.ROOF_Z, drop=0.45, kind="off")
