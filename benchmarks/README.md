# Optional benchmarks

Application CI runs `uv run pytest` against `tests/`. The randomized corpora and
SVM/CNN evaluations live here and run only when requested.

| Command | Purpose | Output |
| --- | --- | --- |
| `uv run pytest benchmarks -q` | Replay synthetic corpora, coordinate variants and paired-result guards | Terminal summary |
| `uv run python -m benchmarks.recognition --stage before` | Evaluate the original models and segmentation | `.cache/benchmarks/algorithm_before.json` |
| `uv run python -m benchmarks.recognition --stage after` | Evaluate current models on identical inputs | `.cache/benchmarks/algorithm_after.json` |
| `uv run python -m benchmarks.junctions` | Reproduce the interrupted-junction comparison | `.cache/benchmarks/segmentation_fix.json` |
| `uv run python -m benchmarks.pixel_gaps` | Reproduce the latest fix and independent holdout | `.cache/benchmarks/pixel_gap_fix.json` |

Run commands from the repository root after `uv sync --locked`. Recognition
benchmarks need `.cache/mnist.npz`, downloaded and checksum-verified by the training
scripts. Both models are bundled. Default evaluation leaves their bytes unchanged;
use recognition's `--update-metadata` only to publish scores after retraining.

[results.json](results.json) is the small checked-in snapshot: sample counts,
accuracy, paired regression counts, input fingerprints and model hashes. Detailed
predictions are generated into ignored `.cache/benchmarks/` instead of committed.
The scripts retain per-case guards, so aggregate improvements cannot hide a lost
correct prediction or an increased edit distance.

| Stable Git reference | Comparison version |
| --- | --- |
| `benchmark-v1` | Original SVM/CNN and x-range segmentation |
| `benchmark-v2` | Augmented models before junction repair |
| `benchmark-junctions` | Repaired junctions before the pixel-gap guard |

Use a full checkout with these tags (`git fetch --tags`). Archived inputs and
reports are read from those versions with `git show`; current reports need not
retain copies of every intermediate experiment.

Final expression seeds are 90210 (240 cases), 314159/271828/161803 (600 each), and
235711/101317/192323 (600 each). Geometry controls use separate generators and
seeds. Once a holdout has been inspected, it becomes regression coverage. Further
algorithm tuning needs a fresh holdout. Synthetic strokes are not validation on
new human-written operators; MNIST is the held-out human-digit evaluation.
