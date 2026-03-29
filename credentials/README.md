# credentials/

This folder holds your Google service account key. It is excluded from version control.

## Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Download the JSON key file
6. Rename it to `service-account.json` and place it here:

```
credentials/service-account.json
```

7. Open your Google Spreadsheet
8. Click **Share** and add the service account's `client_email` (found inside the JSON) with **Editor** access

## Important

- `credentials/*.json` is in `.gitignore` — it will never be committed
- Never share or commit this file
- Set the path in `.env`: `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json`
