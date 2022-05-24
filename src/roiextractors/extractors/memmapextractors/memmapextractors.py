import os
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Dict

import numpy as np
from tqdm import tqdm

from ...imagingextractor import ImagingExtractor
from typing import Tuple, Dict

from ...extraction_tools import (
    PathType,
    DtypeType,
)


class MemmapImagingExtractor(ImagingExtractor):

    extractor_name = "MemmapImagingExtractor"

    def __init__(
        self,
        imaging_extractor: ImagingExtractor,
        save_path: PathType = None,
        verbose: bool = False,
    ):

        pass

    def get_frames(self, frame_idxs=None):
        if frame_idxs is None:
            frame_idxs = [frame for frame in range(self.get_num_frames())]
        return self._video.take(indices=frame_idxs, axis=self.frame_axis)

    def get_image_size(self):
        return (self._rows, self._columns)

    def get_num_frames(self):
        return self._num_frames

    def get_sampling_frequency(self):
        return self._sampling_frequency

    def get_channel_names(self):
        """List of  channels in the recoding.

        Returns
        -------
        channel_names: list
            List of strings of channel names
        """
        pass

    def get_num_channels(self):
        """Total number of active channels in the recording

        Returns
        -------
        no_of_channels: int
            integer count of number of channels
        """
        return self._num_channels

    @staticmethod
    def write_imaging(imaging_extractor: ImagingExtractor, save_path: PathType = None, verbose: bool = False):
        """
        Static method to write imaging.

        Parameters
        ----------
        imaging: ImagingExtractor object
            The EXTRACT segmentation object from which an EXTRACT native format
            file has to be generated.
        save_path: str
            path to save the native format.
        overwrite: bool
            If True and save_path is existing, it is overwritten
        """
        imaging = imaging_extractor
        video_to_save = np.memmap(
            save_path,
            shape=(
                imaging.get_num_frames(),
                imaging.get_num_channels(),
                imaging.get_image_size()[0],
                imaging.get_image_size()[1],
            ),
            dtype=imaging.get_dtype(),
            mode="w+",
        )

        if verbose:
            for ch in range(imaging.get_num_channels()):
                print(f"Saving channel {ch}")
                for i in tqdm(range(imaging.get_num_frames())):
                    plane = imaging.get_frames(i, channel=ch)
                    video_to_save[ch, i] = plane
        else:
            for ch in range(imaging.get_num_channels()):
                for i in range(imaging.get_num_frames()):
                    plane = imaging.get_frames(i, channel=ch)
                    video_to_save[ch, i] = plane

        video_to_save.flush()
