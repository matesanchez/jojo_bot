====================================================
  JOJO BOT v1.0 — Purification Expert
  Internal Tool — Nurix Therapeutics
====================================================

QUICK START
-----------
1. Double-click "Jojo Bot.exe"  ← look for the Jojo avatar icon
   The app opens in its own dedicated window — no browser tab, no
   terminal windows. Everything runs quietly in the background.
2. The Jojo Bot window opens automatically
3. Click the gear icon (⚙) in the top-right corner
4. Go to the "API Key" tab and enter your Anthropic API key
   (Get one at https://console.anthropic.com — pay-as-you-go)
5. Click Save — you're ready to chat!

Your API key is stored only on YOUR computer (in your user profile
at %APPDATA%\JojoBot\config.json). It is never shared with anyone.


ADDING YOUR OWN DOCUMENTS
--------------------------
Jojo Bot comes pre-loaded with 232 ÄKTA manuals and Nurix SOPs.
To add more PDFs to the knowledge base:

1. Open the app and click the gear icon (⚙)
2. Go to the "Knowledge Base" tab
3. Drop your PDF files into the upload area
4. Choose the document type from the dropdown
5. Click "Add to Knowledge Base"
6. Jojo Bot will process and index the new documents immediately


STOPPING JOJO BOT
-----------------
Just close the Jojo Bot window — the background servers shut down automatically.
Alternatively, double-click "Stop Jojo Bot.bat" to force-stop everything.


PORTS USED
----------
Backend API:  http://localhost:8000
Frontend UI:  http://localhost:3000
Both ports are local-only. Nothing is accessible from outside your computer.


TROUBLESHOOTING
---------------
• "Cannot reach the backend server" banner
  → The background server may have crashed. Close Jojo Bot and relaunch it.
  → Or double-click "Start Jojo Bot.bat" as a fallback.

• App opens but gives an error on every message
  → Check that you've entered your API key in Settings (⚙).
  → Verify your Anthropic account has credits at console.anthropic.com.

• App opens in a browser tab instead of its own window
  → Your PC may need a Windows Update to get the Edge WebView2 runtime.
  → The app still works — it just opens in your default browser instead.

• Port already in use
  → Another app is using port 3000 or 8000.
  → Run "Stop Jojo Bot.bat" first, then relaunch "Jojo Bot.exe".

• Very slow first response
  → Normal — ChromaDB loads the full vector index on first query.
  → Subsequent responses are much faster.


SYSTEM REQUIREMENTS
-------------------
• Windows 10 or 11 (64-bit)
• 4 GB RAM minimum, 8 GB recommended
• ~2 GB disk space (mostly the knowledge base)
• Internet connection (for Anthropic API calls only)
• No Python, Node.js, or other software installation required


COST
----
Jojo Bot uses the Anthropic Claude API (pay-as-you-go).
Typical question costs $0.01–0.05 depending on context length.
There is no subscription — you only pay for what you use.
Monitor your usage at https://console.anthropic.com/usage


====================================================
  Questions? Contact the Protein Sciences team.
====================================================
