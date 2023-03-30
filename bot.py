from datetime import datetime, timedelta
import asyncio
import random
import logging
import discord
from discord.ext import commands
from discord import app_commands
import torch

from modules.chat import chatbot_wrapper, clear_chat_log
from modules import shared
shared.args.cai_chat = True
from modules.LoRA import add_lora_to_model
from modules.models import load_model

TOKEN = "<token here>"

prompt = "This is a conversation between two people."
your_name = "Person 1"
llamas_name = "Person 2"

reply_embed_json = {
    "title": "Reply #X",
    "color": 39129,
    "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
    "url": "https://github.com/xNul/chat-llama-discord-bot",
    "footer": {
        "text": "Contribute to ChatLLaMA on GitHub!",
    },
    "fields": [
        {
            "name": your_name,
            "value": ""
        },
        {
            "name": llamas_name,
            "value": ":arrows_counterclockwise:"
        }
    ]
}
reply_embed = discord.Embed().from_dict(reply_embed_json)

reset_embed_json = {
    "title": "Conversation has been reset",
    "description": "Replies: 0\nYour name: " + your_name + "\nLLaMA's name: " + llamas_name + "\nPrompt: " + prompt,
    "color": 39129,
    "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
    "url": "https://github.com/xNul/chat-llama-discord-bot",
    "footer": {
        "text": "Contribute to ChatLLaMA on GitHub!"
    }
}
reset_embed = discord.Embed().from_dict(reset_embed_json)

status_embed_json = {
    "title": "Status",
    "description": "You don't have a job queued.",
    "color": 39129,
    "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
    "url": "https://github.com/xNul/chat-llama-discord-bot",
    "footer": {
        "text": "Contribute to ChatLLaMA on GitHub!"
    }
}
status_embed = discord.Embed().from_dict(status_embed_json)

shared.model_name = shared.args.model
shared.model, shared.tokenizer = load_model(shared.model_name)

if shared.args.lora:
    add_lora_to_model(shared.args.lora)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=".", intents=intents)

queues = []
blocking = False
loop = None
reply_count = 0

@client.event
async def on_ready():
    logging.info("bot ready")
    await client.tree.sync()

async def ll_gen(ctx, queues):
    global blocking
    global reply_count

    if len(queues) > 0:
        blocking = True
        reply_count += 1
        user_input = queues.pop(0)
        mention = list(user_input.keys())[0]
        user_input = user_input[mention]
        user_input["name1"] = your_name
        user_input["name2"] = llamas_name
        user_input["context"] = prompt
        user_input["check"] = False
        
        # Prevents the embed character limit error
        embed_user_input_text = user_input["text"]
        if len(user_input["text"]) > 1024:
            embed_user_input_text = user_input["text"][:1021] + "..."
        
        reply_embed.set_field_at(index=0, name=your_name, value=embed_user_input_text, inline=False)
        reply_embed.title = "Reply #" + str(reply_count)
        reply_embed.timestamp = datetime.now() - timedelta(hours=3)
        
        msg = await ctx.send(embed=reply_embed)
        last_resp = ""
        for resp in chatbot_wrapper(**user_input):
            resp_clean = resp[len(resp)-1][1]
            last_resp = resp_clean
            msg_to_user = last_resp + ":arrows_counterclockwise:"
            
            # Prevents the embed character limit error
            if len(last_resp) > 1024:
                last_resp = last_resp[:1024]
                break
            
            reply_embed.set_field_at(index=1, name=llamas_name, value=msg_to_user, inline=False)
            await msg.edit(embed=reply_embed)
        
        logging.info("reply sent: \"" + mention + ": {'text': '" + user_input["text"] + "', 'response': '" + last_resp + "'}\"")
        reply_embed.set_field_at(index=1, name=llamas_name, value=last_resp, inline=False)
        await msg.edit(embed=reply_embed)
        await ll_gen(ctx, queues)
    else:
        blocking = False

def que(ctx, user_input):
    user_id = ctx.message.author.mention
    queues.append({user_id:user_input})
    logging.info(f'reply requested: "{user_id}: {user_input}"')

def check_num_in_que(ctx):
    user = ctx.message.author.mention
    user_list_in_que = [list(i.keys())[0] for i in queues]
    return user_list_in_que.count(user)

@client.hybrid_command(description="Reply to LLaMA")
@app_commands.describe(text="Text")
async def reply(ctx, text, max_new_tokens=200, do_sample=True, temperature=1.99, top_p=0.18, typical_p=1, repetition_penalty=1.15, encoder_repetition_penalty=1, top_k=30, min_length=0, no_repeat_ngram_size=0, num_beams=1, penalty_alpha=0, length_penalty=1, early_stopping=False, seed=-1.0, chat_prompt_size=2048, chat_generation_attempts=1, regenerate=False):
    user_input = {"text": text,
                  "max_new_tokens": max_new_tokens,
                  "do_sample": do_sample,
                  "temperature": temperature,
                  "top_p": top_p,
                  "typical_p": typical_p,
                  "repetition_penalty": repetition_penalty,
                  "encoder_repetition_penalty": encoder_repetition_penalty,
                  "top_k": top_k,
                  "min_length": min_length,
                  "no_repeat_ngram_size": no_repeat_ngram_size,
                  "num_beams": num_beams,
                  "penalty_alpha": penalty_alpha,
                  "length_penalty": length_penalty,
                  "early_stopping": early_stopping,
                  "seed": seed,
                  "chat_prompt_size": chat_prompt_size,
                  "chat_generation_attempts": chat_generation_attempts,
                  "regenerate": regenerate}

    num = check_num_in_que(ctx)
    if num >=10:
        await ctx.send(f'{ctx.message.author.mention} you have 10 items in queue, please allow your requests to finish before adding more to the queue.')
    else:
        global loop
        loop = asyncio.get_running_loop()
        que(ctx, user_input)
        reaction_list = [":thumbsup:", ":laughing:", ":wink:", ":heart:", ":pray:", ":100:", ":sloth:", ":snake:"]
        reaction_choice = reaction_list[random.randrange(8)]
        await ctx.send(f'{ctx.message.author.mention} {reaction_choice} Processing reply...')
        if blocking:
            logging.warning("reply blocking")
        else:
            await ll_gen(ctx, queues)

@client.hybrid_command(description="Reset the conversation with LLaMA")
@app_commands.describe(
    prompt_new="The initial prompt to contextualize LLaMA",
    your_name_new="The name which all users speak as",
    llamas_name_new="The name which LLaMA speaks as"
)
async def reset(ctx, prompt_new=prompt, your_name_new=your_name, llamas_name_new=llamas_name):
    global prompt
    global your_name
    global llamas_name
    global reply_count
    
    prompt = prompt_new
    your_name = your_name_new
    llamas_name = llamas_name_new
    reply_count = 0
    
    shared.stop_everything = True
    clear_chat_log(your_name, llamas_name)
    
    logging.info("conversation reset: {'replies': " + str(reply_count) + ", 'your_name': '" + your_name + "', 'llamas_name': '" + llamas_name + "', 'prompt': '" + prompt + "'}")
    reset_embed.timestamp = datetime.now() - timedelta(hours=3)
    reset_embed.description = "Replies: " + str(reply_count) + "\nYour name: " + your_name + "\nLLaMA's name: " + llamas_name + "\nPrompt: " + prompt
    await ctx.send(embed=reset_embed)

@client.hybrid_command(description="Check the status of your reply queue position and wait time")
async def status(ctx):
    total_num_queued_jobs = len(queues)
    que_user_ids = [list(a.keys())[0] for a in queues]
    if ctx.message.author.mention in que_user_ids:
        user_position = que_user_ids.index(ctx.message.author.mention)+1
        msg = f'{ctx.message.author.mention} Your job is currently {user_position} out of {total_num_queued_jobs} in the queue. Estimated time until response is ready: {user_position * 3/60} minutes.'
    else:
        msg = f'{ctx.message.author.mention} doesn\'t have a job queued.'

    status_embed.timestamp = datetime.now() - timedelta(hours=3)
    status_embed.description = msg
    await ctx.send(embed=status_embed)

client.run(TOKEN, root_logger=True)