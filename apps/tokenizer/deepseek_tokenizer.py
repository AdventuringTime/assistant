from transformers import PreTrainedTokenizerFast

# 加载 DeepSeek 分词器
tokenizer = PreTrainedTokenizerFast(
    tokenizer_file="apps/tokenizer/tokenizer.json",
    trust_remote_code=True
)


def tokenize(text):
    """
    对文本进行分词，返回词元列表

    Parameters:
        text (str): 待分词的文本

    Returns:
        list: 词元列表
    """
    result = tokenizer.encode(text)
    return [tokenizer.decode([id]) for id in result]