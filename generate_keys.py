"""Generate a test PGP keypair and save to the keys/ directory."""
import os
import pgpy
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm

keys_dir = os.path.join(os.path.dirname(__file__), "keys")
os.makedirs(keys_dir, exist_ok=True)

# Generate key
key = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 2048)
uid = pgpy.PGPUID.new("PGP Function", comment="test key", email="pgp@test.local")
key.add_uid(uid, usage={KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
            hashes=[HashAlgorithm.SHA256],
            ciphers=[SymmetricKeyAlgorithm.AES256],
            compression=[CompressionAlgorithm.ZLIB])

# Save
with open(os.path.join(keys_dir, "public.asc"), "w") as f:
    f.write(str(key.pubkey))

with open(os.path.join(keys_dir, "private.asc"), "w") as f:
    f.write(str(key))

print(f"Keys written to {keys_dir}/")
print(f"  public.asc  — {key.pubkey.fingerprint}")
print(f"  private.asc — {key.fingerprint}")
