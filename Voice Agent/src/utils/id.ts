const ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
const ID_LENGTH = 10

export const createId = (prefix: string): string => `${prefix}_${createRandomId()}`

function createRandomId(): string {
  const bytes = new Uint8Array(ID_LENGTH)
  crypto.getRandomValues(bytes)

  return Array.from(bytes, (byte) => ID_ALPHABET[byte % ID_ALPHABET.length]).join("")
}
