# Project Overview

The goal of this project/repository is to summarize **Covid-19 news** in a news article using T5-small transformer models. I have used pre-trained **T5-small transfomer** and fine tuned it on the data to summarize the news in an article.

# Data Source

You can get the data from [here](https://76.223.36.25/open-access/free-dataset-newsmessage-boardsblogs-about-coronavirus-4-month-data-52m-posts). I have used a subset of data to train,validate and test the model.

# Evaluation metrics

Following are the results obtained using finetuned biobert. Fine tuned Biobert achieved 2.5% better F1 score as compared to finetuned bert (base)

Precision: 83 %
Recall: 89.7 %
F1: 86.3 %
Accuracy: 98.3 %

# Web Application

[Here](https://huggingface.co/spaces/shubham555/BioBERT_NER_Disease_Identification) is the link to Web Application deployed on HuggingFace Space using gradio.
