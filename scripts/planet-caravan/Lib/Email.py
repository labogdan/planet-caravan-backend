import os
import requests


def send_email(subject: str = 'Notification', body: str = ''):
    return requests.post(
        f"https://api.mailgun.net/v3/{os.getenv('MAILGUN_DOMAIN')}/messages",
        auth=("api", os.getenv('MAILGUN_API_KEY')),
        data={"from": "Planet Caravan Sync <noreply@planetcaravansmokeshop.com>",
              "to": [os.getenv('NOTIFICATIONS_EMAIL')],
              "subject": subject,
              "text": body})

