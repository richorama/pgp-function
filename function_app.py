"""
Azure Function App for PGP encryption/decryption of Azure Blob Storage files.

Endpoints:
  POST /api/encrypt  — encrypts a blob, writes <original>.pgp
  POST /api/decrypt  — decrypts a .pgp blob, writes the file without .pgp extension

Body (JSON):
  { "blob_url": "https://<account>.blob.core.windows.net/<container>/<blob>" }

PGP keys are loaded from the "keys" directory next to this file:
  keys/public.asc   — used for encryption
  keys/private.asc  — used for decryption

If the private key is passphrase-protected, set PGP_PASSPHRASE in app settings.
"""

import json
import logging
import os
from urllib.parse import urlparse

import azure.functions as func
import pgpy
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
KEYS_DIR = os.path.join(os.path.dirname(__file__), "keys")


def _load_public_key():
    path = os.path.join(KEYS_DIR, "public.asc")
    key, _ = pgpy.PGPKey.from_file(path)
    return key


def _load_private_key():
    path = os.path.join(KEYS_DIR, "private.asc")
    key, _ = pgpy.PGPKey.from_file(path)
    passphrase = os.environ.get("PGP_PASSPHRASE")
    return key, passphrase


def _blob_service():
    conn = os.environ["BLOB_CONNECTION_STRING"]
    return BlobServiceClient.from_connection_string(conn)


def _parse_blob_url(blob_url: str):
    """Return (container, blob_path) from a full blob URL."""
    parsed = urlparse(blob_url)
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse container/blob from URL: {blob_url}")
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Encrypt
# ---------------------------------------------------------------------------
@app.route(route="encrypt", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def encrypt(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("PGP encrypt request received")

    try:
        body = req.get_json()
        blob_url = body["blob_url"]
    except (ValueError, KeyError):
        return func.HttpResponse(
            json.dumps({"error": "Provide JSON body with 'blob_url'"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        container, blob_path = _parse_blob_url(blob_url)
        service = _blob_service()

        # Download source blob
        src = service.get_blob_client(container, blob_path)
        plaintext_bytes = src.download_blob().readall()

        # Encrypt
        pub_key = _load_public_key()
        message = pgpy.PGPMessage.new(plaintext_bytes, file=True)
        encrypted = pub_key.encrypt(message)

        # Upload encrypted blob
        dest_path = blob_path + ".pgp"
        dest = service.get_blob_client(container, dest_path)
        dest.upload_blob(str(encrypted).encode(), overwrite=True)

        return func.HttpResponse(
            json.dumps({"encrypted_blob": f"{container}/{dest_path}"}),
            mimetype="application/json",
        )
    except Exception as exc:
        logging.exception("Encrypt failed")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )


# ---------------------------------------------------------------------------
# Decrypt
# ---------------------------------------------------------------------------
@app.route(route="decrypt", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def decrypt(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("PGP decrypt request received")

    try:
        body = req.get_json()
        blob_url = body["blob_url"]
    except (ValueError, KeyError):
        return func.HttpResponse(
            json.dumps({"error": "Provide JSON body with 'blob_url'"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        container, blob_path = _parse_blob_url(blob_url)
        if not blob_path.endswith(".pgp"):
            return func.HttpResponse(
                json.dumps({"error": "Blob must have .pgp extension to decrypt"}),
                status_code=400,
                mimetype="application/json",
            )

        service = _blob_service()

        # Download encrypted blob
        src = service.get_blob_client(container, blob_path)
        ciphertext = src.download_blob().readall()

        # Decrypt
        priv_key, passphrase = _load_private_key()
        pgp_message = pgpy.PGPMessage.from_blob(ciphertext)

        if passphrase:
            with priv_key.unlock(passphrase):
                decrypted = priv_key.decrypt(pgp_message)
        else:
            decrypted = priv_key.decrypt(pgp_message)

        # Upload decrypted blob (strip .pgp)
        dest_path = blob_path[: -len(".pgp")]
        dest = service.get_blob_client(container, dest_path)
        dest.upload_blob(decrypted.message, overwrite=True)

        return func.HttpResponse(
            json.dumps({"decrypted_blob": f"{container}/{dest_path}"}),
            mimetype="application/json",
        )
    except Exception as exc:
        logging.exception("Decrypt failed")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )
