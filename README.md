# PGP Blob Encrypt/Decrypt — Azure Function

An Azure Function that encrypts and decrypts files in Azure Blob Storage using PGP.

## Endpoints

| Method | Route           | Description                                              |
|--------|-----------------|----------------------------------------------------------|
| POST   | `/api/encrypt`  | Encrypts a blob and writes it back with a `.pgp` extension |
| POST   | `/api/decrypt`  | Decrypts a `.pgp` blob and writes it without the extension |

### Request body

```json
{
  "blob_url": "https://<account>.blob.core.windows.net/<container>/<blob>"
}
```

### Response

```json
{ "encrypted_blob": "<container>/<blob>.pgp" }
```

## Setup

### Prerequisites

- Python 3.9+
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4
- An Azure Storage account

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Copy or edit `local.settings.json` and set your storage connection string:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BLOB_CONNECTION_STRING": "<your-azure-storage-connection-string>"
  }
}
```

### PGP keys

Place your keys in the `keys/` directory:

| File               | Purpose                  |
|--------------------|--------------------------|
| `keys/public.asc`  | Public key (encryption)  |
| `keys/private.asc` | Private key (decryption) |

To generate a test keypair:

```bash
python generate_keys.py
```

If the private key has a passphrase, set `PGP_PASSPHRASE` in `local.settings.json`.

### Run locally

```bash
source .venv/bin/activate
func start
```

The function host starts at `http://localhost:7071`.

## Usage examples

**Encrypt a blob:**

```bash
curl -X POST http://localhost:7071/api/encrypt \
  -H "Content-Type: application/json" \
  -d '{"blob_url": "https://<account>.blob.core.windows.net/<container>/hello.txt"}'
```

**Decrypt a blob:**

```bash
curl -X POST http://localhost:7071/api/decrypt \
  -H "Content-Type: application/json" \
  -d '{"blob_url": "https://<account>.blob.core.windows.net/<container>/hello.txt.pgp"}'
```

## Project structure

```
├── function_app.py        # Encrypt & decrypt HTTP functions
├── generate_keys.py       # Helper to generate a test PGP keypair
├── keys/
│   ├── public.asc         # PGP public key
│   └── private.asc        # PGP private key (gitignored)
├── host.json              # Azure Functions host config
├── local.settings.json    # Local app settings (gitignored)
└── requirements.txt       # Python dependencies
```
