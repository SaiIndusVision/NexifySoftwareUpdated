from typing import Optional

import lightning as L
from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader


class CustomImageDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, index):
        img_path = self.image_paths[index]
        image = Image.open(img_path).convert("RGB")
        label = self.labels[index]

        if self.transform:
            image = self.transform(image)

        return image, label


class CustomDataModule(L.LightningDataModule):
    def __init__(
        self,
        data_list: list[dict],
        batch_size: int = 16,
        classes = list[str],
        transform: Optional[object] = None,
    ):
        super().__init__()
        self.batch_size = batch_size
        self.transfrom = transform

        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None
        self.classes = classes

        self.data_list = data_list
        self.prepare_data()

    def prepare_data(self):
        """
        Use this method to download or prepare data if needed.
        """
        self.split_data = {
            "train": {"image_paths": [], "labels": []},
            "valid": {"image_paths": [], "labels": []},
            "test": {"image_paths": [], "labels": []},
        }

        for item in self.data_list:
            self.split_data[item["category"]]["image_paths"].append(item["image_path"])
            self.split_data[item["category"]]["labels"].append(item["class"])

    def setup(self, stage: str = None):
        """
        Set up datasets for different stages: fit, test, predict.
        Avoids reloading unless necessary.
        """
        if self.transfrom is None:
            self.transfrom = transforms.Compose([transforms.ToTensor()])

        if stage == "fit" or stage is None:
            self.train_dataset = CustomImageDataset(
                self.split_data["train"]["image_paths"],
                self.split_data["train"]["labels"],
                transform=self.transfrom,
            )
            self.val_dataset = CustomImageDataset(
                self.split_data["valid"]["image_paths"],
                self.split_data["valid"]["labels"],
                transform=self.transfrom,
            )

        self.transfrom = transforms.Compose([transforms.ToTensor()])
        if stage == "test" or stage is None:
            self.test_dataset = CustomImageDataset(
                self.split_data["test"]["image_paths"],
                self.split_data["test"]["labels"],
                transform=self.transfrom,
            )

        if stage == "predict":
            pass

    def train_dataloader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size, shuffle=True)

    def val_dataloader(self):
        return DataLoader(self.val_dataset, batch_size=self.batch_size)

    def test_dataloader(self):
        return DataLoader(self.test_dataset, batch_size=self.batch_size)
