# Cryptography and End-to-End Encryption Documentation

## Overview

This voting system implements comprehensive end-to-end encryption using modern cryptographic standards to ensure ballot secrecy, voter privacy, and election integrity. The system employs client-side encryption, mixnet anonymization, and secure key management.

## Cryptographic Architecture

### 1. Asymmetric Encryption (RSA-OAEP)

The system uses RSA with Optimal Asymmetric Encryption Padding (OAEP) for ballot encryption:

- **Key Size**: 2048-bit RSA keys
- **Padding Scheme**: OAEP with MGF1 and SHA-256
- **Hash Algorithm**: SHA-256
- **Public Exponent**: 65537 (standard)

#### Key Generation Process
```python
# From backend/voting/crypto_utils.py
def generate_rsa_keypair_pem() -> Tuple[str, str]:
    private_key = rsa.generate_private_key(
        public_exponent=65537, 
        key_size=2048
    )
    # Returns (public_key_pem, private_key_pem)
```

### 2. End-to-End Encryption Flow

#### Step 1: Key Distribution
- Each election generates a unique RSA key pair
- Public key is exposed via API for client-side encryption
- Private key remains securely stored on the server

#### Step 2: Client-Side Ballot Encryption
```javascript
// From frontend/src/utils/crypto.js
export const encryptBallot = async ({ publicKeyPem, candidateId }) => {
  // Import RSA public key using Web Crypto API
  const cryptoKey = await window.crypto.subtle.importKey(
    "spki", keyBuffer, {
      name: "RSA-OAEP",
      hash: "SHA-256",
    }, false, ["encrypt"]
  );

  // Create ballot payload
  const payload = JSON.stringify({
    candidate_id: Number(candidateId),
    ts: new Date().toISOString(), // Timestamp for replay protection
  });

  // Encrypt using RSA-OAEP
  const encrypted = await window.crypto.subtle.encrypt({
    name: "RSA-OAEP",
  }, cryptoKey, new TextEncoder().encode(payload));

  return btoa(binary); // Base64 encoded ciphertext
};
```

#### Step 3: Secure Transmission
- Encrypted ballots are transmitted over HTTPS
- Ballots never leave the client in plaintext form
- Server receives only RSA-OAEP encrypted ciphertext

#### Step 4: Mixnet Processing
```python
# From backend/voting/mixnet.py
def flush_mixed_votes(election_id: int) -> int:
    # 1. Collect queued encrypted votes
    batch = _mix_queue[election_id][:]
    
    # 2. Random shuffle for anonymization
    random.SystemRandom().shuffle(batch)
    
    # 3. Batch decrypt with private key
    for item in batch:
        payload = json.loads(decrypt_ballot(
            election.private_key_pem, 
            item["encrypted_ballot"]
        ))
        candidate_id = int(payload["candidate_id"])
        # Store decrypted vote
```

## Mixnet Anonymization System

### Purpose
The mixnet provides voter anonymity by:
1. **Batching**: Collecting multiple encrypted votes
2. **Shuffling**: Randomizing order to break timing correlations
3. **Batch Decryption**: Processing votes together to obscure individual choices

### Implementation Details

#### Threading-Safe Queue
```python
_queue_lock = threading.Lock()
_mix_queue: Dict[int, List[dict]] = defaultdict(list)

def queue_encrypted_vote(*, election: Election, voter_hash: str, encrypted_ballot: str):
    with _queue_lock:
        _mix_queue[election.id].append({
            "voter_hash": voter_hash,
            "encrypted_ballot": encrypted_ballot,
        })
```

#### Cryptographic Security Properties

**Confidentiality**: 
- RSA-OAEP provides semantic security
- Only election private key can decrypt ballots
- Ballots encrypted before network transmission

**Integrity**:
- OAEP padding prevents chosen ciphertext attacks
- Timestamps prevent replay attacks
- Voter hashing prevents double voting

**Anonymity**:
- Mixnet shuffling breaks voter-ballot linkage
- Batch processing obscures timing information
- Encrypted ballots stored until mixnet processing

## Security Considerations

### 1. Key Management
- **Private Key Storage**: Server-side, database encrypted
- **Public Key Distribution**: Via API, read-only access
- **Key Rotation**: Per-election generation ensures forward secrecy

### 2. Threat Mitigations
- **Man-in-the-Middle**: Prevented by client-side encryption
- **Server Compromise**: Limited by encrypted ballot storage
- **Replay Attacks**: Prevented by timestamp validation
- **Coercion Resistance**: Enhanced by mixnet anonymization

### 3. Cryptographic Standards Compliance
- **FIPS 186-4**: RSA key generation standards
- **PKCS#1 v2.2**: OAEP padding specification
- **NIST SP 800-56B**: Asymmetric key management

## Technical Implementation

### Frontend Cryptography (Web Crypto API)
```javascript
// Browser-native cryptographic operations
window.crypto.subtle.importKey()  // Key import
window.crypto.subtle.encrypt()   // RSA-OAEP encryption
```

### Backend Cryptography (Python Cryptography)
```python
# Production-grade cryptographic library
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
```

### Data Flow Security
1. **Client**: Encrypt ballot with election public key
2. **Transit**: HTTPS + encrypted payload
3. **Server**: Queue encrypted ballot
4. **Mixnet**: Shuffle and batch decrypt
5. **Storage**: Decrypted votes with anonymized metadata

## Compliance and Auditing

### Cryptographic Audit Trail
- All encrypted ballots logged for audit
- Mixnet processing records maintained
- Key generation events tracked

### Verification Mechanisms
- Vote receipt generation for voters
- Admin audit logs for mixnet operations
- Cryptographic hash verification for integrity

## Future Enhancements

### Potential Cryptographic Upgrades
1. **Homomorphic Encryption**: For tallying without decryption
2. **Zero-Knowledge Proofs**: For eligibility verification
3. **Threshold Cryptography**: Distributed key management
4. **Post-Quantum Algorithms**: Future-proofing against quantum attacks

### Privacy Enhancements
1. **Multi-Server Mixnet**: Distributed anonymization
2. **Timing Obfuscation**: Additional privacy layers
3. **Deniable Encryption**: Coercion resistance

## Security Summary

This voting system provides:
- **End-to-End Encryption**: Ballots encrypted client-side
- **Voter Anonymity**: Mixnet shuffling and batch processing
- **Cryptographic Integrity**: RSA-OAEP with SHA-256
- **Auditability**: Complete cryptographic trail
- **Scalability**: Efficient batch processing

The implementation follows industry best practices and cryptographic standards to ensure a secure, private, and verifiable electronic voting system.
