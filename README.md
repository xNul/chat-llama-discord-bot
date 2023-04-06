# ChatLLaMA Discord Bot

A Discord Bot for chatting with LLaMA. It's not as good as ChatGPT, but LLaMA and its derivatives are pretty impressive on their own. Use `/reply` to talk to LLaMA. To clear chat history with LLaMA or change the initial prompt, use `/reset`. Sometimes LLaMA will get stuck or you will want to change the initial prompt to something more interesting so `/reset` is well used.

<div align="center">
  <video src="https://user-images.githubusercontent.com/894305/223963813-18e58d3c-4f9b-479c-8cdb-a2ad0df935c3.mp4" width=400/>
</div>

# Setup

1. Get LLaMA setup and working with https://github.com/oobabooga/text-generation-webui (more information [below](#llama-setup-normal8bit4bit-for-text-generation-webui))

2. Install discord.py with `pip install discord`

3. Edit `bot.py` with your Discord bot's token

4. Place `bot.py` inside the root of the text-generation-webui directory

5. Run with your text-generation-webui command but change `server.py` to `bot.py`. For example,`python bot.py --model <LLaMA model>`

Note: For ease of use, `bot.py` supports all `server.py` model-related command line arguments.

# Example Transcript

```
Your name is James and you love having conversations. You write long sentences and write very eloquently. Your responses are many sentences long. You enjoy talking with people and engaging them in interesting topics. My name is Robert and I like to have conversations with you James.

Robert: Hi James, how are you doing today?
James:  Hello Robert, I am doing fine today.

Robert: I have heard you are an amazing person! I am so glad to finally meet you!
James:  You are so kind! I am happy to finally meet you too.

Robert: How is Sarah and the kids? Is the kid's new school turning out as good as you had hoped?
James:  Sarah is doing great, and our children are growing up so quickly! The new school is a lot better than I had expected.

Robert: Thank goodness! I remember in my day, we had 3 classrooms and only one chalkboard! Schools around here have really grown!
James:  I remember those days. I think the world is getting better and better. I like that!

Robert: Do you remember that time in astronomy when John saw a shooting star?! He cataloged it and it turned out to be a new comet! I saw a news story on it recently. Apparently, they're going to name it after him! They want to use his last name though, because his first name is too generic
James:  I remember that. I am happy for John. That is awesome news.

Robert: Quick question, what is the circumference of the Earth? It was a question on Lindsey's homework last night and for the life of me, I just can't remember the answer!
James:  Hmm, I do not know that answer. I will look it up.

Robert: Sounds good! What did you find?
James:  The circumference of the Earth is 24,901 miles.

Robert: Ahhh very good to know. These days, the world feels like it's getting smaller and smaller with the internet!
James:  Indeed! It is crazy to think about how the world has grown to be so small in recent years.
```

# LLaMA Setup (normal/8bit/4bit) for `text-generation-webui`

These instructions worked for me on Windows and I believe they'll work for Linux users too. I'm not sure if these instructions will work on WSL. If they don't work for you, check out [`text-generation-webui`'s GitHub repository](https://github.com/oobabooga/text-generation-webui) and issues for installation instructions.

### Normal & 8bit LLaMA Setup

1. Install Anaconda
2. **Windows only**: Install Git for Windows
3. Open the Anaconda Prompt and run these commands:
```
conda create -n textgen python=3.10.9 torchvision torchaudio pytorch-cuda=11.7 cuda-toolkit conda-forge::ninja conda-forge::git -c pytorch -c nvidia/label/cuda-11.7.0 -c nvidia
conda activate textgen
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui
pip install -r requirements.txt
```
4. **Windows only**: Follow the instructions [here](https://github.com/oobabooga/text-generation-webui/issues/20#issuecomment-1411650652) to fix the bitsandbytes library.
5. **Linux only**: Follow the instructions [here](https://github.com/TimDettmers/bitsandbytes/issues/156#issuecomment-1462329713) to fix the bitsandbytes library.

### 4bit LLaMA Setup

Run these commands:
```
mkdir repositories
cd repositories
git clone https://github.com/oobabooga/GPTQ-for-LLaMa.git -b cuda
cd GPTQ-for-LLaMa
pip install -r requirements.txt
python setup_cuda.py install
```

Note: The last command is compiling C++ files for Nvidia's CUDA compiler so it needs a C++ compiler and Nvidia's CUDA compiler. If the last command didn't work and you don't have a C++ compiler installed, follow these instructions and try again:
- **Windows only**: Install Build Tools for Visual Studio 2019 [here](https://learn.microsoft.com/en-us/visualstudio/releases/2019/history#release-dates-and-build-numbers), remember to checkmark "Desktop development with C++", and add the `cl` compiler to the environment.
- **Linux only**: Run the command `sudo apt install build-essential`.

### Downloading Normal & 8bit LLaMA Models

1. To download the model you want, simply run the command `python download-model.py decapoda-research/llama-Xb-hf` where `X` is the size of the model you want to download like `7` or `13`.
2. Once downloaded, you have to fix the outdated config of the model. Open `models/llama-Xb-hf/tokenizer_config.json` and change `LLaMATokenizer` to `LlamaTokenizer`.
3. If you only want to run a normal or 8bit model, you're done. If you want to run a 4bit model, continue onto the next section.

### Downloading 4bit LLaMA Models

Running a 4bit model requires an entirely different type of model and therefore a separate download. Find their downloads [here](https://github.com/oobabooga/text-generation-webui/wiki/LLaMA-model#step-2-get-the-pre-converted-weights). If you want the 4bit 7b model, download from the converted *without* group-size torrent. Otherwise, download from the converted *with* group-size torrent. Download the folder corresponding to the model you want and place it in your `models` folder.

### Running the LLaMA Models with text-generation-webui

##### Normal LLaMA Model
`python server.py --model llama-Xb-hf`

##### 8bit LLaMA Model
`python server.py --model llama-Xb-hf --load-in-8bit`

##### 4bit LLaMA Model without group-size
`python server.py --model llama-Xb-4bit --wbits 4`

##### 4bit LLaMA Model with group-size
`python server.py --model llama-Xb-4bit-128g --wbits 4 --groupsize 128`

Note: To run with ChatLLaMA, follow steps 2-4 [above](#setup) and for the command, replace `server.py` with `bot.py`.
