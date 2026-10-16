# S4 branch-local structural contrast

2026-10-16. Follow-up to S4-LOCALITY-DIAGNOSIS.md; no stage completion is claimed here.

Run 38861970860 measured source a5da52b9eabf5da3901af3747169212c1791995f. At diagnosis, the completed head-a, reserved-d and reserved-e jobs had all nine S3 scenes passing and all nine S4 outside-edge changes exactly 0. All side-lit S4 scenes passed. Front S4 failed only edge-ink-overwhelms-face: head-a 0.124286, reserved-d 0.122294, reserved-e 0.125881 versus the unchanged 0.12 cap. Source digest S4 e7a6cd003d8d60820df32b86760191479882e5c2be9d75774a1681d36cc4e351. This snapshot is not an assertion that the other three jobs or the advanced UI had finished.

The area-weighted face-mean repair removed unoccluded-light leakage but still mixed a geometric crease with a light-visibility transition: two adjacent faces with identical 0.8 lit and 0.1 unlit irradiance can have whole-face means 0.8 and 0.45 solely because a shadow crosses half of one face. At angle 40 degrees the old mean test falsely labels the whole edge hard, even though the common lit segment has zero form contrast. A synthetic negative control reproduces this independently of any head identity, screenshot or cap.

The new selector intersects the actual geometric shared line with both lit domains and, separately, with both dark domains. It applies the original angle and linear-contrast rules within each branch. Direct visibility transitions remain exactly as painted by S3; they are not additionally outlined as geometric creases. Genuine same-branch hard/soft contrast is retained, partial support keeps only the matching segment, hidden neighbors still cannot supply a crease, and invalid irradiance/grid inputs fail explicitly.

Classification counts now report the highest accepted segment class per shared mesh edge; unsupported edges are lost. Within each branch the comparison is still based on the face's vertex-mean irradiance, not a continuous cross-edge derivative. This approximation is explicit. Camera-occlusion and silhouette hard edges are unchanged.

No identity parameters, light conditions, angle/contrast thresholds, widths, opacity, feather margins, error tolerances, point budgets or ink cap are changed. The previously failed area-mean calculation is retained only as a diagnostic control and regression negative, never as the active ink selector. Actual all-18-scene measurements and the advanced UI must still pass before completion or merge.
