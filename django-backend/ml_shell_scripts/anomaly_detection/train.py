import os
import json
import argparse
from datetime import datetime

os.environ["NUMEXPR_MAX_THREADS"] = "4"

import requests
from anomalib.models import Padim, Patchcore, ReverseDistillation
from anomalib.engine import Engine
from anomalib.callbacks import ModelCheckpoint

from custom_datamodule import Folder
from create_augmentations import ImageModificationPipeline

def train(args):

    # ==================
    # Prepare Dataset
    # ==================
    response = requests.get(args.fetch_dataset_url)
    if response.status_code == 200:
        path_label_object = response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")


    # =================
    # Augmentations
    # =================
    augmentations_object = json.loads(args.augmentations)
    transforms = ImageModificationPipeline.build_pipeline_modifier(augmentations_object)


    # =================
    # Data Preparation
    # =================
    datamodule = Folder(
        name=args.dataset_name,
        path_label_object=path_label_object,
        seed=args.seed,
        train_batch_size=args.train_batch_size,
        eval_batch_size=args.eval_batch_size,
        num_workers=args.num_workers,
        train_augmentations=transforms,
    )

    valid = [entry for entry in path_label_object if entry.get("label_id") is not None]
    print(f"Found {len(valid)} valid labeled entries.")

    if len(valid) < 3:
        raise ValueError(
            "Not enough labeled entries (min 3 recommended) for training."
        )

    datamodule.setup()


    # =========
    # Logger
    # =========
    # wandb_logger = AnomalibWandbLogger(project=args.project, name=args.run_name)


    # =========
    # Callbacks
    # =========
    # create weights directory if not exists
    results_save_dir = args.results_save_dir + '/weights'
    os.makedirs(results_save_dir, exist_ok=True)

    # create timestamp directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_save_dir = results_save_dir + f'./{timestamp}'
    os.makedirs(results_save_dir, exist_ok=True)

    checkpoint_callback = ModelCheckpoint(
        dirpath=results_save_dir,
        filename=f"{timestamp}_{args.model_name.lower()}",
    )


    # =======
    # Model
    # =======
    MODELS = {
        "padim":Padim,
        "patchcore":Patchcore,
        "reversedistillation":ReverseDistillation
    }
    model = MODELS.get(args.model_name.lower(), Padim)()


    # =========
    # Engine
    # =========
    engine = Engine(
        # logger=wandb_logger,
        max_epochs=args.max_epochs,
        accelerator="auto",
        devices=args.devices,
        callbacks=[checkpoint_callback]
    )


    # ====================================
    # Run training, validation, and test
    # ====================================
    engine.fit(model=model, datamodule=datamodule)
    engine.validate(model=model, datamodule=datamodule)
    engine.test(model=model, datamodule=datamodule)


    metrics_file_path = os.path.join(results_save_dir, f"{timestamp}_metrics_and_model_path.json")
    
    logged_metrics = model.trainer.logged_metrics
    result_metrics = dict()
    for k, v in logged_metrics.items():
        result_metrics[k] = v.item()

    with open(metrics_file_path, "w") as f:
        json.dump(result_metrics, f, indent=4)

    print(f"Metrics saved to: {metrics_file_path}")

    payload = {
        "job_id": "12354",
        "progress" : 100,
        "status":"Done"
    }

    response = requests.post(args.progress_api, json=payload)

    if response.status_code in {200, 201}:
        print("Progress sent successfully")
        return True
    else:
        print(f"Progress send failed. Status code: {response.status_code}, Response: {response.text}")
        return False
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anomalib Training Script with Folder Data")

    parser.add_argument("--sku_id", type=int, required=True, help="SKU Id of the dataset to be trained.")
    parser.add_argument("--version_id", type=str, required=True, help="Version Id of the dataset to be trained.")
    parser.add_argument("--augmentations", type=str, help="Augmentations to be applied on images for training.")
    parser.add_argument("--max_epochs", type=int, required=True, help="Maximum number of epochs")
    parser.add_argument("--fetch_dataset_url", type=str, required=True, help="URL of the end point to fetch dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--train_batch_size", type=int, default=16, help="Training batch size")
    parser.add_argument("--eval_batch_size", type=int, default=16, help="Evaluation batch size")
    parser.add_argument("--devices", type=int, default=1, help="Number of devices to use")
    parser.add_argument("--num_workers", type=int, default=2, help="Number of data loading workers")
    parser.add_argument("--model_name", type=str, required=True, help="Name of the model")

    parser.add_argument("--dataset_name", type=str, required=True, help="Name of the dataset")
    parser.add_argument("--results_save_dir", type=str, required=True, help="The directory path where results need to be saved.")
    parser.add_argument("--progress_api", type=str, required=True, help="End point url to update training status")

    args = parser.parse_args()
    train(args)


# Model specific input parameters

# Padim, PatchCore
# --num_workers = 0
# --max_epochs=1
