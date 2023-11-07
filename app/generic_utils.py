# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
from functools import wraps
import time
from urllib.parse import urlparse
from pathlib import Path
import json
import os
import pypdf
import traceback
from openai import OpenAI
import random


def with_retry(max_retries=5, retry_wait=3):
    """Decorator that retries a function call a specified number of times"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            n_retries = 0
            while True:
                try:
                    r = func(*args, **kwargs)
                    break
                except Exception as e:
                    if n_retries < max_retries:
                        time.sleep(retry_wait)
                        n_retries += 1
                    else:
                        raise Exception(
                            f"Fetching failed after {max_retries} retries for {func.__name__} with args {args} and kwargs {kwargs}! Original exception: {e}"
                        )
            return r

        return wrapper

    return decorator


@with_retry(max_retries=5, retry_wait=3)
def fetch(url):
    """
    Send GET request to a specified url and retrieve html as string.
    Raises exception for non-200 status codes.
    """
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r


def get_soup(url: str) -> BeautifulSoup:
    """Get BeautifulSoup object from url."""
    return BeautifulSoup(fetch(url).text, "html.parser")


def get_rightmost_url_part(url):
    """Given an resource url, return the rightmost part. In case of REST
    urls this usually corresponds to a ressource identifier.
    Trailing slashes are stripped.
    """
    return url.strip("/").rsplit("/", 1)[-1]


def get_url_root(url: str) -> str:
    """Given an url, return the root url. Example:
    Given https://www.schlieren.ch/politbusiness, return https://www.schlieren.ch
    """
    return urlparse(url).scheme + "://" + urlparse(url).netloc


def get_previous_run_json_as_id_dict(file: Path) -> dict:
    """Load result json file from previous runs if it exists.
    Returns dict with file id as keys and item dict as values if file exists.
    Returns empty dict if no file exists.
    """
    try:
        with open(file, "r") as f:
            result_json = json.load(f)
        # The result json has some top level metadata which is not of interest.
        # We only want the data array, which contains a list of item dicts.
        return {i["item_id"]: i for i in result_json["data"]}
    except FileNotFoundError:
        return {}


def download_and_save_pdf(pdf_url, path):
    """
    Download pdf file from pdf_url with retry logic and save to path.
    Raises exception for non-200 status codes.
    """
    r = fetch(pdf_url)
    with open(path, "wb") as f:
        f.write(r.content)


def read_pdf_text(pdf_path: Path) -> str:
    """Given a path to a pdf file, return the text content of the pdf.

    Args:
        path (str): Path to pdf file.

    Returns:
        str: Content of pdf file.
    """
    with open(pdf_path, "rb") as f:
        pdf = pypdf.PdfReader(f)
        text = (
            " ".join(page.extract_text() for page in pdf.pages)
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .strip()
        )
        # Get rid of multiple whitespaces using join/split pattern.
        text = " ".join(text.split())
    return text


def clean_text(text: str) -> str:
    """Given a text, clean it up by removing duplicate whitespaces, tab and newlines."""
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return " ".join(text.split()).strip()


def generate_openai_summary(text_to_summarize):
    """Text summarization in german using ChatGPT API."""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    system_prompt = clean_text(
        """
        Als deutschsprachiger Zusammenfassungsroboter erhältst du einen Text und sollst
        eine prägnante TL;DR (Too Long; Didn't Read)-Zusammenfassung auf Deutsch erstellen.
        Du darfst höchstens 5 Sätze verwenden. Der Anfang und das Ende des bereitgestellten
        Textes könnten aus Unsinnswörter oder zufälligen Zeichen bestehen,
        die ignoriert werden sollten. Die Zusammenfassung endet mit korrekter Interpunktion.
        Du gibst nur die Zusammenfassung zurück.
        """
    )
    return (
        client.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # "gpt-4-32k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_to_summarize},
            ],
            temperature=0.3,
        )
        .choices[0]
        .message.content
    )


def summarize_text(text, max_attempts=5):
    """Given a text, return a summary of the text using ChatGPT API.
    Requiers OPENAI_API_KEY env variable to be set."""
    attempt = 0
    while True:
        attempt += 1
        try:
            summary = generate_openai_summary(text)
            break
        except Exception as e:
            # There are many things that can go wrong here, some of them are our fault (too many tokens), but
            # openai has also been wonky due to server overload. Therefore, we need some retry logic here.
            # We distinguish between openai errors and non-openai errors. In most cases we just sleep and retry,
            # following a kinda exponential backoff, for 6 attempts: 4, 8, 16, 32, 64, 128s with minimal randomness.
            # In case of too many input tokens, we recursively split the text and
            # summarize each part, which in case is then summarized again.
            if attempt > max_attempts:
                raise Exception(
                    f"Failed to summarize text after {max_attempts} attempts! Last exception: {e} - {traceback.format_exc()}"
                )
            elif "Please reduce the length of the messages." in str(e):
                text = (
                    summarize_text(text[: len(text) // 2])
                    + ". "
                    + summarize_text(text[len(text) // 2 :])
                )
            else:
                time.sleep(2 * 2**attempt + 2 * random.random())
    # ChatGPT might start TL;DR responses with "TL;DR:", which we remove here.
    return clean_text(summary).replace("TL;DR:", "").strip()


def create_pdf_summary(pdf_url: str, pdf_tmp_directory: Path) -> str:
    """Given an url pointing to a pdf file, return a summary of its content.
    This function will apply OCR if needed and use ChatGPT API for summarization.

    Args:
        pdf_url (str): url to pdf file

    Returns:
        str: summary of pdf content.
    """

    pdf_id = get_rightmost_url_part(pdf_url)
    tmp_pdf_path = pdf_tmp_directory / f"{pdf_id}.pdf"
    download_and_save_pdf(pdf_url, tmp_pdf_path)
    ocr_pdf_german_inplace(tmp_pdf_path)
    text = read_pdf_text(tmp_pdf_path)
    assert text, "Error in read_pdf_text: PDF text was empty!"
    summary = summarize_text(text)
    assert summary, "PDF summary was empty!"
    return summary


def ocr_pdf_german_inplace(pdf_path: Path):
    try:
        # Perform OCR on PDF file:
        # Firstly, rewrite file with ghostscript, because it seems to decrease errors when using ocrmypdf:
        # https://ocrmypdf.readthedocs.io/en/latest/errors.html#input-file-filename-is-not-a-valid-pdf
        # Then perform OCR (german) in-place. If this does not work it is okay,
        # and we will just try to read the original PDF below.
        # Implementation note:
        # It seems ghostscript cannot read and write to same file, so introduce another temporary file here
        # which is then used for ocrmypdf. Output of ocrmypdf will then overwrite orignal file. That way
        # the downstream code can just use the original file path, no matter if OCR was applied or not.
        pdf_id = pdf_path.stem
        directory = pdf_path.parent
        tmp_pdf_path_aux = directory / f"{pdf_id}_aux.pdf"
        os.system(f"gs -q -o {tmp_pdf_path_aux} -dSAFER -sDEVICE=pdfwrite {pdf_path}")
        os.system(
            f"ocrmypdf -q --output-type pdf --redo-ocr -l deu {tmp_pdf_path_aux} {pdf_path}"
        )
    except Exception as e:
        pass
    finally:
        # Remove temporary file in any case if exists.
        if os.path.exists(tmp_pdf_path_aux):
            os.remove(tmp_pdf_path_aux)
