from pathlib import Path
from typing import Dict, Any
from collections.abc import Sequence

from pandas import DataFrame
from torchvision.transforms.v2 import Transform

from anomalib.data.datasets.base.image import AnomalibDataset
from anomalib.data.datamodules.base.image import AnomalibDataModule
from anomalib.data.utils import Split, TestSplitMode, ValSplitMode, DirType, LabelName


class CustomDataset(AnomalibDataset):
    def __init__(
        self,
        name: str,
        path_label_object: Dict[str, Any],
        normal_dir: str | Path | Sequence[str | Path] = None,
        augmentations: Transform | None = None,
        root: str | Path | None = None,
        abnormal_dir: str | Path | Sequence[str | Path] | None = None,
        normal_test_dir: str | Path | Sequence[str | Path] | None = None,
        mask_dir: str | Path | Sequence[str | Path] | None = None,
        split: str | Split | None = None,
        extensions: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(augmentations=augmentations)

        self._name = name
        self.split = split
        self.root = root
        self.normal_dir = normal_dir
        self.abnormal_dir = abnormal_dir
        self.normal_test_dir = normal_test_dir
        self.mask_dir = mask_dir
        self.extensions = extensions

        self.samples = make_folder_dataset(
            path_label_object=path_label_object,
            split=self.split,
        )

    @property
    def name(self) -> str:
        """Get dataset name.

        Returns:
            str: Name of the dataset
        """
        return self._name


def make_folder_dataset(
    path_label_object,
    split: str | Split | None = None,
) -> DataFrame:

    filenames = []
    labels = []

    for dict_elemet in path_label_object:
        filenames.append(dict_elemet["image"])
        if dict_elemet["label_id"] == 0:
            labels.append(DirType.NORMAL)
        else:
            labels.append(DirType.ABNORMAL)

    samples = DataFrame({"image_path": filenames, "label": labels})
    samples = samples.sort_values(by="image_path", ignore_index=True)

    # Create label index for normal (0) and abnormal (1) images.
    samples.loc[
        (samples.label == DirType.NORMAL) | (samples.label == DirType.NORMAL_TEST),
        "label_index",
    ] = LabelName.NORMAL
    samples.loc[(samples.label == DirType.ABNORMAL), "label_index"] = LabelName.ABNORMAL
    samples.label_index = samples.label_index.astype("Int64")

    samples["mask_path"] = ""

    # remove all the rows with temporal image samples that have already been assigned
    samples = samples.loc[
        (samples.label == DirType.NORMAL)
        | (samples.label == DirType.ABNORMAL)
        | (samples.label == DirType.NORMAL_TEST)
    ]

    # Ensure the pathlib objects are converted to str.
    # This is because torch dataloader doesn't like pathlib.
    samples = samples.astype({"image_path": "str"})

    # Create train/test split.
    # By default, all the normal samples are assigned as train.
    # and all the abnormal samples are test.
    samples.loc[(samples.label == DirType.NORMAL), "split"] = Split.TRAIN
    samples.loc[
        (samples.label == DirType.ABNORMAL) | (samples.label == DirType.NORMAL_TEST),
        "split",
    ] = Split.TEST

    # infer the task type
    samples.attrs["task"] = (
        "classification" if (samples["mask_path"] == "").all() else "segmentation"
    )

    # Get the data frame for the split.
    if split:
        samples = samples[samples.split == split]
        samples = samples.reset_index(drop=True)

    return samples


class Folder(AnomalibDataModule):
    def __init__(
        self,
        name: str,
        path_label_object: Dict[str, Any],
        normal_dir: str | Path | Sequence[str | Path] = None,
        root: str | Path | None = None,
        abnormal_dir: str | Path | Sequence[str | Path] | None = None,
        normal_test_dir: str | Path | Sequence[str | Path] | None = None,
        mask_dir: str | Path | Sequence[str | Path] | None = None,
        normal_split_ratio: float = 0.2,
        extensions: tuple[str] | None = None,
        train_batch_size: int = 32,
        eval_batch_size: int = 32,
        num_workers: int = 8,
        train_augmentations: Transform | None = None,
        val_augmentations: Transform | None = None,
        test_augmentations: Transform | None = None,
        augmentations: Transform | None = None,
        test_split_mode: TestSplitMode | str = TestSplitMode.FROM_DIR,
        test_split_ratio: float = 0.2,
        val_split_mode: ValSplitMode | str = ValSplitMode.FROM_TEST,
        val_split_ratio: float = 0.5,
        seed: int | None = None,
    ) -> None:
        self._name = name
        self.root = root
        self.path_label_object = path_label_object
        self.normal_dir = normal_dir
        self.abnormal_dir = abnormal_dir
        self.normal_test_dir = normal_test_dir
        self.mask_dir = mask_dir
        self.extensions = extensions
        test_split_mode = TestSplitMode(test_split_mode)
        val_split_mode = ValSplitMode(val_split_mode)
        super().__init__(
            train_batch_size=train_batch_size,
            eval_batch_size=eval_batch_size,
            num_workers=num_workers,
            train_augmentations=train_augmentations,
            val_augmentations=val_augmentations,
            test_augmentations=test_augmentations,
            augmentations=augmentations,
            test_split_mode=test_split_mode,
            test_split_ratio=test_split_ratio,
            val_split_mode=val_split_mode,
            val_split_ratio=val_split_ratio,
            seed=seed,
        )

        self.normal_split_ratio = normal_split_ratio

    def _setup(self, _stage: str | None = None) -> None:
        self.train_data = CustomDataset(
            name=self.name,
            split=Split.TRAIN,
            root=self.root,
            path_label_object=self.path_label_object,
            normal_dir=self.normal_dir,
            abnormal_dir=self.abnormal_dir,
            normal_test_dir=self.normal_test_dir,
            mask_dir=self.mask_dir,
            extensions=self.extensions,
        )

        self.test_data = CustomDataset(
            name=self.name,
            split=Split.TEST,
            root=self.root,
            path_label_object=self.path_label_object,
            normal_dir=self.normal_dir,
            abnormal_dir=self.abnormal_dir,
            normal_test_dir=self.normal_test_dir,
            mask_dir=self.mask_dir,
            extensions=self.extensions,
        )

    @property
    def name(self) -> str:
        """Get name of the datamodule.

        Returns:
            Name of the datamodule.
        """
        return self._name
