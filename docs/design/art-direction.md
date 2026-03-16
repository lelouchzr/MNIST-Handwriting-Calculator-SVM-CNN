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

## Responsive inspection panel

The later inspection change uses two fresh generated references:
`inspector-desktop-reference.png` and `inspector-mobile-reference.png`. The mobile
reference was generated separately rather than cropped from desktop.

The desktop reference gives the drawing about two thirds of the screen and the
inspector one third, separated by a straight vertical rule. Its compact header,
close control, symbol navigation and three equal tabs establish the hierarchy.
The implementation uses a 400–480 px dock, 20 px internal gutters, 44 px controls
and its own scrolling content area. The working area reserves the dock width;
calculation and history continue below the drawing while inspection is open.

The mobile reference keeps the same type, colors and tab treatment in a bottom
panel above a subdued backdrop. The implementation retains the existing square
corners and uses up to 90dvh with safe-area padding. The header and navigation stay
visible while details scroll. Short landscape screens use a compact header.

The references are layout guides, not classifier evidence: the implementation
keeps real input pixels, measured scores and signed masking legends. It does not
copy the reference's glowing pixel treatment or its inaccurate influence wording.
The existing navigation, English copy and result behavior remain authoritative.

Base UI Dialog supplies the interaction shell: a non-modal dock at 1100 px and
above, a modal panel below that breakpoint, with dismissal, scroll locking and
focus handling. Base UI Tabs replaces both custom keyboard-navigation handlers.
The selected symbol and active tab survive breakpoint changes. Reduced-motion
preferences disable panel and backdrop transitions. CSS defines all visual styles;
no Tailwind or additional visual theme is required.

Editing the drawing leaves the dock open with a recognition-needed state. This
keeps canvas geometry stable under an active pointer, unmounts obsolete detail
views and aborts their pending explanation requests. The next recognition selects
the first new symbol. Closing the dock returns the normal working layout.

## Algorithm-demo copy cleanup

The UI is a lightweight companion to the recognition algorithms. The visible
introduction, slogans, help dialog and shortcut, footer, repeated editing advice
and empty-state onboarding have been removed. The working controls, segmentation,
class scores, evaluation metrics and masking explanations remain. Calibration
labels and real error messages stay visible where needed to interpret the models.
