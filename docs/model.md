# Model card

## Data and scope

Single-line digits and `+ - * / ( )`, plus geometric decimal detection. Touching
characters, multiline layout, fractions and superscripts remain unsupported.

Digits come from [MNIST](https://yann.lecun.com/exdb/mnist/), by Yann LeCun, Corinna
Cortes and Christopher J. C. Burges, through the
[Keras mirror](https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz).
SHA-256: `731c5ac602752760c8e48fbffcf8c3b850d9dc2a2aedcf2cc48468fc17b673d1`.

Code, pen paths and synthetic drawing routines are independent. The original
project reference was [Youjia Zhang's calculator](https://github.com/YoujiaZhang/MNIST-Calculator-Handwriting-recognition);
no upstream notebooks, images, extended dataset archive or weights are included.
The repository software is [MIT licensed](../LICENSE); MNIST retains its attribution.

## Recognition

| Stage | Method |
| --- | --- |
| Initial groups | Thin 8-connected centerlines, guarded by continuous horizontal support within the 3 px pen radius. |
| Gap repair | Aligned endpoint tangents; broken horizontal junctions require a unique transverse stem endpoint inside the gap. |
| Division | A horizontal bar with aligned small dots on both sides; one decimal is insufficient. |
| Decimal | Compact extent below 12 logical pixels; elongated minus signs stay classifiers' responsibility. |
| Input | Rasterize at 3×, crop ink, fit inside 20 × 20, center by mass on 28 × 28. |
| SVM | 324 HOG features, LinearSVC C=2, three-fold sigmoid calibration with grouped source variants. |
| CNN | Conv(1→12, 3×3), ReLU, pool; Conv(12→24, 3×3), ReLU, pool; FC64, dropout 0.2, FC16. 79,104 parameters. |

Canvas coordinates span 1,000 logical pixels. Segmentation uses fixed geometry,
independent of class labels and classifier confidence. Compare gives both models
identical normalized pixels. SVM probabilities are calibrated; CNN softmax scores
are uncalibrated, so comparing confidence alone does not establish superiority.

## Training

| Shared inputs | Samples |
| --- | ---: |
| MNIST training originals | 40,000 |
| One affine variant per original | 40,000 |
| Procedural pen digits | 4,500 |
| Generated operators | 7,200 |
| **Training total** | **91,700** |
| Separate validation: MNIST training split / pen digits / operators | 5,000 / 300 / 600 |

Seed 42; validation generation seed 7301. Affine augmentation uses about ±9°
rotation, shear ±0.10, scale 0.94–1.06, translation ±0.65 px and occasional dilation.
Originals and variants stay in the same SVM calibration fold. The CNN uses Adam
lr 0.001, batch 128, StepLR at epoch 8 ×0.3; epoch 11 of 12 has the best separate
validation accuracy. Official test digits never select a checkpoint.

## Evaluation and reproduction

The [compact results](../benchmarks/results.json) record the original and current
scores, sample counts, input fingerprints and model hashes. The
[benchmark guide](../benchmarks/README.md) provides optional commands and stable
version references. Full predictions are regenerated into ignored local logs.

| Held-out input | Samples | Current SVM | Current CNN |
| --- | ---: | ---: | ---: |
| Entire MNIST test split | 10,000 | 97.37% | 98.84% |
| Procedural pen operators | 1,200 | 99.83% | 99.75% |
| Latest independent expressions, exact string | 1,800 | 1,786/1,800 | 1,797/1,800 |

Isolated classification allows all 16 classes. Expressions are compared before
arithmetic evaluation or correction. Character error uses Levenshtein distance.
Segmentation requires the ordered symbol count and per-box IoU ≥ 0.5, with bounds
padded by 3 px for lines and points. The latest 1,800-expression holdout has all
segmentations correct and no paired regressions against the previous version.

Development failures became explicit fixtures; fresh seeds were evaluated after
freezing each fix. Later tuning requires another holdout. Procedural inputs share
a generator family with training and do not validate new human operators. MNIST
validates human digits only. Combined training/segmentation improvements are not
an ablation study. CPU seeds and the lockfile aid reproducibility, but floating
point behavior can vary across platforms.

## Artifacts and inspection

| Record | Location |
| --- | --- |
| Weights | `models/symbols.joblib`, `models/cnn.pt` |
| Training, validation and isolated-score metadata | `models/metrics.json`, `models/cnn_metrics.json`, `models/comparison.json` |
| CNN validation history | `models/training_history.json` |
| Benchmark summary and protocol | `benchmarks/results.json`, `benchmarks/README.md` |

Only load trusted joblib artifacts. CNN loading uses `weights_only=True` on CPU.
Missing models are unavailable and return 503 instead of silently switching.
Manual corrections and expression-source selection preserve original predictions.

Occlusion explains each model's own top class with 576 overlapping 5 × 5 zero
masks on fixed input. Each pixel averages `original score − masked score` over
covering windows. Compare maps share a scale; decimal rules have no probabilities
or map. This is local sensitivity, not causality or proof of correctness.
