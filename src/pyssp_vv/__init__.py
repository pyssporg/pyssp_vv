"""Verification and validation for simulation models.

Two capabilities, one distribution:

- :mod:`pyssp_vv.measure` — how far apart two trajectories are. Series,
  alignment, metric families, normalisation, coverage, figures.
- :mod:`pyssp_vv.judge` — whether that is acceptable, and why. Roles,
  criterion, sufficiency, dispositions, verdicts.

The contracts (:mod:`pyssp_vv.policy`, :mod:`pyssp_vv.judge`,
:mod:`pyssp_vv.evidence`) are standard-library only. Measurement needs numpy and
ships behind the ``measure`` extra.
"""

__version__ = "0.1.0"
