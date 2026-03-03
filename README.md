# InkCalc

A handwriting-first math workspace. Draw a single-line expression, inspect each
prediction, correct ambiguous symbols, and calculate without running arbitrary code.

Python handles image preparation, classification and arithmetic. React handles the
canvas, editable predictions and browser-local calculation history.

## Development

Requires Python 3.11+ (3.12 recommended), Node.js 22+, and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run uvicorn inkcalc.api:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the Vite URL. Its `/api` proxy connects to the local Python service.

## Inspiration

Inspired by [Youjia Zhang's MNIST handwriting calculator](https://github.com/YoujiaZhang/MNIST-Calculator-Handwriting-recognition).
InkCalc is an independent implementation: no notebook code, weights, images or
extended-symbol dataset are copied from that repository. See `docs/model.md` for
training data, evaluation and limitations.
