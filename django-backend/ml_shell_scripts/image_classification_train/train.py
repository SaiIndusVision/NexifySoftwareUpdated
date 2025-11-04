import os
import json
import requests
import argparse
import pandas as pd
import lightning as L
from lightning.pytorch.loggers import CSVLogger

from create_augmentations import ImageModificationPipeline
from classification_model import LitClassification
from classification_registry import model_registry
from classification_datamodule import CustomDataModule
from data_transforms import get_classification_transforms
from model_callbacks import get_model_checkpoint_callback, PredictionVisualizer, ConfusionMatrixVisualizer, GraphPlotter, ROCPlotter

# TODO : Use the created augmentations/ currently unused.
# TODO : Write all the metrics in one text file.

def train(args):

    MODEL = args.model_name
    NUM_EPOCHS = args.epochs
    BATCH_SIZE = args.train_batch_size
    SAVE_DIR = args.results_save_dir

    #==================
    # Prepare Dataset
    #==================

    dataset_query_params = {
        "sku_id": args.sku_id,
        "version_id": args.version_id,
        "absolute_path": "true"
    }

    response = requests.get(args.fetch_dataset_url, params=dataset_query_params)
    if response.status_code == 200:
        json_obj = response.json()
        DATA_LIST = json_obj['data_list']
        DATA_CLASSES = json_obj['data_classes']
    else:
        print(f"Error: {response.status_code}, {response.text}")

    with open('./dataset.json', 'r') as file:
        json_obj = json.loads(file.read())

    # =================
    # Augmentations
    # =================
    
    augmentations_object = json.loads(args.augmentations)
    transforms = ImageModificationPipeline.build_pipeline_modifier(
        augmentations_object.get("augmentations")
    )
    transform = get_classification_transforms()
    
    # =================
    # Data Preparation
    # =================
    # Prepare data
    dm = CustomDataModule(
        data_list=DATA_LIST, 
        transform=transform,
        batch_size=BATCH_SIZE,
        classes=DATA_CLASSES
    )
    dm.setup()

    # =========
    # Logger
    # =========
    csv_logger = CSVLogger(os.path.join(SAVE_DIR,"log"), name=MODEL)

    # =======
    # Model
    # =======
    model = LitClassification(model=MODEL, classes=dm.classes, save_dir=SAVE_DIR)

    # ===========
    # Callbacks
    # ===========
    checkpoint_callback = get_model_checkpoint_callback(SAVE_DIR)

    # ==================
    # Initialize trainer
    # ==================
    trainer = L.Trainer(max_epochs=NUM_EPOCHS,
                        accelerator='auto',
                        logger=csv_logger,
                        callbacks=[checkpoint_callback,
                                PredictionVisualizer(val_dataloader=dm.val_dataloader(), save_dir=SAVE_DIR),
                                ConfusionMatrixVisualizer(val_dataloader=dm.val_dataloader(), save_dir=SAVE_DIR),
                                ROCPlotter(save_dir=SAVE_DIR),
                                GraphPlotter(save_dir=SAVE_DIR)
                                ])

    # Train 
    trainer.fit(model, dm)

    # Post Process CSV
    csv_path = csv_logger.log_dir + "/" + "metrics.csv"
    pd.read_csv(csv_path).groupby('epoch').mean().reset_index().to_csv(csv_path, index=False)

    # Infer validation set images & draw confusion matrix
    best_model_path = checkpoint_callback.best_model_path
    print(f"Best model path: {best_model_path}")

    best_model = LitClassification.load_from_checkpoint(best_model_path, model=MODEL, classes=dm.classes)
    trainer.validate(best_model, datamodule=dm)

    trainer.test(best_model, datamodule=dm)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The classification model training and dataset.")

    parser.add_argument("--model_name", type=str, required=True, help="Name of the model")

    parser.add_argument("--fetch_dataset_url", type=str, required=True, help="URL of the end point to fetch dataset.")
    parser.add_argument("--sku_id", type=int, required=True, help="SKU Id of the dataset to be trained.")
    parser.add_argument("--version_id", type=int, required=True, help="Version Id of the dataset to be trained.")
    parser.add_argument("--augmentations", type=str, help="Augmentations to be applied on images for training.")
    parser.add_argument("--results_save_dir", type=str, required=True, help="The directory path where results need to n")

    parser.add_argument("--train_batch_size", type=int, default=16, help="Training batch size")
    parser.add_argument("--max_epochs", type=int, required=True, help="Maximum number of epochs")

    args = parser.parse_args()
    train(args)
