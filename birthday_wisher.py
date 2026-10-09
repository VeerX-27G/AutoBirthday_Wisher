"""Auto Birthday Wisher

Reads birthdays.csv, and if anyone has a birthday today, emails them a random
letter from letter_templates/ with [NAME] replaced by their name and [AGE]
replaced by the age they are turning (e.g. "21st").

Runs locally (credentials from a .env file) or on GitHub Actions
(credentials from repository secrets exposed as environment variables).
"""

import glob
import os
import random
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas
from dotenv import load_dotenv

# Locally this loads .env; on GitHub Actions there is no .env, so it does nothing
# and the values come from the workflow's environment (GitHub Secrets).
load_dotenv()

MY_EMAIL = os.environ.get("EMAIL")
MY_PASSWORD = os.environ.get("SENDER_PASSWORD")

# GitHub runners use UTC, so "today" is always worked out in your own time zone.
# Override with a TIMEZONE variable if you ever need a different one.
TIMEZONE = os.environ.get("TIMEZONE", "America/Regina")

# Set DRY_RUN=1 to see who would be emailed without sending anything.
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

if not DRY_RUN:
    missing = [n for n, v in (("EMAIL", MY_EMAIL), ("SENDER_PASSWORD", MY_PASSWORD)) if not v]
    if missing:
        sys.exit(f"❌ Missing required environment variables / secrets: {', '.join(missing)}")

today = datetime.now(ZoneInfo(TIMEZONE))
today_tuple = (today.month, today.day)


def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 23 -> '23rd', 112 -> '112th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def new_age(row):
    """The age the person is turning today, or None if the year is missing/invalid."""
    try:
        age = today.year - int(row["year"])
    except (KeyError, ValueError, TypeError):
        return None
    return age if age > 0 else None


try:
    data = pandas.read_csv("birthdays.csv")
except FileNotFoundError:
    sys.exit("❌ birthdays.csv not found. Create it with the columns: name,email,year,month,day")

required_columns = {"name", "email", "month", "day"}
if not required_columns.issubset(data.columns):
    sys.exit(f"❌ birthdays.csv must have these columns: {', '.join(sorted(required_columns))}")

# Everyone whose birthday is today (more than one person can share a birthday).
# Feb 29 birthdays are only matched on Feb 29 itself (leap years), never on Feb 28.
birthday_people = []
seen_emails = set()
for _, row in data.iterrows():
    row_tuple = (int(row["month"]), int(row["day"]))
    if row_tuple != today_tuple:
        continue
    email = str(row["email"]).strip()
    if email in seen_emails:  # skip accidental duplicate rows
        continue
    seen_emails.add(email)
    birthday_people.append((str(row["name"]).strip(), email, new_age(row)))

if not birthday_people:
    print(f"No birthdays today ({today:%B %d}).")
    sys.exit(0)

templates = sorted(glob.glob("letter_templates/letter_*.txt"))
if not templates:
    sys.exit("❌ No letter templates found in letter_templates/ (expected letter_1.txt, letter_2.txt, ...)")


def build_message(name, email, age):
    with open(random.choice(templates), encoding="utf-8") as letter_file:
        contents = letter_file.read().replace("[NAME]", name)
    if age:
        contents = contents.replace("[AGE]", ordinal(age))
        subject = f"Happy {ordinal(age)} Birthday!"
    else:
        # No usable year in the CSV: drop the placeholder and keep a plain greeting.
        contents = contents.replace("[AGE] ", "").replace("[AGE]", "")
        subject = "Happy Birthday!"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MY_EMAIL
    msg["To"] = email
    msg.set_content(contents)  # UTF-8, so names/emoji with accents work
    return msg


if DRY_RUN:
    for name, email, age in birthday_people:
        wish = f"Happy {ordinal(age)} birthday" if age else "Happy birthday"
        print(f"[DRY RUN] Would send '{wish}' to {name} <{email}>")
    sys.exit(0)

failures = 0
try:
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)
        for name, email, age in birthday_people:
            try:
                connection.send_message(build_message(name, email, age))
                # Email addresses are deliberately not printed: workflow logs can be public.
                print(f"🎂 Birthday email sent to {name}")
            except Exception as e:
                failures += 1
                print(f"❌ Could not send to {name}: {type(e).__name__}: {e}")
except Exception as e:
    print(f"❌ Could not connect or log in to Gmail: {type(e).__name__}: {e}")
    sys.exit(1)

# A non-zero exit makes the GitHub run show a red X instead of a false green check.
sys.exit(1 if failures else 0)
