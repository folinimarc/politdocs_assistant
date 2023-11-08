# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import json
import re
from thefuzz import fuzz

import generic_utils as gu


def get_full_table_soup(url: str) -> BeautifulSoup:
    """The table on the page only shows the last 10 years by default. Data for all years can be requested with a form
    that sends a GET request. For this we need a form_token, which is embedded in the form submit button."""
    table_soup = gu.get_soup(url)
    form_token = table_soup.find(
        "input", id="politische_geschaefte_suchformular__token"
    )["value"]
    table_url_all_years = f"{url}?politische_geschaefte_suchformular[vomStart]=&politische_geschaefte_suchformular[vomEnd]=&politische_geschaefte_suchformular[_token]={form_token}"
    return gu.get_soup(table_url_all_years)


def extract_items(soup: BeautifulSoup, root_url: str) -> list[dict]:
    """Extract row objects from table soup."""
    # The table tag has a data attribute data-entities that contains the whole
    # table data as json in a data-attribute data-entities.
    # We can use this to extract the item detail urls (which are contained in the
    # href attribute in an a tag within the title key of each json object >.<)
    # without the hassle of caring about pagination or parsing html.
    items_raw = json.loads(soup.find("table").attrs["data-entities"])["data"]
    # Add item id, full url to item detail page and replace title.
    # Each row's title is a hyperlink to the item detail page, so we can extract
    # the href from the title attribute. The item identifier is the last part of
    # the url.
    for i in items_raw:
        i["item_url"] = root_url + re.search(r"href=\"(.*?)\"", i["title"]).groups()[0]
        i["item_id"] = gu.get_rightmost_url_part(i["item_url"])
        i["title"] = i["title-sort"].strip().capitalize()
    return items_raw


def add_response_links_inplace(items):
    """
    Some items are responses ("Beantwortungen") to other items.
    Try to detect these relationships using fuzzy matching of titles
    and add links to responses to each affected item.
    This happens in-place.

    Criteria for a link is a high similarity in the titles.
    We ignore titles which contain "gemeindeparlament" because these are
    protocol items and not responses.
    """
    for i in items:
        i["related_items"] = []
    for i1 in range(len(items)):
        item1 = items[i1]
        i1_title = item1["title"].lower()
        if "gemeindeparlament" in i1_title:
            continue
        for i2 in range(i1 + 1, len(items)):
            item2 = items[i2]
            i2_title = item2["title"].lower()
            ratio = fuzz.partial_ratio(i1_title, i2_title)
            if ratio > 95:
                item1["related_items"].append(
                    {"item_id": item2["item_id"], "title": item2["title"]}
                )
                item2["related_items"].append(
                    {"item_id": item1["item_id"], "title": item1["title"]}
                )


def enrich_item_from_detail_page(item_raw: dict) -> dict:
    """Given a dict of a scrapped raw item, perform all processing
    required to return a dictionary that holds all key attributes for an item:
    - status: OK or ERROR
    - error_msg: Empty string if status is OK, otherwise error message.
    - processed_asof: Date of processing.
    - item_id: Item id.
    - item_url: Item detail page url.
    - title: Item title.
    - category: Item category.
    - date: Item date.
    - author: Item author.
    - pdf_url: Url to pdf file.
    - pdf_id: Pdf id.

    Args:
        item_raw (dict): A scrapped raw item.

    Returns:
        dict: Dict that contains key attributes for an item.
    """

    # Clean and transfer item attributes from raw item.
    item_url = item_raw["item_url"]
    item = {
        "item_url": item_url,
        "title": item_raw["title"],
        "category": item_raw["_kategorieId-sort"].title(),
        "date": item_raw["_geschaeftsdatum-sort"],
        "related_items": item_raw["related_items"],
    }

    # Fetch item detail page to extract author and pdf links
    soup = gu.get_soup(item_url)

    # Add author
    # Ideally we would extract the author from the item detail page's creator (Verfasser) tag.
    # Otherwise, check if the title contains "vorlage stadtrat" and set author to "Stadtrat".
    # Otherwise, check if the title contains "gemeindeparlament" together with either "beschluss" or "protokoll" and set author to "Gemeindeparlament".
    # Use "Unspezifiziert" (unspecified) as fallback.
    author = "Unspezifiziert"
    author_tag = soup.find("dt", string=re.compile("Verfasser"))
    title_lower = item["title"].lower()
    if author_tag:
        author_tag_a = author_tag.next_sibling.find("a")
        if author_tag_a:
            author = author_tag_a.get_text().strip()
        else:
            author = author_tag.next_sibling.get_text().strip()
    elif "vorlage stadtrat" in title_lower:
        author = "Stadtrat"
    elif "gemeindeparlament" in title_lower and (
        "beschluss" in title_lower or "protokoll" in title_lower
    ):
        author = "Gemeindeparlament"
    item.update({"author": author.title()})

    # Get PDF url, which is the href attribut of a download button element.
    pdf_url = (
        gu.get_url_root(item_url)
        + soup.find(
            lambda tag: tag.has_attr("href")
            and "_doc" in tag["href"]
            and "Download" in tag.string
        )["href"]
    )
    # Pdf identifier is the last part of the url.
    pdf_id = gu.get_rightmost_url_part(pdf_url)
    item.update({"pdf_url": pdf_url, "pdf_id": pdf_id})

    return item
