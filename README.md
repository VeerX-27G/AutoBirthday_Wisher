# AutoBirthday_Wisher

Never forget a birthday again. This script checks a list of birthdays every day and, when someone's birthday is today, automatically emails them a birthday letter from your Gmail account. It runs for free on GitHub Actions, so nothing needs to be left running on your computer.

## How it works

1. Every morning GitHub Actions starts the workflow (or you start it yourself).
2. `birthday_wisher.py` reads `birthdays.csv` and looks for anyone whose month and day match today (in the Regina time zone).
3. For each match, it works out the age they are turning, picks one of the letters in `letter_templates/` at random, replaces `[NAME]` with their name and `[AGE]` with their new age (for example "Happy 21st birthday!"), and sends it through Gmail. The email subject is also "Happy 21st Birthday!".
4. If nobody has a birthday today, it does nothing.

## Files

| File | Purpose |
| --- | --- |
| `birthday_wisher.py` | The script that finds today's birthdays and sends the emails |
| `birthdays.csv` | Your list of people (see format below) |
| `letter_templates/letter_*.txt` | Letter templates; one is picked at random for each email |
| `requirements.txt` | Python dependencies (`pandas`, `python-dotenv`) |
| `.github/workflows/birthday_wisher.yaml` | GitHub Actions workflow that runs the script daily |

## Set it up

### 1. Fill in `birthdays.csv`

```csv
name,email,year,month,day
Mom,mom@example.com,1978,7,7
Alex,alex@example.com,1995,2,25
```

- `name` is inserted into the letter, `email` is where it is sent.
- `month` and `day` are numbers (`7`, not `July`). `year` is the birth year and is used to work out the age they are turning. If it is missing, the email just says "Happy birthday!" without an age.
- Several people can share a birthday and each will get their own email.
- Someone born on February 29 is wished on February 29 only, so they get an email in leap years but not in other years.

### 2. Edit the letters (optional)

Each file in `letter_templates/` is a plain text letter. Write `[NAME]` where the person's name should go and `[AGE]` where their new age should go (it becomes "21st", "22nd" and so on, so "Happy [AGE] birthday!" turns into "Happy 21st birthday!"). To add more, create `letter_4.txt`, `letter_5.txt` and so on; they are picked up automatically.

### 3. Add your credentials as repository secrets

Go to **Settings -> Secrets and variables -> Actions -> New repository secret** and create:

| Secret | Value |
| --- | --- |
| `EMAIL` | The Gmail address the wishes are sent from |
| `SENDER_PASSWORD` | A [Gmail app password](https://support.google.com/accounts/answer/185833) for that address (not your normal Gmail password) |

### 4. Check the schedule

The workflow runs every day at **06:00 UTC (0:00 AM in Regina)**. To change the time, edit the `cron` line in `.github/workflows/birthday_wisher.yaml`:

```yaml
schedule:
  - cron: "0 6 * * *"
```

### 5. Test it

Open the **Actions** tab, choose **Birthday Wisher** on the left, and click **Run workflow**. To test safely, add a row to `birthdays.csv` with today's date and your own email address.

## Run it on your own computer

1. Install Python 3.9 or newer.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project folder (it is ignored by git):

   ```env
   EMAIL=your_gmail_address
   SENDER_PASSWORD=your_gmail_app_password
   ```

4. Run it:

   ```bash
   python birthday_wisher.py
   ```

To see who would be emailed without sending anything, set `DRY_RUN=1` first (for example `DRY_RUN=1 python birthday_wisher.py`).

## Notes

- Gmail limits how many emails an account can send per day, which is far above what a birthday list needs.
- GitHub disables scheduled workflows after 60 days without activity in the repository. If that happens, re-enable the workflow from the Actions tab.
