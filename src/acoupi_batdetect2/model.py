"""Acoupi detection and classification Models."""

import logging
from typing import TYPE_CHECKING, Optional

import numpy as np
from acoupi import data
from acoupi.components import types

try:
    from itertools import batched
except ImportError:
    from itertools import islice

    def batched(iterable, n):
        if n < 1:
            raise ValueError("n must be at least one")
        it = iter(iterable)
        while batch := tuple(islice(it, n)):
            yield batch

if TYPE_CHECKING:
    from batdetect2 import BatDetect2API

# Set the logging level of the numba library to WARNING for easier debugging
logging.getLogger("numba").setLevel(logging.WARNING)


class BatDetect2(types.Model):
    """BatDetect2 Model to analyse the audio recording.

    This model uses the BatDetect2 library to detect bat calls in audio
    recordings and classify them into one of the 18 UK bat species.

    Attributes
    ----------
    name : str
        The name of the model, by default "BatDetect2".
    """

    name: str = "BatDetect2"

    def __init__(self, detection_threshold: float = 0.001):
        """Initialise the BatDetect2 model."""
        self.detection_threshold = detection_threshold
        self._api = None

    @property
    def api(self) -> "BatDetect2API":
        self.load_api()
        return self._api

    def load_api(self):
        if self._api is not None:
            return

        try:
            from batdetect2 import BatDetect2API

            self._api = BatDetect2API.from_checkpoint()
        except (ImportError, AttributeError):
            from batdetect2 import api

            self._api = api

    def run(self, recording: data.Recording) -> data.ModelOutput:
        """Run the model on the recording.

        Parameters
        ----------
        recording : data.Recording
            The audio recording to process.

        Returns
        -------
        data.ModelOutput
            The model output containing the detections.
        """
        # Get the audio path of the recorded file
        audio_file_path = recording.path

        if not audio_file_path:
            return data.ModelOutput(
                name_model=self.name,
                recording=recording,
                detections=[],
            )

        import torch

        # Use modern batched API if available
        if hasattr(self.api, "inference_config") and hasattr(self.api, "model"):
            from batdetect2.core.arrays import adjust_width
            from batdetect2.inference.clips import get_clips_from_files

            clipping = self.api.inference_config.clipping
            clips = get_clips_from_files(
                [audio_file_path],
                duration=clipping.duration,
                overlap=clipping.overlap,
                max_empty=clipping.max_empty,
                discard_empty=clipping.discard_empty,
            )
            class_names = self.api.targets.class_names
            detections = []
            batch_size = self.api.inference_config.loader.batch_size

            for clip_batch in batched(clips, batch_size):
                spectrograms = [
                    self.api.generate_spectrogram(self.api.load_clip(clip))
                    for clip in clip_batch
                ]
                max_width = max(
                    spectrogram.shape[-1] for spectrogram in spectrograms
                )
                batch = torch.stack(
                    [
                        adjust_width(spectrogram, max_width)
                        for spectrogram in spectrograms
                    ]
                )
                with torch.inference_mode():
                    outputs = self.api.model.detector(batch)
                    clip_detections = self.api.postprocessor(
                        outputs,
                        detection_threshold=self.detection_threshold,
                    )

                for clip, detected_calls in zip(
                    clip_batch,
                    clip_detections,
                    strict=True,
                ):
                    transformed = self.api.output_transform.to_clip_detections(
                        detections=detected_calls,
                        clip=clip,
                    )
                    for det in transformed.detections:
                        top_index = int(np.argmax(det.class_scores))
                        score = float(det.class_scores[top_index])
                        coords = tuple(float(c) for c in det.geometry.coordinates)
                        detections.append(
                            data.Detection(
                                detection_score=score,
                                location=data.BoundingBox.from_coordinates(
                                    coords[0],
                                    coords[1],
                                    coords[2],
                                    coords[3],
                                ),
                                tags=[
                                    data.PredictedTag(
                                        tag=data.Tag(
                                            key="species",
                                            value=str(class_names[top_index]),
                                        ),
                                        confidence_score=score,
                                    ),
                                ],
                            )
                        )

            return data.ModelOutput(
                name_model=self.name,
                recording=recording,
                detections=detections,
            )

        # Fallback for legacy api module
        audio = self.api.load_audio(str(audio_file_path))  # type: ignore
        spec = self.api.generate_spectrogram(audio)  # type: ignore

        with torch.inference_mode():
            raw_detections, _ = self.api.process_spectrogram(spec)  # type: ignore

        detections = [
            data.Detection(
                detection_score=float(detection["det_prob"]),
                location=data.BoundingBox.from_coordinates(
                    float(detection["start_time"]),
                    float(detection["low_freq"]),
                    float(detection["end_time"]),
                    float(detection["high_freq"]),
                ),
                tags=[
                    data.PredictedTag(
                        tag=data.Tag(
                            key="species",
                            value=str(detection["class"]),
                        ),
                        confidence_score=float(detection["class_prob"]),
                    ),
                ],
            )
            for detection in raw_detections
        ]

        return data.ModelOutput(
            name_model=self.name,
            recording=recording,
            detections=detections,
        )


BatDetect2Model = BatDetect2

