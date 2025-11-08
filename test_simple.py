#!/usr/bin/env python3
import os
import sys

# Lire directement le .env
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

print(f"Test avec clé: {api_key[:30]}...\n")

from openai import OpenAI
client = OpenAI(api_key=api_key)

try:
    response = client.embeddings.create(
        input="test simple",
        model="text-embedding-3-small"
    )
    print("🎉 SUCCÈS!")
    print(f"Dimensions: {len(response.data[0].embedding)}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
