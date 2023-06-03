from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
import asyncio
import random
import json
import re
import copy
import logging
import math
import glob
import os
import warnings
import discord
from discord.ext import commands
from discord import app_commands
import torch

logger = logging.getLogger("discord")
logger.propagate = False

# Intercept custom bot arguments
import sys
bot_arg_list = ["--limit-history", "--token"]
bot_argv = []
for arg in bot_arg_list:
    try:
        index = sys.argv.index(arg)
    except:
        index = None
    
    if index is not None:
        bot_argv.append(sys.argv.pop(index))
        bot_argv.append(sys.argv.pop(index))

import argparse
parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=54))
parser.add_argument("--token", type=str, help="Discord bot token to use their API.")
parser.add_argument("--limit-history", type=int, help="When the history gets too large, performance issues can occur. Limit the history to improve performance.")
bot_args = parser.parse_args(bot_argv)

os.environ["BITSANDBYTES_NOWELCOME"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, message="TypedStorage is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="You have modified the pretrained model configuration to control generation")

import modules.extensions as extensions_module
from modules.chat import generate_chat_reply, clear_chat_log, load_character
from modules import shared, utils
shared.args.chat = True
from modules.LoRA import add_lora_to_model
from modules.models import load_model

TOKEN = "<token here>"

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
            "name": "",
            "value": ""
        },
        {
            "name": "",
            "value": ":arrows_counterclockwise:"
        }
    ]
}
reply_embed = discord.Embed().from_dict(reply_embed_json)

reset_embed_json = {
    "title": "Conversation has been reset",
    "description": "Replies: 0\nYour name: \nLLaMA's name: \nPrompt: ",
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

# Load text-generation-webui
# Define functions
def get_model_specific_settings(model):
    settings = shared.model_config
    model_settings = {}

    for pat in settings:
        if re.match(pat.lower(), model.lower()):
            for k in settings[pat]:
                model_settings[k] = settings[pat][k]

    return model_settings

def list_model_elements():
    elements = ["cpu_memory", "auto_devices", "disk", "cpu", "bf16", "load_in_8bit", "load_in_4bit", "compute_dtype", "quant_type", "use_double_quant", "wbits", "groupsize", "model_type", "pre_layer", "threads", "n_batch", "no_mmap", "mlock", "n_gpu_layers", "n_ctx", "llama_cpp_seed"]
    for i in range(torch.cuda.device_count()):
        elements.append(f"gpu_memory_{i}")

    return elements

def load_preset_values(preset_menu, state, return_dict=False):
    generate_params = {
        "do_sample": True,
        "temperature": 1,
        "top_p": 1,
        "typical_p": 1,
        "epsilon_cutoff": 0,
        "eta_cutoff": 0,
        "repetition_penalty": 1,
        "encoder_repetition_penalty": 1,
        "top_k": 50,
        "num_beams": 1,
        "penalty_alpha": 0,
        "min_length": 0,
        "length_penalty": 1,
        "no_repeat_ngram_size": 0,
        "early_stopping": False,
        "mirostat_mode": 0,
        "mirostat_tau": 5.0,
        "mirostat_eta": 0.1,
    }
    
    with open(Path(f"presets/{preset_menu}.txt"), "r") as infile:
        preset = infile.read()
    for i in preset.splitlines():
        i = i.rstrip(",").strip().split("=")
        if len(i) == 2 and i[0].strip() != "tokens":
            generate_params[i[0].strip()] = eval(i[1].strip())
    
    generate_params["temperature"] = min(1.99, generate_params["temperature"])
    if return_dict:
        return generate_params
    else:
        state.update(generate_params)
        return state, *[generate_params[k] for k in ["do_sample", "temperature", "top_p", "typical_p", "epsilon_cutoff", "eta_cutoff", "repetition_penalty", "encoder_repetition_penalty", "top_k", "min_length", "no_repeat_ngram_size", "num_beams", "penalty_alpha", "length_penalty", "early_stopping", "mirostat_mode", "mirostat_tau", "mirostat_eta"]]

# Update the command-line arguments based on the interface values
def update_model_parameters(state, initial=False):
    elements = list_model_elements()  # the names of the parameters
    gpu_memories = []

    for i, element in enumerate(elements):
        if element not in state:
            continue

        value = state[element]
        if element.startswith("gpu_memory"):
            gpu_memories.append(value)
            continue

        if initial and vars(shared.args)[element] != vars(shared.args_defaults)[element]:
            continue

        # Setting null defaults
        if element in ["wbits", "groupsize", "model_type"] and value == "None":
            value = vars(shared.args_defaults)[element]
        elif element in ["cpu_memory"] and value == 0:
            value = vars(shared.args_defaults)[element]

        # Making some simple conversions
        if element in ["wbits", "groupsize", "pre_layer"]:
            value = int(value)
        elif element == "cpu_memory" and value is not None:
            value = f"{value}MiB"

        if element in ["pre_layer"]:
            value = [value] if value > 0 else None

        setattr(shared.args, element, value)

    found_positive = False
    for i in gpu_memories:
        if i > 0:
            found_positive = True
            break

    if not (initial and vars(shared.args)["gpu_memory"] != vars(shared.args_defaults)["gpu_memory"]):
        if found_positive:
            shared.args.gpu_memory = [f"{i}MiB" for i in gpu_memories]
        else:
            shared.args.gpu_memory = None

# Loading custom settings
settings_file = None
if shared.args.settings is not None and Path(shared.args.settings).exists():
    settings_file = Path(shared.args.settings)
elif Path("settings.json").exists():
    settings_file = Path("settings.json")

if settings_file is not None:
    logger.info(f"Loading settings from {settings_file}...")
    new_settings = json.loads(open(settings_file, "r").read())
    for item in new_settings:
        shared.settings[item] = new_settings[item]

# Set default model settings based on settings.json
shared.model_config[".*"] = {
    "wbits": "None",
    "model_type": "None",
    "groupsize": "None",
    "pre_layer": 0,
    "mode": shared.settings["mode"],
    "skip_special_tokens": shared.settings["skip_special_tokens"],
    "custom_stopping_strings": shared.settings["custom_stopping_strings"],
}

shared.model_config.move_to_end(".*", last=False)  # Move to the beginning

# Default extensions
extensions_module.available_extensions = utils.get_available_extensions()
if shared.is_chat():
    for extension in shared.settings["chat_default_extensions"]:
        shared.args.extensions = shared.args.extensions or []
        if extension not in shared.args.extensions:
            shared.args.extensions.append(extension)
else:
    for extension in shared.settings["default_extensions"]:
        shared.args.extensions = shared.args.extensions or []
        if extension not in shared.args.extensions:
            shared.args.extensions.append(extension)

available_models = utils.get_available_models()

# Model defined through --model
if shared.args.model is not None:
    shared.model_name = shared.args.model

# Only one model is available
elif len(available_models) == 1:
    shared.model_name = available_models[0]

# Select the model from a command-line menu
elif shared.args.model_menu:
    if len(available_models) == 0:
        logger.error("No models are available! Please download at least one.")
        sys.exit(0)
    else:
        print("The following models are available:\n")
        for i, model in enumerate(available_models):
            print(f"{i+1}. {model}")

        print(f"\nWhich one do you want to load? 1-{len(available_models)}\n")
        i = int(input()) - 1
        print()

    shared.model_name = available_models[i]

# If any model has been selected, load it
if shared.model_name != "None":
    model_settings = get_model_specific_settings(shared.model_name)
    shared.settings.update(model_settings)  # hijacking the interface defaults
    update_model_parameters(model_settings, initial=True)  # hijacking the command-line arguments

    # Load the model
    shared.model, shared.tokenizer = load_model(shared.model_name)
    if shared.args.lora:
        add_lora_to_model(shared.args.lora)

# Use the model parameters for LLaMA
default_preset = shared.settings['presets'][next((k for k in shared.settings['presets'] if re.match(k.lower(), shared.model_name.lower())), 'default')]
preset_menu = default_preset if not shared.args.flexgen else "Naive"

# Importing the extension files and executing their setup() functions
if shared.args.extensions is not None and len(shared.args.extensions) > 0:
    extensions_module.load_extensions()

generate_model_params = load_preset_values(preset_menu, {}, return_dict=True)

name1_instruct, name2_instruct, _, _, context_instruct, turn_template = load_character(shared.settings["instruction_template"], '', '', instruct=True)
name1, name2, _, greeting, context, _ = load_character("None", shared.settings["name1"], shared.settings["name2"], instruct=False)

# Finding the default values for the GPU and CPU memories
total_mem = []
for i in range(torch.cuda.device_count()):
    total_mem.append(math.floor(torch.cuda.get_device_properties(i).total_memory / (1024 * 1024)))

default_gpu_mem = []
if shared.args.gpu_memory is not None and len(shared.args.gpu_memory) > 0:
    for i in shared.args.gpu_memory:
        if "mib" in i.lower():
            default_gpu_mem.append(int(re.sub("[a-zA-Z ]", "", i)))
        else:
            default_gpu_mem.append(int(re.sub("[a-zA-Z ]", "", i)) * 1000)
while len(default_gpu_mem) < len(total_mem):
    default_gpu_mem.append(0)

default_gpu_memories = {}
for i in range(len(total_mem)):
    default_gpu_memories[f"gpu_memory_{i}"] = default_gpu_mem[i]

if shared.args.cpu_memory is not None:
    default_cpu_mem = re.sub("[a-zA-Z ]", "", shared.args.cpu_memory)
else:
    default_cpu_mem = 0

shared.persistent_interface_state.update({
    "max_new_tokens": shared.settings["max_new_tokens"],
    "seed": shared.settings["seed"],
    "temperature": generate_model_params["temperature"],
    "top_p": generate_model_params["top_p"],
    "top_k": generate_model_params["top_k"],
    "typical_p": generate_model_params["typical_p"],
    "epsilon_cutoff": generate_model_params["epsilon_cutoff"],
    "eta_cutoff": generate_model_params["eta_cutoff"],
    "repetition_penalty": generate_model_params["repetition_penalty"],
    "encoder_repetition_penalty": generate_model_params["encoder_repetition_penalty"],
    "no_repeat_ngram_size": generate_model_params["no_repeat_ngram_size"],
    "min_length": generate_model_params["min_length"],
    "do_sample": generate_model_params["do_sample"],
    "penalty_alpha": generate_model_params["penalty_alpha"],
    "num_beams": generate_model_params["num_beams"],
    "length_penalty": generate_model_params["length_penalty"],
    "early_stopping": generate_model_params["early_stopping"],
    "mirostat_mode": generate_model_params["mirostat_mode"],
    "mirostat_tau": generate_model_params["mirostat_tau"],
    "mirostat_eta": generate_model_params["mirostat_eta"],
    "add_bos_token": shared.settings["add_bos_token"],
    "ban_eos_token": shared.settings["ban_eos_token"],
    "truncation_length": shared.settings["truncation_length"],
    "custom_stopping_strings": shared.settings["custom_stopping_strings"],
    "skip_special_tokens": shared.settings["skip_special_tokens"],
    "preset_menu": preset_menu,
    "stream": not shared.args.no_stream,
    "name1": name1,
    "name2": name2,
    "greeting": greeting,
    "context": context,
    "chat_prompt_size": shared.settings["chat_prompt_size"],
    "chat_generation_attempts": shared.settings["chat_generation_attempts"],
    "stop_at_newline": shared.settings["stop_at_newline"],
    "mode": shared.settings["mode"],
    "instruction_template": shared.settings["instruction_template"],
    "character_menu": shared.args.character or shared.settings["character"],
    "name1_instruct": name1_instruct,
    "name2_instruct": name2_instruct,
    "context_instruct": context_instruct,
    "turn_template": turn_template,
    "chat_style": shared.settings["chat_style"],
    "chat-instruct_command": shared.settings["chat-instruct_command"],
    "cpu_memory": default_cpu_mem,
    "auto_devices": shared.args.auto_devices,
    "disk": shared.args.disk,
    "cpu": shared.args.cpu,
    "bf16": shared.args.bf16,
    "load_in_8bit": shared.args.load_in_8bit,
    "load_in_4bit": shared.args.load_in_4bit,
    "compute_dtype": shared.args.compute_dtype,
    "quant_type": shared.args.quant_type,
    "use_double_quant": shared.args.use_double_quant,
    "wbits": shared.args.wbits if shared.args.wbits > 0 else "None",
    "groupsize": shared.args.groupsize if shared.args.groupsize > 0 else "None",
    "model_type": shared.args.model_type or "None",
    "pre_layer": shared.args.pre_layer[0] if shared.args.pre_layer is not None else 0,
    "threads": shared.args.threads,
    "n_batch": shared.args.n_batch,
    "no_mmap": shared.args.no_mmap,
    "mlock": shared.args.mlock,
    "n_gpu_layers": shared.args.n_gpu_layers,
    "n_ctx": shared.args.n_ctx,
    "llama_cpp_seed": shared.args.llama_cpp_seed,
    **default_gpu_memories
})

shared.generation_lock = Lock()

# Loading the bot
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=".", intents=intents)

queues = []
blocking = False
reply_count = 0

async def llm_gen(ctx, queues):
    global blocking
    global reply_count

    if len(queues) > 0:
        blocking = True
        reply_count += 1
        user_input = queues.pop(0)
        mention = list(user_input.keys())[0]
        user_input = user_input[mention]
        
        # Prevents the embed character limit error
        embed_user_input_text = user_input["text"]
        if len(user_input["text"]) > 1024:
            embed_user_input_text = user_input["text"][:1021] + "..."
        
        reply_embed.set_field_at(index=0, name=user_input["state"]["name1"], value=embed_user_input_text, inline=False)
        reply_embed.title = "Reply #" + str(reply_count)
        reply_embed.timestamp = datetime.now() - timedelta(hours=3)
        reply_embed.set_field_at(index=1, name=user_input["state"]["name2"], value=":arrows_counterclockwise:", inline=False)
        
        msg = await ctx.send(embed=reply_embed)
        fin_resp = None
        last_resp = ""
        for resp in generate_chat_reply(history=shared.history, **user_input):
            fin_resp = resp
            resp_clean = resp["visible"][len(resp["visible"])-1][1]
            last_resp = resp_clean
            msg_to_user = last_resp + ":arrows_counterclockwise:"
            
            # Prevents the embed character limit error
            if len(msg_to_user) > 1024:
                last_resp = last_resp[:1024]
                break
            
            reply_embed.set_field_at(index=1, name=user_input["state"]["name2"], value=msg_to_user, inline=False)
            await msg.edit(embed=reply_embed)
        
        logger.info("reply sent: \"" + mention + ": {'text': '" + user_input["text"] + "', 'response': '" + last_resp + "'}\"")
        reply_embed.set_field_at(index=1, name=user_input["state"]["name2"], value=last_resp, inline=False)
        await msg.edit(embed=reply_embed)
        
        shared.history = copy.deepcopy(fin_resp)
        if bot_args.limit_history is not None and len(shared.history["visible"]) > bot_args.limit_history:
            shared.history["visible"].pop(0)
            shared.history["internal"].pop(0)
        
        await llm_gen(ctx, queues)
    else:
        blocking = False

@client.event
async def on_ready():
    logger.info("bot ready")
    await client.tree.sync()

@client.hybrid_command(description="Reply to LLaMA")
@app_commands.describe(text="Your reply")
async def reply(ctx, text, max_new_tokens=None, seed=None, temperature=None, top_p=None, top_k=None, typical_p=None, repetition_penalty=None, encoder_repetition_penalty=None, no_repeat_ngram_size=None, do_sample=None, penalty_alpha=None, num_beams=None, length_penalty=None, add_bos_token=None, custom_stopping_strings=None, name1=None, name2=None, context=None, turn_template=None, chat_generation_attempts=None, stop_at_newline=None, mode=None, regenerate=False, _continue=False):
    persistant_interface_state_copy = shared.persistent_interface_state.copy()
    
    local_args = locals()
    for key, value in local_args.items():
        if value != None and key not in ['ctx', 'text', 'regenerate', '_continue', 'persistant_interface_state_copy']:
            persistant_interface_state_copy[key] = value
    
    # Not all parameters can be given as arguments. The Discord API has a limit of 25 arguments.
    user_input = {
        "text": text,
        "state": persistant_interface_state_copy,
        "regenerate": regenerate,
        "_continue": _continue
    }

    num = check_num_in_que(ctx)
    if num >=10:
        await ctx.send(f"{ctx.message.author.mention} You have 10 items in queue, please allow your requests to finish before adding more to the queue.")
    else:
        que(ctx, user_input)
        reaction_list = [":thumbsup:", ":laughing:", ":wink:", ":heart:", ":pray:", ":100:", ":sloth:", ":snake:"]
        reaction_choice = reaction_list[random.randrange(8)]
        await ctx.send(f"{ctx.message.author.mention} {reaction_choice} Processing reply...")
        if not blocking:
            await llm_gen(ctx, queues)

@client.hybrid_command(description="Reset the conversation with LLaMA")
@app_commands.describe(
    prompt="The initial prompt to contextualize LLaMA",
    your_name="The name which all users speak as",
    llamas_name="The name which LLaMA speaks as"
)
async def reset(ctx, prompt=shared.settings["context"], your_name=shared.settings["name1"], llamas_name=shared.settings["name2"]):
    global reply_count
    reply_count = 0
    
    shared.stop_everything = True
    clear_chat_log("", shared.settings["mode"])
    shared.settings["name1"] = your_name
    shared.settings["name2"] = llamas_name
    shared.settings["context"] = prompt
    shared.persistent_interface_state["name1"] = your_name
    shared.persistent_interface_state["name2"] = llamas_name
    shared.persistent_interface_state["context"] = prompt
    
    name1_instruct, name2_instruct, _, _, context_instruct, turn_template = load_character(shared.settings["instruction_template"], your_name, llamas_name, instruct=True)
    shared.persistent_interface_state["name1_instruct"] = name1_instruct
    shared.persistent_interface_state["name2_instruct"] = name2_instruct
    shared.persistent_interface_state["context_instruct"] = prompt + "\n\n"
    shared.persistent_interface_state["turn_template"] = turn_template
    
    logger.info("conversation reset: {'replies': " + str(reply_count) + ", 'your_name': '" + your_name + "', 'llamas_name': '" + llamas_name + "', 'prompt': '" + prompt + "'}")
    reset_embed.timestamp = datetime.now() - timedelta(hours=3)
    reset_embed.description = "Replies: " + str(reply_count) + "\nYour name: " + your_name + "\nLLaMA's name: " + llamas_name + "\nPrompt: " + prompt
    await ctx.send(embed=reset_embed)

@client.hybrid_command(description="Check the status of your reply queue position and wait time")
async def status(ctx):
    total_num_queued_jobs = len(queues)
    que_user_ids = [list(a.keys())[0] for a in queues]
    if ctx.message.author.mention in que_user_ids:
        user_position = que_user_ids.index(ctx.message.author.mention) + 1
        msg = f"{ctx.message.author.mention} Your job is currently {user_position} out of {total_num_queued_jobs} in the queue. Estimated time until response is ready: {user_position * 20/60} minutes."
    else:
        msg = f"{ctx.message.author.mention} doesn\'t have a job queued."

    status_embed.timestamp = datetime.now() - timedelta(hours=3)
    status_embed.description = msg
    await ctx.send(embed=status_embed)

def que(ctx, user_input):
    user_id = ctx.message.author.mention
    queues.append({user_id:user_input})
    logger.info(f"reply requested: '{user_id}: {user_input}'")

def check_num_in_que(ctx):
    user = ctx.message.author.mention
    user_list_in_que = [list(i.keys())[0] for i in queues]
    return user_list_in_que.count(user)

client.run(bot_args.token if bot_args.token else TOKEN)
