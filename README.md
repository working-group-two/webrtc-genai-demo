# WebRTC Demo

The WebTerminalProtocol (WTP) API may be used to intercept phone calls to a given number as described in
https://developer.cisco.com/docs/mobility-services/how-to-make-and-receive-webrtc-calls/.

## Voicebot

The demo application can be found in the [voicebot](voicebot) directory.

The Voicebot is a simple voice chatbot over the phone, written in Python using our hosted Python SDK
from https://buf.build/wgtwo/wgtwoapis/docs/main:wgtwo.webterminal.v0.

When running, this application will pick up any call to your subscription and forward that to either the echo service,
ChatGPT, or Gemini.

This application is not in any way affiliated with OpenAI or Google, and is not intended for production use.
