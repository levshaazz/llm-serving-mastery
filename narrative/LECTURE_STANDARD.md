# Lecture authoring standard

This is the binding definition of done for every new or substantially revised lecture.

## 1. Design before markup

Create `narrative/LNN.md` before editing deck fragments. The beat sheet must state:

1. the opening production incident or decision;
2. the learner's starting mental model;
3. the conceptual turns that change that model;
4. the worked examples and the numbers they use;
5. the interactive diagrams and the decision each one lets the learner explore;
6. the closing payoff and the bridge to the next topic;
7. primary sources for unstable or technical claims.

A full lecture targets **80–100 slides**. This is a depth target, not permission to split one idea into
many thin slides. Material that cannot fit the live session stays in the deck and is explicitly marked
for self-study; the course keeps all 15 topics.

## 2. Canonical visual grammar

Lecture 0 is the executable template. Reuse its shell, tokens, and native types: `title`, `agenda`,
`objectives`, `divider`, `definition`, `formula`, `two-col`, `table`, `quote`, `walkthrough`,
`misconception`, `pause`, `art-hero`, `refs`, and `final`. Reuse the existing `sequence`, `archflow`,
`budget`, and lab engines for interaction.

Hard rules:

- no lecture-specific stylesheet for layout;
- no ad-hoc high-level grid/card system that duplicates a native component;
- no inline positioning except declarative coordinates required by a documented diagram engine;
- no text smaller than the template tokens and no “fix” based on shrinking the whole slide;
- a missing visual pattern is added to the shared template only when it will be reusable;
- every shared pattern ships with documentation, a minimal fixture, light/dark coverage, print behavior,
  keyboard behavior when interactive, and a structural/render gate.

## 3. Depth and evidence

Each lecture must contain:

- a concrete end-to-end system boundary and at least three fully worked numerical examples;
- at least three interactive diagrams that expose a decision, trade-off, or changing state;
- at least two production failure stories or scenarios with detection and mitigation;
- explicit assumptions, units, denominators, and percentile scope for every performance number;
- primary-source citations for APIs, algorithms, product behavior, and time-sensitive claims;
- a “what this model omits” statement for every simplifying analytical model;
- a measurement contract and an actionable learner deliverable.

Generic claims such as “latency matters” are not teaching. Show a trace, a queue, a calculation, a
request payload, a metric definition, or an experiment that makes the claim falsifiable.

## 4. Interactive diagrams

Interactions are course assets, not one-off decorations. Prefer an existing engine. If none fits, add a
reusable widget with deterministic logic separated from presentation, a documented mount contract,
keyboard controls, reduced-motion behavior, reset behavior, a blank-mount failure check, and a rendered
fixture. The same widget should be reusable in the deck and a future Playground/Book surface.

## 5. Generated artwork and the mascot

Use the built-in image-generation workflow for narrative scenes, the mascot, and other raster artwork.
Do not approximate mascot scenes with improvised CSS drawings or generic stock imagery.

- `_research/mascots.py` is the locked character bible.
- Serega wears exactly one deep forest-green Tatar tübetey and never a chef's toque.
- The hero and final narrative plates include Serega; across narrative plates, he appears in at least
  the ratio enforced by `_research/check_images.py`.
- Store lossless masters under `_research/masters/LNN/`; publish optimized WebP under
  `Lectures/assets/img/LNN/`; never optimize a master in place.
- Every brief records the use case, scene, composition, constraints, and avoid list. Avoid embedded text
  unless the image itself is explicitly about typography.

## 6. Guardrail ratchet

Every observed defect is evidence that the checks are incomplete. For clipping, overlap, empty widgets,
wrong component structure, unreadable type, broken deep links, missing assets, bad theme contrast, or
incorrect step states:

1. capture the smallest reproducible fixture or selector;
2. make the check fail on the broken version;
3. repair the component/content;
4. make the check pass;
5. keep the fixture and check permanently.

Never weaken a guardrail merely to make a deck pass. If an exception is real, encode it narrowly and
document why it is safe.

## 7. Verification and definition of done

Before publication:

1. assemble the deck and run `npm run check`;
2. run the production build;
3. render every slide at 1920×1080 in light and dark themes;
4. inspect every slide—not a sample—and every step of interactive slides;
5. inspect overview, presenter notes, print/handout behavior, keyboard navigation, and reduced motion;
6. verify agenda links and all external citations;
7. record any newly discovered defect as a permanent guardrail.

The deck is done only when the content, interactions, and rendered result all pass review.
