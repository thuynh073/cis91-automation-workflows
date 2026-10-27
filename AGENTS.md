# Working with the CIS 91 n8n server

- The n8n API is at https://n8n-cis091.codislabs.club/api/v1
- My API key is in the environment variable N8N_API_KEY. Send it in the
  header `X-N8N-API-KEY: $N8N_API_KEY`. Never print the key.
- Use curl to call the API. Workflows are JSON with name, nodes,
  connections and settings.
- My initials are JH. Start every workflow name with "JH - ".
- Only create or change the workflows I name. Never delete a workflow,
  and never activate or deactivate one.
