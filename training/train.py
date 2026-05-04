"""
Tenacious-Bench SFT Training Script — Path A
Backbone: Qwen3 4B (unsloth/Qwen3-4B-bnb-4bit) | Framework: Unsloth + TRL SFTTrainer
Run on: Google Colab T4 (free tier, fp16) or RunPod 4090 (bf16)

DATA SPLIT NOTE (Gap 2 fix):
    This script now defaults to training_data/sft_train.jsonl and
    training_data/sft_eval.jsonl — files produced by the PROBE-LEVEL split
    in generate_full_training_data.py.  Using these files prevents the
    near-zero eval loss caused by semantic overlap when the eval set contains
    Magpie variants of the same seed tasks seen during training.

    DO NOT use preferences_train.jsonl / preferences_dev.jsonl as the
    train/eval split for new runs — those files share probe_ids across
    partitions and will produce misleadingly low eval loss.

Usage:
    python training/train.py \
        --output_dir ./training/output \
        --hub_repo mike-D83/tenacious-bench-sft-adapter-v0.1 \
        --push_to_hub

Requirements:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps xformers trl peft accelerate bitsandbytes
"""

import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

import torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig

# Unsloth requires CUDA — run this script on Google Colab T4, not locally.
# Install on Colab:
#   pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
#   pip install --no-deps xformers trl peft accelerate bitsandbytes
try:
    from unsloth import FastLanguageModel  # type: ignore[import-not-found]
except ImportError as _err:
    raise ImportError(
        "unsloth is not installed. This script must run on Google Colab T4 (free tier).\n"
        "Install: pip install 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'"
    ) from _err

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"training/training_run_seed42_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

SEED = 42
MODEL_NAME  = "unsloth/Qwen3-4B-bnb-4bit"   # Qwen3 4B via Unsloth hub (4-bit QLoRA)
MAX_SEQ_LEN = 2048
LORA_RANK    = 16
LORA_ALPHA   = 16
LORA_DROPOUT = 0          # Unsloth optimised for 0 dropout
TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Probe-level split files (Gap 2 fix — use these, not preferences_*.jsonl)
TRAIN_DATA_PATH = "training_data/sft_train.jsonl"
DEV_DATA_PATH   = "training_data/sft_eval.jsonl"
OUTPUT_DIR      = "training/output"

# ── Argument parsing ─────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Tenacious-Bench SFT training (Path A)")
    p.add_argument("--output_dir",      default=OUTPUT_DIR)
    p.add_argument("--train_data",      default=TRAIN_DATA_PATH)
    p.add_argument("--dev_data",        default=DEV_DATA_PATH)
    p.add_argument("--hub_repo",        default="mike-D83/tenacious-bench-sft-adapter-v0.1")
    p.add_argument("--push_to_hub",     action="store_true")
    # Epoch-based training (matches actual 441-step / 3-epoch run)
    p.add_argument("--num_epochs",      type=int,   default=3,
                   help="Number of full training epochs (default 3 = ~441 steps on 1,247 pairs)")
    p.add_argument("--lr",              type=float, default=2e-4)
    p.add_argument("--batch_size",      type=int,   default=2)
    p.add_argument("--grad_accum",      type=int,   default=4)
    p.add_argument("--max_seq_len",     type=int,   default=MAX_SEQ_LEN)
    p.add_argument("--seed",            type=int,   default=SEED)
    return p.parse_args()

# ── Model + LoRA loading ──────────────────────────────────────────────────────

def load_model_and_tokenizer(args):
    log.info("Loading %s with Unsloth 4-bit QLoRA (max_seq_len=%d)", MODEL_NAME, args.max_seq_len)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
        use_rslora=False,
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    log.info("Trainable params: %s / %s (%.2f%%)", f"{trainable:,}", f"{total:,}", 100 * trainable / total)

    return model, tokenizer

# ── Dataset loading ───────────────────────────────────────────────────────────

def read_jsonl(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def format_row(row: dict) -> dict:
    """Format a prompt/chosen pair as Qwen ChatML text."""
    system = row.get("system", "")
    prompt = row["prompt"]
    chosen = row["chosen"]

    if system:
        text = (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n{chosen}<|im_end|>"
        )
    else:
        text = (
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n{chosen}<|im_end|>"
        )
    return {"text": text}


def load_dataset_split(path: str) -> Dataset:
    log.info("Loading data from %s", path)
    rows = read_jsonl(path)
    formatted = [format_row(r) for r in rows]
    log.info("  %d examples loaded", len(formatted))
    return Dataset.from_list(formatted)

# ── Training ──────────────────────────────────────────────────────────────────

def train(args):
    log.info("=" * 60)
    log.info("Tenacious-Bench SFT Training — Path A")
    log.info("Model: %s | epochs=%d | LR=%s", MODEL_NAME, args.num_epochs, args.lr)
    log.info("Train data: %s", args.train_data)
    log.info("Eval  data: %s", args.dev_data)
    log.info("=" * 60)

    model, tokenizer = load_model_and_tokenizer(args)

    train_dataset = load_dataset_split(args.train_data)
    eval_dataset  = load_dataset_split(args.dev_data) if Path(args.dev_data).exists() else None

    if eval_dataset is None:
        log.warning(
            "Eval file not found: %s\n"
            "  Run training_data/generate_full_training_data.py first to create sft_eval.jsonl",
            args.dev_data,
        )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
        args=SFTConfig(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.num_epochs,      # epoch-based (was: max_steps=60)
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            eval_strategy="epoch" if eval_dataset else "no",
            save_strategy="epoch",
            save_total_limit=2,
            load_best_model_at_end=eval_dataset is not None,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            output_dir=args.output_dir,
            seed=args.seed,
            report_to="none",
            optim="adamw_8bit",
        ),
    )

    log.info("Starting training run...")
    result = trainer.train()

    log.info("Training complete.")
    log.info("Final train loss: %.4f", result.training_loss)
    log.info("Total steps: %d", result.global_step)
    log.info(
        "Training time: %.1fs (%.1f min)",
        result.metrics.get("train_runtime", 0),
        result.metrics.get("train_runtime", 0) / 60,
    )

    # Log best eval checkpoint for transparency
    if eval_dataset is not None:
        best_ckpt = getattr(trainer.state, "best_model_checkpoint", "unknown")
        best_metric = getattr(trainer.state, "best_metric", "?")
        log.info("Best eval checkpoint: %s  (eval_loss=%.4f)", best_ckpt, best_metric or 0)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    log.info("LoRA adapter saved to %s", args.output_dir)

    if args.push_to_hub:
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            log.warning("HF_TOKEN not set. Skipping hub push.")
        else:
            log.info("Pushing adapter to HuggingFace Hub: %s", args.hub_repo)
            model.push_to_hub(args.hub_repo, token=hf_token)
            tokenizer.push_to_hub(args.hub_repo, token=hf_token)
            log.info("Hub push complete.")

    return result

# ── Inference helper (for ablation scoring) ───────────────────────────────────

def generate_email(model, tokenizer, system_prompt: str, user_brief: str, max_new_tokens: int = 200) -> str:
    """Generate an email for a single prospect brief. Used by ablation scripts."""
    FastLanguageModel.for_inference(model)

    text = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_brief}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    decoded = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return decoded.strip()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    train(args)
