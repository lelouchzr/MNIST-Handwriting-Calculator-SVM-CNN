import type { ModelId, Token } from "./types";

export function tokensForModel(
  tokens: Token[],
  model: ModelId,
): Token[] | null {
  if (!tokens.every((token) => token.models[model])) return null;
  return tokens.map((token) => ({
    ...token,
    ...token.models[model]!,
    label: token.models[model]!.predicted_label,
    corrected: false,
  }));
}
