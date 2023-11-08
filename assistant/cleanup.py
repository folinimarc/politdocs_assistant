# -*- coding: utf-8 -*-
from openai import OpenAI

client = OpenAI()

print("Deleting all files.")
for f in list(client.files.list()):
    print(f"Deleting file {f.id}")
    client.files.delete(f.id)

print("Deleting all assistants.")
for a in list(client.beta.assistants.list()):
    print(f"Deleting assistant {a.id}")
    client.beta.assistants.delete(a.id)

print("Done.")
