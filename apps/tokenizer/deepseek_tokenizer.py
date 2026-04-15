from transformers import PreTrainedTokenizerFast

tokenizer = PreTrainedTokenizerFast(
    tokenizer_file="apps/tokenizer/tokenizer.json",
    trust_remote_code=True
)

def tokenize(text):
    result = tokenizer.encode(text)
    return [tokenizer.decode([id]) for id in result]
