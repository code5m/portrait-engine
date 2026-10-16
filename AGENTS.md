# Portrait Engine — research continuation contract

最高原则：**研究的是通用生成能力，人物作品是验证手段，写实质量是核心衡量标准。**

Before changing code or reporting progress, read:
1. `docs/RESEARCH-CONSTITUTION.md` — rendering constraints and evidence boundaries.
2. `research/sketch/stages.json` and `docs/sketch/STATUS.md` — actual completed/current/next stages.
3. The active report under `docs/sketch/` and its evidence, if present.
4. The current GitHub main SHA, PR state and same-commit CI. Do not rely on an earlier chat's green status.

## Record each completed stage in the same PR

A stage closure must update its report, machine-readable evidence (with source digest and real CI run), stages.json and STATUS.md together. `test/sketch-stages.test.mjs` rejects COMPLETE without evidence, and rejects S0 evidence when its implementation changes. Never mark COMPLETE merely because a plan, script or generated Git tree exists.

S0 calibrates reference tools and CSS shape/light transfer. It does NOT complete S1–S6 or prove human-portrait realism. Downloaded ICT geometry and generated working caches stay in ignored `test-results/` or `data/`. Explicit, checksum-bound copies of actual CSS captures and independent reference PNGs may be archived under `research/sketch/evidence/raw/` as read-only evaluation evidence; they are never textures, numerical compiler inputs or production assets. The workbench serves only its explicit static/API allowlist, not arbitrary archive paths. This durable-evidence exception does not relax the rendering-media or artistic-evidence rules in the research constitution. Keep production src/, styles/ and standalone.html unchanged unless a separately registered portrait experiment justifies changes.

Preserve failed experiments and disclose limitations. Engineering checks can permit merging opt-in research; they cannot create human observers or certify ART_PASS. Do not weaken tests to hide a failed experiment.

If interrupted, resume the exact next action in STATUS.md. Do not restart S0, invent prior results, or create a parallel roadmap. At every stage boundary store the evidence and decision in GitHub, not only the chat.
