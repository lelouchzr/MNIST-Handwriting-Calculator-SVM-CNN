# Model card

## Scope and provenance

Single-line handwritten digits and `+ - * / ( )`, with geometric decimal detection.
No general mathematical OCR, fractions, superscripts, multiline layout or reliable
separation of touching characters.

InkCalc's code, pen paths and synthetic drawing routines are independent. The project
was inspired by [Youjia Zhang's calculator](https://github.com/YoujiaZhang/MNIST-Calculator-Handwriting-recognition);
no upstream notebooks, images, extended dataset archive or weights are included.

[MNIST](https://yann.lecun.com/exdb/mnist/), by Yann LeCun, Corinna Cortes and
Christopher J. C. Burges, is fetched from the
[Keras mirror](https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz).
Archive SHA-256: `731c5ac602752760c8e48fbffcf8c3b850d9dc2a2aedcf2cc48468fc17b673d1`.

## Segmentation and input

| Step | Implementation |
| --- | --- |
| Initial groups | Rasterize thin centerlines and label 8-connected components. Overlapping x ranges alone no longer merge adjacent symbols. |
| Gap repair | Join aligned detached pieces and compatible outward endpoint tangents within bounded gaps. Rebuild the stem, then repair a horizontal junction only with a unique transverse endpoint in the gap, within the 3 px pen radius. Preserve separate minus signs. |
| Division | Combine an aligned small dot above and below a horizontal bar; one nearby decimal is insufficient. |
| Decimal | A compact mark below 12 logical pixels, excluding elongated short lines, bypasses both classifiers. |
| Raster | Supersample at 3× with rounded endpoints, then downsample. |
| Normalize | Crop ink, fit within 20 × 20, center by mass on a 28 × 28 frame. |

Canvas coordinates span 1,000 logical pixels. Segmentation uses geometry and fixed
thresholds, not a learned detector. It preserves stroke-order independence. The
three known interrupted-stroke regressions are now fixed; one case still fails
in the fresh follow-up corpus described below.

## Classifiers and training

Both models receive identical normalized arrays and labels.

| Item | SVM | CNN |
| --- | --- | --- |
| Input | 324 HOG features: 9 orientations, 7 × 7 cells, 2 × 2 blocks | 28 × 28 grayscale pixels |
| Classifier | LinearSVC, C=2 | Conv(1→12, 3×3), ReLU, pool; Conv(12→24, 3×3), ReLU, pool; FC64, dropout 0.2, FC16 |
| Scores | Three-fold sigmoid-calibrated probabilities | Uncalibrated softmax |
| Fitting | Stratified group folds keep original and augmented variants together | Adam, lr 0.001, batch 128, StepLR at epoch 8 ×0.3 |
| Selection | Fixed settings | Best validation accuracy, epoch 11 of 12 |
| Validation accuracy, mixed 5,900 inputs | 97.32% | 98.61% |

The CNN has 79,104 parameters. CPU execution, seed 42 and the lockfile aid
reproducibility; floating-point results can vary across platforms.

| Shared dataset | Samples |
| --- | ---: |
| MNIST training originals | 40,000 |
| One affine variant per original | 40,000 |
| Procedural pen digits | 4,500 |
| Synthetic operators: legacy raster + pen paths | 7,200 |
| **Training total** | **91,700** |
| Separate validation: MNIST training split / pen digits / operators | 5,000 / 300 / 600 |

Affine augmentation adds rotation about ±9°, shear ±0.10, scale 0.94–1.06,
translation ±0.65 pixels and occasional dilation. Validation uses seed 7301 and
unused MNIST training indices. No official MNIST test digit enters training or
checkpoint selection. Original/variant group IDs prevent calibration leakage.

## Initial frozen before/after protocol

Baseline revision: `200719072ee4fc0463abc31b89973fa0fb80c6b2`. The benchmark extracts
its recognition module and weight files with `git show`. HOG, normalization and CNN
architecture are unchanged, so both revisions use the same inference primitives.

Final seed: **90210**. Segmentation parameters were developed separately on seed
1701. These initial results were run after training without checkpoint selection
or threshold tuning on the final data. The three failures later became explicit
regression fixtures for the junction fix; this set is no longer an unseen test.

| Evaluation input | Samples | SVM before → after | CNN before → after |
| --- | ---: | ---: | ---: |
| Entire official MNIST test split | 10,000 | 96.82 → 97.37% | 97.53 → 98.84% |
| Procedural isolated pen digits | 1,000 | 98.90 → 100.00% | 98.40 → 100.00% |
| Procedural isolated operators | 1,200 | 99.67 → 99.83% | 95.08 → 99.75% |
| Exact procedural expressions | 240 | 62.08 → 98.33% | 58.75 → 98.75% |
| Expression character error rate | 960 characters | 35.625 → 0.729% | 38.125 → 0.729% |

Isolated classification allows all 16 classes. Expression accuracy compares the
entire recognized string, before arithmetic evaluation, without correction.
Character error rate uses Levenshtein edits divided by expected characters.

Each expression profile has 40 cases: spaced, tight, decimal, division, interrupted
and slanted. Expected boxes come from the known pen paths. Segmentation success
requires an identical ordered segment count and each box's IoU ≥ 0.5, after padding
bounds by three pixels to handle lines and points.

| Segmentation | Before | After |
| --- | ---: | ---: |
| Spaced / division / slanted | 120/120 | 120/120 |
| Tight | 0/40 | 40/40 |
| Decimal | 0/40 | 40/40 |
| Interrupted | 40/40 | 37/40 |
| Total | 160/240 | 237/240 |

This measures the combined update; it is not an ablation separating augmentation,
training volume, rasterization and grouping effects. Synthetic digits, operators
and expressions share a generator family with training. Their high scores do not
establish accuracy on new human-written operators or full expressions. MNIST tests
human digits only. The previous 2,000-digit headline used a different slice and
must not be compared directly with this 10,000-digit evaluation.

## Junction fix and fresh validation

The fix addresses interrupted horizontal feet whose vertical stem ends in the
missing section. A separate pass first rebuilds interrupted stems, then requires
aligned fragments and exactly one tall component ending transversely inside the
gap. It retains the original gap limits and requires contact within the pen radius.
No labels, case IDs or classifier confidence enter this geometric rule.

Compared with revision `cb7a7317305ddaa9d9a6de865787bf42740b0761`, both model files
are byte-identical. All isolated-symbol metrics and confusions reproduce exactly.

| Corpus | Cases | Segmentation before → after | Exact SVM before → after | Exact CNN before → after |
| --- | ---: | ---: | ---: | ---: |
| Existing regression corpus | 240 | 237 → 240 | 236 → 239 | 237 → 240 |
| Fresh expressions | 1,800 | 1,758 → 1,799 | 1,739 → 1,779 | 1,755 → 1,796 |
| Independent geometric controls | 800 | 646 → 800 | — | — |

Development uses the three saved failures and geometric probes with seed 424242.
Fresh expression seeds **314159, 271828, 161803** each produce 600 cases; independent
geometric controls use seed **515151**. They were evaluated after freezing the fix,
with no further algorithm tuning on their outcomes. The geometry generator does
not use the training digit templates: it covers top/bottom junctions, absent
contact, adjacent minuses, parallel neighbors, decimals, interior contact and
non-collinear fragments, with random scale, rotation, translation and stroke order.
Negative controls include enough clearance to avoid physically connected ink.

Paired checks reject any previously correct segmentation or exact prediction
becoming incorrect, any per-expression edit-distance increase, and any per-profile
character-error-rate increase. All checks pass. One fresh segmentation failure
remains; these synthetic results still do not validate new human handwriting.

Reproduce with the bundled weights and a checkout containing the previous release:
`uv run python scripts/validate_segmentation.py`. The report records input
fingerprints, model hashes, raw expression outcomes and every gained/lost case.
The initial reports remain historical records of the first upgrade.

## Reproduction and artifacts

Follow the training and benchmark commands in the [README](../README.md). A full
Git checkout must contain the baseline revision. Both weight files are committed;
normal startup needs no download. Only load trusted joblib artifacts. CNN loading
uses a state dictionary with `weights_only=True` on CPU. Missing or corrupt models
are marked unavailable; requests return 503 instead of silently switching models.

| Record | Location |
| --- | --- |
| Training / validation metadata and input hashes | `models/metrics.json`, `models/cnn_metrics.json` |
| Per-epoch loss and validation accuracy | `models/training_history.json` |
| Raw predictions, confusions, per-expression results | `models/algorithm_before.json`, `models/algorithm_after.json` |
| Before/after scores and per-profile segmentation | `models/algorithm_comparison.json` |
| Junction fix, fresh corpora and paired regression guards | `models/segmentation_fix.json` |
| Current SVM/CNN comparison | `models/comparison.json` |

Final input fingerprint:
`13f58a15e46182868b7abbd98c23f164303fdd07ccb5a18b7d1f513f4642d757`.
The benchmark refuses to compare mismatched protocols or input fingerprints.

## Inspection semantics

`POST /api/recognize` segments and normalizes once, then supplies the same pixels
to SVM and CNN in Compare mode. Choosing an expression source or manually correcting
a symbol preserves both original model predictions. Decimal rules have no class
probabilities and are excluded from classifier agreement.

`POST /api/explain` explains each model's own top class with 576 overlapping 5 × 5
zero masks on the fixed normalized input. Signed effect is
`score(original class | input) − score(original class | masked input)`; each pixel
averages effects from covering windows. Compare maps share one color scale.
This is local sensitivity, not causality or proof of correctness. Masked inputs
may be outside the training distribution. CNN confidence remains uncalibrated.
