---
hide:
  - toc
---

# Discord

It is possible to send messages to your Discord channels in events of success or/and failed backups.
Good idea might be to have one muted and one normal channel on your server so success messages will be printed to muted one and fail messages to one not muted.

Integration is via **Discord webhooks** and environment variables.

Follow their documentation [https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

You should generate webhooks like `"https://discord.com/api/webhooks/1111111111/long-token"` and `"https://discord.com/api/webhooks/22222222222222/another-long-token"` this way

## Environemt variables

| Name                             | Type | Description                                     | Default |
| :------------------------------- | :--- | :---------------------------------------------- | :------ |
| DISCORD_SUCCESS_WEBHOOK_URL      | url  | URL for success messages.                       | -       |
| DISCORD_FAIL_WEBHOOK_URL         | url  | URL for fail messages.                          | -       |
| DISCORD_NOTIFICATION_MAX_MSG_LEN | int  | Maximum length of messages send to discord API. | 1500    |

## Examples:

```bash
DISCORD_SUCCESS_WEBHOOK_URL="https://discord.com/api/webhooks/1111111111/long-token"
DISCORD_FAIL_WEBHOOK_URL="https://discord.com/api/webhooks/22222222222222/another-long-token"
```

<br>
<br>