export function cn(...inputs) {
  // Simple className merger without external dependencies
  return inputs
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}
