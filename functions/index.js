const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const fetch = require("node-fetch");

// Securely stored in Google Secret Manager
const GROQ_API_KEY = defineSecret("GROQ_API_KEY");

exports.aiProxy = onCall(
  { secrets: [GROQ_API_KEY], cors: true },
  async (request) => {
    // 1. Require authentication
    if (!request.auth) {
      throw new HttpsError("unauthenticated", "You must be signed in.");
    }

    const { messages, systemPrompt, model, temperature, maxTokens } = request.data;

    if (!Array.isArray(messages) || messages.length === 0) {
      throw new HttpsError("invalid-argument", "messages array is required.");
    }

    // 2. Cap history to avoid token blowup
    const trimmed = messages.slice(-10);

    const body = {
      model: model || "llama-3.3-70b-versatile",
      messages: [
        ...(systemPrompt ? [{ role: "system", content: systemPrompt }] : []),
        ...trimmed,
      ],
      temperature: temperature ?? 0.7,
      max_tokens: maxTokens ?? 800,
    };

    // 3. Call Groq
    let response;
    try {
      response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${GROQ_API_KEY.value()}`,
        },
        body: JSON.stringify(body),
      });
    } catch (err) {
      console.error("Groq fetch error:", err);
      throw new HttpsError("internal", "Could not reach AI service.");
    }

    if (!response.ok) {
      const text = await response.text();
      console.error("Groq API error:", response.status, text);
      if (response.status === 429) {
        throw new HttpsError("resource-exhausted", "AI rate limit reached. Try again in a moment.");
      }
      throw new HttpsError("internal", `AI service error (${response.status}).`);
    }

    const result = await response.json();
    const reply = result.choices?.[0]?.message?.content || "";

    return {
      reply,
      model: result.model,
      usage: result.usage,
    };
  }
);