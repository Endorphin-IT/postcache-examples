// Post a photo to Instagram through postcache (Node 18+).
//
//   POSTCACHE_API_KEY=pc_live_... IG_USER_ID=... IG_ACCESS_TOKEN=... node post-to-instagram.mjs photo.jpg "Caption"
//
// 1. Upload the file to postcache; it checks the photo against Instagram's feed rules (convert=pad fixes size and format).
// 2. Give the public URL to the Instagram Graph API and publish.
// 3. Delete the file from postcache.
import { readFile } from 'node:fs/promises'
import { basename } from 'node:path'

const POSTCACHE = 'https://postcache.dev/v1/media'
const GRAPH = 'https://graph.facebook.com/v23.0/'
const auth = { authorization: `Bearer ${process.env.POSTCACHE_API_KEY}` }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function graph(method, path, params = {}) {
  const body = new URLSearchParams({ ...params, access_token: process.env.IG_ACCESS_TOKEN })
  const res = method === 'POST' ? await fetch(GRAPH + path, { method, body }) : await fetch(`${GRAPH}${path}?${body}`)
  const json = await res.json()
  if (json.error) throw new Error(`Meta: ${json.error.message}`)
  return json
}

async function upload(path) {
  const res = await fetch(`${POSTCACHE}?convert=pad`, {
    method: 'PUT',
    headers: { ...auth, 'x-target': 'instagram.feed', 'x-filename': basename(path) },
    body: await readFile(path),
  })
  let media = await res.json()
  while (media.status === 'converting') { // postcache is fixing the file
    await sleep(3000)
    media = await (await fetch(`${POSTCACHE}/${media.id}`, { headers: auth })).json()
  }
  if (!media.url) throw new Error(`postcache: ${JSON.stringify(media.checks ?? media)}`)
  return media
}

const [path, caption = ''] = process.argv.slice(2)
const media = await upload(path)
try {
  const ig = process.env.IG_USER_ID
  const { id: container } = await graph('POST', `${ig}/media`, { image_url: media.url, caption })
  for (let i = 0; i < 30; i++) { // Instagram fetches the URL in the background
    if ((await graph('GET', container, { fields: 'status_code' })).status_code === 'FINISHED') break
    await sleep(5000)
  }
  const { id: post } = await graph('POST', `${ig}/media_publish`, { creation_id: container })
  console.log('published:', (await graph('GET', post, { fields: 'permalink' })).permalink)
} finally {
  await fetch(`${POSTCACHE}/${media.id}`, { method: 'DELETE', headers: auth })
}
