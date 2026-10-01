"""Test Suite for Acoupi BatDetect2 Model."""

from acoupi import data

from acoupi_batdetect2.model import BatDetect2, BatDetect2Model


def test_batdetect2(recording: data.Recording):
    assert BatDetect2Model is BatDetect2
    model = BatDetect2()
    detections = model.run(recording)

    assert isinstance(detections, data.ModelOutput)
    assert detections.name_model == "BatDetect2"
    assert len(detections.detections) == 51

    for det in detections.detections:
        assert type(det.detection_score) is float
        assert isinstance(det.location.coordinates, tuple)
        for coord in det.location.coordinates:
            assert type(coord) is float
        for tag in det.tags:
            assert type(tag.confidence_score) is float
            assert type(tag.tag.value) is str
