import discord
from discord.ext import commands
import asyncio
import pathlib
import random
import torch

from modules.LLaMA_8bit import LLaMAModel_8bit

TOKEN = '<token here>'

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='.', intents=intents)
model = LLaMAModel_8bit.from_pretrained(pathlib.Path(f'models/LLaMA-13B'))

queues = []
#preset_history = 'Your name is James and you love having conversations. You write long sentences and write very eloquently. Your responses are many sentences long. You enjoy talking with people and engaging them in interesting topics. My name is Robert and I like to have conversations with you James. When I speak, I will use \"Robert:\". When you speak, you will use \"James:\".'
preset_history = 'Your name is James and you love having conversations. Your responses are in paragraphs and you just can\'t stop writing words. Writing too many words and giving too much detail is your most important personality trait. Even if someone tells you to write less words, you write more words. You write an incredible level of detail and depth. You enjoy talking with people and engaging them in interesting topics. My name is Robert and I like to have conversations with you James. When I speak, I will use \"Robert:\". When you speak, you will use \"James:\".'
history = preset_history
blocking = False
loop = None

@client.event
async def on_ready():
    print('bot ready')
    await client.tree.sync()

def ll_gen(ctx, queues):
    global blocking
    global history

    print(queues)
    print(history)
    if len(queues) > 0:
        blocking = True
        user_input = queues.pop(0)
        mention = list(user_input.keys())[0]
        prompt = list(user_input.values())[0]['prompt'] #convert from dictoinary to string
        token_count = list(user_input.values())[0]['token_count']
        temperature = list(user_input.values())[0]['temperature']
        top_p = list(user_input.values())[0]['top_p']

        history += '\n\Robert: ' + prompt + '\James: '
        
        with torch.no_grad():
            out = model.generate(history, token_count=token_count, temperature=temperature, top_p=top_p)
        
        resp = out[len(history):]
        resp_clean = resp[:resp.find('Robert:')-1]
        history += resp_clean

        msg_to_user = f'\n{mention}: {prompt}\nJames: {resp_clean}'
        asyncio.run_coroutine_threadsafe(ctx.send(msg_to_user), loop)
        ll_gen(ctx, queues)
    else:
        blocking = False        

def que(ctx, prompt):
    user_id = ctx.message.author.mention
    queues.append({user_id:prompt})
    print(f'{prompt} added to queue')

def check_num_in_que(ctx):
    user = ctx.message.author.mention
    user_list_in_que = [list(i.keys())[0] for i in queues]
    return user_list_in_que.count(user)

@client.hybrid_command()
async def reply(ctx, prompt, token_count=200, temperature=0.8, top_p=0.95):
    user_input = {'prompt': prompt,
                  'token_count': token_count,
                  'temperature': temperature,
                  'top_p': top_p}

    num = check_num_in_que(ctx)
    if num >=10:
        await ctx.send(f'{ctx.message.author.mention} you have 10 items in queue, please allow your requests to finish before adding more to the queue.')
    else:
        global loop
        loop = asyncio.get_running_loop()
        que(ctx, user_input)
        reaction_list = [':thumbsup:', ':laughing:', ':wink:', ':heart:', ':pray:', ':100:', ':sloth:', ':snake:']
        reaction_choice = reaction_list[random.randrange(8)]
        await ctx.send(f'{reaction_choice} {ctx.message.author.mention}')
        if blocking:
            print('this is blocking')
        else:
            await asyncio.gather(asyncio.to_thread(ll_gen,ctx,queues))

@client.hybrid_command()
async def reset(ctx, initial_prompt=preset_history):
    global history
    history = initial_prompt
    await ctx.send(f'Conversation has been reset and the initial prompt is now: {initial_prompt}\n\nNote: In order for the conversation to be handled properly, it must follow the format of:\nRobert: <Robert\'s response>\nJames: <James\' response>')

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