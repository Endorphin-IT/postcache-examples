# postcache examples

[postcache](https://postcache.dev) gives AI agents a public, short-lived URL for an image or video, so they can post it to Instagram, Threads and Facebook. Those APIs only take media from a public URL; postcache hosts the file, checks it against the platform's rules before the post (and can fix it with `convert`), then deletes it.

- Docs: https://postcache.dev/docs · OpenAPI: https://postcache.dev/openapi.json · llms.txt: https://postcache.dev/llms.txt
- MCP server: `https://postcache.dev/mcp` (Streamable HTTP), listed in the MCP Registry as `dev.postcache/postcache`

## Quick start

```sh
curl -X PUT "https://postcache.dev/v1/media" \
  -H "Authorization: Bearer $POSTCACHE_API_KEY" \
  -H "x-target: instagram.feed" \
  --data-binary @photo.jpg
```

The answer has `url` (give it to the platform as `image_url` / `video_url`) and `id`. After the post is live, `DELETE /v1/media/{id}`. Targets: `instagram.feed`, `instagram.carousel`, `instagram.reels`, `instagram.story`, `threads`, `facebook.page`.

If the file breaks a rule, you get `422` with each problem and its fix. Add `?convert=crop` or `?convert=pad` and postcache fixes it for you (`202`, then poll `GET /v1/media/{id}` until `ready`). `?dry_run=1` checks without storing anything.

Paying per upload without an API key (x402 and MPP, $0.01 per upload) is coming soon. Until then, use a free key from https://postcache.dev/login.

## Examples

| | |
| --- | --- |
| [python/post_to_instagram.py](python/post_to_instagram.py) | Upload a photo, publish it to an Instagram business account, delete the file. Standard library only. |
| [node/post-to-instagram.mjs](node/post-to-instagram.mjs) | The same in Node 18+ with `fetch`. |

Both need `POSTCACHE_API_KEY`, `IG_USER_ID` (the Instagram business account id) and `IG_ACCESS_TOKEN` (a token with `instagram_content_publish`).

## Agent skill

[skills/posting-media-with-postcache](skills/posting-media-with-postcache/SKILL.md) teaches an agent the whole flow: upload per target, the platform rules, the Instagram, Threads and Facebook publishing calls, and the Meta media errors it prevents. Install it with:

```sh
npx skills add Endorphin-IT/postcache-examples
```

## MCP

Tools: `upload_media`, `check_media`, `get_media`, `delete_media`. Tool calls need the API key in the `Authorization` header.

Claude Code:

```sh
claude mcp add --transport http postcache https://postcache.dev/mcp --header "Authorization: Bearer pc_live_..."
```

Cursor, Windsurf and other clients with an `mcp.json`:

```json
{
  "mcpServers": {
    "postcache": {
      "url": "https://postcache.dev/mcp",
      "headers": { "Authorization": "Bearer pc_live_..." }
    }
  }
}
```

## License

MIT
