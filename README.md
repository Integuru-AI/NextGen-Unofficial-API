# NextGen Unofficial API

Unofficial Python integrations for NextGen.

## Integrations

- `nextgen_query_appointments.py` - `query_appointments` (2,323 live events).
- `nextgen_list_patients.py` - `list_patients` (975 live events).
- `nextgen_list_locations.py` - `list_locations` (393 live events).
- `nextgen_create_appointment.py` - `create_appointment` (54 live events).

## Usage

Each file exposes a `run(input, context)` entrypoint. The runtime is expected to provide:

- `input`: integration-specific request fields.
- `context["headers"]`: authenticated request headers when required.
- `context["base_url"]`: the platform base URL when overriding the default.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Info

This unofficial API is built by [Integuru.ai](https://integuru.ai/).

For custom requests or hosted authentication, contact richard@taiki.online.

See the [complete list of APIs by Integuru](https://github.com/Integuru-AI/APIs-by-Integuru).
