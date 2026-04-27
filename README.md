# Ambient Weather Local Push

Home Assistant custom integration for Ambient Weather stations using the local
custom server push protocol.

## Installation with HACS

1. Add this repository as a custom HACS integration repository.
2. Install **Ambient Weather Local Push**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and add
   **Ambient Weather Local Push**.
5. Configure your station with the host, path, and port shown by the setup
   dialog.

The generated path includes `?q=1` by design. Ambient Weather stations append
payload values with `&PASSKEY=...`; priming the query string keeps the webhook
request valid for Home Assistant.

Sensor definitions and calculations are based on
[`tlskinneriv/awnet_local`](https://github.com/tlskinneriv/awnet_local), adapted
for direct webhook ingestion.
