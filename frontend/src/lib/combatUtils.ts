export function addTokenToInitiative(order: string[], tokenId: string): string[] {
  if (!tokenId) return order;
  if (order.includes(tokenId)) return order;
  return [...order, tokenId];
}
