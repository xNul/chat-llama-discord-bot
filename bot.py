import discord
from discord.ext import commands
import asyncio
import random
import torch

import modules.shared as shared
from modules.models import load_model
from modules.chat import chatbot_wrapper, clear_chat_log

TOKEN = "<token here>"

prompt = "This is a conversation between two people."
person_1 = "Person 1"
person_2 = "Person 2"

shared.args.chat = True
shared.model_name = shared.args.model
shared.model, shared.tokenizer = load_model(shared.model_name)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=".", intents=intents)

queues = []
blocking = False
loop = None

@client.event
async def on_ready():
    print("bot ready")
    await client.tree.sync()

async def ll_gen(ctx, queues):
    global blocking

    print(queues)
    if len(queues) > 0:
        blocking = True
        user_input = queues.pop(0)
        mention = list(user_input.keys())[0]
        user_input = user_input[mention]
        user_input["name1"] = person_1
        user_input["name2"] = person_2
        user_input["context"] = prompt
        user_input["check"] = True
        
        msg = None
        last_resp = ""
        for resp in chatbot_wrapper(**user_input):
            resp_clean = resp[len(resp)-1][1]
            last_resp = f'\n{mention}: {user_input["text"]}\n{person_2}: {resp_clean}'
            msg_to_user = last_resp + ":arrows_counterclockwise:"
            
            if msg:
                await msg.edit(content=msg_to_user)
            elif resp_clean != "":
                msg = await ctx.send(msg_to_user)
        
        await msg.edit(content=last_resp)
        await ll_gen(ctx, queues)
    else:
        blocking = False        

def que(ctx, user_input):
    user_id = ctx.message.author.mention
    queues.append({user_id:user_input})
    print(f'{user_input} added to queue')

def check_num_in_que(ctx):
    user = ctx.message.author.mention
    user_list_in_que = [list(i.keys())[0] for i in queues]
    return user_list_in_que.count(user)

@client.hybrid_command()
async def reply(ctx, text, max_new_tokens=200, do_sample=True, temperature=1.99, top_p=0.18, typical_p=1, repetition_penalty=1.15, top_k=30, min_length=0, no_repeat_ngram_size=0, num_beams=1, penalty_alpha=0, length_penalty=1, early_stopping=False, chat_prompt_size=2048, chat_generation_attempts=1):
    user_input = {"text": text,
                  "max_new_tokens": max_new_tokens,
                  "do_sample": do_sample,
                  "temperature": temperature,
                  "top_p": top_p,
                  "typical_p": typical_p,
                  "repetition_penalty": repetition_penalty,
                  "top_k": top_k,
                  "min_length": min_length,
                  "no_repeat_ngram_size": no_repeat_ngram_size,
                  "num_beams": num_beams,
                  "penalty_alpha": penalty_alpha,
                  "length_penalty": length_penalty,
                  "early_stopping": early_stopping,
                  "chat_prompt_size": chat_prompt_size,
                  "chat_generation_attempts": chat_generation_attempts}

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
            print("this is blocking")
        else:
            await ll_gen(ctx, queues)

@client.hybrid_command()
async def reset(ctx, prompt_new=prompt):
    global prompt
    prompt = prompt_new
    clear_chat_log(person_1, person_2)
    await ctx.send(f'Conversation has been reset and the initial prompt is now: {prompt}\n\nNote: In order for the conversation to be handled properly, it must follow the format of:\n{person_1}: <{person_1}\'s response>\n{person_2}: <{person_2}\' response>')

@client.hybrid_command()
async def change_names(ctx, person_1_new=person_1, person_2_new=person_2):
    global person_1
    global person_2
    person_1 = person_1_new
    person_2 = person_2_new
    await ctx.send(f'Names have been changed to "{person_1}" and "{person_2}"')

@client.hybrid_command()
async def status(ctx):
    total_num_queued_jobs = len(queues)
    que_user_ids = [list(a.keys())[0] for a in queues]
    if ctx.message.author.mention in que_user_ids:
        user_position = que_user_ids.index(ctx.message.author.mention)
        msg = f'{ctx.message.author.mention} Your job is currently {user_position}/{total_num_queued_jobs} in queue. Estimated time until response is ready: {user_position * 30/60} minutes.'
    else:
        msg = f'{ctx.message.author.mention} you don\'t have a job queued.'

    await ctx.send(msg)

@client.hybrid_command()
async def showqueue(ctx):
    await ctx.send(queues)
    print(queues)

client.run(TOKEN)