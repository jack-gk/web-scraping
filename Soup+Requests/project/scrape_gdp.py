import re
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup


URL = "https://en.wikipedia.org/wiki/List_of_Nobel_laureates_in_Physics"
html = requests.get(URL, timeout=30).text
soup = BeautifulSoup(html, "lxml")

table = soup.find("table", class_="wikitable")

# remove superscript reference links and convert <br> to spaces
for tag in table.select("sup.reference"):
    tag.decompose()
for br in table.find_all("br"):
    br.replace_with(" ")

rows, rowspan_cache = [], {}

for tr in table.select("tr"):
    row, col_idx = [], 0

    for td in tr.find_all(["th", "td"]):

        while col_idx in rowspan_cache:
            text, remaining = rowspan_cache[col_idx]
            row.append(text)
            if remaining == 1:
                del rowspan_cache[col_idx]
            else:
                rowspan_cache[col_idx][1] -= 1
            col_idx += 1

        text = td.get_text(" ", strip=True)
        span = int(td.get("rowspan", 1))

        is_image_only = td.find("img") and not text
        cell_value = "" if is_image_only else text
        row.append(cell_value)

        if span > 1:
            rowspan_cache[col_idx] = [cell_value, span - 1]

        col_idx += 1

    while col_idx in rowspan_cache:
        text, remaining = rowspan_cache[col_idx]
        row.append(text)
        if remaining == 1:
            del rowspan_cache[col_idx]
        else:
            rowspan_cache[col_idx][1] -= 1
        col_idx += 1

    rows.append(row)


max_cols = len(rows[0])
for r in rows:
    r.extend(" " * (max_cols - len(r)))

df_full = pd.DataFrame(rows[1:], columns=rows[0])
df = df_full.drop(columns=["Image", "Ref"])

df["Year"] = pd.to_numeric(df["Year"])
df = df.dropna(subset=["Year"]).astype({"Year": int})


_ALIAS = {
    "United States of America": "USA",
    "United States":            "USA",
    "American":                 "USA",
    "British":                  "UK",
    "Soviet":                   "Russia / Soviet Union",
    "Russian":                  "Russia / Soviet Union",
    "West German":              "Germany",
    "German":                   "Germany"
}


def clean_nations(cell: str) -> list[str]:
    """Return a list of canonical country names extracted from one cell."""
    if not cell:
        return []

    cell = re.sub(r"\[[^\]]+]", "", cell)

    tokens = re.split(r"[\s/–-]+", cell)

    clean = []
    for t in tokens:
        t = t.strip(",")
        if not t:
            continue
        t = t.title()
        clean.append(_ALIAS.get(t, t))
    return clean


def tally_by_year(year_or_iterable) -> Counter:
    """Return Counter of nationalities for a given year or iterable of years."""
    if isinstance(year_or_iterable, int):
        mask = df["Year"] == year_or_iterable
    else:
        mask = df["Year"].isin(year_or_iterable)

    nations = Counter()
    for cell in df.loc[mask, "Nationality"]:
        nations.update(clean_nations(cell))
    return nations


def pie_for_year(year_or_iterable = range(1901, 2024), *, max_labels: int = 10) -> None:
    """
    Draw a pie chart of nationality share.
    If there are more than `max_labels` slices,
    collapse the least-common ones into “Other”.
    """
    counts = tally_by_year(year_or_iterable)
    if not counts:
        print("No data available for that year / range.")
        return

    # prepare labels and sizes
    labels, sizes = zip(*counts.most_common())
    if len(labels) > max_labels:
        labels = list(labels[:max_labels]) + ["Other"]
        sizes = list(sizes[:max_labels]) + [sum(sizes[max_labels:])]

    # title string (single year vs range)
    if isinstance(year_or_iterable, int):
        title = str(year_or_iterable)
    else:
        title = f"{min(year_or_iterable)}–{max(year_or_iterable)}"

    # plot
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"Nobel Physics laureates by nationality ({title})")
    plt.tight_layout()
    plt.show()


pie_for_year(2019)
pie_for_year(range(2000, 2010))
pie_for_year()