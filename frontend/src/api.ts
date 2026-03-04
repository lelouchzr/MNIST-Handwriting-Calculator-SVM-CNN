export async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal ?? AbortSignal.timeout(15000),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Ce dessin est trop complexe. Réessayez avec moins de traits.",
    );
  }
  return data as T;
}
