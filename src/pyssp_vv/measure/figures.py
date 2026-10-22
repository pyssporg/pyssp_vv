"""Figure specification: rendering as a view of a comparison.

Contract (not yet implemented): given a :class:`~pyssp_vv.measure.metrics.Comparison`
and a criterion, describe the figure — overlay, residual panel, tolerance band,
gap shading, shift indicator — as data. Rendering is a separate adapter behind
the ``figures`` extra.

Figures are derived artifacts: regenerable from the comparison and the policy,
never hashed into evidence, and never an acceptance criterion. A comparison
figure draws the criterion band, so a reader can see what was judged.
"""
