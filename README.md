# ChatLLaMA Discord Bot

A Discord Bot for chatting with LLaMA. Does not include RLHF, but LLaMA is pretty impressive on its own. Use `/reply` to prompt LLaMA. To clear chat history with LLaMA or change the initial prompt, use `/reset`. Oftentimes LLaMA will get stuck in a loop or you will want to change the initial prompt to something more interesting so `/reset` is well used.

1. Get LLaMA setup and working with https://github.com/oobabooga/text-generation-webui (more information [here](https://github.com/oobabooga/text-generation-webui/issues/147))

2. Edit `bot.py` with your Discord bot's token and LLaMA model (default is 13B 8-bit)

3. Place `bot.py` inside the root of the text-generation-webui directory

4. Run `python bot.py`
