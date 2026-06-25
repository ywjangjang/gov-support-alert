"""Slack Incoming Webhook으로 메시지를 보내는 모듈."""
import requests


def send_slack_message(webhook_url, text):
    response = requests.post(webhook_url, json={"text": text}, timeout=15)
    response.raise_for_status()
    return response.text
