# -*- coding: utf-8 -*-
from init_utils import create_directory, get_default_logger
import generic_utils as gu
import schlieren_utils as su

import traceback
from pathlib import Path
import os
import datetime
import json
import shutil

# Constants
table_url = "https://www.schlieren.ch/politbusiness"
data_directory = Path("../dev/data")
out_file = data_directory / "items.json"
pdf_tmp_directory = data_directory / "pdf"

# Setup
logger = gu.get_default_file_and_stream_logger("politdocs", data_directory)
logger.info(
    f"Creating data directory {data_directory.absolute()} and pdf tmp directory {pdf_tmp_directory.absolute()}."
)
gu.create_directory(data_directory, purge=False)
gu.create_directory(pdf_tmp_directory, purge=True)
gu.create_directory(frontend_directory, purge=True)
result_dict = {
    "processed_asof": datetime.datetime.now().strftime("%Y-%m-%d"),
    "version": os.getenv(
        "VERSION",
        "You should not see this, because a VERSION env variable should always be set.",
    ),
    "data": [],
}

# Create backup of previous run, so we (hopefully) never lose data.
logger.info(f"Creating backup of previous run at {out_file.absolute()}.json.bak")
if out_file.exists():
    shutil.copy(out_file, out_file.with_suffix(".json.bak"))

# Processing
logger.info(f"Fetching data from {table_url}.")
table_soup = su.get_full_table_soup(table_url)

logger.info(f"Extracting items from {table_url} and idenfitfying related items.")
table_root_url = gu.get_url_root(table_url)
items_raw = su.extract_items(table_soup, table_root_url)
su.add_response_links_inplace(items_raw)

logger.info(f"Load file from previous runs if it exists to avoid redundant work.")
prev_run = gu.get_previous_run_json_as_id_dict(out_file)

logger.info(f"Processing {len(items_raw)} items...")
for i, item_raw in enumerate(items_raw, 1):
    item_raw_id = item_raw["item_id"]
    logger.info(f"Processing item {i}/{len(items_raw)} (id: {item_raw_id})")

    # Check whether the item was already was successfully processed.
    # If so, copy it from previous run and just update the related_items
    # to make sure its up to date. If anything bad happens, log it and continue
    # as if no previous run exists.
    try:
        if prev_run.get(item_raw_id, {}).get("status") == "OK":
            item = prev_run[item_raw_id]
            item["related_items"] = item_raw["related_items"]
            result_dict["data"].append(item)
            continue
    except Exception as e:
        logger.error(
            f"Error when checking if item {item_raw_id} was already processed: {e}"
        )

    # The item was not processed in previous runs or failed in previous runs.
    # Create item skeleton.
    item = {
        "item_id": item_raw_id,
        "status": "YOU_SHOULD_NEVER_SEE_THIS",
        "error_msg": "",
        "processed_asof": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
    # Enrich item with details, download pdf and perform ocr,
    # extract text from pdf and summarize. Whenever something goes wrong,
    # set status to ERROR and add error message and go to next item.
    pdf_tmp_path = None
    try:
        item.update(su.enrich_item_from_detail_page(item_raw))
        pdf_url = item["pdf_url"]
        pdf_id = gu.get_rightmost_url_part(pdf_url)
        pdf_tmp_path = pdf_tmp_directory / f"{pdf_id}.pdf"
        gu.download_and_save_pdf(pdf_url, pdf_tmp_path)
        gu.ocr_pdf_german_inplace(pdf_tmp_path)
        pdf_text = gu.read_pdf_text(pdf_tmp_path)
        assert pdf_text, "Error in read_pdf_text: PDF text was empty!"
        pdf_summary = gu.summarize_text(pdf_text)
        assert pdf_summary, "PDF summary was empty!"
        item.update(
            {
                "status": "OK",
                "pdf_text": pdf_text,
                "pdf_summary": pdf_summary,
            }
        )
        result_dict["data"].append(item)
    except Exception as e:
        logger.info(f"Error when processing item {item_raw_id}: {e}")
        item.update(
            {
                "status": "ERROR",
                "error_msg": f"Exception: {e}. Original exception Traceback: {traceback.format_exc()}",
            }
        )
    finally:
        # Delete pdf from tmp directory in any case.
        if pdf_tmp_path and pdf_tmp_path.exists():
            pdf_tmp_path.unlink()

        # Update result file every 25 items.
        if i % 25 == 0:
            logger.info(f"Persist result to {out_file.absolute()}")
            gu.write_json(result_dict, out_file)

# Persist result as json file.
logger.info(f"Persist result to {out_file.absolute()}")
gu.write_json(result_dict, out_file)

logger.info("Done.")
