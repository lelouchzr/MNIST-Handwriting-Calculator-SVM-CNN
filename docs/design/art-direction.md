# InkCalc interface redesign

## Image-first source

The two reference images were generated with the built-in image generation tool
before frontend implementation, following `image-taste-frontend`.

- `workspace-desktop-reference.png`: the complete working screen at readable scale.
- `workspace-mobile-reference.png`: a fresh portrait composition, not a crop.

The previous UI used a large promotional introduction, small muted labels and
several similarly rounded containers. The new composition is a working calculator:
the drawing, symbol review, expression and result establish the reading order.

## Analysis before implementation

**Desktop.** The reference uses roughly 60 px outer gutters at 1536 px, a thin
header divider, a single-line heavy heading, and a two-column composition. The
left drawing/review area is a little over twice the width of the right result.
Toolbar, paper and action row share one rectangular border. The paper has faint
square ruling, a small yellow folio, and no surrounding shadow. A thin top rule
introduces the symbol review. Character tiles stack handwriting, prediction and
score vertically. The expression is large monospace beside a black calculation
button. The yellow recognition button is the other strong action. The result uses
an uninterrupted pale yellow field, large black numerals, and a rule separating
the calculation steps. History is a flat list of rows rather than nested cards.

**Mobile.** The wordmark and utility controls occupy the first line; navigation
moves to its own line. The compact heading remains one line. The canvas stays
large enough to draw, using uniform logical scaling. Four symbol tiles fit in
one horizontal row. The expression keeps its calculation action adjacent. The
result follows the expression and becomes a horizontal number/label composition.
History follows the result in the document flow. Controls need at least 44 px
touch targets even where the generated reference depicts smaller keys.

**Readable source copy.** “À main levée.”, “Écrivez. Vérifiez. Calculez.”,
“Reconnaître”, “Lecture”, “Expression”, “Calculer”, “Résultat”, “Derniers calculs”,
and “Calcul local · Aucun dessin conservé”. The real UI displays actual data and
empty/error states; the mockups' history examples are not seeded into storage.

## Extracted system

- Background: `#f2f1ed`; paper: `#ffffff`; text/ink: `#20211f`.
- Secondary text: `#686961`; structural borders: `#cecec7`.
- Accent: `#f4ca48`; result background: `#f5edcc`.
- DM Sans, weights 400–800, for interface and wordmark; IBM Plex Mono for math.
- Desktop heading around 56–62 px, wordmark 40 px, section headings 20 px,
  body 14–16 px, secondary labels 12–13 px, result around 120–148 px.
- Gutters 40–48 px desktop / 16 px mobile; column gap 28 px.
- Crisp rectangular geometry; corner radius 0–3 px; no gradients or shadows.
- Signature elements: vertical rhythm lines, off-grid editorial heading,
  product UI panel stack, oversized result number.
- Motion cues: short cinematic fade-through for results and controlled expansion
  for history. The final history expands immediately to avoid scroll movement;
  reduced motion also disables the result fade. The pen stays immediate.

## Generation prompts

Desktop prompt: create a single front-on French handwriting-calculator working
screen, Swiss notebook/industrial-calculator direction, off-white, near-black and
signal yellow; slim header; “À main levée.”; bordered toolbar/paper/action surface;
square grid and handwritten 12 + 7; compact prediction tiles; editable monospace
expression; pale yellow result with 19 and explicit arithmetic; flat history;
no marketing sections, card collection, gradients, shadows, fake metrics or badges.

Mobile prompt: generate a new high-resolution portrait version of that same
system, with two-line header/navigation, 16 px-equivalent gutters, usable canvas,
four character tiles in one row, adjacent expression/action, seven operator keys,
horizontal result band and history below. Preserve readable text and touch spacing;
do not shrink the desktop composition into a phone image.
