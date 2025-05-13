# WebRTC Demo

This is a simple voice chatbot over the phone.

It shows how to use the WebTerminalProtocol (WTP) API to intercept phone calls to a given number.

Phone call signalling allows to redirect media to a different destination.

VoiceBot uses FastRTC to establish a WebRTC connection to the Voice Core
in order to receive the media stream. Once the media stream is received,
it can be passed to any AI engine for processing.

VoiceBot demonstrates how to use OpenAIs or Google's Gemini API to do bidirectional
audio chat with LLM.

Also, for testing purposes, it can simply echo incoming audio back to the caller.

## Running the Application

### Arguments

| Argument           | Environment Variable | Required | Description              |
|--------------------|----------------------|----------|--------------------------|
| `--grpc-target`    | `GRPC_TARGET`        | `yes`    | WG2 API Gateway endpoint |
| `--client-id`      | `CLIENT_ID`          | `yes`    | WG2 Client ID            |
| `--client-secret`  | `CLIENT_SECRET`      | `yes`    | WG2 Client Secret        |
| `--msisdn`         | `MSISDN`             | `yes`    | MSISDN of subscription   |
| `--openai-api-key` | `OPENAI_API_KEY`     | `no`     | OpenAI API Key           |
| `--gemini-api-key` | `GEMINI_API_KEY`     | `no`     | Gemini API Key           |

### gRPC target

gRPC target is the regional WG2 API Gateway endpoint
This must be set to the correct endpoint for the region where your subscription is located,

This may be any of the following:

- `api.shamrock.wgtwo.com`
- `api.oak.wgtwo.com`
- `api.sakura.wgtwo.com`

See: https://developer.cisco.com/docs/mobility-services/api-environments/

### API Keys for AI Services

If you provide an API key, the application will use this service to process the audio.

If no API keys are provided, the application will run in echo test mode.

- Get your OpenAI API key from https://platform.openai.com/signup.
- Get your Gemini API key from https://aistudio.google.com/app/apikey.

### Prerequisites

You need to set up a virtual environment and install the required dependencies.

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Invoke the Application

This will run the application in echo test mode, as no API keys for AI services are provided.

```shell
export CLIENT_SECRET=my-secret

python3 app.py \
  --grpc-target=api.shamrock.wgtwo.com \
  --client-id=00f89e48-f3b9-435c-9375-7bc072e0c525 \
  --msisdn=4799000000
```

When you are done, you can deactivate the virtual environment.

```shell
deactivate
```

## Troubleshooting

You need to ensure you are on a VoIP-friendly network.
That is, UDP traffic must be allowed to pass through the network.

Otherwise, you may experience that the call is picked up but no audio is heard.
