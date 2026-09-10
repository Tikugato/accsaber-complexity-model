# Training

This folder stays empty until we train our own per-note accuracy model, and the PyTorch work for that lives here.

The one thing the rest of the repo needs from whatever gets built here is an ONNX file with the same shape as the pinned BeatLeader network. Input `input_1` of `[batch, 32, 49]`, output `time_distributed_2` of `[batch, 8, 1]`, both float32. The 49 numbers per note come out of `complexity_model/encoding.py`, and a new model can reuse that encoding directly or ship its own and swap the encoder alongside it. Drop the file into `models/`, point `COMPLEXITY_MODEL_FILE` at it, and the service serves it.

The maps to train on are the ranked pool, and the labels are our own players' scores, which the backend exports as CSV from `/v1/ranking/complexity/dataset/scores` with a ranking head token.
