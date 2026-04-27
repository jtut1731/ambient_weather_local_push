# Ambient Weather Local Push

Home Assistant custom integration for Ambient Weather stations using the local
custom server push protocol.

Developed and tested with WS-2000. Please create an Issue and report if it works
with any other models.

### Working Models
- WS-2000

## Installation with HACS

1. Add this repository as a custom HACS integration repository.
2. Install **Ambient Weather Local Push**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and add
   **Ambient Weather Local Push**.
5. Configure your station with the host, path, and port shown by the setup
   dialog. (*See note below)
>Note: The generated path includes `?q=1` by design. Ambient Weather
stations append non-HTTP-compliant payload values with `&PASSKEY=...`; priming
the query string keeps the webhook request valid for Home Assistant.

<img width="735" height="427" alt="image" src="https://github.com/user-attachments/assets/e8762e37-86df-4dbc-9371-fba77fd4cebe" />
<br>
<br>
Sensor definitions and calculations are based on
[`tlskinneriv/awnet_local`](https://github.com/tlskinneriv/awnet_local), adapted
for direct webhook ingestion without the need for any Home Assistant Apps such
as [`AWNET`](https://github.com/tlskinneriv/hassio-addons/tree/master/awnet).
