# -*- coding: utf-8 -*-
from openai import OpenAI
from pathlib import Path


# Following https://platform.openai.com/docs/assistants/how-it-works/creating-assistants
client = OpenAI()

# Split files
import json
import io

data_json = Path("../dev/data/items.json")
file_ids = []

# USE CHUNKED FILES FOR FULLTEXT
# with open(data_json, "r") as f:
#     data = json.loads(f.read())
# def chunks(xs, n_chunks):
#     n = (len(xs) // n_chunks) + 1
#     return (xs[i:i+n] for i in range(0, len(xs), n))
# for chunk in chunks(data["data"], 4):
#     print(f"Create file with {len(chunk)} items.")
#     file = client.files.create(
#         file=io.BytesIO(json.dumps({"data": chunk}, indent=4).encode('utf-8')),
#         purpose='assistants'
#     )
#     file_ids.append(file.id)

# USE SINGLE FILE FOR SUMMARYTEXT
print("Create file with all items.")
data_json = Path("../dev/frontend/items_slim.json")
file = client.files.create(file=open(data_json, "rb"), purpose="assistants")
file_ids.append(file.id)

# TEST MARKDOWN TABLE
# pip install pandas tabulate
# print("Create markdown table file.")
# import pandas as pd
# with open(data_json, "r") as f:
#     data = json.loads(f.read())
# data_md = Path("../dev/data/pdf/test.md")
# pd.DataFrame(data["data"]).to_markdown(data_md, index=False, tablefmt="github")
# file = client.files.create(
#     file=open(data_md, 'rb'),
#     purpose='assistants'
# )
# file_ids.append(file.id)


assistant = client.beta.assistants.create(
    name="Politdocs Assistant",
    instructions="""
  You are a helpful assistant fluent in German. You are asked to answer questions about the Schlieren city council.
  You are given several JSON-files, which contain the data you need to answer the questions. The data is in German and structured as follows:
  Each JSON-file has a data attribute, which contains an array of JSON-objects, each of which represents a city council item.
  Each item has a title, a date, an author. The attribute pdf_text contains a full length text which was extracted by OCR from the original
  PDF-file. The attribute pdf_url contains the URL to the original PDF-file. The attribute pdf_summary contains a summary of the PDF-file.
  Most text is in German and your user base is als German speaking, so you can assume that all text is in German.

  Your job is to load and parse all JSON files to answer questions, provide aggregate statistics or act as an intelligent
  search engine. Make sure you provide a convenient search experience, for example by ignoring capitilation or typos in the search query.

  Do NOT provide any annotations, because the data you are given is already a processed internal file. Instead, you should use the
  link to the original PDF document (pdf_url) or original website (item_url) to reference a source.
  """,
    model="gpt-4-1106-preview",
    tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
    file_ids=file_ids,
)

thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Begrüsse den Nutzer und beschreibe kurz deinen Zweck. Starte mit einem nicht so offensichtlichen Fun-Fact, den du aus den Daten entnimmst.",
)
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
)

import time

while True:
    status = client.beta.threads.runs.retrieve(
        thread_id=thread.id, run_id=run.id
    ).status
    if status != "completed":
        print(f"Working on it... (status: {run.status})")
        time.sleep(4)
        continue
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print("ANTWORT:")
    print(messages.data[0].content[0].text.value)
    print("ANNOTATIONS:")
    print(messages.data[0].content[0].text.annotations)
    prompt = input("What do you want to know next?\n")
    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=prompt
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
