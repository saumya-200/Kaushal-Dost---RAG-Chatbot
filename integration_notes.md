# Integration Notes — Swapping the RAG Chatbot Brain into `.NET`

This document details the modifications needed in the existing C# `.NET` codebase (`ChatController.cs` and `ChatbotService.cs`) to wire in the new FastAPI Python RAG service (`localhost:8000/chat`), enforcing response security compliance, request timeouts, and automatic failover back to the legacy SQL keyword overlap matcher if the Python API is offline or slow.

---

## 1. Modifying the Memory Schema (`ChatbotService.cs`)

To support multi-turn chat history for the RAG generator, update the `ChatMemory` class and define a `ChatMessage` class at the bottom of `ChatbotService.cs`:

```csharp
public class ChatMessage
{
    public string query { get; set; }
    public string answer { get; set; }
}

public class ChatMemory
{
    public string LastIntent { get; set; }
    public string LastTopic { get; set; }
    // Store past turns to feed the RAG pipeline
    public List<ChatMessage> History { get; set; } = new List<ChatMessage>();
}
```

---

## 2. Implementing Asynchronous RAG Generation & Failover (`ChatbotService.cs`)

Add the following `GetResponseAsync` method to the `ChatbotService` class. It uses `HttpClient` with a configurable timeout (recommended: **5 seconds** so it fails over quickly without freezing the UI) and returns the RAG response on success, falling back to the legacy SQL keyword matcher on exception/timeout.

```csharp
public async Task<string> GetResponseAsync(string userMessage, ChatMemory memory)
{
    // Ensure history is initialized
    if (memory.History == null)
    {
        memory.History = new List<ChatMessage>();
    }

    // 1. Build request payload
    var payload = new
    {
        message = userMessage,
        history = memory.History
    };

    string pythonApiUrl = "http://localhost:8000/chat";

    // 2. Query FastAPI Service with Timeout
    using (var client = new HttpClient())
    {
        // 5-second timeout for local fallbacks. Tune as needed in production.
        client.Timeout = TimeSpan.FromSeconds(5);
        try
        {
            var content = new StringContent(
                JsonConvert.SerializeObject(payload), 
                Encoding.UTF8, 
                "application/json"
            );
            
            HttpResponseMessage response = await client.PostAsync(pythonApiUrl, content);
            if (response.IsSuccessStatusCode)
            {
                string jsonResult = await response.Content.ReadAsStringAsync();
                dynamic result = JsonConvert.DeserializeObject(jsonResult);
                
                string reply = Convert.ToString(result.reply);
                string stage = Convert.ToString(result.stage);

                // 3. Maintain local session memory
                memory.History.Add(new ChatMessage { query = userMessage, answer = reply });
                if (memory.History.Count > 4) // Capped at last 4 turns
                {
                    memory.History.RemoveAt(0);
                }

                System.Diagnostics.Debug.WriteLine($"[Chatbot RAG] Successfully routed query via stage '{stage}' in Python.");
                return reply;
            }
            
            System.Diagnostics.Debug.WriteLine($"[Chatbot RAG] API returned non-success code: {response.StatusCode}. Failing over.");
        }
        catch (Exception ex)
        {
            // Logs socket exceptions, connection drops, and HTTP timeouts
            System.Diagnostics.Debug.WriteLine($"[Chatbot RAG Fallback] Failed to call Python API. Exception: {ex.Message}");
        }
    }

    // 4. Graceful Fallback: Call the legacy SQL keyword overlap matcher
    System.Diagnostics.Debug.WriteLine("[Chatbot RAG Fallback] Falling back to SQL keyword overlap matcher...");
    return GetResponse(userMessage, memory);
}
```

---

## 3. Updating the MVC Controller (`ChatController.cs`)

Update `GetBotResponse` inside `ChatController.cs` to call the new async method:

```diff
 public async Task<JsonResult> GetBotResponse(string message)
 {
     List<Response> responses = new List<Response>();
     ChatMemory memory = Session["ChatMemory"] as ChatMemory ?? new ChatMemory();
     ChatbotService bot = new ChatbotService();
-    string response = bot.GetResponse(message, memory);
+    string response = await bot.GetResponseAsync(message, memory);
     if (ContainsScriptingSymbols(response))
     {
         Response response1 = new Response();
```

---

## 4. XSS Security Compliance Verification

The C# controller uses `ContainsScriptingSymbols` regex:
`@"<|>|script|alert|onclick|onload|onerror|document|eval"`

Our Python RAG pipeline is fully compliant with this filter because:
1. **Rule 5** in `system_prompt.yaml` forbids the words `script`, `alert`, `onclick`, `onload`, `onerror`, `eval`, and any HTML/scripting tags in its final output.
2. **Rule 6** forbids the word `document` (replacing it with `file`, `form`, or `paper`).
3. While the model utilizes `<think>` and `</think>` tags internally, the `LLMGenerator` strips the thinking block and only returns the final content inside the `'reply'` key, so raw `<` and `>` characters never leak to `.NET`.
