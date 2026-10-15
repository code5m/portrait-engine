# Research 013: Structural Identity, Not a Shared Puppet Face

Status: ENGINEERING EXPERIMENT / ART_UNVERIFIED. Parent: Research 012, PR #7.

## Hypothesis

Three identity records currently give different landmark coordinates, but share one elliptic silhouette and near-identical organ geometry. Numeric uniqueness is not visual identity. The simplest falsifiable correction is a **continuous perimeter** with independent skull, malar, and mandibular station widths, and coupled proportions for eyes, eyebrows, nose and mouth.

R013 computes CSS `clip-path: polygon(...)` using 51 samples per left/right contour, smoothly interpolating at fixed facial heights. CSS still paints every pixel. The proposal is not a medical mesh, and does not hide a bitmap, image model, SVG or Canvas.

## Experiment controls

- Old: `standalone.html` (unchanged default, before switching).
- Candidate: `standalone.html?r013=anatomy`.
- Preserve `?r012=form`, R005–R010 experimental routes, v1/v2 character JSON.
- Render two identity IDs, two light modes, baseline and candidate: 8 browser screenshots.
- Structural contract: contour must vary with jaw and cheek DNA, but remain the *same across changes in light*; lighting variables change with light, not identity.
- If pixel differences are present but both versions still look like mannequins, the result is **NOT** aesthetic success.

## Criteria for genuine improvement

Reviewers must judge whether (a) silhouettes actually differ, (b) eyes and nose look integrated with the same human structure, (c) identities survive side/front lighting, and (d) head no longer looks like a plastic doll. Independent evaluation is required before promoting a candidate. No automatic screenshot difference, fingerprint uniqueness, or CI pass can establish realism.

## Known debts

Current CSS hair masses and frontal template may still dominate the identity. `clip-path` samples are an approximation of head silhouette, not a continuous 3D volume. The old orbit/pupil coordinates and jaw masses remain stylized. Should R013 fail visual inspection, record that outcome and redesign specific shapes rather than merely intensify contrast.
