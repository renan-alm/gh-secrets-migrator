#!/usr/bin/env python3
import base64
import json
import os
from nacl import encoding, public

secret = os.environ['SECRET_VALUE']
public_key = os.environ['PUBLIC_KEY']
repo_ids_json = os.environ['REPO_IDS_JSON']

# Encrypt the secret
public_key_bytes = base64.b64decode(public_key)
sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
encrypted = sealed_box.encrypt(secret.encode('utf-8'))
encrypted_value = base64.b64encode(encrypted).decode('utf-8')

# Create the payload
repo_ids = json.loads(repo_ids_json)
payload = {
    'encrypted_value': encrypted_value,
    'key_id': os.environ['KEY_ID'],
    'visibility': 'selected',
    'selected_repository_ids': repo_ids
}

# Output as JSON to a temp file for gh api
with open('/tmp/payload.json', 'w') as f:
    json.dump(payload, f)
