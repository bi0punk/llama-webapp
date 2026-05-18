from app.model_profiles import describe_model, guess_family, parse_billions, parse_quant


def test_parse_billions():
    assert parse_billions("llama-2-7b-Q4_K_M.gguf") == 7.0
    assert parse_billions("Mistral-7B-v0.1.gguf") == 7.0
    assert parse_billions("tinyllama-1.1b.gguf") == 1.1
    assert parse_billions("test.gguf") is None


def test_parse_quant():
    assert parse_quant("model-Q4_K_M.gguf") == "Q4-M"
    assert parse_quant("model-q8_0.gguf") == "Q8"
    assert parse_quant("model.gguf") is None
    assert parse_quant("noquant") is None


def test_guess_family():
    assert guess_family("llama-2-7b.gguf") == "llama"
    assert guess_family("mistral-7b.gguf") == "mistral"
    assert guess_family("qwen-14b.gguf") == "qwen"
    assert guess_family("unknown-model.gguf") == "unknown"


def test_describe_model_no_size():
    profile = describe_model("llama-2-7b-Q4_K_M.gguf")
    assert profile["billions"] == 7.0
    assert profile["quant"] == "Q4-M"
    assert profile["family"] == "llama"
    assert profile["threads"] >= 1
    assert profile["ctx_size"] in (2048, 4096, 8192)
    assert "--parallel" in profile["extra_args"]
