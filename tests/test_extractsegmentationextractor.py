import tempfile
from shutil import rmtree

import h5py
import numpy as np
from hdmf.testing import TestCase
from lazy_ops import DatasetView
from numpy.testing import assert_array_equal
from parameterized import parameterized, param

from roiextractors import (
    ExtractSegmentationExtractor,
    NewExtractSegmentationExtractor,
    LegacyExtractSegmentationExtractor,
)

from .setup_paths import OPHYS_DATA_PATH


class TestExtractSegmentationExtractor(TestCase):
    ophys_data_path = OPHYS_DATA_PATH / "segmentation_datasets" / "extract"

    @classmethod
    def setUpClass(cls):
        cls.sampling_frequency = 30.0
        cls.ophys_data_path = OPHYS_DATA_PATH / "segmentation_datasets" / "extract"

    def test_extract_segmentation_extractor_file_path_does_not_exist(self):
        """Test that the extractor raises an error if the file does not exist."""
        not_a_mat_file_path = "not_a_mat_file.txt"
        with self.assertRaisesWith(AssertionError, f"File {not_a_mat_file_path} does not exist."):
            ExtractSegmentationExtractor(
                file_path=not_a_mat_file_path,
                sampling_frequency=self.sampling_frequency,
            )

    def test_extract_segmentation_extractor_file_path_is_not_a_mat_file(self):
        """Test that the extractor raises an error if the file is not a .mat file."""
        not_a_mat_file_path = OPHYS_DATA_PATH / "segmentation_datasets" / "nwb" / "nwb_test.nwb"
        with self.assertRaisesWith(AssertionError, f"File {not_a_mat_file_path} must be a .mat file."):
            ExtractSegmentationExtractor(
                file_path=not_a_mat_file_path,
                sampling_frequency=self.sampling_frequency,
            )

    def test_extract_segmentation_extractor_with_default_output_struct_name(self):
        """Test that the extractor returns the NewExtractSegmentationExtractor
        when the default "output" struct name is used."""
        extractor = ExtractSegmentationExtractor(
            file_path=self.ophys_data_path / "extract_public_output.mat",
            sampling_frequency=self.sampling_frequency,
        )

        self.assertIsInstance(extractor, NewExtractSegmentationExtractor)

    param_list = [
        param(
            file_path=ophys_data_path / "2014_04_01_p203_m19_check01_extractAnalysis.mat",
            output_struct_name="extractAnalysisOutput",
            extractor_class=LegacyExtractSegmentationExtractor,
        ),
        param(
            file_path=ophys_data_path / "extract_public_output.mat",
            output_struct_name="output",
            extractor_class=NewExtractSegmentationExtractor,
        ),
    ]

    @parameterized.expand(
        param_list,
    )
    def test_extract_segmentation_extractor_redirects(self, file_path, output_struct_name, extractor_class):
        """
        Test that the extractor class redirects to the correct class
        given the version of the .mat file.
        """
        extractor = ExtractSegmentationExtractor(
            file_path=file_path,
            output_struct_name=output_struct_name,
            sampling_frequency=self.sampling_frequency,
        )

        self.assertIsInstance(extractor, extractor_class)


class TestNewExtractSegmentationExtractor(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file_path = OPHYS_DATA_PATH / "segmentation_datasets" / "extract" / "extract_public_output.mat"
        cls.output_struct_name = "output"
        cls.sampling_frequency = 30.0

        cls.test_config_path = tempfile.mkdtemp()

    def setUp(self):
        self.extractor = NewExtractSegmentationExtractor(
            file_path=self.file_path,
            output_struct_name=self.output_struct_name,
            sampling_frequency=self.sampling_frequency,
        )

    def tearDown(self):
        self.extractor.close()

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.test_config_path)

    def test_extractor_output_struct_assertion(self):
        """Test that the extractor raises an error if the output struct name is not in the file."""
        with self.assertRaisesWith(AssertionError, "Output struct not found in file."):
            NewExtractSegmentationExtractor(
                file_path=self.file_path,
                output_struct_name="not_output",
                sampling_frequency=self.sampling_frequency,
            )

    def test_extractor_no_timestamps_or_sampling_frequency(self):
        """Test that the extractor raises an error if neither timestamps
        nor sampling frequency are provided."""
        with self.assertRaisesWith(exc_type=AssertionError, exc_msg=(
                "Either sampling_frequency or timestamps must be provided."
        )):
            NewExtractSegmentationExtractor(
                file_path=self.file_path,
            )

    def test_extractor_timestamps_and_sampling_frequency_provided(self):
        """Test that the extractor raises an error when both timestamps
        and sampling frequency are provided."""
        with self.assertRaisesWith(exc_type=AssertionError, exc_msg=(
                "Either sampling_frequency or timestamps must be provided, but not both."
        )):
            NewExtractSegmentationExtractor(
                file_path=self.file_path,
                timestamps=np.arange(0, 2000),
                sampling_frequency=self.sampling_frequency
            )

    def test_extractor_length_of_timestamps_does_not_match_number_of_frames(self):
        """Test that the extractor raises an error if the timestamps does not have the
        same length as the number of frames."""

        with self.assertRaisesWith(exc_type=AssertionError, exc_msg=(
                "The timestamps should have the same length of the number of frames!"
        )):
            NewExtractSegmentationExtractor(
                file_path=self.file_path,
                timestamps=[0, 1, 2, 3],
            )

    def test_extractor_timestamps_provided(self):
        timestamps = np.arange(0, 2000)
        self.extractor = NewExtractSegmentationExtractor(
            file_path=self.file_path,
            timestamps=timestamps,
        )

        assert_array_equal(self.extractor._times, timestamps)

    def test_extractor_data_validity(self):
        """Test that the extractor class returns the expected data."""

        with h5py.File(self.file_path, "r") as segmentation_file:
            spatial_weights = DatasetView(
                segmentation_file[self.output_struct_name]["spatial_weights"]
            ).lazy_transpose()
            self.assertEqual(self.extractor._image_masks.shape, spatial_weights.shape)

            temporal_weights = DatasetView(segmentation_file[self.output_struct_name]["temporal_weights"])
            self.assertEqual(self.extractor._roi_response_dff.shape, temporal_weights.shape)

            self.assertEqual(self.extractor._roi_response_raw, None)

            self.assertEqual(self.extractor._sampling_frequency, self.sampling_frequency)
            self.assertIsInstance(self.extractor.get_sampling_frequency(), float)

            assert_array_equal(self.extractor.get_image_size(), [50, 50])

            num_rois = temporal_weights.shape[0]
            self.assertEqual(self.extractor.get_num_rois(), num_rois)

            num_frames = temporal_weights.shape[1]
            self.assertEqual(self.extractor.get_num_frames(), num_frames)

            self.assertEqual(self.extractor.get_rejected_list(), [])
            self.assertEqual(self.extractor.get_accepted_list(), list(range(num_rois)))

    param_list = [
        param(accepted_list=[4, 6, 12, 18]),
        param(accepted_list=[]),
        param(accepted_list=list(range(20))),
    ]

    @parameterized.expand(
        param_list,
    )
    def test_extractor_accepted_list(self, accepted_list):
        """Test that the extractor class returns the list of accepted and rejected ROIs
        correctly given the list of non-zero ROIs."""
        dummy_image_mask = np.zeros((20, 50, 50))
        dummy_image_mask[accepted_list, ...] = 1

        self.extractor._image_masks = dummy_image_mask

        assert_array_equal(self.extractor.get_accepted_list(), accepted_list)
        assert_array_equal(
            self.extractor.get_rejected_list(),
            list(set(range(20)) - set(accepted_list)),
        )

    def test_extractor_read_from_dummy_file(self):
        """Test the extractor with a dummy file."""

        dummy_temporal_weights = np.zeros((10, 100))
        dummy_spatial_weights = np.zeros((10, 5, 5))
        with h5py.File(self.test_config_path + "/test_file.mat", "a") as output_struct:
            output = output_struct.create_group("output")
            output.create_dataset("temporal_weights", data=dummy_temporal_weights)
            output.create_dataset("spatial_weights", data=dummy_spatial_weights)
            config = output.create_group("config")
            config.create_dataset("preprocess", data=[0])
            thresholds = config.create_group("thresholds")
            config.create_dataset("S_corr_thresh", data=np.array([0.1]))
            config.create_dataset("max_iter", data=np.array([10.0]))
            thresholds.create_dataset("S_dup_corr_thresh", data=np.array([0.95]))
            thresholds.create_dataset("T_dup_corr_thresh", data=np.array([0.95]))

        self.extractor = NewExtractSegmentationExtractor(
            file_path=self.test_config_path + "/test_file.mat",
            sampling_frequency=self.sampling_frequency,
        )

        self.assertEqual(self.extractor.config["S_corr_thresh"], [0.1])
        self.assertEqual(self.extractor.config["max_iter"], [10.0])
        self.assertEqual(self.extractor.config["thresholds"]["S_dup_corr_thresh"], [0.95])
        self.assertEqual(self.extractor.config["thresholds"]["T_dup_corr_thresh"], [0.95])
        self.assertEqual(self.extractor.config["preprocess"], [0])
        self.assertEqual(self.extractor._roi_response_dff, None)
        assert_array_equal(self.extractor._roi_response_raw, dummy_temporal_weights)
        assert_array_equal(self.extractor._image_masks, dummy_spatial_weights.T)
