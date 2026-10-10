---
name: posting-media-with-postcache
description: Use when an agent publishes an image or video to Instagram, Threads or Facebook Pages through Meta's Graph API and the file is local, private or generated, needs a public image_url or video_url, or Meta returned a media error such as 2207052, 2207009, 2207026, 2207004, 2207005 or 2207003.
---

# Posting media with postcache

## Overview

Meta's publishing APIs don't accept file uploads for images. They fetch the media from a public URL (`image_url`, `video_url`, `url`). postcache gives the file that URL, checks it against the target platform's rules first, can convert it, and deletes it after the post.

Base URL `https://postcache.dev`. Auth `Authorization: Bearer $POSTCACHE_API_KEY` (free key: sign up at https://postcache.dev/login). Without a key, the upload answers `402` with x402 and MPP payment challenges ($0.01 per upload).

## The flow

1. **Upload once per target.** The rules differ by platform, so the same file can pass on Threads and fail on Instagram.
   ```sh
   curl -X PUT "https://postcache.dev/v1/media?convert=pad" \
     -H "Authorization: Bearer $POSTCACHE_API_KEY" \
     -H "x-target: instagram.story" -H "x-filename: today.png" \
     --data-binary @/path/today.png
   ```
   - `201`: use `url`.
   - `202` (`status: "converting"`): poll `GET /v1/media/{id}` every few seconds until `ready` (use `url`) or `failed` (read `checks`).
   - `422 checks_failed`: each problem has `rule`, `message` and `fix`. Duration is never fixed by convert.
   - Files that are already on the web: `POST /v1/media/from-url` with JSON `{source_url, target, convert}`.
2. **Create the container** with that `url`, wait for it, then publish (see the table below).
3. **Delete only after publishing** (`DELETE /v1/media/{id}`). Meta fetches the file while it processes the container, so deleting earlier can cause 2207052.

## Targets and rules

| `x-target` | Images | Video |
| --- | --- | --- |
| `instagram.feed`, `instagram.carousel` | JPEG, ≤ 8 MB, ratio 4:5 to 1.91:1 | carousel only: Reels rules |
| `instagram.story` | JPEG, ≤ 8 MB, any ratio (9:16 best) | 3–60 s, ≤ 100 MB |
| `instagram.reels` | n/a | MP4/MOV, H.264/HEVC + AAC, 23–60 fps, ≤ 1920 px wide, ≤ 25 Mbps, 3 s–15 min, ≤ 300 MB |
| `threads` | JPEG or PNG, ≤ 8 MB | ≤ 5 min, ≤ 1 GB |
| `facebook.page` | JPEG or PNG, ≤ 10 MB | MP4/MOV, ≤ 1 GB |

`convert=pad` (white or black bars) or `convert=crop` fixes format, ratio, color space, size, codecs, fps, bitrate and `moov` placement. HEIC images are not accepted: convert them to JPEG first. `dry_run=1` checks without storing.

## Publishing calls

| Platform | Create | Wait | Publish |
| --- | --- | --- | --- |
| Instagram (`graph.facebook.com/v25.0`) | `POST /{ig-user-id}/media` `image_url` (+ `media_type=STORIES`, or `REELS` with `video_url`) | `GET /{container}?fields=status_code` until `FINISHED` | `POST /{ig-user-id}/media_publish` `creation_id` |
| Threads (`graph.threads.net/v1.0`) | `POST /{threads-user-id}/threads` `media_type=IMAGE` `image_url` `text` | about 30 s, or `GET /{container}?fields=status` | `POST /{threads-user-id}/threads_publish` `creation_id` |
| Facebook Page | `POST /{page-id}/photos` `url` `message` (publishes directly) | n/a | n/a |

Carousels: upload each item with `instagram.carousel`, create one child container per item (`is_carousel_item=true`), then a `CAROUSEL` container with `children`.

## Meta errors this prevents

| Subcode | Meaning | postcache answer |
| --- | --- | --- |
| 2207052 | Meta could not fetch the URL | public URL, ASCII filename, correct content type |
| 2207009 | image ratio outside 4:5 to 1.91:1 | `422` with `aspect`; `convert=pad`/`crop` |
| 2207005 | image is not JPEG (Instagram) | `convert` turns PNG/WebP/GIF into sRGB JPEG |
| 2207004 | image over 8 MB | `convert` shrinks it |
| 2207026 | video format not supported | `convert` re-encodes to H.264/AAC MP4 |
| 2207003 | download timed out | static file with byte ranges; retry with a new container |

Details: https://postcache.dev/errors

## Common mistakes

- Uploading once and reusing the Instagram-checked URL for Threads, or the reverse. Upload per target.
- Deleting the file right after creating the container. Delete after `media_publish` / `threads_publish` returns an id.
- A TTL too short for scheduled posts. Set `?ttl=` in seconds (3600 to 604800, default 86400) to cover the publish time.
- Retrying only `media_publish` after an error can post twice. Retry from container creation and keep a "posted" marker.

## MCP

`https://postcache.dev/mcp` (Streamable HTTP, same `Authorization` header). Tools: `upload_media`, `check_media`, `get_media`, `delete_media`; `upload_media` takes `source_url` or `data_base64` (up to 10 MB).
