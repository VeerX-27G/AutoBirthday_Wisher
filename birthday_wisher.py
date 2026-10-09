"""Auto Birthday Wisher

Reads birthdays.csv, and if anyone has a birthday today, emails them a random
letter from letter_templates/ with [NAME] replaced by their name.

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

# Someone born on Feb 29 gets their wish on Feb 28 in years that have no Feb 29.
is_leap_year = today.year % 4 == 0 and (today.year % 100 != 0 or today.year % 400 == 0)
include_leap_day = today_tuple == (2, 28) and not is_leap_year

try:
    data = pandas.read_csv("birthdays.csv")
except FileNotFoundError:
    sys.exit("❌ birthdays.csv not found. Create it with the columns: name,email,year,month,day")

required_columns = {"name", "email", "month", "day"}
if not required_columns.issubset(data.columns):
    sys.exit(f"❌ birthdays.csv must have these columns: {', '.join(sorted(required_columns))}")

# Everyone whose birthday is today (more than one person can share a birthday).
birthday_people = []
seen_emails = set()
for _, row in data.iterrows():
    row_tuple = (int(row["month"]), int(row["day"]))
    is_today = row_tuple == today_tuple or (include_leap_day and row_tuple == (2, 29))
    if not is_today:
        continue
    email = str(row["email"]).strip()
    if email in seen_emails:  # skip accidental duplicate rows
        continue
    seen_emails.add(email)
    birthday_people.append((str(row["name"]).strip(), email))

if not birthday_people:
    print(f"No birthdays today ({today:%B %d}).")
    sys.exit(0)

templates = sorted(glob.glob("letter_templates/letter_*.txt"))
if not templates:
    sys.exit("❌ No letter templates found in letter_templates/ (expected letter_1.txt, letter_2.txt, ...)")


def build_message(name, email):
    with open(random.choice(templates), encoding="utf-8") as letter_file:
        contents = letter_file.read().replace("[NAME]", name)
    msg = EmailMessage()
    msg["Subject"] = "Happy Birthday!"
    msg["From"] = MY_EMAIL
    msg["To"] = email
    msg.set_content(contents)  # UTF-8, so names/emoji with accents work
    return msg


if DRY_RUN:
    for name, email in birthday_people:
        print(f"[DRY RUN] Would send a birthday email to {name} <{email}>")
    sys.exit(0)

failures = 0
try:
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(MY_EMAIL, MY_PASSWORD)
        for name, email in birthday_people:
            try:
                connection.send_message(build_message(name, email))
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
