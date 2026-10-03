# Learning OS — Persistent Web UI

This is the first persistent UI boundary for the Learning OS.

## Architecture

```text
Android/browser
      ↓
Persistent UI at one URL
      ↓ fetch('/api/...')
Local Learning OS server
      ↓
Airtable REST API
      ↓
Learning state / missions / projects / radar
```

The browser never receives the Airtable token. The token lives only in the server process environment.

## Start

On the machine running the local server:

```bash
export AIRTABLE_TOKEN='your_token_here'
./start.sh
```

Open:

```text
http://127.0.0.1:8000
```

From a phone on the same LAN, use the computer's LAN address:

```text
http://<computer-ip>:8000
```

## Important behavior

- The HTML page is persistent; it is not regenerated for every session.
- The UI reads current state from `/api/state`.
- Airtable remains the source of truth.
- Offline mode does not fabricate learner state.
- Project progress and project decisions remain separate from mastery.
- New visual artifacts can be added later as reusable learning components inside this same application.

## Current scope

Implemented UI surfaces:

- Home / current mission
- Adaptive mode selection
- Mission view
- Projects
- Technology Radar
- Backend health indicator

Not yet connected in this layer:

- Full assessment submission
- Voice interview capture
- Full Visual Engine artifact loader
- Direct checkpoint commit

Those remain engine/API integration steps rather than static HTML generation.
