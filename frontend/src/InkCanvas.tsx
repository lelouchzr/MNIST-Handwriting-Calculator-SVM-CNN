import { useEffect, useRef } from "react";
import type { PointerEvent } from "react";
import type { Point, Stroke } from "./types";

type Props = { strokes: Stroke[]; onChange: (strokes: Stroke[]) => void };
export const WIDTH = 1000;
export const HEIGHT = 360;

function paint(context: CanvasRenderingContext2D, stroke: Stroke) {
  if (!stroke.length) return;
  context.strokeStyle = "#20211f";
  context.fillStyle = "#20211f";
  context.lineWidth = 6;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();
  context.moveTo(...stroke[0]);
  for (const point of stroke.slice(1)) context.lineTo(...point);
  context.stroke();
  if (stroke.length === 1) {
    context.beginPath();
    context.arc(...stroke[0], 3, 0, Math.PI * 2);
    context.fill();
  }
}

export function InkCanvas({ strokes, onChange }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const current = useRef<Stroke>([]);
  const pointer = useRef<number | null>(null);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const redraw = () => {
      // Match CSS dimensions so phone strokes retain their original aspect ratio.
      const rect = element.getBoundingClientRect();
      element.height = Math.round(
        (WIDTH * rect.height) / Math.max(1, rect.width),
      );
      const context = element.getContext("2d");
      if (!context) return;
      for (const stroke of strokesRef.current) paint(context, stroke);
    };
    const observer = new ResizeObserver(redraw);
    observer.observe(element);
    redraw();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext("2d");
    if (!element || !context) return;
    context.clearRect(0, 0, WIDTH, element.height);
    for (const stroke of strokes) paint(context, stroke);
  }, [strokes]);

  function point(event: PointerEvent<HTMLCanvasElement>): Point {
    const rect = event.currentTarget.getBoundingClientRect();
    return [
      Math.max(
        0,
        Math.min(WIDTH, ((event.clientX - rect.left) * WIDTH) / rect.width),
      ),
      Math.max(
        0,
        Math.min(1000, ((event.clientY - rect.top) * WIDTH) / rect.width),
      ),
    ];
  }

  function start(event: PointerEvent<HTMLCanvasElement>) {
    if (pointer.current !== null || event.button !== 0) return;
    if (strokesRef.current.length >= 256) return;
    pointer.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    current.current = [point(event)];
    const context = canvas.current?.getContext("2d");
    if (context) paint(context, current.current);
  }

  function move(event: PointerEvent<HTMLCanvasElement>) {
    if (pointer.current !== event.pointerId || current.current.length >= 3500)
      return;
    const next = point(event);
    const previous = current.current.at(-1)!;
    if (Math.hypot(next[0] - previous[0], next[1] - previous[1]) < 1.2) return;
    current.current.push(next);
    const context = canvas.current?.getContext("2d");
    if (context) paint(context, [previous, next]);
  }

  function finish(event: PointerEvent<HTMLCanvasElement>) {
    if (pointer.current !== event.pointerId) return;
    const completed = current.current;
    pointer.current = null;
    current.current = [];
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (completed.length) onChange([...strokesRef.current, completed]);
  }

  return (
    <div className="paper">
      <canvas
        ref={canvas}
        width={WIDTH}
        height={HEIGHT}
        aria-label="Handwriting canvas"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={finish}
        onPointerCancel={finish}
        onLostPointerCapture={finish}
      />
      {!strokes.length && (
        <div className="paper-placeholder" aria-hidden="true">
          <span>Write here.</span>
          <p>or load an example to get started</p>
        </div>
      )}
      <span className="paper-mark" aria-hidden="true">
        01
      </span>
    </div>
  );
}

export function downloadInk(strokes: Stroke[]): void {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = Math.max(
    HEIGHT,
    ...strokes.flatMap((stroke) => stroke.map((point) => point[1] + 24)),
  );
  const context = canvas.getContext("2d");
  if (!context) return;
  context.fillStyle = "white";
  context.fillRect(0, 0, canvas.width, canvas.height);
  for (const stroke of strokes) paint(context, stroke);
  const link = document.createElement("a");
  link.download = "inkcalc-drawing.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
}
