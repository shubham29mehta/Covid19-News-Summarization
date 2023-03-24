# -*- coding: utf-8 -*-
"""Covid-19 News Summarization.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1sH_lAhDNzLrU40OmiH3hVdo9iP31YaeY

## Set Up
"""

# Checking out the GPU we have access to. This is output is from the google colab version. 
!nvidia-smi

from google.colab import drive
drive.mount('/content/drive')

! pwd

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/My Drive/Covid-19 Summarization/Data/

# Install transformers and PyTorch Lightning libraries

!pip install datasets transformers
!pip install pytorch-lightning
!pip install SentencePiece

import pandas as pd
import numpy as np
import seaborn as sns
import json
import os, glob
import math

from io import open
import unicodedata
import string
import re
import random

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
import pytorch_lightning as pl

from transformers import T5ForConditionalGeneration, AutoTokenizer
from transformers import get_linear_schedule_with_warmup, AdamW
from datasets import Dataset
import datasets

from sklearn.model_selection import train_test_split

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#set seed

def set_seeds(seed):
    """Set seeds for reproducibility."""
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    pl.seed_everything(seed) # multi-GPU

SEED = 42
# Set seeds for reproducibility
set_seeds(seed=SEED)

"""## Load Data"""

path = '/content/drive/My Drive/Covid-19 Summarization/Data'

dataset = []
target = []
count = 0

for filename in glob.glob(os.path.join(path, '*.json')):
    while count < 2:
        with open(filename, 'r') as f:
            lines = f.readlines()
        f.close()
  
        for line in lines:
            dataset.append(json.loads(line)['text'])
            target.append(json.loads(line)['title'])
        count +=1

#creating the dataframe
d = {'text': dataset, 'summary': target}
df = pd.DataFrame(d)

#save data as pickle file
df.to_pickle("./extracted_data.pkl")

#load data
df = pd.read_pickle("./extracted_data.pkl")

df.shape

#taking a subset of data
df = df[:30000]

df.head()

#checking for any null values
df.isnull().sum()

# Hugging face datasets
covid19_news_dataset = Dataset.from_pandas(df)
covid19_news_dataset

"""Now that we have a training corpus, one final thing to check is the distribution of words in the reviews and their titles. This is especially important for summarization tasks, where short reference summaries in the data can bias the model to only output one or two words in the generated summaries. The plots below show the word distributions, and we can see that thethere are few summaries with just 0-2 words:"""

# Commented out IPython magic to ensure Python compatibility.
import seaborn as sns
import matplotlib.pyplot as plt
# %matplotlib inline
text_word_count = []
summary_word_count = []

# populate the lists with sentence lengths
for text in covid19_news_dataset['text']:
      text_word_count.append(len(text.split()))

for summary in covid19_news_dataset['summary']:
      summary_word_count.append(len(summary.split()))

length_df = pd.DataFrame({'text':text_word_count, 'summary':summary_word_count})


fig, axs = plt.subplots(1, 2, figsize=(10, 5))

sns.histplot(data=length_df, x="text",bins = 50,ax= axs[0])
sns.histplot(data=length_df, x="summary",bins = 100,ax= axs[1])
axs[0].set_title('News text')
axs[1].set_title('News Summary')


plt.show()

"""To deal with this, we’ll filter out the examples with very short titles so that our model can produce more interesting summaries."""

covid19_news_dataset = covid19_news_dataset.filter(lambda x: len(x["summary"].split()) > 2)

#convert to pandas to apply preprocessing
covid19_news_dataset_df = Dataset.to_pandas(covid19_news_dataset)

"""## Preprocess data"""

contraction_mapping = {"ain't": "is not", "aren't": "are not","can't": "cannot", "'cause": "because", "could've": "could have", "couldn't": "could not",

                           "didn't": "did not", "doesn't": "does not", "don't": "do not", "hadn't": "had not", "hasn't": "has not", "haven't": "have not",

                           "he'd": "he would","he'll": "he will", "he's": "he is", "how'd": "how did", "how'd'y": "how do you", "how'll": "how will", "how's": "how is",

                           "I'd": "I would", "I'd've": "I would have", "I'll": "I will", "I'll've": "I will have","I'm": "I am", "I've": "I have", "i'd": "i would",

                           "i'd've": "i would have", "i'll": "i will",  "i'll've": "i will have","i'm": "i am", "i've": "i have", "isn't": "is not", "it'd": "it would",

                           "it'd've": "it would have", "it'll": "it will", "it'll've": "it will have","it's": "it is", "let's": "let us", "ma'am": "madam",

                           "mayn't": "may not", "might've": "might have","mightn't": "might not","mightn't've": "might not have", "must've": "must have",

                           "mustn't": "must not", "mustn't've": "must not have", "needn't": "need not", "needn't've": "need not have","o'clock": "of the clock",

                           "oughtn't": "ought not", "oughtn't've": "ought not have", "shan't": "shall not", "sha'n't": "shall not", "shan't've": "shall not have",

                           "she'd": "she would", "she'd've": "she would have", "she'll": "she will", "she'll've": "she will have", "she's": "she is",

                           "should've": "should have", "shouldn't": "should not", "shouldn't've": "should not have", "so've": "so have","so's": "so as",

                           "this's": "this is","that'd": "that would", "that'd've": "that would have", "that's": "that is", "there'd": "there would",

                           "there'd've": "there would have", "there's": "there is", "here's": "here is","they'd": "they would", "they'd've": "they would have",

                           "they'll": "they will", "they'll've": "they will have", "they're": "they are", "they've": "they have", "to've": "to have",

                           "wasn't": "was not", "we'd": "we would", "we'd've": "we would have", "we'll": "we will", "we'll've": "we will have", "we're": "we are",

                           "we've": "we have", "weren't": "were not", "what'll": "what will", "what'll've": "what will have", "what're": "what are",

                           "what's": "what is", "what've": "what have", "when's": "when is", "when've": "when have", "where'd": "where did", "where's": "where is",

                           "where've": "where have", "who'll": "who will", "who'll've": "who will have", "who's": "who is", "who've": "who have",

                           "why's": "why is", "why've": "why have", "will've": "will have", "won't": "will not", "won't've": "will not have",

                           "would've": "would have", "wouldn't": "would not", "wouldn't've": "would not have", "y'all": "you all",

                           "y'all'd": "you all would","y'all'd've": "you all would have","y'all're": "you all are","y'all've": "you all have",

                           "you'd": "you would", "you'd've": "you would have", "you'll": "you will", "you'll've": "you will have",

                           "you're": "you are", "you've": "you have"}

def preprocess(text):
    text = text.lower() # lowercase
    text = text.split() # split the text into list on whitespace

    #applying contradiction mapping
    for i in range(len(text)):
        word = text[i]
        if word in contraction_mapping:
            text[i] = contraction_mapping[word]
    text = " ".join(text)

    text = text.replace("'s",'') # convert your's -> your
    # Remove words in parenthesis
    text = re.sub(r"\([^)]*\)", "", text)

    # Spacing and filters
    text = re.sub(r"([-;;.,!?<=>])", r" \1 ", text)
    text = re.sub("[^A-Za-z0-9]+", " ", text) # remove non alphanumeric chars
    text = re.sub(" +", " ", text)  # remove multiple spaces
    text = text.strip() #removes leading and trailing spaces
    return text

# Apply to dataframe
preprocessed_df = covid19_news_dataset_df.copy()
preprocessed_df.text = preprocessed_df.text.apply(preprocess)
preprocessed_df.summary = preprocessed_df.summary.apply(preprocess)

print (f"{covid19_news_dataset_df.text.values[1]}\n\n{preprocessed_df.text.values[1]}\n")
print (f"{covid19_news_dataset_df.summary.values[1]}\n\n{preprocessed_df.summary.values[1]}")

covid19_news_dataset = Dataset.from_pandas(preprocessed_df)

"""## Split Data"""

# 70% train, 30% test + validation
train_test_dataset = covid19_news_dataset.train_test_split(test_size=0.3,seed = 42)
# Split the 30% test + valid in half test, half valid
test_valid = train_test_dataset['test'].train_test_split(test_size=0.5,seed = 42)
# gather everyone if you want to have a single DatasetDict
train_test_valid_dataset = datasets.DatasetDict({
    'train': train_test_dataset['train'],
    'test': test_valid['test'],
    'valid': test_valid['train']})

covid19_news_dataset = train_test_valid_dataset

covid19_news_dataset

def show_samples(dataset, num_samples=5, seed=42):
    sample = dataset["train"].shuffle(seed=seed).select(range(num_samples))
    for example in sample:
        print(f"\n'>> Title: {example['summary']}'")
        print(f"'>> Review: {example['text']}'")


show_samples(covid19_news_dataset)

"""## Evaluation Metric: ROUGE"""

!pip install rouge_score

! pip install evaluate

rouge = datasets.load_metric('rouge')

"""## Baseline Model"""

!pip install nltk

import nltk

nltk.download("punkt")

from nltk.tokenize import sent_tokenize


def three_sentence_summary(text):
    return "\n".join(sent_tokenize(text)[:3])


print(three_sentence_summary(covid19_news_dataset["train"][1]["text"]))

def evaluate_baseline(dataset, metric):
    summaries = [three_sentence_summary(text) for text in dataset["text"]]
    return metric.compute(predictions=summaries, references=dataset["summary"])

import pandas as pd

score = evaluate_baseline(covid19_news_dataset["valid"], rouge)
rouge_names = ["rouge1", "rouge2", "rougeL", "rougeLsum"]
rouge_dict = dict((rn, round(score[rn].mid.fmeasure * 100, 2)) for rn in rouge_names)
rouge_dict

"""## Tokenizer and Model (T5-Small)"""

from transformers import AutoTokenizer

model_checkpoint = 't5-small'
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint)

inputs = tokenizer("I loved reading the Hunger Games!")
inputs

tokenizer.convert_ids_to_tokens(inputs.input_ids)

max_input_length = 512
max_target_length = 30


def preprocess_function(examples):
    model_inputs = tokenizer(
        examples["text"],
        max_length=max_input_length,
        truncation=True,
    )
    labels = tokenizer(
        examples["summary"], max_length=max_target_length, truncation=True
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_datasets = covid19_news_dataset.map(preprocess_function, batched=True)

tokenized_datasets

!pip install nltk

import nltk

nltk.download("punkt")

from nltk.tokenize import sent_tokenize


def three_sentence_summary(text):
    return "\n".join(sent_tokenize(text)[:3])


print(three_sentence_summary(covid19_news_dataset["train"][1]["text"]))

def evaluate_baseline(dataset, metric):
    summaries = [three_sentence_summary(text) for text in dataset["text"]]
    return metric.compute(predictions=summaries, references=dataset["summary"])

import pandas as pd

score = evaluate_baseline(covid19_news_dataset["valid"], rouge)
rouge_names = ["rouge1", "rouge2", "rougeL", "rougeLsum"]
rouge_dict = dict((rn, round(score[rn].mid.fmeasure * 100, 2)) for rn in rouge_names)
rouge_dict

from transformers import AutoModelForSeq2SeqLM

model = AutoModelForSeq2SeqLM.from_pretrained(model_checkpoint)

! pwd

from transformers import Seq2SeqTrainingArguments

batch_size = 8
num_train_epochs = 5
# Show the training loss with every epoch
logging_steps = len(tokenized_datasets["train"]) // batch_size
model_name = model_checkpoint.split("/")[-1]

args = Seq2SeqTrainingArguments(
    output_dir=f"{model_name}-finetuned",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=4,
    learning_rate=5.6e-5,
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    weight_decay=0.01,
    warmup_steps=500,
    num_train_epochs=num_train_epochs,
    predict_with_generate=True,
    logging_steps=logging_steps,
    load_best_model_at_end=True
)

import numpy as np

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    # Decode generated summaries into text
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    # Replace -100 in the labels as we can't decode them
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    # Decode reference summaries into text
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    # ROUGE expects a newline after each sentence
    decoded_preds = ["\n".join(sent_tokenize(pred.strip())) for pred in decoded_preds]
    decoded_labels = ["\n".join(sent_tokenize(label.strip())) for label in decoded_labels]
    # Compute ROUGE scores
    result = rouge.compute(
        predictions=decoded_preds, references=decoded_labels, use_stemmer=True
    )
    # Extract the median scores
    result = {key: value.mid.fmeasure * 100 for key, value in result.items()}
    return {k: round(v, 4) for k, v in result.items()}

from transformers import DataCollatorForSeq2Seq

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

tokenized_datasets

features = [tokenized_datasets["train"][i] for i in range(2)]

from transformers import Seq2SeqTrainer,EarlyStoppingCallback

trainer = Seq2SeqTrainer(
    model,
    args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["valid"],
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks = [EarlyStoppingCallback(early_stopping_patience = 3)]
)

trainer.train()

trainer.evaluate()

predictions,label_ids,metrics = trainer.predict(tokenized_datasets["test"])

predictions.shape,label_ids.shape

#evaluation on test set
metrics

"""## Inference"""

! pip install transformers

from transformers import pipeline

model_checkpoint = "./t5-small-finetuned/checkpoint-12575"
summarizer = pipeline("summarization", model=model_checkpoint)

def print_summary(idx):
    text = covid19_news_dataset["test"][idx]["text"]
    actual_summary = covid19_news_dataset["test"][idx]["summary"]
    predicted_summary = summarizer(covid19_news_dataset["test"][idx]["text"])[0]["summary_text"]
    print(f"'>>> News: {text}'")
    print(f"\n'>>> Actual Summary: {actual_summary}'")
    print(f"\n'>>> Predicted Summary: {predicted_summary}'")

print_summary(2)

"""## Gradio Web App"""

! pip install gradio

examples = covid19_news_dataset["test"]['text'][2]

examples = 'china central bank said it will inject 1 2 trillion yuan worth of liquidity into the markets via reverse repo operations on monday as the country prepares to reopen its stock markets amid a new coronavirus outbreak file photo a woman walks out of the headquarters of the people bank of china the central bank in beijing november 20 2013 reuters jason lee file photo 02 feb 2020 04 40pm share this content bookmark shanghai china central bank said it will inject 1 2 trillion yuan worth of liquidity into the markets via reverse repo operations on monday as the country prepares to reopen its stock markets amid a new coronavirus outbreak china authorities have pledged to use various monetary policy tools to ensure liquidity remains reasonably ample and to support firms affected by the virus epidemic which has so far claimed 305 lives all but one in china the people bank of china made the announcement in a statement published on its website on sunday adding the total liquidity in the banking system will be 900 billion yuan higher than the same period in 2019 after the injection according to reuters calculations based on official central bank data 1 05 trillion yuan worth of reverse repos are set to mature on monday meaning that 150 billion yuan in net cash will be injected investors are bracing for a volatile session in chinese markets when onshore trades resume on monday after a break for the lunar new year which was extended by the government china stock currency and bond markets have all been closed since jan 23 and had been due to re open last friday there will be no further delays to the reopening the country securities market regulator said in an interview published by the state backed people daily newspaper on sunday the china securities regulatory commission said it had taken the decision after balancing various factors and believed the outbreak impact on the market would be short term to support firms affected by the epidemic the csrc said companies that had expiring stock pledge agreements could apply for extensions with securities firms and it would urge corporate bond investors to extend the maturity dates of debt the csrc is also considering launching hedging tools for the a share market to help alleviate market panic and will suspend evening sessions of futures trading starting from monday it said we believe that the successive introduction and implementation of policy measures will play a better role in improving market expectations and preventing irrational behavior it told the people daily newspaper china is facing mounting isolation as other countries introduce travel curbs airlines suspend flights and governments evacuate their citizens risking worsening a slowdown in the world second largest economy on sunday the philippines reported the growing epidemic of a coronavirus has claimed its first fatality outside of china where new confirmed infections jumped by a daily record to top 14 000 cases source reuters'

import gradio as gr
title = 'Text Summarization'

def text_summarizer(text):
    summary = summarizer(text)[0]["summary_text"]
    return summary

demo = gr.Interface(fn = text_summarizer,
inputs = gr.Textbox(placeholder="Enter News here...",label = "News"),
outputs = gr.Textbox(label="Generated Summary"),
title = title,
examples=[examples],
allow_flagging = False)  


demo.launch()

text_summarizer('china central bank said it will inject 1 2 trillion yuan worth of liquidity into the markets via reverse repo operations on monday as the country prepares to reopen its stock markets amid a new coronavirus outbreak file photo a woman walks out of the headquarters of the people bank of china the central bank in beijing november 20 2013 reuters jason lee file photo 02 feb 2020 04 40pm share this content bookmark shanghai china central bank said it will inject 1 2 trillion yuan worth of liquidity into the markets via reverse repo operations on monday as the country prepares to reopen its stock markets amid a new coronavirus outbreak china authorities have pledged to use various monetary policy tools to ensure liquidity remains reasonably ample and to support firms affected by the virus epidemic which has so far claimed 305 lives all but one in china the people bank of china made the announcement in a statement published on its website on sunday adding the total liquidity in the banking system will be 900 billion yuan higher than the same period in 2019 after the injection according to reuters calculations based on official central bank data 1 05 trillion yuan worth of reverse repos are set to mature on monday meaning that 150 billion yuan in net cash will be injected investors are bracing for a volatile session in chinese markets when onshore trades resume on monday after a break for the lunar new year which was extended by the government china stock currency and bond markets have all been closed since jan 23 and had been due to re open last friday there will be no further delays to the reopening the country securities market regulator said in an interview published by the state backed people daily newspaper on sunday the china securities regulatory commission said it had taken the decision after balancing various factors and believed the outbreak impact on the market would be short term to support firms affected by the epidemic the csrc said companies that had expiring stock pledge agreements could apply for extensions with securities firms and it would urge corporate bond investors to extend the maturity dates of debt the csrc is also considering launching hedging tools for the a share market to help alleviate market panic and will suspend evening sessions of futures trading starting from monday it said we believe that the successive introduction and implementation of policy measures will play a better role in improving market expectations and preventing irrational behavior it told the people daily newspaper china is facing mounting isolation as other countries introduce travel curbs airlines suspend flights and governments evacuate their citizens risking worsening a slowdown in the world second largest economy on sunday the philippines reported the growing epidemic of a coronavirus has claimed its first fatality outside of china where new confirmed infections jumped by a daily record to top 14 000 cases source reuters')

"""## Push to Hub"""

! pip install huggingface_hub transformers

from transformers import AutoTokenizer,AutoModelForSeq2SeqLM

checkpoint = "./t5-small-finetuned/checkpoint-12575"
model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint)
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

type(model)

from huggingface_hub import notebook_login

notebook_login()

model.push_to_hub("covid19_news_summarization_finetuned")

tokenizer.push_to_hub("covid19_news_summarization_finetuned")