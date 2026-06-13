# NextGen Unofficial API

Unofficial Python integrations for NextGen.

## Integrations

- `nextgen_nextgen_auth_list_patients.py` - `nextgen_auth_list_patients` (14 live events).
- `nextgen_nextgen_auth_create_patient.py` - `nextgen_auth_create_patient` (4 live events).

## Usage

Each file exposes a `run(input, context)` or `run(headers, input)` style entrypoint, matching the source integration runtime.
Authenticated request headers/cookies are expected to be supplied by the caller when required.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Info

This unofficial API is built by [Integuru.ai](https://integuru.ai/).

For custom requests or hosted authentication, contact richard@taiki.online.

See the [complete list of APIs by Integuru](https://github.com/Integuru-AI/APIs-by-Integuru).
