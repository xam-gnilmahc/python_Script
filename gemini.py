# Install necessary libraries
# !pip install datasets torch peft accelerate bitsandbytes trl

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from datasets import load_dataset
from peft import LoraConfig, PeftModel
from trl import SFTTrainer
from transformers import TrainingArguments
import bitsandbytes as bnb

# Configuration for 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load the tokenizer and model
device_map = {"": 0}
model_id = "google/gemma-2b"
tokenizer_id = "philschmid/gemma-tokenizer-chatml"

print('Loading tokenizer...')
tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)

print('Loading model...')
model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map=device_map)
model.config.use_cache = False
model.config.pretraining_tp = 1

# Load the dataset
dataset_name = "lucasmccabe-lmi/CodeAlpaca-20k"
dataset = load_dataset(dataset_name, split="train")

# Function to find all linear layer names
def find_all_linear_names(model):
    lora_module_names = set()
    for name, module in model.named_modules():
        if isinstance(module, bnb.nn.Linear4bit):
            names = name.split(".")
            lora_module_names.add(names[0] if len(names) == 1 else names[-1])

    if "lm_head" in lora_module_names:
        lora_module_names.remove("lm_head")
    return list(lora_module_names)

# Identify target modules for LoRA
target = find_all_linear_names(model)
print("Target modules for LoRA:", target)

# Load LoRA configuration
peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.05,
    r=64,
    bias="none",
    target_modules=target,
    task_type="CAUSAL_LM",
)

# Define training arguments
args = TrainingArguments(
    output_dir="gemma-2b-coder",  # directory to save model
    num_train_epochs=1,             # number of training epochs
    per_device_train_batch_size=1,  # batch size per device
    gradient_accumulation_steps=1,  # gradient accumulation steps
    gradient_checkpointing=True,     # use gradient checkpointing
    optim="adamw_torch_fused",      # optimizer
    logging_steps=100,               # log every 100 steps
    save_strategy="epoch",           # save checkpoint every epoch
    bf16=True,                       # use bfloat16 precision
    tf32=True,                       # use tf32 precision
    learning_rate=2e-4,              # learning rate
    max_grad_norm=0.3,              # max gradient norm
    warmup_ratio=0.03,               # warmup ratio
    lr_scheduler_type="constant",    # learning rate scheduler
    push_to_hub=False,               # do not push to hub
    report_to="tensorboard",         # report to tensorboard
)

# Initialize the trainer
max_seq_length = 1512  # max sequence length for packing
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_config,
    args=args,
    packing=False,
)

# Start training
with torch.no_grad():
    torch.cuda.empty_cache()
    trainer.train()

# Save the model
trainer.save_model()

# Test the model
pipe = pipeline(task="text-generation", model="gemma-2b-coder", tokenizer=tokenizer, max_length=200)
eos_token = tokenizer("<|im_end|>", add_special_tokens=False)["input_ids"][0]

def test_inference(prompt):
    prompt = pipe.tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True)
    outputs = pipe(prompt, max_new_tokens=100, do_sample=True, temperature=0.1, top_k=50, top_p=0.95, eos_token_id=eos_token)
    return outputs[0]['generated_text'][len(prompt):].strip()

# Example usage of the test function
example_prompt = "What is the best way to learn Python?"
output = test_inference(example_prompt)
print("Model output:", output)
