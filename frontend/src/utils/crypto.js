const pemToArrayBuffer = (pem) => {
  const b64 = pem.replace(/-----BEGIN PUBLIC KEY-----/g, "").replace(/-----END PUBLIC KEY-----/g, "").replace(/\s/g, "");
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
};

export const encryptBallot = async ({ publicKeyPem, candidateId }) => {
  const keyBuffer = pemToArrayBuffer(publicKeyPem);
  const cryptoKey = await window.crypto.subtle.importKey(
    "spki",
    keyBuffer,
    {
      name: "RSA-OAEP",
      hash: "SHA-256",
    },
    false,
    ["encrypt"]
  );

  const payload = JSON.stringify({
    candidate_id: Number(candidateId),
    ts: new Date().toISOString(),
  });
  const encrypted = await window.crypto.subtle.encrypt(
    {
      name: "RSA-OAEP",
    },
    cryptoKey,
    new TextEncoder().encode(payload)
  );

  const bytes = new Uint8Array(encrypted);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};
