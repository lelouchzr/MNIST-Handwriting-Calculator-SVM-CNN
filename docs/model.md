# Model card

## Scope and provenance

InkCalc recognizes isolated handwritten digits and arithmetic symbols on one line.
It does not implement general mathematical OCR, fractions, superscripts, touching
characters or multi-line expressions.

The implementation, original pen paths and synthetic operator generator are written
for InkCalc. Inspiration: [Youjia Zhang's calculator](https://github.com/YoujiaZhang/MNIST-Calculator-Handwriting-recognition).
No upstream notebook code, images, extended dataset archive or weights are included.

Digits use [MNIST](https://yann.lecun.com/exdb/mnist/), credited to Yann LeCun,
Corinna Cortes and Christopher J. C. Burges, through the
[Keras mirror](https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz).
The archive checksum is verified before use. `scripts/training_data.py` generates
operators using original drawing routines and supplies the shared data to both trainers.

## Shared input and models

1. Group pen strokes by horizontal overlap/proximity and rasterize each group.
2. Crop to the ink, fit within 20 × 20 pixels, and center by mass on a 28 × 28 frame.
3. **SVM:** extract 324 HOG features (9 orientations, 7 × 7 cells, 2 × 2 blocks),
   then predict with a linear SVM and three-fold sigmoid calibration.
4. **CNN:** use the same normalized pixels directly with Conv(1→12, 3 × 3), ReLU,
   max-pool, Conv(12→24, 3 × 3), ReLU, max-pool, a 64-unit fully connected layer,
   dropout 0.2 and 16 logits. This original network has 79,104 parameters.

Marks smaller than twelve logical pixels use a geometric decimal-point rule.
Neither model supplies a probability or sensitivity map for those marks. The
canvas has 1,000 logical pixels across and preserves aspect ratio on phones.

## Recorded evaluation

Both models use the same 20,000 MNIST training digits and 3,900 generated operators
(650 per class), with seed 42. The CNN trains on CPU for eight fixed epochs with
Adam (learning rate 0.001), batch size 128. Held-out tests are evaluated only after
training and do not select an epoch or checkpoint.

| Evaluation set | Samples | SVM accuracy | CNN accuracy |
| --- | ---: | ---: | ---: |
| First 2,000 MNIST test digits, all classes eligible | 2,000 | 95.65% | 96.65% |
| Fresh synthetic operators, all classes eligible | 600 | 99.33% | 99.50% |

The ordered training and test input arrays, including labels, have matching SHA-256
fingerprints stored in `models/metrics.json`, `models/cnn_metrics.json` and
`models/comparison.json`. Agreement is 95.35% on test digits and 99.50% on synthetic
operators. Model accuracy and agreement are different quantities.

These are symbol classification results, not complete-expression accuracy. The
operator evaluation uses the same synthetic drawing family as training and does not
validate human-written operators. No real operator or segmentation benchmark is included.

SVM scores are calibrated probabilities. CNN scores are **uncalibrated softmax
estimates**. A larger confidence number does not establish which model is better;
use held-out accuracy and inspect actual disagreements. Neither model is guaranteed
correct on drawings outside its training distribution.

## Reproduce

```sh
uv sync --locked
uv run python scripts/train.py --digits 20000
uv run python scripts/train_cnn.py --digits 20000 --epochs 8
uv run pytest
```

The first training run downloads about 11 MB of MNIST data into ignored `.cache/`.
Both trained artifacts are committed, so normal startup needs no dataset or weight
download. PyTorch uses a dedicated CPU package index. GPU support is not required.
The seed, package lock and CPU execution aid reproducibility; floating-point behavior
can still vary across platforms.

Only load the trusted repository artifacts. The SVM uses joblib. The CNN stores a
state dictionary and primitive metadata, loaded on CPU with
[`torch.load(..., weights_only=True)`](https://docs.pytorch.org/docs/stable/generated/torch.load.html).
No model upload endpoint is provided. Missing/corrupt models are marked unavailable;
a request for an unavailable model returns 503 rather than silently using another.

## Recognition and inspection API

`POST /api/recognize` accepts bounded strokes plus `model: "svm" | "cnn" | "compare"`
(default `svm`). It returns the raster crop, normalized input preview, original
prediction, all 16 scores, scoring method and per-model outputs. Compare segments
and normalizes once, then passes the same pixels to both models. Decimal marks are
excluded from the agreement count.

Compare initially uses the SVM expression. Explicitly selecting the CNN expression
updates editable labels and displayed source scores, while preserving both original
model outputs. Manual corrections also leave the recorded predictions unchanged.

`POST /api/explain` accepts the same model selection and a zero-based `symbol_index`.
Each classifier explains its own top class; no client-supplied label chooses a target.
The normalized floating-point frame stays fixed while each overlapping 5 × 5 window
is set to zero. The SVM recomputes HOG without recentering; the CNN consumes the masked
pixels directly in bounded inference batches of 64, with evaluation mode and no gradients.

For class c, a window's signed effect is `score(c | original) - score(c | masked)`.
Each displayed pixel averages the effects of all covering windows, including borders.
There are 576 windows per model. Zero-effect maps remain zero without normalization errors.

Yellow means masking lowered the class score; hatching means it raised it. Single-model
maps use a per-symbol color scale. Compare uses one shared magnitude scale across both
maps, with target class and original score labelled separately. Values are percentage-point
changes in different score functions, not directly comparable measures of correctness.
This is sensitivity to perturbations, not causal attribution. Masking can create inputs
outside the training distribution. PNG previews quantize to eight bits; model inference
and sensitivity retain the normalized float values.

## Demonstration example

The "Synthetic example" action uses an original jittered pen path selected to
illustrate a disagreement in the committed models. It is explicitly a synthetic demo,
not an accuracy benchmark or an additional held-out evaluation set. Predictions and
maps are always computed by the actual models. Retrained models may agree on this example.

## Limits and privacy

- Leave space between characters; overlapping horizontal bounds can merge symbols.
- Use one-line mouse, finger or stylus input; photographs are not supported.
- Arithmetic is bounded to 256 input characters and magnitude 10¹⁵; display rounds
  to 12 decimals. Parentheses, precedence, negatives and decimal commas are supported.
- Only 20 calculation results are stored in browser history. Drawings and model
  explanations stay in transient memory; closing inspection or changing the drawing
  discards its explanation cache.
- In the documented local setup, handwriting is sent only to the local Python API.
  Hosting that API elsewhere changes where handwriting is processed.
